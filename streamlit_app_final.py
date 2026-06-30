import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool
import base64
import os
import json
import html as _html
import contextlib
import datetime as _dt
from datetime import date, datetime, timedelta
from io import BytesIO
import hashlib
import secrets
import bcrypt
from typing import Optional
import google.generativeai as genai
import requests as _requests
from urllib.parse import urlencode
from PIL import Image
import io as _io_mod
import base64 as _b64mod

# ── Gemini helper ──────────────────────────────────────────────────────
def _get_gemini_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GOOGLE_API_KEY", "") or ""
        except Exception:
            key = ""
    return key

def _gemini(model_name: str = "gemini-2.0-flash"):
    key = _get_gemini_key()
    if not key:
        raise ValueError("GOOGLE_API_KEY não configurada")
    genai.configure(api_key=key)
    return genai.GenerativeModel(model_name)

# ── Barista Expert AI ──────────────────────────────────────────────────
def ask_barista_expert(pergunta: str, history: list | None = None) -> str:
    """Pergunta ao Barista Expert usando Gemini com knowledge base e histórico."""
    try:
        with open("coffee_knowledge.json", "r", encoding="utf-8") as f:
            kb = json.load(f)
        kb_text = json.dumps(kb, indent=2, ensure_ascii=False)
    except FileNotFoundError:
        kb_text = ""

    system_prompt = (
        "Você é um Barista Expert — especialista em café com 15+ anos de experiência.\n\n"
        + (f"Base de conhecimento:\n{kb_text}\n\n" if kb_text else "")
        + "Instruções:\n"
        "1. Responda em português brasileiro, prático e direto\n"
        "2. Dê dicas actionáveis que o usuário possa executar já\n"
        "3. Responda como um barista experiente explicando para outro barista."
    )

    chat_history = []
    if history:
        for m in history[-10:]:
            role = "user" if m["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [m["content"]]})

    genai.configure(api_key=_get_gemini_key())

    for _model_name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"):
        try:
            model_with_sys = genai.GenerativeModel(
                _model_name,
                system_instruction=system_prompt
            )
            chat = model_with_sys.start_chat(history=chat_history)
            resp = chat.send_message(pergunta)
            return resp.text
        except Exception as e:
            _err = str(e)
            if "429" in _err or "quota" in _err.lower() or "exhausted" in _err.lower():
                continue  # tenta próximo modelo
            return f"❌ Erro: {_err}"

    return (
        "⚠️ Cota da API Gemini esgotada em todos os modelos disponíveis. "
        "Ative o faturamento em aistudio.google.com para continuar usando o Barista Expert."
    )

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee Production",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_DIR = os.path.dirname(os.path.abspath(__file__))

# Fuso local — o servidor (Render) roda em UTC; sem isso a hora sai errada
from zoneinfo import ZoneInfo
_TZ = ZoneInfo("America/Sao_Paulo")

def _now_local():
    from datetime import datetime as _dtt
    return _dtt.now(_TZ).replace(tzinfo=None)

def _today_local():
    return _now_local().date()

def _load_mobile_css() -> None:
    css_path = os.path.join(_DIR, ".streamlit", "static", "mateu_coffee_mobile.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def _load_logo(max_width: int = 380) -> bool:
    """Renderiza o logo na tela de login usando o PNG oficial da marca.

    Preferência absoluta: assets/mateu_coffee_logo.png (a marca real).
    Fallback (apenas se o arquivo sumir): wordmark serifado.
    """
    try:
        b64 = _logo_b64()
        if b64:
            st.markdown(
                f'<div style="text-align:center;padding:1rem 0">'
                f'<img src="data:image/webp;base64,{b64}" alt="Mateu Coffee" '
                f'style="max-width:{max_width}px;width:100%;height:auto;'
                f'margin:0 auto;display:block">'
                f'</div>',
                unsafe_allow_html=True)
            return True
        st.markdown(_wordmark_html("hero", with_tag=True), unsafe_allow_html=True)
        return False
    except Exception:
        st.markdown(_wordmark_html("hero", with_tag=True), unsafe_allow_html=True)
        return False

def _show_daily_consumption() -> None:
    """Widget de consumo: xícaras hoje + semana + custo mensal + total."""
    hoje = _today_local()
    user_id = st.session_state.get('user_id')
    primeiro_dia_mes = hoje.replace(day=1)

    stats = _fetch("""
        SELECT
          COALESCE(COUNT(CASE WHEN data = %s THEN 1 END), 0)              AS hoje_n,
          COALESCE(SUM(CASE WHEN data = %s THEN gramas ELSE 0 END), 0)    AS hoje_g,
          COALESCE(COUNT(CASE WHEN data >= %s THEN 1 END), 0)             AS semana_n,
          COALESCE(SUM(CASE WHEN data >= %s THEN gramas ELSE 0 END), 0)   AS semana_g,
          COUNT(*)                                                         AS total_n,
          COALESCE(SUM(gramas), 0)                                         AS total_g
        FROM extracoes WHERE user_id = %s
    """, (hoje, hoje, hoje - timedelta(days=6), hoje - timedelta(days=6), user_id), _v=_v())

    cost_mes = _fetch("""
        SELECT c.valor_compra, c.tamanho_pacote, e.gramas
        FROM extracoes e JOIN coffees c ON c.id = e.coffee_id
        WHERE e.data >= %s AND e.user_id = %s AND c.valor_compra > 0 AND c.tamanho_pacote > 0
    """, (primeiro_dia_mes, user_id), _v=_v())

    s = stats[0] if stats else {"hoje_n": 0, "hoje_g": 0, "semana_n": 0, "semana_g": 0, "total_n": 0, "total_g": 0}
    custo_mes = sum(
        (r["valor_compra"] / r["tamanho_pacote"]) * r["gramas"]
        for r in cost_mes if r["valor_compra"] and r["tamanho_pacote"]
    )
    custo_str = f"R$ {custo_mes:.2f}" if custo_mes > 0 else "—"
    media_semana = (int(s["semana_n"]) / 7) if s["semana_n"] else 0
    hoje_n = int(s["hoje_n"])
    mes_nome = hoje.strftime("%b").capitalize()

    st.markdown(
        f'<div class="mc-consumo">'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Hoje</p>'
        f'    <p class="mc-consumo-value accent">{hoje_n}</p>'
        f'    <p class="mc-consumo-sub">{"xícara" if hoje_n == 1 else "xícaras"} · {s["hoje_g"]:.0f}g</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Esta Semana</p>'
        f'    <p class="mc-consumo-value">{int(s["semana_n"])}</p>'
        f'    <p class="mc-consumo-sub">{s["semana_g"]:.0f}g · {media_semana:.1f}/dia</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Gasto em {mes_nome}</p>'
        f'    <p class="mc-consumo-value" style="font-size:15px">{custo_str}</p>'
        f'    <p class="mc-consumo-sub">acumulado no mês</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Total Histórico</p>'
        f'    <p class="mc-consumo-value">{int(s["total_n"])}</p>'
        f'    <p class="mc-consumo-sub">{s["total_g"]:.0f}g consumidos</p>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _logo_b64() -> Optional[str]:
    """Lê o logo uma vez e cacheia indefinidamente (arquivo estático)."""
    # WebP otimizado (13KB) em vez do PNG original (346KB) — o base64 é
    # embutido no HTML 3x por página; isso era o gargalo no mobile.
    for fname in ("mateu_coffee_logo.webp", "mateu_coffee_logo_opt.png",
                  "mateu_coffee_logo.png"):
        logo_path = os.path.join(_DIR, "assets", fname)
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None

def _show_logo() -> None:
    # 🚀 BARISTA EXPERT LIVE - CACHE INVALIDATION v4
    b64 = _logo_b64()
    if b64:
        st.markdown(
            f'<div class="mc-hero-full">'
            f'<img src="data:image/webp;base64,{b64}" alt="Mateu Coffee">'
            f'<p class="mc-tagline">Para baristas e entusiastas,<br>para mim, e para você também</p>'
            f'</div>',
            unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="app-header">
          <div style="font-size:32px">☕</div>
          <div>
            <div class="app-header-title">Mateu Coffee Production</div>
            <div class="app-header-sub">Cadastro · Extração · Análise · Histórico</div>
          </div>
        </div>""", unsafe_allow_html=True)

_load_mobile_css()

# ── PWA Manifest (instalar como app no Android/iOS) ───────────────────
st.markdown("""
<link rel="manifest" href="data:application/json;charset=utf-8,%7B%22name%22%3A%22Mateu%20Coffee%22%2C%22short_name%22%3A%22Mateu%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%230A0A0A%22%2C%22theme_color%22%3A%22%23E8722E%22%2C%22orientation%22%3A%22portrait%22%7D">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Mateu Coffee">
<meta name="theme-color" content="#E8722E">
<style>
  /* Remove margens extras no mobile para parecer app nativo */
  @media (display-mode: standalone) {
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=DM+Serif+Display:ital@0;1&family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">
<style>
    /* ═══════════════════════════════════════════════════════════════
       MATEU COFFEE — DESIGN TOKENS
       Paleta extraída do logo oficial: gato + xícara em laranja vibrante
       sobre preto puro, com "COFFEE" em cinza quente.
       ═══════════════════════════════════════════════════════════════ */
    :root {
        --mc-bg: #0D0B09;
        --mc-surface: #161210;
        --mc-surface-2: #1E1A16;
        --mc-surface-3: #27211B;
        --mc-border: #2E2820;
        --mc-border-strong: #3E3630;

        --mc-orange: #D97732;
        --mc-orange-hover: #E8883A;
        --mc-orange-soft: #3D1F0D;
        --mc-orange-glow: rgba(217, 119, 50, 0.16);

        --mc-text: #F2EBE0;
        --mc-text-2: #B4ACA4;
        --mc-text-3: #8A8278;
        --mc-text-muted: #6C6660;

        --mc-success: #4CAF6F;
        --mc-error: #E55A4C;
        --mc-warning: #E8A23E;
        --mc-info: #5BB0E8;
    }

    /* ─── Light Mode — classe aplicada pelo toggle ────────────────── */
    .mc-light {
        --mc-bg: #FAF7F4;
        --mc-surface: #FFFFFF;
        --mc-surface-2: #F2EDE8;
        --mc-surface-3: #EAE4DE;
        --mc-border: #E0D8D0;
        --mc-border-strong: #C8BEB4;
        --mc-orange: #C8541A;
        --mc-orange-hover: #D96420;
        --mc-orange-soft: #FDE8D8;
        --mc-orange-glow: rgba(200, 84, 26, 0.14);
        --mc-text: #1A1208;
        --mc-text-2: #4A3C30;
        --mc-text-3: #7A6A5A;
        --mc-text-muted: #A89880;
        --mc-success: #2E7D4A;
        --mc-error: #C0392B;
        --mc-warning: #C07000;
        --mc-info: #1A6EA8;
    }
    .mc-light .stApp { background-color: var(--mc-bg) !important; color: var(--mc-text) !important; }
    .mc-light [data-testid="stSidebar"] { background-color: var(--mc-surface) !important; }
    .mc-light [data-testid="stHeader"]  { background-color: var(--mc-bg) !important; }

    /* ─── Tipografia base ─────────────────────────────────────────── */
    html, body, [class*="css"], .stApp, div, p, span, label,
    h1, h2, h3, h4, h5, h6, button, input, textarea, select {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    .mc-serif, .mc-serif * {
        font-family: 'DM Serif Display', 'Cormorant Garamond', Georgia, serif !important;
    }

    .stApp { background-color: var(--mc-bg); color: var(--mc-text); }
    .block-container {
        padding: 2rem 2.5rem 3rem !important;
        max-width: 1280px;
    }

    /* ─── Hierarquia de títulos (h1 > h2 > h3) ──────────────────────
       Contraste sobre #0A0A0A:
         #F5EDE8 = 17.3:1 (AAA)
         #B8B0A8 = 9.4:1  (AAA)
         #8A8278 = 5.0:1  (AA texto comum)
         #6C6660 = 3.3:1  (AA texto grande apenas)
       ──────────────────────────────────────────────────────────── */
    h1 {
        font-family: 'DM Serif Display', Georgia, serif !important;
        font-size: 28px !important;
        font-weight: 400 !important;
        color: var(--mc-text) !important;
        letter-spacing: -0.01em !important;
        margin: 0 0 1rem 0 !important;
    }
    h2 {
        font-family: 'DM Serif Display', Georgia, serif !important;
        font-size: 22px !important;
        font-weight: 400 !important;
        color: var(--mc-text) !important;
        letter-spacing: -0.01em !important;
        margin: 1.5rem 0 0.75rem 0 !important;
    }
    h3 {
        font-size: 17px !important;
        font-weight: 600 !important;
        color: var(--mc-text) !important;
        letter-spacing: -0.01em !important;
        margin: 1rem 0 0.5rem 0 !important;
    }
    h4 {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: var(--mc-text-2) !important;
        margin: 0.75rem 0 0.4rem 0 !important;
    }

    /* Markdown geral */
    .stMarkdown p, .stMarkdown li {
        color: var(--mc-text) !important;
        font-size: 14px !important;
        line-height: 1.65 !important;
    }
    .stMarkdown strong { color: var(--mc-text) !important; font-weight: 700 !important; }
    .stMarkdown em     { color: var(--mc-text-2) !important; }

    /* ─── Header da aplicação ───────────────────────────────────── */
    .app-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 0 0 1.5rem 0;
        border-bottom: 0.5px solid var(--mc-border);
        margin-bottom: 2rem;
    }
    .app-header-title {
        font-size: 24px;
        font-weight: 800;
        color: var(--mc-text);
        letter-spacing: -0.03em;
        margin: 0;
    }
    .app-header-sub {
        font-size: 11px;
        color: var(--mc-text-3);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 4px 0 0 0;
        font-weight: 600;
    }

    /* ─── Tabs (navegação principal) — underline minimalista ────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-radius: 0;
        padding: 0;
        border: none;
        border-bottom: 0.5px solid var(--mc-border);
        width: 100%;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 0;
        color: var(--mc-text-3);
        font-size: 13px;
        font-weight: 500;
        padding: 10px 18px;
        border: none;
        border-bottom: 2px solid transparent;
        margin-bottom: -0.5px;
        transition: color 0.15s ease, border-color 0.15s ease;
        letter-spacing: 0;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: transparent;
        color: var(--mc-text);
        border-bottom-color: var(--mc-border-strong);
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: var(--mc-orange) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid var(--mc-orange) !important;
        box-shadow: none !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-panel"]  { padding-top: 1.5rem !important; }

    /* ─── Section labels (eyebrow) ──────────────────────────────── */
    .section-label {
        font-size: 11px;
        font-weight: 600;
        color: var(--mc-orange);
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin: 0 0 1.25rem 0;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .section-label::before {
        content: '';
        display: inline-block;
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--mc-orange);
        flex-shrink: 0;
    }
    .section-divider {
        border: none;
        border-top: 0.5px solid var(--mc-border);
        margin: 2.25rem 0;
    }

    /* ─── Tags / chips ─────────────────────────────────────────── */
    .tag {
        display: inline-block;
        background: var(--mc-surface-2);
        border: 0.5px solid var(--mc-border);
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        color: var(--mc-text-2);
        padding: 4px 10px;
        margin: 2px 4px 2px 0;
        letter-spacing: 0.02em;
    }
    .tag-accent {
        border-color: var(--mc-orange);
        color: var(--mc-orange);
        background: var(--mc-orange-soft);
    }

    /* ─── Info rows (label · valor) ────────────────────────────── */
    .info-row {
        display: flex;
        gap: 12px;
        align-items: baseline;
        margin: 8px 0;
        padding: 4px 0;
    }
    .info-key {
        font-size: 11px;
        color: var(--mc-text-3);
        font-weight: 700;
        min-width: 100px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .info-val {
        font-size: 14px;
        color: var(--mc-text);
        font-weight: 500;
    }

    /* ─── Métricas (cards de KPI) ──────────────────────────────── */
    div[data-testid="stMetric"] {
        background: var(--mc-surface) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 12px !important;
        padding: 18px 22px !important;
        transition: border-color 0.18s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: var(--mc-border-strong) !important;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 10px !important;
        font-weight: 700 !important;
        color: var(--mc-text-3) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'DM Serif Display', Georgia, serif !important;
        font-size: 24px !important;
        font-weight: 400 !important;
        color: var(--mc-orange) !important;
        letter-spacing: -0.01em !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 11px !important;
        font-weight: 600 !important;
    }

    /* ─── Inputs (text, number, textarea, date) ────────────────── */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input {
        background: var(--mc-surface) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 8px !important;
        color: var(--mc-text) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 11px 14px !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--mc-text-muted) !important;
        font-weight: 400 !important;
    }
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    .stDateInput input:focus,
    .stTimeInput input:focus {
        border-color: var(--mc-orange) !important;
        box-shadow: 0 0 0 3px var(--mc-orange-glow) !important;
        outline: none !important;
    }
    .stTextInput input:disabled,
    .stNumberInput input:disabled {
        background: var(--mc-surface-2) !important;
        color: var(--mc-text-3) !important;
        opacity: 0.7;
    }

    /* Selects */
    div[data-baseweb="select"] > div {
        background: var(--mc-surface) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 8px !important;
        color: var(--mc-text) !important;
        min-height: 42px !important;
    }
    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--mc-orange) !important;
        box-shadow: 0 0 0 3px var(--mc-orange-glow) !important;
    }
    div[data-baseweb="popover"] ul {
        background: var(--mc-surface-2) !important;
        border: 0.5px solid var(--mc-border) !important;
    }
    div[data-baseweb="popover"] li {
        color: var(--mc-text) !important;
    }
    div[data-baseweb="popover"] li:hover {
        background: var(--mc-orange-soft) !important;
    }

    /* ─── Labels (acima dos inputs) ─────────────────────────────
       11px com peso 700 e cor #B8B0A8 — contraste 9.4:1 (AAA).
       Antes era #6B3A4A com contraste 2.1:1 (falha WCAG).
       ─────────────────────────────────────────────────────── */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stTextArea label, .stDateInput label, .stTimeInput label,
    .stRadio label, .stFileUploader label, .stSlider label,
    .stCheckbox label, label[data-testid="stWidgetLabel"] {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: var(--mc-text-2) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        margin-bottom: 6px !important;
    }
    .stRadio > label > div:first-child,
    .stCheckbox > label > div:first-child {
        color: var(--mc-text-2) !important;
    }

    /* Helper text dos inputs */
    .stTextInput div[data-testid="InputInstructions"],
    .stNumberInput div[data-testid="InputInstructions"] {
        color: var(--mc-text-3) !important;
        font-size: 11px !important;
    }

    /* ─── Botões ────────────────────────────────────────────── */
    .stButton > button {
        background: var(--mc-surface-2) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 8px !important;
        color: var(--mc-text) !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        padding: 10px 22px !important;
        transition: all 0.18s ease !important;
        letter-spacing: 0;
    }
    .stButton > button:hover {
        background: var(--mc-surface-3) !important;
        border-color: var(--mc-border-strong) !important;
        color: var(--mc-text) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0); }

    .stButton > button[kind="primary"] {
        background: var(--mc-orange) !important;
        border-color: var(--mc-orange) !important;
        color: #0D0B09 !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px var(--mc-orange-glow) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--mc-orange-hover) !important;
        border-color: var(--mc-orange-hover) !important;
        box-shadow: 0 6px 16px var(--mc-orange-glow) !important;
        transform: translateY(-1px);
    }

    /* Download button */
    .stDownloadButton > button {
        background: var(--mc-surface-2) !important;
        border: 0.5px solid var(--mc-border) !important;
        color: var(--mc-text) !important;
    }

    /* ─── Radio chips ─────────────────────────────────────────── */
    .stRadio > div { gap: 8px !important; }
    .stRadio > div > label {
        background: var(--mc-surface) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 8px !important;
        padding: 9px 16px !important;
        color: var(--mc-text-2) !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        transition: all 0.15s ease !important;
    }
    .stRadio > div > label:hover {
        border-color: var(--mc-border-strong) !important;
        color: var(--mc-text) !important;
    }
    .stRadio > div > label:has(input:checked) {
        background: var(--mc-orange-soft) !important;
        border-color: var(--mc-orange) !important;
        color: var(--mc-orange) !important;
        font-weight: 600 !important;
    }

    /* ─── Sliders ─────────────────────────────────────────────── */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: var(--mc-orange) !important;
        border-color: var(--mc-orange) !important;
        box-shadow: 0 0 0 4px var(--mc-orange-glow) !important;
    }
    .stSlider [data-baseweb="slider"] > div > div > div {
        background: var(--mc-orange) !important;
    }

    /* ─── Expanders ───────────────────────────────────────────── */
    [data-testid="stExpander"] details {
        background: var(--mc-surface) !important;
        border: 0.5px solid var(--mc-border) !important;
        border-radius: 12px !important;
        margin-bottom: 0.75rem;
    }
    [data-testid="stExpander"] summary {
        color: var(--mc-text) !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        padding: 14px 18px !important;
    }
    [data-testid="stExpander"] summary:hover {
        background: var(--mc-surface-2) !important;
    }
    .streamlit-expanderContent,
    [data-testid="stExpander"] > details > div {
        background: var(--mc-surface) !important;
        border-top: 0.5px solid var(--mc-border) !important;
        padding: 20px !important;
    }

    /* ─── File uploader ───────────────────────────────────────── */
    .stFileUploader > div {
        background: var(--mc-surface) !important;
        border: 1.5px dashed var(--mc-border-strong) !important;
        border-radius: 10px !important;
        transition: border-color 0.18s ease;
    }
    .stFileUploader > div:hover {
        border-color: var(--mc-orange) !important;
    }
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        color: var(--mc-text-2) !important;
    }
    .stFileUploader small { color: var(--mc-text-3) !important; }

    /* ─── Alerts (success / error / warning / info) ───────────── */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 4px !important;
        font-size: 13px !important;
        padding: 14px 18px !important;
    }
    div[data-testid="stAlert"][data-baseweb="notification"] > div:first-child {
        font-weight: 600 !important;
    }

    /* ─── Divider ─────────────────────────────────────────────── */
    hr {
        border-color: var(--mc-border) !important;
        margin: 1.75rem 0 !important;
    }

    /* ─── Dataframe ───────────────────────────────────────────── */
    .stDataFrame {
        background: var(--mc-surface) !important;
        border-radius: 10px !important;
        border: 0.5px solid var(--mc-border) !important;
    }

    /* ─── Tooltips ────────────────────────────────────────────── */
    div[role="tooltip"] {
        background: var(--mc-surface-3) !important;
        color: var(--mc-text) !important;
        border: 0.5px solid var(--mc-border-strong) !important;
        font-size: 12px !important;
    }

    /* ─── Streamlit padrão: melhorias finais ──────────────────── */
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* Scrollbar */
    ::-webkit-scrollbar       { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--mc-bg); }
    ::-webkit-scrollbar-thumb { background: var(--mc-border-strong); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--mc-orange); }

    /* ─── Hero / logo na página inicial ───────────────────────── */
    .mc-hero-full {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .mc-hero-full img {
        max-width: 320px;
        width: 100%;
        height: auto;
    }
    .mc-tagline {
        color: var(--mc-text-2);
        font-size: 13px;
        font-weight: 500;
        letter-spacing: 0.03em;
        margin: 1rem 0 0 0;
        line-height: 1.6;
    }

    /* ═══════════════════════════════════════════════════════════
       PADRÕES DE EXPERIÊNCIA — Componentes reutilizáveis
       ═══════════════════════════════════════════════════════════ */

    /* Stepper de seção (1 ⚪ título) */
    .mc-step {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        margin: 2.5rem 0 1.25rem;
        padding-bottom: 0.5rem;
    }
    .mc-step-num {
        flex-shrink: 0;
        width: 32px; height: 32px;
        background: var(--mc-orange);
        color: #0A0A0A;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800;
        font-size: 14px;
        box-shadow: 0 2px 8px var(--mc-orange-glow);
    }
    .mc-step-num.muted {
        background: var(--mc-surface-3);
        color: var(--mc-text-3);
        box-shadow: none;
    }
    .mc-step-body { flex: 1; min-width: 0; }
    .mc-step-title {
        font-size: 17px;
        font-weight: 700;
        color: var(--mc-text);
        letter-spacing: -0.01em;
        margin: 0;
        line-height: 1.2;
    }
    .mc-step-sub {
        font-size: 12px;
        color: var(--mc-text-3);
        margin: 4px 0 0;
        line-height: 1.4;
    }

    /* Empty-state card (sem dados) */
    .mc-empty {
        text-align: center;
        padding: 3rem 1.5rem;
        background: var(--mc-surface);
        border: 0.5px dashed var(--mc-border-strong);
        border-radius: 14px;
        margin: 1rem 0;
    }
    .mc-empty-icon {
        font-size: 56px;
        line-height: 1;
        margin-bottom: 1rem;
        opacity: 0.85;
    }
    .mc-empty-title {
        font-size: 18px;
        font-weight: 700;
        color: var(--mc-text);
        margin: 0 0 0.5rem 0;
    }
    .mc-empty-sub {
        font-size: 13px;
        color: var(--mc-text-2);
        max-width: 420px;
        margin: 0 auto 1.5rem;
        line-height: 1.55;
    }
    .mc-empty-hint {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        background: var(--mc-orange-soft);
        border: 0.5px solid var(--mc-orange);
        color: var(--mc-orange);
        border-radius: 24px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ═══════════════════════════════════════════════════════════
       BRAND WORDMARK — Replica fiel do logo "MATEU COFFEE"
       Fonte: Cormorant Garamond (serif transicional)
       MATEU em laranja vibrante · COFFEE em cinza quente
       ═══════════════════════════════════════════════════════════ */
    .mc-mark {
        font-family: 'Cormorant Garamond', 'Playfair Display', Georgia, serif !important;
        text-align: center;
        line-height: 0.95;
        letter-spacing: 0.04em;
    }
    .mc-mark-row {
        display: inline-flex;
        align-items: center;
        gap: 0.5em;
        line-height: 0.95;
    }
    .mc-mark-mateu {
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-weight: 600;
        color: var(--mc-orange);
        letter-spacing: 0.08em;
    }
    .mc-mark-coffee {
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-weight: 600;
        color: var(--mc-text-2);
        letter-spacing: 0.08em;
    }
    .mc-mark-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--mc-orange);
        line-height: 1;
    }
    .mc-mark-tag {
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-weight: 500;
        font-style: italic;
        color: var(--mc-text-3);
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-top: 0.4em;
    }

    /* Tamanho HERO (login) */
    .mc-mark-hero .mc-mark-mateu,
    .mc-mark-hero .mc-mark-coffee { font-size: 56px; }
    .mc-mark-hero .mc-mark-icon  { font-size: 64px; margin-right: 8px; }
    .mc-mark-hero .mc-mark-tag   { font-size: 11px; }
    @media (max-width: 640px) {
        .mc-mark-hero .mc-mark-mateu,
        .mc-mark-hero .mc-mark-coffee { font-size: 40px; }
        .mc-mark-hero .mc-mark-icon  { font-size: 46px; }
    }

    /* Tamanho COMPACT (topbar) */
    .mc-mark-compact .mc-mark-mateu,
    .mc-mark-compact .mc-mark-coffee { font-size: 22px; }
    .mc-mark-compact .mc-mark-icon  { font-size: 24px; margin-right: 4px; }
    .mc-mark-compact .mc-mark-tag   { font-size: 9px; }

    /* Tamanho TINY (footer/atalhos) */
    .mc-mark-tiny .mc-mark-mateu,
    .mc-mark-tiny .mc-mark-coffee { font-size: 15px; }
    .mc-mark-tiny .mc-mark-icon  { font-size: 16px; }

    /* Hero de login — logo em destaque máximo */
    .mc-login-hero {
        text-align: center;
        padding: 2.5rem 0 2rem;
        border-bottom: 0.5px solid var(--mc-border);
        margin-bottom: 1.75rem;
    }
    .mc-login-hero img {
        max-width: 480px !important;
        width: 90% !important;
        filter: drop-shadow(0 8px 32px rgba(232, 114, 46, 0.28));
        transition: filter 0.3s ease;
    }
    .mc-login-title {
        font-size: 26px;
        font-weight: 800;
        color: var(--mc-text);
        margin: 1.75rem 0 0.4rem 0;
        letter-spacing: -0.03em;
    }
    .mc-login-sub {
        font-size: 14px;
        color: var(--mc-text-2);
        margin: 0;
        line-height: 1.6;
        max-width: 380px;
        margin: 0 auto;
    }

    /* ─── Oculta o iframe do CookieManager (extra-streamlit-components)
       que renderiza no canto da tela durante o carregamento ─────── */
    iframe[title*="cookie"],
    iframe[title*="Cookie"],
    .stCustomComponentV1:has(iframe[title*="cookie"]) {
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    /* Previne flash de layout parcial durante hidratação */
    .stApp [data-testid="stAppViewContainer"] > section:first-child {
        min-height: 100vh;
    }

    /* Compact header (logo · email · sair) */
    .mc-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 0.5rem 0 1.25rem;
        border-bottom: 1px solid var(--mc-border);
        margin-bottom: 1.5rem;
    }
    .mc-topbar-brand {
        display: flex; align-items: center; gap: 10px;
    }
    .mc-topbar-brand-text {
        font-size: 14px;
        font-weight: 800;
        color: var(--mc-text);
        letter-spacing: -0.01em;
    }
    .mc-topbar-brand-tag {
        font-size: 10px;
        color: var(--mc-orange);
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-weight: 700;
        margin: -2px 0 0;
    }
    .mc-topbar-user {
        display: flex; align-items: center; gap: 8px;
        font-size: 12px;
        color: var(--mc-text-2);
        font-weight: 600;
    }
    .mc-topbar-user-avatar {
        width: 28px; height: 28px; border-radius: 50%;
        background: var(--mc-orange-soft);
        border: 1px solid var(--mc-orange);
        color: var(--mc-orange);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800;
        font-size: 12px;
    }

    /* Stat trio do widget consumo */
    .mc-consumo {
        display: flex;
        gap: 0;
        align-items: stretch;
        background: linear-gradient(135deg, var(--mc-surface) 0%, var(--mc-surface-2) 100%);
        border: 1px solid var(--mc-border);
        border-left: 4px solid var(--mc-orange);
        border-radius: 12px;
        padding: 14px 18px;
        margin: 0 0 1.5rem;
        flex-wrap: wrap;
    }
    .mc-consumo-cell {
        flex: 1 1 0;
        min-width: 100px;
        padding: 0 12px;
        border-right: 1px solid var(--mc-border);
    }
    .mc-consumo-cell:last-child { border-right: none; }
    .mc-consumo-label {
        font-size: 10px;
        color: var(--mc-text-3);
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 4px;
    }
    .mc-consumo-value {
        font-size: 18px;
        color: var(--mc-text);
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .mc-consumo-value.accent { color: var(--mc-orange); }
    .mc-consumo-sub {
        font-size: 11px;
        color: var(--mc-text-3);
        margin: 2px 0 0;
    }
    @media (max-width: 640px) {
        .mc-consumo-cell { border-right: none; border-bottom: 1px solid var(--mc-border); padding: 8px 0; }
        .mc-consumo-cell:last-child { border-bottom: none; }
    }

    /* ═══════════════════════════════════════════════════════════
       RECEITAS — Cards, badges e lista numerada
       ═══════════════════════════════════════════════════════════ */
    .mc-recipe-meta {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 1rem 0 1.5rem;
    }
    @media (max-width: 640px) {
        .mc-recipe-meta { grid-template-columns: repeat(2, 1fr); }
    }
    .mc-recipe-meta-cell {
        background: var(--mc-surface-2);
        border: 1px solid var(--mc-border);
        border-radius: 10px;
        padding: 12px 14px;
        text-align: left;
    }
    .mc-recipe-meta-label {
        font-size: 10px;
        color: var(--mc-text-3);
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 4px;
    }
    .mc-recipe-meta-value {
        font-size: 14px;
        color: var(--mc-text);
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .mc-recipe-meta-value.accent { color: var(--mc-orange); }

    /* Badges/chips de filtro */
    .mc-recipe-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        background: var(--mc-orange-soft);
        border: 1px solid var(--mc-orange);
        color: var(--mc-orange);
        border-radius: 100px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-right: 6px;
    }
    .mc-recipe-badge.neutral {
        background: var(--mc-surface-2);
        border-color: var(--mc-border);
        color: var(--mc-text-2);
    }

    /* Lista de equipamentos como chips */
    .mc-equip {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 0.5rem 0 1rem;
    }
    .mc-equip-chip {
        background: var(--mc-surface-2);
        border: 1px solid var(--mc-border);
        color: var(--mc-text-2);
        font-size: 12px;
        font-weight: 600;
        padding: 5px 10px;
        border-radius: 6px;
    }

    /* Lista numerada de passos */
    .mc-steps { counter-reset: stp; padding: 0; margin: 0; list-style: none; }
    .mc-steps li {
        counter-increment: stp;
        position: relative;
        padding: 12px 14px 12px 48px;
        margin: 0 0 8px;
        background: var(--mc-surface);
        border: 1px solid var(--mc-border);
        border-radius: 10px;
        font-size: 13.5px;
        line-height: 1.55;
        color: var(--mc-text);
    }
    .mc-steps li::before {
        content: counter(stp);
        position: absolute;
        left: 12px; top: 11px;
        width: 26px; height: 26px;
        background: var(--mc-orange);
        color: #0A0A0A;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800;
        font-size: 12px;
        font-family: 'Inter', sans-serif;
    }

    /* Lista de ingredientes (visual mais quente) */
    .mc-ingredients {
        background: linear-gradient(135deg, var(--mc-surface) 0%, var(--mc-orange-soft) 200%);
        border: 1px solid var(--mc-border);
        border-left: 4px solid var(--mc-orange);
        border-radius: 10px;
        padding: 14px 18px;
        margin: 0.5rem 0 1rem;
    }
    .mc-ingredients ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .mc-ingredients li {
        font-size: 14px;
        color: var(--mc-text);
        font-weight: 500;
        line-height: 1.6;
        padding: 4px 0 4px 20px;
        position: relative;
    }
    .mc-ingredients li::before {
        content: "•";
        color: var(--mc-orange);
        font-weight: 800;
        font-size: 16px;
        position: absolute;
        left: 4px;
    }

    /* Fonte */
    .mc-recipe-source {
        font-size: 11px;
        color: var(--mc-text-3);
        font-style: italic;
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--mc-border);
    }

    /* Pill de data relativa */
    .mc-when {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        background: var(--mc-surface-2);
        border: 0.5px solid var(--mc-border);
        border-radius: 100px;
        font-size: 11px;
        font-weight: 600;
        color: var(--mc-text-2);
        letter-spacing: 0.02em;
    }
    .mc-when.today { background: var(--mc-orange-soft); border-color: var(--mc-orange); color: var(--mc-orange); }

    /* ─── Mobile ──────────────────────────────────────────────── */
    @media (max-width: 640px) {
        .block-container { padding: 0.75rem 0.85rem 9rem !important; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }

        /* Tabs mobile: underline scrollável */
        .stTabs [data-baseweb="tab-list"] {
            width: 100% !important;
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            position: sticky;
            top: 0;
            z-index: 999;
            background: var(--mc-bg) !important;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            gap: 0;
            padding: 0;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 14px;
            font-size: 12px;
            white-space: nowrap;
            flex-shrink: 0;
            min-height: 42px;
        }
        .stTabs [data-baseweb="tab-panel"] { padding-top: 1.1rem !important; }

        /* Alvos de toque ≥44px (recomendação Apple/Google) */
        .stButton > button {
            width: 100%;
            min-height: 46px;
            font-size: 15px !important;
        }
        .stDownloadButton > button { width: 100%; min-height: 46px; }
        [data-testid="stExpander"] summary { min-height: 46px; padding: 10px 12px; }
        .stCheckbox { min-height: 40px; }

        /* font-size 16px nos inputs impede o zoom automático do iOS */
        .stTextInput input, .stTextArea textarea,
        .stNumberInput input, .stDateInput input,
        .stSelectbox [data-baseweb="select"] div { font-size: 16px !important; }
        .stTextInput input, .stNumberInput input, .stDateInput input { min-height: 44px; }

        /* Colunas empilham em vez de espremer */
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.5rem !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
        }
        /* Formulários longos: 1 coluna só */
        [data-testid="stForm"] [data-testid="stColumn"],
        [data-testid="stExpander"] [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Métricas compactas */
        [data-testid="stMetric"] { padding: 8px 10px !important; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }

        /* Sliders: área de toque maior */
        .stSlider, [data-testid="stSelectSlider"] { padding: 6px 4px; }
        .stSlider [role="slider"] { width: 22px !important; height: 22px !important; }

        /* Imagens nunca estouram a largura */
        img { max-width: 100% !important; height: auto !important; }

        /* Login: hero em destaque */
        .mc-login-hero img { max-width: 360px !important; }
        .mc-login-sub { font-size: 13px !important; }

        /* Logo da topbar: tamanho controlado no mobile */
        .mc-topbar-logo { height: 73px !important; width: auto !important; }

        /* Login: a coluna central ocupa a tela toda (corrige meia-tela) */
        [data-testid="stColumn"]:has(.mc-login-hero) {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Login mobile: conteúdo no alto da tela, sem vão */
        .block-container:has(.mc-login-hero) { padding-top: 0.75rem !important; }
        .mc-login-hero { padding-top: 0 !important; }

        /* Topbar mobile: marca centralizada em linha própria, e-mail abaixo */
        [data-testid="stColumn"]:has(.mc-topbar-logo) {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        .mc-topbar-logo { margin: 0 auto !important; }
        .mc-topbar-user { justify-content: center !important; }

        /* Indicador de que há mais abas à direita (fade + seta) */
        .stTabs { position: relative; }
        .stTabs::after {
            content: "›";
            position: absolute;
            top: 8px; right: 0;
            height: 44px; width: 34px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; font-weight: 700;
            color: var(--mc-orange);
            background: linear-gradient(to right, transparent, var(--mc-bg) 55%);
            pointer-events: none;
            z-index: 5;
        }
    }

    /* Slot invisível do cookie: não ocupa espaço nem vira "sombra" */
    [data-testid="stElementContainer"]:has(iframe[height="0"]) {
        display: none !important;
    }

    /* Login: centraliza o conteúdo sem colunas (sem skeleton) */
    .block-container:has(.mc-login-hero) {
        max-width: 680px !important;
        margin: 0 auto !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Database layer ─────────────────────────────────────────────────────
@st.cache_resource
def _get_pool() -> pg_pool.ThreadedConnectionPool:
    # keepalives prevent Neon from closing idle SSL connections
    kwargs = dict(
        connect_timeout=10,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return pg_pool.ThreadedConnectionPool(1, 10, db_url, **kwargs)
    try:
        s = st.secrets["connections"]["postgresql"]
        return pg_pool.ThreadedConnectionPool(
            1, 10,
            host=s["host"], port=int(s["port"]), dbname=s["database"],
            user=s["username"], password=s["password"], **kwargs)
    except Exception:
        pass
    return pg_pool.ThreadedConnectionPool(
        1, 10,
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        **kwargs)

@contextlib.contextmanager
def _db():
    """Pega uma conexão do pool; revalida e recria a pool se a conexão estiver morta (Neon idle timeout)."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        # Verifica se a conexão SSL ainda está viva
        try:
            conn.cursor().execute("SELECT 1")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # Conexão morta — descarta, limpa cache da pool e abre uma nova
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
            _get_pool.clear()
            pool = _get_pool()
            conn = pool.getconn()
        yield conn
    finally:
        try:
            if conn.closed:
                pool.putconn(conn, close=True)
            else:
                pool.putconn(conn)
        except Exception:
            pass

def _run(query: str, params: tuple = ()) -> None:
    with _db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    _bump()

def _bump() -> None:
    st.session_state["_v"] = st.session_state.get("_v", 0) + 1
    _fetch.clear()

@st.cache_data(ttl=600, show_spinner=False)
def _fetch(query: str, params: tuple = (), _v: int = 0) -> list:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            cur.close()

def _v() -> int:
    return st.session_state.get("_v", 0)

# ─── Cookie manager para persistência real do "Manter-me conectado" ───
# st.session_state é EFÊMERO (vive só enquanto a aba está aberta).
# Cookie no browser é o único jeito de manter sessão entre visitas.
_COOKIE_NAME = "mc_remember"

def _read_cookie() -> Optional[str]:
    """Lê o cookie enviado pelo browser na conexão (st.context, Streamlit 1.37+)."""
    try:
        return st.context.cookies.get(_COOKIE_NAME)
    except Exception:
        return None

def _hash_senha(senha: str) -> str:
    """Hash bcrypt — lento por design, resistente a brute-force."""
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def _verify_senha(senha: str, hash_stored: str) -> bool:
    """Verifica senha. Suporta bcrypt (novo) e SHA-256 legado (migração)."""
    # Bcrypt começa com $2b$ ou $2a$
    if hash_stored.startswith("$2"):
        try:
            return bcrypt.checkpw(senha.encode(), hash_stored.encode())
        except Exception:
            return False
    # Legado SHA-256: formato "{salt}${hex}"
    parts = hash_stored.split("$")
    if len(parts) == 2:
        salt, h = parts
        return hashlib.sha256(f"{salt}{senha}".encode()).hexdigest() == h
    return False

class LoginResult:
    OK = "ok"
    INVALID = "invalid"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"

_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECS  = 600   # 10 minutos

# ── Google OAuth ────────────────────────────────────────────────────────
_GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO   = "https://www.googleapis.com/oauth2/v2/userinfo"
_GOOGLE_SCOPES     = "openid email profile"

def _google_redirect_uri() -> str:
    return os.environ.get("GOOGLE_REDIRECT_URI", "https://mateucoffee.souleandroribeiro.com.br")

def _google_auth_url() -> str:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return ""
    params = urlencode({
        "client_id":     client_id,
        "redirect_uri":  _google_redirect_uri(),
        "response_type": "code",
        "scope":         _GOOGLE_SCOPES,
        "access_type":   "online",
        "prompt":        "select_account",
    })
    return f"{_GOOGLE_AUTH_URL}?{params}"

def _login_google(code: str) -> str:
    """Troca o authorization code por tokens, busca o email e faz login/cadastro."""
    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return LoginResult.ERROR
    try:
        tok = _requests.post(_GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  _google_redirect_uri(),
            "grant_type":    "authorization_code",
        }, timeout=10).json()
        access_token = tok.get("access_token")
        if not access_token:
            return LoginResult.ERROR

        info = _requests.get(_GOOGLE_USERINFO,
                             headers={"Authorization": f"Bearer {access_token}"},
                             timeout=10).json()
        email     = (info.get("email") or "").lower().strip()
        google_id = str(info.get("id") or "")
        if not email:
            return LoginResult.ERROR

        existing = _fetch("SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1",
                          (email,), _v=0)
        if existing:
            uid = existing[0]["id"]
            _run("UPDATE usuarios SET google_id=%s WHERE id=%s", (google_id, uid))
        else:
            _run("INSERT INTO usuarios (email, senha_hash, google_id) VALUES (%s, %s, %s)",
                 (email, "", google_id))
            uid = _fetch("SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1",
                         (email,), _v=0)[0]["id"]

        st.session_state['user_id']    = uid
        st.session_state['user_email'] = email
        return LoginResult.OK
    except Exception as e:
        return LoginResult.ERROR

def _login(email: str, senha: str, remember: bool = False) -> str:
    """Valida credenciais. Retorna LoginResult.{OK, INVALID, ERROR, RATE_LIMITED}."""
    # Rate limiting — primeiro no DB (cross-tab/browser), depois session_state como backup rápido
    now = _now_local()
    attempts = [t for t in st.session_state.get('_login_attempts', [])
                if (now - t).total_seconds() < _LOGIN_WINDOW_SECS]
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        return LoginResult.RATE_LIMITED
    # Verifica também no DB (resiste a múltiplas abas e novos browsers)
    try:
        _db_attempts = _fetch("""
            SELECT COUNT(*) AS n FROM login_attempts
            WHERE email=LOWER(%s) AND attempted_at > NOW() - INTERVAL '10 minutes'
        """, (email.strip(),), _v=0)
        if _db_attempts and int(_db_attempts[0]['n']) >= _MAX_LOGIN_ATTEMPTS:
            return LoginResult.RATE_LIMITED
    except Exception:
        pass  # tabela ainda não existe — degradação graciosa

    try:
        result = _fetch(
            "SELECT id, email, senha_hash FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1",
            (email.strip(),), _v=0,
        )
    except Exception:
        return LoginResult.ERROR

    if not result:
        attempts.append(now)
        st.session_state['_login_attempts'] = attempts
        try:
            _run("INSERT INTO login_attempts (email, attempted_at) VALUES (LOWER(%s), NOW())",
                 (email.strip(),))
        except Exception:
            pass
        return LoginResult.INVALID
    usuario = result[0]
    if not _verify_senha(senha, usuario['senha_hash']):
        attempts.append(now)
        st.session_state['_login_attempts'] = attempts
        try:
            _run("INSERT INTO login_attempts (email, attempted_at) VALUES (LOWER(%s), NOW())",
                 (email.strip(),))
        except Exception:
            pass
        return LoginResult.INVALID

    # Migração silenciosa: re-hash SHA-256 legado → bcrypt
    if not usuario['senha_hash'].startswith("$2"):
        try:
            _run("UPDATE usuarios SET senha_hash=%s WHERE id=%s",
                 (_hash_senha(senha), usuario['id']))
        except Exception:
            pass

    st.session_state['user_id'] = usuario['id']
    st.session_state['user_email'] = usuario['email']
    st.session_state.pop('_login_attempts', None)

    if remember:
        try:
            token = secrets.token_urlsafe(32)
            expira = _now_local() + timedelta(days=30)
            _run(
                "UPDATE usuarios SET remember_token=%s, remember_token_expires=%s WHERE id=%s",
                (token, expira, usuario['id'])
            )
            st.session_state['remember_token'] = token
            # NÃO grava o cookie aqui: o st.rerun() do botão de login desmontaria
            # o componente antes do browser executar o JS (cookie nunca era salvo).
            # A gravação acontece no próximo run, já na página autenticada.
            st.session_state['_pending_cookie'] = (token, expira)
        except Exception:
            # login funcionou, mas remember-me falhou — não bloqueia a sessão
            pass

    return LoginResult.OK

def _check_remember_token() -> bool:
    """Restaura sessão a partir de query_param mc_token, cookie ou session_state."""
    if st.session_state.get('user_id'):
        return True
    if st.session_state.get('_token_checked'):
        return False

    # Prioridade: query_param (confiável entre reruns) > cookie HTTP > session_state
    token = (st.query_params.get("mc_token") or
             _read_cookie() or
             st.session_state.get('remember_token'))

    st.session_state['_token_checked'] = True

    if not token:
        return False

    try:
        result = _fetch(
            "SELECT id, email, remember_token_expires FROM usuarios WHERE remember_token=%s",
            (token,), _v=0)
        if not result:
            if "mc_token" in st.query_params:
                del st.query_params["mc_token"]
            return False
        usuario = result[0]
        expiry = usuario['remember_token_expires']
        if expiry and expiry < _now_local():
            if "mc_token" in st.query_params:
                del st.query_params["mc_token"]
            return False
        st.session_state['user_id']        = usuario['id']
        st.session_state['user_email']     = usuario['email']
        st.session_state['remember_token'] = token
        return True
    except Exception:
        return False

def _logout() -> None:
    """Limpa sessão, token no DB, cookie e query param."""
    user_id = st.session_state.get('user_id')
    if user_id:
        try:
            _run("UPDATE usuarios SET remember_token=NULL, remember_token_expires=NULL WHERE id=%s", (user_id,))
        except Exception:
            pass
    st.session_state['_clear_cookie'] = True
    if "mc_token" in st.query_params:
        del st.query_params["mc_token"]
    for k in ['user_id', 'user_email', 'remember_token', '_token_checked', '_cookie_attempts']:
        st.session_state.pop(k, None)

_DB_READY: bool = False  # module-level: runs migrations once per process

def _init_db() -> None:
    global _DB_READY
    if _DB_READY:
        st.session_state["_db_ready"] = True
        return
    if st.session_state.get("_db_ready"):
        _DB_READY = True
        return
    with _db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    remember_token TEXT,
                    remember_token_expires TIMESTAMP
                );
            """)
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token TEXT;")
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token_expires TIMESTAMP;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS coffees (
                    id SERIAL PRIMARY KEY, data_cadastro DATE NOT NULL DEFAULT CURRENT_DATE,
                    nome TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'Grãos',
                    torra TEXT NOT NULL DEFAULT 'Média', notas TEXT DEFAULT '',
                    classificacao INTEGER DEFAULT 0, fazenda TEXT DEFAULT '',
                    regiao TEXT DEFAULT '', data_torra DATE,
                    tamanho_pacote INTEGER DEFAULT 250, foto_embalagem TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS extracoes (
                    id SERIAL PRIMARY KEY,
                    coffee_id INTEGER REFERENCES coffees(id) ON DELETE CASCADE,
                    data DATE NOT NULL DEFAULT CURRENT_DATE,
                    metodo TEXT NOT NULL DEFAULT 'Espresso',
                    gramas FLOAT NOT NULL DEFAULT 18, moedor TEXT DEFAULT '',
                    clicks_moedor INTEGER DEFAULT 0, agua_alvo FLOAT NOT NULL DEFAULT 300,
                    tds FLOAT DEFAULT 0, tempo_extracao INTEGER NOT NULL DEFAULT 150,
                    brew_ratio FLOAT DEFAULT 0, ey FLOAT DEFAULT 0, fluxo FLOAT DEFAULT 0,
                    foto_caneca TEXT, classificacao INTEGER DEFAULT 0,
                    notas TEXT DEFAULT '', created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                ALTER TABLE coffees
                    ADD COLUMN IF NOT EXISTS local_compra      TEXT  DEFAULT '',
                    ADD COLUMN IF NOT EXISTS valor_compra      FLOAT DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS data_compra       DATE,
                    ADD COLUMN IF NOT EXISTS classificacao_cafe TEXT DEFAULT '',
                    ADD COLUMN IF NOT EXISTS intensidade       INTEGER DEFAULT 5;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS capsulas (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES usuarios(id),
                    nome TEXT NOT NULL,
                    marca TEXT DEFAULT '',
                    maquina TEXT NOT NULL DEFAULT 'Nespresso',
                    intensidade INTEGER DEFAULT 5,
                    quantidade INTEGER DEFAULT 10,
                    aluminio BOOLEAN DEFAULT FALSE,
                    volume_ml INTEGER DEFAULT 40,
                    foto_embalagem TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_capsulas_user_id ON capsulas(user_id);
            """)
            cur.execute("""
                ALTER TABLE capsulas
                    ADD COLUMN IF NOT EXISTS crema_stars         INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS corpo_stars         INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS equilibrio_stars    INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS acidez_stars        INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS amargor_stars       INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS presenca_boca_stars INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS docura_stars        INTEGER DEFAULT 3,
                    ADD COLUMN IF NOT EXISTS nota_final_stars    INTEGER DEFAULT 3;
            """)
            cur.execute("""
                ALTER TABLE usuarios
                    ADD COLUMN IF NOT EXISTS last_grinder TEXT,
                    ADD COLUMN IF NOT EXISTS last_clicks INTEGER DEFAULT 0;
            """)
            cur.execute("""
                ALTER TABLE extracoes
                    ADD COLUMN IF NOT EXISTS crema_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS corpo_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS equilibrio_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS acidez_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS amargor_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS presenca_boca_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS docura_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS nota_final_stars INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS balanco_ideal TEXT DEFAULT '',
                    ADD COLUMN IF NOT EXISTS data_hora_extracao TIMESTAMP DEFAULT NOW();
            """)
            cur.execute("""
                ALTER TABLE coffees    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id);
                ALTER TABLE extracoes  ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id);
                CREATE INDEX IF NOT EXISTS idx_coffees_user_id   ON coffees(user_id);
                CREATE INDEX IF NOT EXISTS idx_extracoes_user_id ON extracoes(user_id);
            """)
            cur.execute("SELECT COUNT(*) FROM usuarios")
            if cur.fetchone()[0] == 1:
                cur.execute("SELECT id FROM usuarios LIMIT 1")
                sole_user = cur.fetchone()[0]
                cur.execute("UPDATE coffees   SET user_id=%s WHERE user_id IS NULL", (sole_user,))
                cur.execute("UPDATE extracoes SET user_id=%s WHERE user_id IS NULL", (sole_user,))

            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name='usuarios' AND column_name='remember_token_created')
                       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='usuarios' AND column_name='remember_token_expires')
                    THEN
                        ALTER TABLE usuarios RENAME COLUMN remember_token_created TO remember_token_expires;
                    END IF;
                END $$;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name='extracoes' AND column_name='doçura_stars')
                       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='extracoes' AND column_name='docura_stars')
                    THEN
                        ALTER TABLE extracoes RENAME COLUMN "doçura_stars" TO docura_stars;
                    END IF;
                END $$;
            """)
            cur.execute("""
                ALTER TABLE extracoes
                    ADD COLUMN IF NOT EXISTS temp_real    FLOAT DEFAULT NULL,
                    ADD COLUMN IF NOT EXISTS pressao_real FLOAT DEFAULT NULL;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id             SERIAL PRIMARY KEY,
                    user_id        INTEGER REFERENCES usuarios(id),
                    tipo           TEXT NOT NULL DEFAULT 'manual',
                    criado_em      TIMESTAMP DEFAULT NOW(),
                    notas          TEXT DEFAULT '',
                    coffees_data   JSONB DEFAULT '[]',
                    extracoes_data JSONB DEFAULT '[]',
                    capsulas_data  JSONB DEFAULT '[]',
                    git_hash       TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_backups_criado_em ON backups(criado_em DESC);
            """)
            # Migração: adiciona user_id em backups antigos
            cur.execute("ALTER TABLE backups ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id);")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS barista_chats (
                    id        SERIAL PRIMARY KEY,
                    user_id   INTEGER REFERENCES usuarios(id),
                    role      TEXT NOT NULL,
                    content   TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_barista_chats_user ON barista_chats(user_id, criado_em);
            """)
            # Remove coluna app_code (não usada — evita armazenar código-fonte no banco)
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name='backups' AND column_name='app_code')
                    THEN ALTER TABLE backups DROP COLUMN app_code; END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name='backups' AND column_name='usuarios_data')
                    THEN ALTER TABLE backups DROP COLUMN usuarios_data; END IF;
                END $$;
            """)
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS google_id TEXT;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id           SERIAL PRIMARY KEY,
                    email        TEXT NOT NULL,
                    attempted_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email, attempted_at DESC);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS grinder_profiles (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER REFERENCES usuarios(id),
                    coffee_id  INTEGER REFERENCES coffees(id) ON DELETE CASCADE,
                    moedor     TEXT NOT NULL DEFAULT '',
                    torra      TEXT NOT NULL DEFAULT 'Média',
                    metodo     TEXT NOT NULL DEFAULT 'Espresso',
                    clicks     INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, coffee_id, moedor, torra, metodo)
                );
                CREATE INDEX IF NOT EXISTS idx_grinder_profiles_user ON grinder_profiles(user_id, coffee_id);
            """)

            conn.commit()
            _DB_READY = True
            st.session_state["_db_ready"] = True
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

# ── Backup ─────────────────────────────────────────────────────────────
def _backup_criar(tipo: str = "manual", notas: str = "", user_id: Optional[int] = None) -> bool:
    """Snapshot dos dados do usuário (sem código-fonte)."""
    uid = user_id or st.session_state.get('user_id')
    if not uid:
        return False
    try:
        coffees   = _fetch("SELECT * FROM coffees   WHERE user_id=%s", (uid,), _v=_v())
        extracoes = _fetch("SELECT * FROM extracoes WHERE user_id=%s", (uid,), _v=_v())
        capsulas  = _fetch("SELECT * FROM capsulas  WHERE user_id=%s", (uid,), _v=_v())

        def _rows_to_json(rows):
            out = []
            for r in rows:
                d = dict(r)
                for k, val in d.items():
                    if hasattr(val, 'isoformat'):
                        d[k] = val.isoformat()
                out.append(d)
            return json.dumps(out, ensure_ascii=False)

        try:
            import subprocess
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            git_hash = ""

        _run("""INSERT INTO backups
                    (user_id, tipo, notas, coffees_data, extracoes_data, capsulas_data, git_hash)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)""",
             (uid, tipo, notas,
              _rows_to_json(coffees), _rows_to_json(extracoes),
              _rows_to_json(capsulas), git_hash))
        return True
    except Exception as e:
        st.error(f"Erro ao criar backup: {e}")
        return False


def _backup_listar(user_id: int) -> list:
    return _fetch("""SELECT id, tipo, criado_em, notas, git_hash,
                            jsonb_array_length(coffees_data)   AS n_cafes,
                            jsonb_array_length(extracoes_data) AS n_extracoes,
                            jsonb_array_length(capsulas_data)  AS n_capsulas
                     FROM backups WHERE user_id=%s
                     ORDER BY criado_em DESC LIMIT 30""", (user_id,), _v=_v())


def _backup_restaurar_dados(backup_id: int, user_id: int) -> bool:
    """Restaura dados do backup para o usuário dono. Não afeta outros usuários."""
    try:
        rows = _fetch(
            "SELECT coffees_data, extracoes_data, capsulas_data FROM backups WHERE id=%s AND user_id=%s",
            (backup_id, user_id), _v=_v())
        if not rows:
            st.error("Backup não encontrado ou não pertence a esta conta.")
            return False

        _backup_criar("pre-restore", f"Auto-backup antes de restaurar #{backup_id}", user_id)

        b = rows[0]
        coffees   = json.loads(b["coffees_data"])
        extracoes = json.loads(b["extracoes_data"])
        capsulas  = json.loads(b["capsulas_data"])

        with _db() as conn:
            cur = conn.cursor()
            try:
                # Apaga apenas os registros do usuário atual
                cur.execute("DELETE FROM extracoes WHERE user_id=%s", (user_id,))
                cur.execute("DELETE FROM capsulas  WHERE user_id=%s", (user_id,))
                cur.execute("DELETE FROM coffees   WHERE user_id=%s", (user_id,))

                # Whitelists — previne SQL injection via colunas arbitrárias no JSON
                _OK_COFFEE = {'id','data_cadastro','nome','tipo','torra','notas',
                    'classificacao','classificacao_cafe','fazenda','regiao',
                    'data_torra','tamanho_pacote','foto_embalagem','created_at',
                    'local_compra','valor_compra','data_compra','intensidade','user_id'}
                _OK_EXTRA  = {'id','coffee_id','data','metodo','gramas','moedor',
                    'clicks_moedor','agua_alvo','tds','tempo_extracao','brew_ratio',
                    'ey','fluxo','foto_caneca','classificacao','notas','created_at',
                    'crema_stars','corpo_stars','equilibrio_stars','acidez_stars',
                    'amargor_stars','presenca_boca_stars','docura_stars',
                    'nota_final_stars','balanco_ideal','data_hora_extracao',
                    'user_id','temp_real','pressao_real'}
                _OK_CAP    = {'id','user_id','nome','marca','maquina','intensidade',
                    'quantidade','aluminio','volume_ml','foto_embalagem','created_at',
                    'crema_stars','corpo_stars','equilibrio_stars','acidez_stars',
                    'amargor_stars','presenca_boca_stars','docura_stars','nota_final_stars'}

                for c in coffees:
                    c["user_id"] = user_id
                    cols = [k for k in c.keys() if k in _OK_COFFEE]
                    ph   = ", ".join(["%s"] * len(cols))
                    cur.execute(
                        f"INSERT INTO coffees ({', '.join(cols)}) VALUES ({ph}) ON CONFLICT (id) DO NOTHING",
                        [c[k] for k in cols])

                for e in extracoes:
                    e["user_id"] = user_id
                    cols = [k for k in e.keys() if k in _OK_EXTRA]
                    ph   = ", ".join(["%s"] * len(cols))
                    cur.execute(
                        f"INSERT INTO extracoes ({', '.join(cols)}) VALUES ({ph}) ON CONFLICT (id) DO NOTHING",
                        [e[k] for k in cols])

                for cap in capsulas:
                    cap["user_id"] = user_id
                    cols = [k for k in cap.keys() if k in _OK_CAP]
                    ph   = ", ".join(["%s"] * len(cols))
                    cur.execute(
                        f"INSERT INTO capsulas ({', '.join(cols)}) VALUES ({ph}) ON CONFLICT (id) DO NOTHING",
                        [cap[k] for k in cols])

                conn.commit()
                _bump()
                return True
            except Exception as e:
                conn.rollback()
                st.error(f"Erro ao restaurar dados: {e}")
                return False
            finally:
                cur.close()
    except Exception as e:
        st.error(f"Erro ao restaurar: {e}")
        return False


def _chat_carregar(user_id: int) -> list:
    """Carrega até 60 mensagens mais recentes do chat do Barista Expert."""
    rows = _fetch(
        "SELECT role, content FROM barista_chats WHERE user_id=%s ORDER BY criado_em ASC LIMIT 60",
        (user_id,), _v=0)
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def _chat_salvar(user_id: int, role: str, content: str) -> None:
    """Salva uma mensagem e mantém no máximo 60 por usuário (FIFO)."""
    _run("INSERT INTO barista_chats (user_id, role, content) VALUES (%s,%s,%s)",
         (user_id, role, content))
    _run("""DELETE FROM barista_chats WHERE user_id=%s AND id NOT IN (
              SELECT id FROM barista_chats WHERE user_id=%s ORDER BY criado_em DESC LIMIT 60)""",
         (user_id, user_id))

def _chat_limpar(user_id: int) -> None:
    _run("DELETE FROM barista_chats WHERE user_id=%s", (user_id,))

def _auto_backup_check(user_id: int) -> None:
    """Cria backup semanal automático se o último foi há mais de 7 dias."""
    if st.session_state.get("_auto_backup_done"):
        return
    st.session_state["_auto_backup_done"] = True
    try:
        rows = _fetch(
            "SELECT criado_em FROM backups WHERE tipo='semanal' AND user_id=%s ORDER BY criado_em DESC LIMIT 1",
            (user_id,), _v=_v())
        now = _dt.datetime.utcnow()
        if not rows or (now - rows[0]["criado_em"]).days >= 7:
            _backup_criar("semanal", "Backup automático semanal", user_id)
    except Exception:
        pass


# ── Helpers ────────────────────────────────────────────────────────────
def _compress_image_bytes(raw_bytes: bytes, max_width: int = 1200,
                          quality: int = 80) -> str:
    """Resize + re-encode JPEG e retorna base64.
    Mantém o original em caso de falha (fallback)."""
    try:
        img = Image.open(BytesIO(raw_bytes))
        # JPEG não aceita RGBA/P/LA
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        # Aplica orientação EXIF (foto de celular costuma vir rotacionada)
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        if img.width > max_width:
            new_h = int(img.height * max_width / img.width)
            img = img.resize((max_width, new_h), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return base64.b64encode(raw_bytes).decode()

def _b64(f) -> Optional[str]:  # f: UploadedFile | None
    """Lê o arquivo enviado, comprime e devolve base64.

    Foto de celular típica: 3-5 MB → resultado ~120-200 KB.
    Sem isso, base64 gigante estoura o WebSocket do Streamlit
    (RangeError: index out of range)."""
    if not f:
        return None
    raw = f.read()
    f.seek(0)
    return _compress_image_bytes(raw, max_width=1200, quality=80)

@st.cache_data(show_spinner=False, max_entries=300)
def _thumbnail(b64_in: Optional[str], max_width: int = 400) -> Optional[str]:
    """Gera thumbnail a partir de base64 existente (cacheado por hash).

    Indispensável para fotos antigas salvas no banco SEM compressão,
    que podem ter vários MB cada. Cacheamos para não reprocessar."""
    if not b64_in:
        return None
    try:
        raw = base64.b64decode(b64_in)
        return _compress_image_bytes(raw, max_width=max_width, quality=70)
    except Exception:
        return b64_in

def _img(b64: Optional[str], w: int = 170) -> None:
    """Renderiza imagem como <img> embutido. Usa thumbnail para
    manter a mensagem WebSocket pequena (~30-80 KB por imagem)."""
    if not b64:
        return
    # 2x para telas Retina, com limite máximo
    thumb = _thumbnail(b64, max_width=min(max(w * 2, 320), 800))
    st.markdown(
        f'<img src="data:image/jpeg;base64,{thumb}" width="{w}" '
        f'style="border-radius:10px;margin-top:4px;display:block;">',
        unsafe_allow_html=True)

def _stars(n: int) -> str:
    n = int(n or 0)
    return "★" * n + "☆" * (5 - n)

def _tag(t: str, accent: bool = False) -> str:
    return f'<span class="tag{" tag-accent" if accent else ""}">{t}</span>'

def _irow(k: str, v: str) -> str:
    return (f'<div class="info-row"><span class="info-key">{_html.escape(str(k))}</span>'
            f'<span class="info-val">{_html.escape(str(v))}</span></div>')

def _ph() -> str:
    return ('<div style="width:150px;height:150px;background:#141414;border:1px solid #2A2A2A;'
            'border-radius:10px;display:flex;align-items:center;justify-content:center;'
            'color:#3A3A3A;font-size:36px;">☕</div>')

METODOS = ["Espresso","Pour Over","French Press","Aeropress",
           "Chemex","Moka Pot","Cold Brew","Sifão","Drip","Outro"]

_LOCAIS_COMPRA = ["Amazon", "Mercado Livre", "Shopee", "Guanabara",
                  "Mundial", "Megabox", "Outros"]

_MOEDORES = ["Starseeker e55Pro", "Acoplado Oster", "Comandante",
             "Hamilton Beach", "Outros"]

# ── IA helpers ─────────────────────────────────────────────────────────

def _get_api_key() -> str:
    """Lê GOOGLE_API_KEY de env ou secrets."""
    return _get_gemini_key()

def _comentario_motor_barista(coffee_info: dict, params: dict) -> str:
    """Gera comentário curto sobre o que esperar deste café com estes parâmetros."""
    if not _get_gemini_key():
        return ""
    try:
        prompt = (
            "Você é um barista sênior. Em 2–3 frases curtas e diretas, "
            "descreva o que esperar na xícara com este café e estes parâmetros. "
            "Seja específico para ESTE café.\n\n"
            f"Café: {coffee_info.get('nome','?')} — Torra {coffee_info.get('torra','Média')} "
            f"— {coffee_info.get('tipo','Grãos')}\n"
            f"Região: {coffee_info.get('regiao','não informada') or 'não informada'}\n"
            f"Notas: {coffee_info.get('notas','não informadas') or 'não informadas'}\n"
            f"Intensidade: {coffee_info.get('intensidade',5)}/12\n\n"
            f"Parâmetros Motor Barista: Dose {params['dose']}g | Yield {params['yield']}g | "
            f"{params['time']}s | {params['temp']}°C | {params['pressure']} bar\n\n"
            "Responda em português. Máximo 70 palavras."
        )
        genai.configure(api_key=_get_gemini_key())
        for _mn in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"):
            try:
                resp = genai.GenerativeModel(_mn).generate_content(prompt)
                return resp.text.strip()
            except Exception as _e:
                if "429" in str(_e) or "quota" in str(_e).lower():
                    continue
                break
        return ""
    except Exception:
        return ""

def _diagnostico_barista_ia(coffee_info: dict, params: dict,
                             real: dict, m_real: dict) -> str:
    """Análise minuciosa como barista sênior — variáveis, resultados e dicas."""
    prompt = f"""Você é um barista sênior com 15 anos de experiência em cafés especiais.

Analise esta extração de forma minuciosa como se estivesse treinando um barista.

## CAFÉ UTILIZADO
- Nome: {coffee_info.get('nome','?')}
- Torra: {coffee_info.get('torra','?')} | Tipo: {coffee_info.get('tipo','?')}
- Região/Origem: {coffee_info.get('regiao','não informada') or 'não informada'}
- Notas de sabor: {coffee_info.get('notas','não informadas') or 'não informadas'}
- Intensidade: {coffee_info.get('intensidade','?')}/12

## PARÂMETROS PLANEJADOS (Motor Barista)
Dose {params['dose']}g | Yield {params['yield']}g | Tempo {params['time']}s | Temp {params['temp']}°C | Pressão {params['pressure']} bar

## O QUE ACONTECEU DE VERDADE
Dose {real['gramas']}g | Yield {real['agua']}g | Tempo {real['tempo']}s | Temp {real['temp_real']}°C | Pressão {real['pressao_real']} bar
TDS: {f"{real['tds']}% (medido)" if real['tds'] > 0 else 'não medido'}

## RESULTADOS CALCULADOS
- Brew Ratio: 1:{real['agua']/max(real['gramas'],0.1):.1f}
- Extraction Yield: {m_real.get('ey',0):.2f}%
- Fluxo médio: {m_real.get('fluxo',0):.2f} g/s
- Status: {m_real.get('status','?')}

Faça uma análise cobrindo:
1. Como as características deste café (torra, origem, notas) afetam o perfil esperado
2. O que os desvios entre planejado vs real revelam sobre a moagem e a máquina
3. O que o EY e o fluxo indicam sobre sub/super-extração ou equilíbrio
4. Dicas práticas e específicas para a PRÓXIMA extração

Seja técnico, direto e acessível. Responda em português brasileiro. Entre 250 e 380 palavras."""

    genai.configure(api_key=_get_gemini_key())
    for _mn in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"):
        try:
            resp = genai.GenerativeModel(_mn).generate_content(prompt)
            return resp.text.strip()
        except Exception as _e:
            if "429" in str(_e) or "quota" in str(_e).lower():
                continue
            raise
    return "⚠️ Cota Gemini esgotada. Ative o faturamento em aistudio.google.com."

# ── Brand wordmark ─────────────────────────────────────────────────────

def _wordmark_html(size: str = "hero", with_tag: bool = True) -> str:
    """Renderiza a marca 'MATEU COFFEE' como wordmark CSS fiel ao logo.

    `size`: 'hero' (login) | 'compact' (topbar) | 'tiny' (footer)
    Usa Cormorant Garamond (serif transicional) — combina com a marca.
    """
    tag = ('<div class="mc-mark-tag">Aplicativo de Café</div>'
           if with_tag else '')
    return (
        f'<div class="mc-mark mc-mark-{size}">'
        f'  <div class="mc-mark-row">'
        f'    <span class="mc-mark-icon">☕</span>'
        f'    <span class="mc-mark-mateu">MATEU</span>'
        f'    <span class="mc-mark-coffee">COFFEE</span>'
        f'  </div>'
        f'  {tag}'
        f'</div>'
    )

# ── Componentes de UX reutilizáveis ────────────────────────────────────

def _step(num: int, title: str, sub: str = "", muted: bool = False) -> None:
    """Cabeçalho de etapa numerada — usado em Nova Extração e em forms longos."""
    cls = "mc-step-num muted" if muted else "mc-step-num"
    st.markdown(
        f'<div class="mc-step">'
        f'<div class="{cls}">{num}</div>'
        f'<div class="mc-step-body">'
        f'<p class="mc-step-title">{title}</p>'
        + (f'<p class="mc-step-sub">{sub}</p>' if sub else '')
        + '</div></div>',
        unsafe_allow_html=True)

def _empty(icon: str, title: str, sub: str, hint: str = "") -> None:
    """Estado vazio com ícone + headline + sub + dica visual."""
    hint_html = f'<div class="mc-empty-hint">→ {hint}</div>' if hint else ""
    st.markdown(
        f'<div class="mc-empty">'
        f'<div class="mc-empty-icon">{icon}</div>'
        f'<p class="mc-empty-title">{title}</p>'
        f'<p class="mc-empty-sub">{sub}</p>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True)

def _relative_date(d) -> str:
    """Devolve 'Hoje', 'Ontem', 'Há N dias' ou data formatada."""
    if d is None:
        return "—"
    if hasattr(d, "date"):
        d = d.date()
    today = _today_local()
    delta = (today - d).days
    if delta < 0:
        return d.strftime("%d/%m/%Y")
    if delta == 0:
        return "Hoje"
    if delta == 1:
        return "Ontem"
    if delta < 7:
        return f"Há {delta} dias"
    if delta < 30:
        w = delta // 7
        return f"Há {w} semana" + ("s" if w > 1 else "")
    if delta < 365:
        m = delta // 30
        return f"Há {m} mês" + ("es" if m > 1 else "")
    return d.strftime("%d/%m/%Y")

def _render_recipe(r: dict) -> None:
    """Renderiza uma receita com badges, métricas, equipamentos, ingredientes
    e passos numerados — layout consistente para a Biblioteca de Receitas."""
    # Descrição
    st.markdown(
        f'<p style="color:#B8B0A8;font-size:14px;line-height:1.6;'
        f'margin:0.5rem 0 1rem">{r["descricao"]}</p>',
        unsafe_allow_html=True)

    # Badges (categoria + dificuldade)
    st.markdown(
        f'<div style="margin-bottom:0.5rem">'
        f'<span class="mc-recipe-badge">{r["categoria"]}</span>'
        f'<span class="mc-recipe-badge neutral">{r["dificuldade"]}</span>'
        f'</div>',
        unsafe_allow_html=True)

    # Métricas em grid 4
    st.markdown(
        f'<div class="mc-recipe-meta">'
        f'  <div class="mc-recipe-meta-cell">'
        f'    <p class="mc-recipe-meta-label">Ratio</p>'
        f'    <p class="mc-recipe-meta-value accent">{r["ratio"]}</p>'
        f'  </div>'
        f'  <div class="mc-recipe-meta-cell">'
        f'    <p class="mc-recipe-meta-label">Tempo</p>'
        f'    <p class="mc-recipe-meta-value">{r["tempo"]}</p>'
        f'  </div>'
        f'  <div class="mc-recipe-meta-cell">'
        f'    <p class="mc-recipe-meta-label">Rendimento</p>'
        f'    <p class="mc-recipe-meta-value">{r["rendimento"]}</p>'
        f'  </div>'
        f'  <div class="mc-recipe-meta-cell">'
        f'    <p class="mc-recipe-meta-label">Moagem</p>'
        f'    <p class="mc-recipe-meta-value">{r["moagem"]}</p>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True)

    # Equipamentos (chips)
    st.markdown('<p class="section-label" style="font-size:11px">'
                'Equipamentos</p>', unsafe_allow_html=True)
    equip_chips = "".join(f'<span class="mc-equip-chip">{e}</span>'
                          for e in r["equipamentos"])
    st.markdown(f'<div class="mc-equip">{equip_chips}</div>',
                unsafe_allow_html=True)

    # Ingredientes
    st.markdown('<p class="section-label" style="font-size:11px">'
                'Ingredientes</p>', unsafe_allow_html=True)
    ing_lis = "".join(f'<li>{i}</li>' for i in r["ingredientes"])
    st.markdown(f'<div class="mc-ingredients"><ul>{ing_lis}</ul></div>',
                unsafe_allow_html=True)

    # Passos numerados
    st.markdown('<p class="section-label" style="font-size:11px">'
                'Passo a passo</p>', unsafe_allow_html=True)
    steps_lis = "".join(f'<li>{p}</li>' for p in r["passos"])
    st.markdown(f'<ol class="mc-steps">{steps_lis}</ol>',
                unsafe_allow_html=True)

    # Fonte
    st.markdown(
        f'<p class="mc-recipe-source">📖 Receita-referência: {r["fonte"]}</p>',
        unsafe_allow_html=True)

    # Botão para aplicar receita na aba Nova Extração
    _dose_match = None
    _yield_match = None
    _tempo_match = None
    _moagem_match = None
    try:
        _ratio_parts = r.get("ratio", "").replace(" ", "").split(":")
        if len(_ratio_parts) == 2:
            _dose_match  = float(_ratio_parts[0]) if _ratio_parts[0].replace(".","").isdigit() else None
            _yield_match = float(_ratio_parts[1]) if _ratio_parts[1].replace(".","").isdigit() else None
    except Exception:
        pass
    _moagem_match = r.get("moagem", "")
    _tempo_str = r.get("tempo", "")
    try:
        _tempo_match = int(_tempo_str.split("–")[0].replace("s","").replace(" ",""))
    except Exception:
        _tempo_match = None

    if st.button(f"⚡ Usar esta receita na Nova Extração",
                 key=f"use_recipe_{r['nome'].replace(' ','_')}",
                 use_container_width=True, type="primary"):
        st.session_state["_recipe_applied"] = {
            "nome":    r["nome"],
            "dose":    _dose_match,
            "yield":   _yield_match,
            "tempo":   _tempo_match,
            "moagem":  _moagem_match,
        }
        st.success("✓ Receita aplicada! Vá para ⚡ Nova Extração.")

# Classificação oficial do café (substitui o campo Fazenda na UI)
CLASSIFICACOES_CAFE = [
    "Especial (>80 pts)",
    "Gourmet",
    "Superior",
    "Tradicional",
    "Extraforte",
]

# ─── Biblioteca de Receitas ────────────────────────────────────────────
# 10 métodos clássicos baseados nas referências mais comentadas:
# James Hoffmann (V60 / French Press / Moka), Campeonato Mundial de
# AeroPress, SCA, padrões clássicos italianos.
RECIPES = [
    {
        "id": "espresso",
        "nome": "Espresso Italiano",
        "metodo": "Espresso",
        "categoria": "Pressão",
        "icon": "⚡",
        "dificuldade": "Intermediário",
        "tempo": "≈30 s extração",
        "rendimento": "Dose dupla · 36 g",
        "ratio": "1 : 2",
        "moagem": "Fina — textura de sal de mesa",
        "descricao": "Base de quase todas as bebidas de café. Padrão moderno do "
                     "campeonato mundial e da maioria das cafeterias.",
        "equipamentos": [
            "Máquina de espresso (9 bar)",
            "Moedor com discos planos ou cônicos",
            "Tamper 58 mm nivelador",
            "Balança 0,1 g",
            "Cronômetro",
        ],
        "ingredientes": [
            "18 g de café especialidade torra média/escura, moído na hora",
            "Água da máquina a 93 °C",
        ],
        "passos": [
            "Pré-aqueça a máquina por ao menos 20 min.",
            "Moa 18 g de café com moagem fina (textura de sal de mesa).",
            "Distribua o pó uniformemente no porta-filtro (WDT com agulha ajuda).",
            "Tampe firme e nivelado (≈15 kg de pressão).",
            "Limpe o resíduo da borda do porta-filtro.",
            "Encaixe e dispare imediatamente. Inicie o cronômetro.",
            "Alvo: 36 g na xícara entre 25 e 30 s.",
            "Tempo curto (<25 s) → moa mais fino. Tempo longo (>30 s) → moa mais grosso.",
        ],
        "fonte": "Padrão WBC moderno (1 : 2 em ≈30 s)",
    },
    {
        "id": "v60",
        "nome": "V60 — The Ultimate Technique",
        "metodo": "Pour Over",
        "categoria": "Filtrado",
        "icon": "💧",
        "dificuldade": "Intermediário",
        "tempo": "≈4 min",
        "rendimento": "1 xícara · 250 ml",
        "ratio": "1 : 16,7",
        "moagem": "Média-fina (um pouco mais fina que sal grosso)",
        "descricao": "Receita do James Hoffmann — o tutorial mais assistido sobre V60. "
                     "Resulta em uma xícara doce, limpa e equilibrada.",
        "equipamentos": [
            "Hario V60 02 (cerâmica ou plástico)",
            "Papel filtro V60 02",
            "Chaleira de bico fino (gooseneck)",
            "Balança 0,1 g com cronômetro",
            "Recipiente / chávena",
        ],
        "ingredientes": [
            "15 g de café especialidade torra clara/média, moído na hora",
            "250 g de água a 95 °C (filtrada)",
        ],
        "passos": [
            "Esquente a água até 95 °C.",
            "Coloque o filtro no V60 e enxágue com água quente para tirar o "
            "gosto de papel e aquecer o coador. Descarte a água.",
            "Adicione 15 g de café moído médio-fino. Faça um pequeno furo no centro.",
            "T = 0 s: Despeje 50 g de água em movimento circular do centro para fora.",
            "Logo após, gire suavemente o V60 (Rao Swirl) para nivelar a cama.",
            "T = 0:45: Comece o pour principal. Vá até 100 g em 10 s.",
            "T = 1:15: Despeje até 200 g em 10 s, com movimento circular.",
            "T = 1:45: Despeje até 250 g em 10 s. Gire suavemente.",
            "T ≈ 3:30: drawdown completo. Bata levemente para nivelar a cama final.",
            "Gire para servir. Beba imediatamente.",
        ],
        "fonte": "James Hoffmann — Ultimate V60 Technique",
    },
    {
        "id": "aeropress",
        "nome": "AeroPress Invertido — Estilo Campeonato",
        "metodo": "Aeropress",
        "categoria": "Imersão",
        "icon": "🚀",
        "dificuldade": "Iniciante",
        "tempo": "≈2 min",
        "rendimento": "1 xícara · 130 ml",
        "ratio": "1 : 7 + diluição",
        "moagem": "Média (textura de areia)",
        "descricao": "Receita do estilo campeonato mundial de AeroPress: extração "
                     "concentrada, depois diluída. Saída suave e brilhante.",
        "equipamentos": [
            "AeroPress + filtro de papel",
            "Moedor",
            "Balança e cronômetro",
            "Chaleira",
        ],
        "ingredientes": [
            "18 g de café moído na hora (moagem média)",
            "100 g de água a 85 °C para extração",
            "30 g de água quente para diluição",
        ],
        "passos": [
            "Posição invertida: coloque o êmbolo na marca 4 do cilindro.",
            "Adicione 18 g de café. Dê uma chacoalhada leve para nivelar.",
            "T = 0:00: Despeje 50 g de água em ≈6 s, molhando todo o pó.",
            "T = 0:30: Despeje mais 50 g (total 100 g). Tampe com filtro encharcado.",
            "T = 1:00: Gire suavemente para misturar e bata na bancada para soltar bolhas.",
            "T = 1:35: Vire o AeroPress sobre o decanter. Comece a pressionar lentamente.",
            "Pressão constante por 30-40 s. Pare quando ouvir o chiado.",
            "Saída: ≈76 g concentrados. Dilua com 30 g de água quente.",
            "Mexa para integrar e sirva.",
        ],
        "fonte": "Padrão World AeroPress Championship",
    },
    {
        "id": "chemex",
        "nome": "Chemex — Café limpo e cristalino",
        "metodo": "Chemex",
        "categoria": "Filtrado",
        "icon": "🧪",
        "dificuldade": "Intermediário",
        "tempo": "≈5 min",
        "rendimento": "2 xícaras · 500 ml",
        "ratio": "1 : 15",
        "moagem": "Média-grossa (textura de areia grossa)",
        "descricao": "Filtro Chemex é mais espesso que o V60 — retém mais óleos e "
                     "dá uma xícara excepcionalmente limpa, com acidez bem definida.",
        "equipamentos": [
            "Chemex 6 cups",
            "Filtro Chemex pré-dobrado (bonded)",
            "Chaleira gooseneck",
            "Balança e cronômetro",
        ],
        "ingredientes": [
            "33 g de café especialidade torra clara/média",
            "500 g de água a 94 °C",
        ],
        "passos": [
            "Abra o filtro com a parte tripla apoiada no bico de vazão.",
            "Enxágue bem com água quente (importante por causa da espessura).",
            "Descarte a água sem mexer no filtro.",
            "Adicione 33 g de café moído médio-grosso.",
            "T = 0: Despeje 70 g (bloom) em espiral. Espere 45 s.",
            "T = 0:45: Vá até 250 g em 30 s, em pours circulares lentos.",
            "T = 1:30: Vá até 400 g em 30 s.",
            "T = 2:15: Vá até 500 g.",
            "Drawdown total entre 4:00 e 5:00. Remova o filtro com cuidado.",
            "Sirva quente — sem balançar a Chemex (a sedimentação dá clareza).",
        ],
        "fonte": "Chemex Coffee Maker — método clássico",
    },
    {
        "id": "french-press",
        "nome": "French Press — Ultimate Recipe",
        "metodo": "French Press",
        "categoria": "Imersão",
        "icon": "🫖",
        "dificuldade": "Iniciante",
        "tempo": "≈9 min",
        "rendimento": "2 xícaras · 500 ml",
        "ratio": "1 : 16,6",
        "moagem": "Média (não grossa, ao contrário do que se diz)",
        "descricao": "Receita do James Hoffmann que mudou paradigma: moagem média, "
                     "espera longa, sem mexer com colher. Resultado limpíssimo.",
        "equipamentos": [
            "French press 1L",
            "Moedor",
            "Balança e cronômetro",
            "Colher grande (não plástica)",
        ],
        "ingredientes": [
            "30 g de café moído na hora (moagem média)",
            "500 g de água a 96 °C",
        ],
        "passos": [
            "Pré-aqueça a French press com água quente. Descarte.",
            "Adicione 30 g de café moído médio.",
            "T = 0: Despeje 500 g de água quente sobre o pó, de uma vez.",
            "T = 4:00: Quebre a crosta de pó na superfície mexendo 3-4 vezes "
            "com a colher. Vão soltar gases.",
            "Retire a espuma e o pó da superfície com a colher (≈30 s).",
            "Deixe descansar de 5 a 8 minutos sem mexer (sedimentação).",
            "Coloque o êmbolo apenas apoiado na superfície — NÃO pressione.",
            "Sirva delicadamente, deixando os últimos 10% no fundo.",
        ],
        "fonte": "James Hoffmann — Ultimate French Press Technique",
    },
    {
        "id": "moka",
        "nome": "Moka Pot — Cafeteira Italiana",
        "metodo": "Moka Pot",
        "categoria": "Pressão",
        "icon": "♨️",
        "dificuldade": "Iniciante",
        "tempo": "≈6 min",
        "rendimento": "Conforme o tamanho da Moka (3, 6, 9 xícaras)",
        "ratio": "Padrão da Moka — preenchimento do funil",
        "moagem": "Média-fina (mais grossa que espresso)",
        "descricao": "Clássico italiano. Café encorpado e intenso, próximo de um "
                     "espresso simples. Truque do Hoffmann: água quente desde o início.",
        "equipamentos": [
            "Moka Pot Bialetti (3, 6 ou 9 xícaras)",
            "Moedor",
            "Chaleira",
            "Fogão",
        ],
        "ingredientes": [
            "Café moído médio-fino o suficiente para preencher o funil sem compactar",
            "Água quente até a válvula de segurança (sem cobri-la)",
        ],
        "passos": [
            "Ferva água em uma chaleira separadamente.",
            "Encha a base da Moka com água quente até logo abaixo da válvula.",
            "Coloque o funil. Preencha com café moído sem compactar — apenas "
            "nivele com o dedo. NÃO use tamper.",
            "Rosqueie a parte de cima com cuidado (atenção: a base está quente).",
            "Leve ao fogão em fogo baixo-médio. Tampa aberta.",
            "Quando o café começar a sair amarelado, fique perto.",
            "Assim que vier um som de chiado e a vazão ficar clara/branca, "
            "remova IMEDIATAMENTE do fogo.",
            "Pare a extração colocando a base sob água fria corrente por 5 s.",
            "Sirva imediatamente — Moka muda muito ao esfriar.",
        ],
        "fonte": "James Hoffmann — How to Make Stovetop Espresso",
    },
    {
        "id": "cold-brew",
        "nome": "Cold Brew — Infusão a Frio",
        "metodo": "Cold Brew",
        "categoria": "Imersão",
        "icon": "🧊",
        "dificuldade": "Iniciante",
        "tempo": "12 a 16 h (geladeira)",
        "rendimento": "1 L de concentrado",
        "ratio": "1 : 8 (concentrado) ou 1 : 12 (pronto)",
        "moagem": "Grossa (textura de pimenta-do-reino grossa)",
        "descricao": "Extração a frio. Doce, baixa acidez, muito refrescante. "
                     "O concentrado guarda na geladeira por até 2 semanas.",
        "equipamentos": [
            "Jarra grande ou frasco de vidro 1,5 L",
            "Coador de papel ou pano (Chemex serve)",
            "Geladeira",
        ],
        "ingredientes": [
            "120 g de café moído grosso (1 : 8 = concentrado) "
            "ou 80 g (1 : 12 = bebida pronta)",
            "1 L de água fria filtrada",
        ],
        "passos": [
            "Pese 120 g de café e moa grosso.",
            "Coloque o café no frasco. Adicione 1 L de água fria.",
            "Mexa bem com uma colher para garantir que todo o pó está molhado.",
            "Tampe e leve à geladeira por 12 a 16 horas.",
            "Coe primeiro em uma peneira fina para tirar o pó grosso.",
            "Filtre o líquido em papel filtro (Chemex/V60) — pode levar 20 min.",
            "Guarde o concentrado em garrafa fechada na geladeira.",
            "Para beber: dilua 1 : 1 com água ou leite, com gelo.",
            "Validade: até 2 semanas na geladeira.",
        ],
        "fonte": "Stumptown Roasters — guia clássico de Cold Brew",
    },
    {
        "id": "cappuccino",
        "nome": "Cappuccino Italiano Clássico",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "☁️",
        "dificuldade": "Avançado",
        "tempo": "≈3 min total",
        "rendimento": "150-180 ml",
        "ratio": "1/3 espresso · 1/3 leite · 1/3 espuma firme",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "O clássico italiano: terços iguais de espresso, leite vaporizado "
                     "e espuma firme e seca. Servido em xícara pequena (180 ml).",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite (350 ml) inox",
            "Termômetro (opcional) ou mão como referência",
            "Xícara de cappuccino 180 ml pré-aquecida",
        ],
        "ingredientes": [
            "1 dose de espresso (18 g → 36 g)",
            "120 ml de leite integral gelado",
        ],
        "passos": [
            "Pré-aqueça a xícara com água quente.",
            "Extraia 1 dose de espresso direto na xícara aquecida (vide receita Espresso).",
            "Encha a jarra com 120 ml de leite gelado.",
            "Posicione o bico do vaporizador 1 cm abaixo da superfície do leite.",
            "Abra o vapor: incorpore ar por 3-4 s (som de 'tch tch') para criar espuma.",
            "Afunde o bico no fundo (sem encostar) e crie um vórtice para integrar.",
            "Pare a 60-65 °C (jarra fica quente demais para segurar).",
            "Bata a jarra na bancada e gire para alinhar leite e espuma.",
            "Despeje delicadamente sobre o espresso. Leve a espuma com a colher por cima.",
            "Sirva imediatamente. Polvilhe cacau ou canela (opcional).",
        ],
        "fonte": "Padrão Italiano (180 ml, 1/3 + 1/3 + 1/3)",
    },
    {
        "id": "latte",
        "nome": "Caffè Latte",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "🥛",
        "dificuldade": "Intermediário",
        "tempo": "≈3 min",
        "rendimento": "250-300 ml",
        "ratio": "1 espresso : 3 leite vaporizado",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "Mais leite que o cappuccino, com microfoam suave em vez de "
                     "espuma firme. Textura aveludada e doce.",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite 500 ml",
            "Xícara grande ou copo 300 ml",
        ],
        "ingredientes": [
            "1 dose de espresso (18 g → 36 g)",
            "200 ml de leite integral gelado",
        ],
        "passos": [
            "Extraia 1 dose de espresso na xícara/copo (vide receita Espresso).",
            "Encha a jarra com 200 ml de leite integral gelado.",
            "Posicione o vaporizador na superfície e abra. Incorpore ar SÓ por 1-2 s "
            "(menos que cappuccino — queremos microfoam, não espuma firme).",
            "Afunde o bico 1 cm e crie um vórtice. Aqueça até 60-65 °C.",
            "Bata a jarra para estourar bolhas grossas. Gire para integrar.",
            "Despeje em fluxo contínuo sobre o espresso, alto e fino no início.",
            "Aproxime a jarra da superfície para começar a desenhar latte art.",
            "Sirva imediatamente.",
        ],
        "fonte": "Padrão SCA — Microfoam latte",
    },
    {
        "id": "flat-white",
        "nome": "Flat White Australiano",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "⚪",
        "dificuldade": "Avançado",
        "tempo": "≈3 min",
        "rendimento": "160-180 ml",
        "ratio": "2 espresso : 3 leite microfoam",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "Estilo australiano/neozelandês: espresso duplo (ristretto) com "
                     "microfoam fininha. Café mais presente que no latte. Sem espuma alta.",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite 350 ml",
            "Xícara 160 ml pré-aquecida",
        ],
        "ingredientes": [
            "1 dose dupla ristretto (20 g → 30-35 g)",
            "120 ml de leite integral gelado",
        ],
        "passos": [
            "Pré-aqueça a xícara.",
            "Extraia 1 dose dupla ristretto (20 g de pó → 30-35 g na xícara em 25-30 s).",
            "Encha a jarra com 120 ml de leite gelado.",
            "Vaporize com MUITO POUCO ar (1 s só) — buscamos textura de tinta acetinada.",
            "Aqueça até 55-60 °C. Microfoam quase invisível.",
            "Bata a jarra. Gire muito até virar uma 'tinta' homogênea.",
            "Despeje em fluxo único e contínuo, baixo na superfície.",
            "Termine com um corte fino — sem 'topo' de espuma.",
            "Diferença para o latte: menos volume, menos espuma, mais café.",
        ],
        "fonte": "Padrão australiano/neozelandês moderno",
    },
]

# ── Coffee Engine ──────────────────────────────────────────────────────
class CoffeeEngine:
    # Perfil sensorial derivado do EY (radar do histórico).
    # Não confundir com as 5 dimensões do Motor Barista interativo,
    # que medem a simulação de variáveis (incluindo Adstringência/canalização).
    ATTRS    = ("Doçura","Acidez","Corpo","Amargor","Finalização")
    TARGET   = (8, 7, 7, 4, 8)
    EY_LOW   = 18.0
    EY_HIGH  = 22.0

    @staticmethod
    def calc(coffee_g: float, water_g: float, tds: Optional[float], time_s: int) -> dict:
        if coffee_g <= 0:
            return {}
        ratio = water_g / coffee_g
        out = {
            "ratio_text": f"1 : {ratio:.1f}",
            "ratio": ratio,
            "ey": 0.0,
            "status": "",
            "delta_color": "off",
            "fluxo": water_g / max(time_s, 1),
        }
        if tds and tds > 0:
            bev = max(water_g - 2.0 * coffee_g, 0)   # retenção ≈ 2× pó
            ey  = (bev * tds) / coffee_g
            out["ey"] = ey
            if ey < CoffeeEngine.EY_LOW:
                out.update(status="Subextraído", delta_color="inverse")
            elif ey <= CoffeeEngine.EY_HIGH:
                out.update(status="Ideal — Sweet Spot", delta_color="off")
            else:
                out.update(status="Superextraído", delta_color="inverse")
        return out

    @staticmethod
    def sensory(ey: float) -> tuple:
        if ey <= 0:  return (7, 7, 7, 5, 7)
        if ey < 18:  return (4, 9, 4, 3, 5)
        if ey > 22:  return (3, 4, 8, 9, 4)
        return (9, 8, 8, 4, 9)

    @staticmethod
    def estimate_ey(coffee_g: float, water_g: float, time_s: int,
                    torra: str = "Média", metodo: str = "Espresso") -> float:
        """Estima EY sem refratômetro (±2-3% de margem). Baseado em modelo SCA/Hoffmann."""
        if coffee_g <= 0 or water_g <= 0:
            return 0.0
        # Retenção por método: espresso retém menos (crema), filtrado retém ~2× pó
        retencao = {"Espresso": 1.5, "Moka Pot": 1.8}.get(metodo, 2.0)
        bev = max(water_g - retencao * coffee_g, 0)
        if bev <= 0:
            return 0.0
        # TDS base estimado por torra (estudo SCA)
        tds_base = {"Clara": 1.35, "Média": 1.45, "Escura": 1.25}.get(torra, 1.45)
        # Ajuste por método: imersão tende a ter TDS menor
        tds_base *= {"Espresso": 1.35, "French Press": 0.88,
                     "Cold Brew": 0.70, "Moka Pot": 1.20}.get(metodo, 1.0)
        # Ajuste por tempo (cinética de extração, cap em 35s para espresso, 4min para filtrado)
        ref_time = 30 if metodo == "Espresso" else 180
        time_factor = min(time_s / ref_time, 1.15)
        estimated_tds = tds_base * (0.75 + 0.5 * time_factor)
        ey = (bev * estimated_tds) / coffee_g
        return round(min(ey, 28.0), 1)

def _dial_in_recomendacao(coffee_id: int, metodo: str, user_id: int) -> dict:
    """Analisa as últimas 3 extrações e retorna recomendação de ajuste de moagem."""
    recentes = _fetch("""
        SELECT gramas, agua_alvo, tempo_extracao, ey, tds, nota_final_stars, clicks_moedor, data
        FROM extracoes
        WHERE coffee_id=%s AND metodo=%s AND user_id=%s
        ORDER BY data DESC, created_at DESC LIMIT 5
    """, (coffee_id, metodo, user_id), _v=_v())

    if not recentes:
        return {"status": "sem_dados"}

    # Calcula médias apenas das extrações com dados válidos
    com_ey  = [r for r in recentes if r.get("ey") and float(r["ey"]) > 0]
    com_nota = [r for r in recentes if r.get("nota_final_stars") and int(r["nota_final_stars"]) > 0]
    n = len(recentes)

    avg_tempo  = sum(int(r["tempo_extracao"] or 0) for r in recentes) / n
    avg_ey     = sum(float(r["ey"]) for r in com_ey) / len(com_ey) if com_ey else 0.0
    avg_nota   = sum(int(r["nota_final_stars"]) for r in com_nota) / len(com_nota) if com_nota else 0.0
    last_clicks = int(recentes[0].get("clicks_moedor") or 0)

    recs = []

    # Diagnóstico EY (prioridade máxima)
    if avg_ey > 0:
        if avg_ey < 18.0:
            recs.append({
                "icone": "⬇️", "cor": "#e74c3c",
                "titulo": f"Sub-extração (EY médio {avg_ey:.1f}%)",
                "acao": "Afine a moagem 1–2 clicks" if last_clicks > 0 else "Afine a moagem",
                "alternativa": f"ou aumente o tempo em 2–3s (atual: {avg_tempo:.0f}s)"
            })
        elif avg_ey > 22.0:
            recs.append({
                "icone": "⬆️", "cor": "#e67e22",
                "titulo": f"Super-extração (EY médio {avg_ey:.1f}%)",
                "acao": "Abra a moagem 1–2 clicks" if last_clicks > 0 else "Abra a moagem",
                "alternativa": f"ou reduza o tempo em 2–3s (atual: {avg_tempo:.0f}s)"
            })
        else:
            recs.append({
                "icone": "✅", "cor": "#27ae60",
                "titulo": f"EY na janela ideal ({avg_ey:.1f}%)",
                "acao": "Mantenha os parâmetros",
                "alternativa": "extração equilibrada"
            })

    # Diagnóstico tempo (só se não há EY para comparar)
    if not com_ey:
        if avg_tempo < 22 and metodo == "Espresso":
            recs.append({
                "icone": "⚡", "cor": "#e74c3c",
                "titulo": f"Fluxo rápido (média {avg_tempo:.0f}s)",
                "acao": "Afine a moagem para aumentar resistência",
                "alternativa": "meta: 25–32s para espresso"
            })
        elif avg_tempo > 38 and metodo == "Espresso":
            recs.append({
                "icone": "🐌", "cor": "#e67e22",
                "titulo": f"Fluxo lento (média {avg_tempo:.0f}s)",
                "acao": "Abra a moagem para aumentar fluxo",
                "alternativa": "meta: 25–32s para espresso"
            })

    # Avaliação sensorial baixa
    if avg_nota > 0 and avg_nota < 2.5 and not recs:
        recs.append({
            "icone": "⭐", "cor": "#8e44ad",
            "titulo": f"Nota sensorial baixa (média {avg_nota:.1f}/5)",
            "acao": "Mude UMA variável por vez: moagem → observe → ajuste",
            "alternativa": "anote o resultado de cada ajuste"
        })

    ultima_data = recentes[0]["data"].strftime("%d/%m") if recentes[0].get("data") else ""
    return {
        "status": "ok",
        "n_extracoes": n,
        "avg_ey": avg_ey,
        "avg_tempo": avg_tempo,
        "avg_nota": avg_nota,
        "last_clicks": last_clicks,
        "ultima_data": ultima_data,
        "recomendacoes": recs,
    }


def _motor_barista_params(torra: str, tipo: str) -> dict:
    """
    Retorna parâmetros pré-definidos para o Motor Barista baseado em torra e tipo,
    buscando um café adocicado com equilíbrio de notas.

    Torra Clara: Extração longa para sacar açúcares, temperatura alta
    Torra Média: Extração equilibrada, temperatura padrão
    Torra Escura: Extração curta para não queimar, temperatura moderada
    """
    # Padrão: dose=18, yield=36, tempo=28, temp=92, pressão=9 (1:2 ratio)
    params = {"dose": 18.0, "yield": 36.0, "time": 28, "temp": 92.0, "pressure": 9.0}

    # Ajustes por torra (visando doçura)
    if torra == "Clara":
        params["time"] = 32  # Tempo maior para extrair mais açúcares
        params["temp"] = 94.0  # Temperatura maior
        params["yield"] = 38  # Yield um pouco maior
    elif torra == "Média":
        params["time"] = 28
        params["temp"] = 92.0
        params["yield"] = 36
    elif torra == "Escura":
        params["time"] = 26  # Tempo menor para não queimar
        params["temp"] = 90.0  # Temperatura menor
        params["yield"] = 34  # Yield menor

    # Ajustes adicionais por tipo
    if tipo == "Moído":
        params["time"] -= 2  # Café moído extrai mais rápido
        params["pressure"] = 8.5

    return params

@st.cache_data(ttl=86400, show_spinner=False)
def _radar(profile: tuple) -> go.Figure:
    attrs = CoffeeEngine.ATTRS
    fig   = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=CoffeeEngine.TARGET, theta=attrs, fill='toself',
        name='Target', line_color='#8A8278', fillcolor='rgba(138,130,120,0.12)'))
    fig.add_trace(go.Scatterpolar(
        r=profile, theta=attrs, fill='toself',
        name='Atual', line_color='#E8722E', fillcolor='rgba(232,114,46,0.22)'))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0,10], gridcolor='#2A2A2A',
                            linecolor='#2A2A2A', tickfont=dict(color='#8A8278', size=9)),
            angularaxis=dict(gridcolor='#2A2A2A', linecolor='#2A2A2A',
                             tickfont=dict(color='#B8B0A8', size=10))),
        showlegend=True,
        legend=dict(font=dict(color='#B8B0A8', size=11), bgcolor='rgba(0,0,0,0)'),
        height=280, margin=dict(l=20,r=20,t=20,b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#B8B0A8', size=11, family='Inter'),
    )
    return fig

# ── Motor Barista HTML ─────────────────────────────────────────────────
_MOTOR_BARISTA_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg:      #0A0A0A;
    --card:    #141414;
    --text:    #F5EDE8;
    --muted:   #8A8278;
    --label:   #B8B0A8;
    --accent:  #E8722E;
    --accent2: #F08842;
    --border:  #2A2A2A;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);padding:16px 4px 4px}
  .layout{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:680px){.layout{grid-template-columns:1fr}}
  .card{background:var(--card);border-radius:8px;padding:18px;border:1px solid var(--border)}
  .card h2{color:var(--accent);font-size:11pt;margin-bottom:16px;border-left:3px solid var(--accent);padding-left:9px;font-weight:700}
  .cg{margin-bottom:14px}
  .cl{display:flex;justify-content:space-between;font-weight:600;font-size:9.5pt;margin-bottom:4px}
  .cl span{color:var(--accent)}
  input[type=range]{width:100%;accent-color:var(--accent);cursor:pointer;height:4px}
  .ht{font-size:7.5pt;color:var(--muted);margin-top:3px;line-height:1.4}
  .chart-wrap{position:relative;height:260px;width:100%}
  .results{margin-top:14px;background:#1C1C1C;border-radius:8px;padding:14px;border:1px solid var(--border)}
  .rt{font-size:9.5pt;font-weight:700;color:var(--accent);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em}
  .vb{font-size:11pt;font-weight:700;color:#F5EDE8;background:#3A1E10;padding:10px 12px;border-radius:6px;border-left:4px solid var(--accent);margin-bottom:8px}
  .vd{font-size:9pt;color:var(--label);line-height:1.55}
</style>
</head>
<body>
<div class="layout">
  <div class="card">
    <h2>Variáveis de Entrada</h2>

    <div class="cg">
      <div class="cl"><label>Massa de Café (Dose)</label><span id="vd">18.0 g</span></div>
      <input type="range" id="id" min="14" max="22" step="0.5" value="18">
      <div class="ht">Quantidade de pó no porta-filtro. Impacta o corpo e resistência ao fluxo.</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Volumetria na Xícara (Yield)</label><span id="vy">36.0 g</span></div>
      <input type="range" id="iy" min="20" max="300" step="1" value="36">
      <div class="ht">Peso final do líquido extraído. Define a taxa de concentração (Ratio).</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Tempo de Extração</label><span id="vt">28 s</span></div>
      <input type="range" id="it" min="10" max="180" step="1" value="28">
      <div class="ht">Tempos baixos subextraem; altos superextraem.</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Temperatura da Água</label><span id="vp">92.0 °C</span></div>
      <input type="range" id="ip" min="85" max="98" step="0.5" value="92">
      <div class="ht">Temperaturas elevadas dissolvem mais amargor; baixas geram acidez crua.</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Pressão da Bomba</label><span id="vb">9.0 bar</span></div>
      <input type="range" id="ib" min="1" max="20" step="0.5" value="9">
      <div class="ht">Fora de 8–10 bar gera canalizações ou falta de crema.</div>
    </div>
  </div>

  <div class="card">
    <h2>Perfil Sensorial Resultante</h2>
    <div class="chart-wrap"><canvas id="rc"></canvas></div>
    <div class="results">
      <div class="rt">Diagnóstico do Especialista:</div>
      <div class="vb" id="vtitle">Balanço Perfeito</div>
      <div class="vd" id="vtext">Carregando análise...</div>
    </div>
  </div>
</div>

<script>
const chart = new Chart(document.getElementById('rc').getContext('2d'), {
  type: 'radar',
  data: {
    labels: ['Acidez','Amargor','Corpo','Doçura','Adstringência'],
    datasets:[{
      data:[5,5,5,5,1],
      backgroundColor:'rgba(232,114,46,0.18)',
      borderColor:'rgba(232,114,46,1)',
      borderWidth:2,
      pointBackgroundColor:'rgba(232,114,46,1)',
      pointRadius:4
    }]
  },
  options:{
    responsive:true,maintainAspectRatio:false,
    scales:{r:{
      angleLines:{color:'#2A2A2A'},grid:{color:'#2A2A2A'},
      pointLabels:{font:{size:10,weight:'bold'},color:'#F5EDE8'},
      suggestedMin:0,suggestedMax:10,ticks:{display:false}
    }},
    plugins:{legend:{display:false}}
  }
});

function sim(){
  const d=+document.getElementById('id').value,
        y=+document.getElementById('iy').value,
        t=+document.getElementById('it').value,
        p=+document.getElementById('ip').value,
        b=+document.getElementById('ib').value;

  document.getElementById('vd').innerText=d.toFixed(1)+' g';
  document.getElementById('vy').innerText=y.toFixed(1)+' g';
  document.getElementById('vt').innerText=t+' s';
  document.getElementById('vp').innerText=p.toFixed(1)+' °C';
  document.getElementById('vb').innerText=b.toFixed(1)+' bar';

  const ratio=y/d;
  let ac=5,am=5,co=5,sw=5,as=1;

  if(ratio>2.4){ac-=(ratio-2.4)*1.5;am+=(ratio-2.4)*2;co-=(ratio-2.4)*1.8;sw-=(ratio-2.4)*1.2}
  else if(ratio<1.7){ac+=(1.7-ratio)*2.5;am-=(1.7-ratio)*2;co+=(1.7-ratio)*2;sw-=(1.7-ratio)*1.5}

  if(t<22){ac+=(22-t)*0.3;am-=(22-t)*0.25;sw-=(22-t)*0.4;co-=(22-t)*0.2}
  else if(t>34){am+=(t-34)*0.4;ac-=(t-34)*0.2;sw-=(t-34)*0.3;as+=(t-34)*0.5}

  const dT=p-92;
  if(dT>0){am+=dT*0.4;ac-=dT*0.2}
  else{ac+=Math.abs(dT)*0.4;am-=Math.abs(dT)*0.3;sw-=Math.abs(dT)*0.2}

  if(b>10){as+=(b-10)*1;am+=(b-10)*0.4}
  else if(b<8){co-=(8-b)*1;sw-=(8-b)*0.4}

  const cl=v=>Math.max(0,Math.min(10,v));
  ac=cl(ac);am=cl(am);co=cl(co);sw=cl(sw);as=cl(as);

  chart.data.datasets[0].data=[ac.toFixed(1),am.toFixed(1),co.toFixed(1),sw.toFixed(1),as.toFixed(1)];
  chart.update();

  let ti="Balanço Perfeito",
      tx="Extração simétrica. Parâmetros em conformidade com os padrões SCA. Acidez brilhante, doçura limpa e corpo aveludado.";
  if(am>7&&ac<3.5){ti="Superextração Crítica (Amargo e Seco)";tx="A água dissolveu compostos pesados da celulose do grão. O café apresenta corpo fino/ralo porém muito amargo, com sensação de queima e finalização cinzenta."}
  else if(ac>7&&am<3.5){ti="Subextração (Ácido Macetado e Ralo)";tx="A extração foi interrompida antes da dissolução dos açúcares complexos. O resultado é um café agressivamente azedo, corpo excessivamente fino e sem finalização."}
  else if(co>7.2&&ratio<1.6){ti="Concentrado / Ristretto denso";tx="Alta concentração de óleos insolúveis e coloides. Corpo extremamente pesado e espesso, com potência ácida elevada. Perfil xaroposo."}
  else if(as>4){ti="Canalização Hidráulica Detectada";tx="Fissuras no bolo de café causadas por alta pressão ou moagem irregular geraram caminhos preferenciais. O café amarra a boca como banana verde."}

  document.getElementById('vtitle').innerText=ti;
  document.getElementById('vtext').innerText=tx;
}

['id','iy','it','ip','ib'].forEach(id=>document.getElementById(id).addEventListener('input',sim));
sim();
</script>
</body>
</html>"""

# ── Cronômetro de extração ─────────────────────────────────────────────
_TIMER_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  :root{--bg:#0A0A0A;--card:#141414;--text:#F5EDE8;--accent:#E8722E;--border:#2A2A2A;--muted:#8A8278;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Inter",sans-serif;background:var(--bg);padding:10px 0 0}
  .wrap{display:flex;align-items:center;gap:16px;background:var(--card);border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:12px;padding:12px 18px;flex-wrap:wrap}
  .disp{font-size:40px;font-weight:800;color:var(--text);letter-spacing:-0.03em;font-variant-numeric:tabular-nums;min-width:110px}
  .disp.run{color:var(--accent)}
  .btns{display:flex;gap:8px;flex-wrap:wrap}
  button{background:#1C1C1C;border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;font-weight:600;padding:9px 16px;cursor:pointer;transition:all .15s;white-space:nowrap}
  button:hover{background:#242424;border-color:#3A3A3A}
  .btn-go{background:var(--accent);border-color:var(--accent);color:#0A0A0A}
  .btn-go:hover{background:#F08842}
  .laps{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}
  .lap{background:#1C1C1C;border:1px solid var(--border);border-radius:6px;padding:3px 9px;font-size:11px;color:var(--muted);font-weight:600}
  .note{font-size:11px;color:var(--muted);margin-top:3px}
</style>
</head>
<body>
<div class="wrap">
  <div id="disp" class="disp">0:00.0</div>
  <div style="flex:1">
    <div class="btns">
      <button class="btn-go" id="btn" onclick="toggle()">▶ Iniciar</button>
      <button onclick="lap()">⚑ Lap</button>
      <button onclick="reset()">↺ Zerar</button>
    </div>
    <div class="laps" id="laps"></div>
    <div class="note" id="note">Pressione ▶ quando começar a extração</div>
  </div>
</div>
<script>
let ms=0,iv=null,laps=[];
function fmt(ms){const s=Math.floor(ms/1000),m=Math.floor(s/60);return m+':'+(s%60).toString().padStart(2,'0')+'.'+Math.floor((ms%1000)/100);}
function toggle(){
  if(iv){clearInterval(iv);iv=null;document.getElementById('btn').textContent='▶ Continuar';document.getElementById('disp').className='disp';document.getElementById('note').textContent='Pausado — '+fmt(ms);}
  else{const t=Date.now()-ms;iv=setInterval(()=>{ms=Date.now()-t;document.getElementById('disp').textContent=fmt(ms);},50);document.getElementById('btn').textContent='⏸ Pausar';document.getElementById('disp').className='disp run';document.getElementById('note').textContent='Cronômetro rodando...';}
}
function lap(){laps.push(fmt(ms));const el=document.getElementById('laps');el.innerHTML=laps.map((l,i)=>`<span class="lap">#${i+1} ${l}</span>`).join('');}
function reset(){clearInterval(iv);iv=null;ms=0;laps=[];document.getElementById('disp').textContent='0:00.0';document.getElementById('disp').className='disp';document.getElementById('btn').textContent='▶ Iniciar';document.getElementById('laps').innerHTML='';document.getElementById('note').textContent='Pressione ▶ quando começar a extração';}
</script>
</body>
</html>"""

# ── Vision · leitura de embalagem ──────────────────────────────────────
def _analisar_embalagem(b64_img: str) -> dict:
    """Analisa foto de embalagem de café usando Gemini Vision."""
    img_bytes = _b64mod.b64decode(b64_img)
    pil_img = Image.open(_io_mod.BytesIO(img_bytes))

    prompt = (
        "Analise esta embalagem de café. "
        "Retorne APENAS um JSON com os campos:\n"
        "  nome: string (marca + nome do café),\n"
        "  fazenda: string ou null,\n"
        "  regiao: string ou null (país/estado de origem),\n"
        "  torra: \"Clara\" | \"Média\" | \"Escura\",\n"
        "  tipo: \"Grãos\" | \"Moído\",\n"
        "  notas: string (notas de sabor se visíveis, senão null),\n"
        "  tamanho_pacote: 250 | 500 | 1000 (em g, ou null),\n"
        "  classificacao_cafe: \"Specialty\" | \"Premium\" | \"Commodity\" | null "
        "(baseado em indícios na embalagem como pontuação SCA, certificações, origem, etc).\n"
        "Se um campo não for identificável, use null. "
        "Responda SOMENTE o JSON, sem markdown."
    )

    genai.configure(api_key=_get_gemini_key())
    for _mn in ("gemini-2.0-flash", "gemini-1.5-flash"):
        try:
            resp = genai.GenerativeModel(_mn).generate_content([pil_img, prompt])
            raw = resp.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception as _e:
            if "429" in str(_e) or "quota" in str(_e).lower():
                continue
            raise
    raise RuntimeError("Cota Gemini esgotada. Ative o faturamento em aistudio.google.com.")

_APP_VERSION = "3.5.3"

@st.dialog("Sobre o Mateu Coffee")
def _about_dialog():
    """Tela 'Sobre' — abre ao clicar na marca; fecha ao clicar fora."""
    b64 = _logo_b64()
    logo_html = (f'<img src="data:image/webp;base64,{b64}" alt="Mateu Coffee" '
                 f'style="max-width:300px;width:100%;height:auto;display:block;'
                 f'margin:0 auto">') if b64 else "<h2>MATEU COFFEE</h2>"
    st.markdown(
        f'<div style="text-align:center;padding:1rem 0 0.5rem">{logo_html}'
        f'<p style="margin:1.25rem 0 0.25rem;font-size:15px;color:var(--mc-text)">'
        f'Versão <b>{_APP_VERSION}</b></p>'
        f'<p style="margin:0.25rem 0;font-size:13px;color:var(--mc-text-2)">'
        f'Criado em junho de 2026</p>'
        f'<p style="margin:0.75rem 0 0;font-size:14px;color:var(--mc-text)">'
        f'Desenvolvido por <b>Leandro Ribeiro</b></p></div>',
        unsafe_allow_html=True)

@st.dialog("Recuperar acesso")
def _forgot_password_dialog():
    st.markdown(
        '<p style="font-size:14px;color:var(--mc-text-2);margin-bottom:1.25rem;line-height:1.6">'
        'Informe seu e-mail e geraremos uma senha temporária para você entrar.</p>',
        unsafe_allow_html=True)
    fp_email = st.text_input("E-mail cadastrado", placeholder="seu@email.com", key="fp_email_input")
    if st.button("Gerar senha temporária", type="primary", use_container_width=True, key="fp_gerar_btn"):
        if not fp_email.strip():
            st.error("Informe seu e-mail.")
        else:
            result = _fetch("SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s)",
                            (fp_email.strip(),), _v=0)
            if not result:
                st.error("E-mail não encontrado.")
            else:
                import string as _str
                tmp_pwd = ''.join(secrets.choice(_str.ascii_letters + _str.digits) for _ in range(10))
                _run("UPDATE usuarios SET senha_hash=%s WHERE LOWER(email)=LOWER(%s)",
                     (_hash_senha(tmp_pwd), fp_email.strip().lower()))
                st.success("Senha temporária gerada com sucesso!")
                st.code(tmp_pwd, language=None)
                st.caption("Copie e use para entrar. Troque a senha depois nas configurações.")

# ── Main ───────────────────────────────────────────────────────────────
def main():
    _init_db()

    # Slot fixo de cookie: SEMPRE renderizado (mesma posição na árvore de
    # elementos em todos os runs). Se aparecesse/sumisse condicionalmente,
    # o Streamlit remontaria os st.tabs e voltaria para a 1ª aba a cada
    # primeira interação após login/logout.
    _pend  = st.session_state.pop('_pending_cookie', None)
    _clear = st.session_state.pop('_clear_cookie', False)
    if _pend:
        _js = (f"window.parent.document.cookie='{_COOKIE_NAME}={_pend[0]}; "
               f"max-age={30*86400}; path=/; SameSite=Lax';")
    elif _clear:
        _js = f"window.parent.document.cookie='{_COOKIE_NAME}=; max-age=0; path=/';"
    else:
        _js = ""
    components.html(f"<script>{_js}</script>", height=0)

    # Dialog "Recuperar senha"
    if st.session_state.get("_show_forgot"):
        st.session_state.pop("_show_forgot")
        _forgot_password_dialog()

    # Dialog "Sobre" — aberto pelo clique na marca (?about=1), em qualquer estado
    if "about" in st.query_params:
        del st.query_params["about"]
        _about_dialog()

    # ── Google OAuth callback ────────────────────────────────────────────
    _g_code  = st.query_params.get("code")
    _g_error = st.query_params.get("error")
    if _g_code and 'user_id' not in st.session_state:
        st.query_params.clear()
        _g_result = _login_google(_g_code)
        if _g_result == LoginResult.OK:
            uid = st.session_state.get('user_id')
            if uid:
                try:
                    _tok = secrets.token_urlsafe(32)
                    _exp = _now_local() + timedelta(days=30)
                    _run("UPDATE usuarios SET remember_token=%s, remember_token_expires=%s WHERE id=%s",
                         (_tok, _exp, uid))
                    st.session_state['remember_token'] = _tok
                    st.session_state['_pending_cookie'] = (_tok, _exp)
                    st.query_params["mc_token"] = _tok
                except Exception:
                    pass
            st.toast("Login com Google realizado!", icon="✅")
            st.rerun()
        else:
            st.error("Falha no login com Google. Tente novamente.")
    elif _g_error:
        st.query_params.clear()

    # ── Autenticação ────────────────────────────────────────────────────
    if 'user_id' not in st.session_state:
        if not _check_remember_token():
            # Container único — centralização via CSS (sem skeleton de colunas)
            col_main = st.container()
            with col_main:
                # Logo + slogan da marca (apenas no login)
                st.markdown('<div class="mc-login-hero">', unsafe_allow_html=True)
                _load_logo(max_width=560)
                st.markdown(
                    '<p style="text-align:center;font-family:\'DM Serif Display\',Georgia,'
                    'serif;font-style:italic;font-size:20px;line-height:1.6;'
                    'color:var(--mc-text-2);max-width:400px;margin:0.75rem auto 0">'
                    'Para baristas, entusiastas e apaixonados por café. '
                    'Para mim e para você também.</p>'
                    '</div>',
                    unsafe_allow_html=True)

                tab_login, tab_cadastro = st.tabs(["  Entrar  ", "  Criar Conta  "])

                with tab_login:
                    st.markdown(
                        '<p class="mc-step-title" style="margin:0.5rem 0 1.25rem">'
                        'Bem-vindo de volta</p>',
                        unsafe_allow_html=True)

                    # Botão Google OAuth (só aparece se GOOGLE_CLIENT_ID configurado)
                    _g_url = _google_auth_url()
                    if _g_url:
                        st.markdown(
                            f'<a href="{_g_url}" target="_self" style="text-decoration:none">'
                            f'<div style="display:flex;align-items:center;justify-content:center;'
                            f'gap:10px;background:#fff;border:1.5px solid #dadce0;border-radius:8px;'
                            f'padding:10px 16px;cursor:pointer;font-size:15px;font-weight:500;'
                            f'color:#3c4043;margin-bottom:0.75rem;transition:box-shadow .2s">'
                            f'<svg width="20" height="20" viewBox="0 0 48 48">'
                            f'<path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.7 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.8 6.1C12.3 13 17.7 9.5 24 9.5z"/>'
                            f'<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17z"/>'
                            f'<path fill="#FBBC05" d="M10.4 28.6A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.9-4.6L2.6 13.3A23.9 23.9 0 0 0 0 24c0 3.8.9 7.4 2.6 10.7l7.8-6.1z"/>'
                            f'<path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.5-5.8c-2 1.4-4.6 2.3-7.7 2.3-6.3 0-11.6-4.2-13.6-10l-7.8 6.1C6.6 42.6 14.6 48 24 48z"/>'
                            f'</svg>'
                            f'Entrar com Google</div></a>',
                            unsafe_allow_html=True)
                        st.markdown(
                            '<div style="display:flex;align-items:center;gap:8px;margin:0.5rem 0">'
                            '<hr style="flex:1;border:none;border-top:0.5px solid var(--mc-border);margin:0">'
                            '<span style="color:var(--mc-text-3);font-size:12px;letter-spacing:.08em">ou</span>'
                            '<hr style="flex:1;border:none;border-top:0.5px solid var(--mc-border);margin:0">'
                            '</div>',
                            unsafe_allow_html=True)

                    email = st.text_input("E-mail", key="login_email",
                                          placeholder="seu@email.com")
                    senha = st.text_input("Senha", type="password", key="login_senha",
                                          placeholder="••••••••")
                    remember_me = st.checkbox("Manter-me conectado por 30 dias",
                                              value=True, key="login_remember")

                    if st.button("Entrar", type="primary",
                                 use_container_width=True, key="btn_login"):
                        outcome = _login(email, senha, remember=remember_me)
                        if outcome == LoginResult.OK:
                            if remember_me and st.session_state.get('remember_token'):
                                st.query_params["mc_token"] = st.session_state['remember_token']
                            st.toast("Login realizado", icon="✅")
                            st.rerun()
                        elif outcome == LoginResult.RATE_LIMITED:
                            st.error("Muitas tentativas. Aguarde 10 minutos antes de tentar novamente.")
                        elif outcome == LoginResult.INVALID:
                            st.error("E-mail ou senha incorretos. Verifique e tente de novo.")
                        else:
                            st.error("Erro ao acessar o banco de dados. Tente novamente em instantes.")

                    if st.button("Esqueci minha senha", use_container_width=True, key="btn_forgot"):
                        st.session_state["_show_forgot"] = True
                        st.rerun()

                with tab_cadastro:
                    st.markdown(
                        '<p class="mc-step-title" style="margin:0.5rem 0 0.25rem">'
                        'Crie sua conta</p>'
                        '<p class="mc-step-sub" style="margin:0 0 1.25rem">'
                        'É grátis e leva 30 segundos. Seus cafés ficam guardados '
                        'só para você.</p>',
                        unsafe_allow_html=True)
                    new_email = st.text_input("E-mail", key="cadastro_email",
                                              placeholder="seu@email.com")
                    new_senha = st.text_input("Senha (mínimo 6 caracteres)",
                                              type="password", key="cadastro_senha",
                                              placeholder="••••••••")
                    new_senha_conf = st.text_input("Confirmar senha", type="password",
                                                   key="cadastro_senha_conf",
                                                   placeholder="••••••••")

                    if st.button("Criar conta", type="primary",
                                 use_container_width=True, key="btn_cadastrar"):
                        if not new_email or not new_senha:
                            st.error("Preencha todos os campos.")
                        elif new_senha != new_senha_conf:
                            st.error("As senhas não conferem.")
                        elif len(new_senha) < 6:
                            st.error("A senha precisa ter pelo menos 6 caracteres.")
                        else:
                            try:
                                hash_pwd = _hash_senha(new_senha)
                                _run("INSERT INTO usuarios (email, senha_hash) VALUES (%s, %s)",
                                     (new_email.strip().lower(), hash_pwd))
                                st.toast("Conta criada com sucesso", icon="✅")
                                st.success("Pronto! Vá na aba **Entrar** para começar.")
                            except Exception:
                                st.error("Esse e-mail já está cadastrado.")
        return

    # ── App Logado ──────────────────────────────────────────────────────
    # Topbar compacta: logo · email · sair (uma linha só)
    user_email_display = st.session_state.get('user_email', '')
    initial = (user_email_display[:1] or "?").upper()

    # Toggle Dark/Light mode — persiste na sessão
    _light_mode = st.session_state.get('_light_mode', False)

    col_brand, col_user, col_theme, col_logout = st.columns([0.60, 0.25, 0.07, 0.08], gap="small")
    with col_brand:
        # Marca oficial — usa o PNG real do logo (cacheado em base64)
        logo_b64 = _logo_b64()
        if logo_b64:
            st.markdown(
                f'<div style="padding-top:4px">'
                f'<a href="?about=1" target="_self" title="Sobre o Mateu Coffee">'
                f'<img src="data:image/webp;base64,{logo_b64}" alt="Mateu Coffee" '
                f'class="mc-topbar-logo" style="height:94px;width:auto;display:block;'
                f'cursor:pointer"></a>'
                f'</div>',
                unsafe_allow_html=True)
        else:
            # Fallback elegante caso o PNG não esteja disponível
            st.markdown(
                '<div style="padding-top:4px">'
                + _wordmark_html("compact", with_tag=False) +
                '</div>',
                unsafe_allow_html=True)
    with col_user:
        st.markdown(
            f'<div class="mc-topbar-user" style="justify-content:flex-end;padding-top:6px">'
            f'<div class="mc-topbar-user-avatar">{initial}</div>'
            f'<span>{user_email_display}</span>'
            f'</div>',
            unsafe_allow_html=True)
    with col_theme:
        _theme_label = "☀️" if _light_mode else "🌙"
        if st.button(_theme_label, use_container_width=True, key="btn_theme",
                     help="Alternar entre modo escuro e claro"):
            st.session_state['_light_mode'] = not _light_mode
            st.rerun()
    with col_logout:
        if st.button("Sair", use_container_width=True, key="btn_logout",
                     help="Sair da conta"):
            _logout()
            st.rerun()

    # Aplica classe light mode no body via JS
    if _light_mode:
        st.markdown(
            '<script>document.body.classList.add("mc-light");</script>'
            '<style>body, .stApp, .block-container { background-color: #FAF7F4 !important; }</style>',
            unsafe_allow_html=True)

    # Widget de consumo (hoje · semana · média · total)
    _show_daily_consumption()

    _auto_backup_check(st.session_state['user_id'])

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab_barista, tab5, tab6, tab7 = st.tabs([
        "  ☕ Novo Café  ", "  ⚡ Nova Extração  ", "  Meus Cafés  ", "  📅 Histórico  ",
        "  ✨ Barista Expert  ", "  📖 Receitas  ", "  🫘 Cápsulas  ", "  🛡️ Backup  "])

    user_id = st.session_state['user_id']

    # ── Tab Barista Expert ─────────────────────────────────────────────
    with tab_barista:
        st.markdown('<p class="section-label">✨ Barista Expert</p>', unsafe_allow_html=True)

        # ── Seção superior: Café Melhor Avaliado + Promoções (2 colunas)
        col_cafe, col_promo = st.columns(2, gap="large")

        # Café com melhor avaliação
        with col_cafe:
            st.markdown('<p class="info-key" style="margin-bottom:0.5rem">Café Melhor Avaliado</p>', unsafe_allow_html=True)
            best_coffee = _fetch("""
                SELECT nome, torra, intensidade, classificacao, notas, regiao
                FROM coffees
                WHERE user_id = %s AND classificacao > 0
                ORDER BY classificacao DESC
                LIMIT 1
            """, (user_id,), _v=_v())

            if best_coffee:
                bc = best_coffee[0]
                st.markdown(f"""
                <div style="background:var(--mc-orange-soft);border:1px solid var(--mc-orange);
                border-radius:12px;padding:16px;margin:0">
                    <p style="margin:0 0 8px;font-weight:700;color:var(--mc-orange);font-size:14px">{_html.escape(bc['nome'])}</p>
                    <p style="margin:0;color:var(--mc-text-2);font-size:12px">
                    <strong>Torra:</strong> {_html.escape(bc['torra'])} | <strong>Intensidade:</strong> {bc['intensidade']}/12
                    </p>
                    <p style="margin:6px 0 0;color:var(--mc-text-3);font-size:12px">{_html.escape(bc['regiao'] or '—')}</p>
                    <p style="margin:8px 0 0;color:var(--mc-text);font-size:11px">{_html.escape(bc['notas'] or '(sem notas)')}</p>
                    <p style="margin:8px 0 0;font-size:18px;color:var(--mc-orange)">{'⭐' * int(bc['classificacao'])}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:20px;color:var(--mc-text-3)">'
                    '<p>Cadastre e avalie seus primeiros cafés</p>'
                    '</div>', unsafe_allow_html=True)

        # Destaque do Dia — rotativo (1 dica por dia)
        _DICAS_BARISTA = [
            ("Acidez agressiva?", "Aumente a temperatura da água em 2°C ou afine a moagem. Temperaturas baixas subextraem compostos doces."),
            ("Café amargo?", "Abra a moagem 1–2 cliques ou reduza a temperatura em 2°C. Superextração dissolve compostos amargos pesados."),
            ("Crema rala ou ausente?", "Verifique a frescura do grão (ideal: 5–21 dias pós-torra) e a pressão da bomba (alvo: 9 bar)."),
            ("Fluxo rápido demais?", "Afine a moagem. Cada clique faz diferença — mude 1 clique por vez e registre o resultado."),
            ("Brew ratio correto?", "Espresso clássico: 1:2 (18g → 36g em 25–30s). Pour over: 1:15 a 1:16. Registre cada variação."),
            ("Degaseificação?", "Grãos muito frescos (< 5 dias pós-torra) liberam CO₂ em excesso e criam barreira à extração. Espere."),
            ("Água importa?", "Água filtrada (TDS 75–150 ppm) extraí melhor. Água muito mole sub-extraí; muito dura, super-extraí."),
            ("EY ideal?", "Extraction Yield entre 18–22% é a janela de ouro. Abaixo = ácido e raso. Acima = amargo e adstringente."),
            ("Temperatura real?", "Cada grau conta: grãos de torra clara pedem 94–96°C; torra escura, 88–92°C para não queimar."),
            ("Consistência primeiro?", "Antes de mudar dois parâmetros, mude um só. Anote o resultado. Só assim você sabe o que causou o quê."),
            ("Moagem e tempo?", "Moagem mais fina = mais resistência = fluxo mais lento = mais extração. Afine para aumentar corpo."),
            ("French Press limpa?", "Técnica Hoffmann: moagem média (não grossa), 9 min de espera, sem mexer, decante o fundo. Xícara límpida."),
            ("V60 desnivelado?", "Após o bloom, gire suavemente o V60 (Rao Swirl) para nivelar a cama e garantir extração uniforme."),
            ("AeroPress versátil?", "No método invertido, você controla 100% o tempo de imersão antes de pressionar. Experimente 1:30 a 2:30."),
            ("Chemex com filtro grosso?", "O filtro bonded da Chemex é 3× mais espesso que o V60 — retem óleos e cria xícara excepcionalmente limpa."),
        ]
        _dica_idx = _today_local().toordinal() % len(_DICAS_BARISTA)
        _dica_titulo, _dica_texto = _DICAS_BARISTA[_dica_idx]

        with col_promo:
            st.markdown('<p class="info-key" style="margin-bottom:0.5rem">Dica do Dia</p>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #E8722E 0%, #F08842 100%);
            border-radius:12px;padding:16px;margin:0;color:#0A0A0A">
                <p style="margin:0 0 8px;font-weight:700;font-size:14px">🎯 {_html.escape(_dica_titulo)}</p>
                <p style="margin:0;font-size:12px;line-height:1.6">{_html.escape(_dica_texto)}</p>
                <p style="margin:12px 0 0;font-size:11px;opacity:0.9">💡 Use o chat abaixo para perguntas específicas</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Chat do Barista Expert
        st.markdown('<p class="section-label">Chat com Barista Expert</p>', unsafe_allow_html=True)

        # Carregar histórico persistido do DB
        _chat_msgs = _chat_carregar(user_id)

        # Histórico de mensagens (acima do input)
        if _chat_msgs:
            for msg in _chat_msgs:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div style="display:flex;justify-content:flex-end;margin:8px 0">'
                        f'<div style="background:var(--mc-orange);color:#0A0A0A;'
                        f'border-radius:12px;border-bottom-right-radius:0;'
                        f'padding:12px 16px;max-width:70%;font-size:14px;line-height:1.5">'
                        f'{_html.escape(msg["content"])}'
                        f'</div></div>',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div style="display:flex;justify-content:flex-start;margin:8px 0">'
                        f'<div style="background:var(--mc-surface);border:1px solid var(--mc-border);'
                        f'border-radius:12px;border-bottom-left-radius:0;'
                        f'padding:12px 16px;max-width:70%;font-size:14px;line-height:1.6;color:var(--mc-text)">'
                        f'{_html.escape(msg["content"])}'
                        f'</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:40px 20px;color:var(--mc-text-3)">'
                '<p style="font-size:14px">Faça uma pergunta sobre café, equipamentos, técnicas ou defeitos de extração...</p>'
                '</div>', unsafe_allow_html=True)

        # Botão para limpar chat
        if _chat_msgs:
            if st.button("🔄 Novo Chat", use_container_width=True):
                _chat_limpar(user_id)
                st.rerun()

        # Input do usuário (abaixo das mensagens)
        col_input, col_send = st.columns([0.9, 0.1], gap="small")
        with col_input:
            pergunta = st.text_input(
                "Pergunta ao Barista Expert...",
                placeholder="Ex: Como calibrar a moagem para espresso?",
                key="barista_input"
            )
        with col_send:
            send_btn = st.button("📨", use_container_width=True, key="barista_send")

        # Processar resposta
        if send_btn and pergunta.strip():
            _chat_salvar(user_id, "user", pergunta)
            with st.spinner("🤔 Barista Expert pensando..."):
                resposta = ask_barista_expert(pergunta, history=_chat_msgs)
            _chat_salvar(user_id, "assistant", resposta)
            st.rerun()

    # ── Tab 1 · Cadastrar café ─────────────────────────────────────────
    with tab1:
        st.markdown('<p class="section-label">Cadastrar Novo Café</p>', unsafe_allow_html=True)

        # Aplica resultado da análise de IA antes de renderizar os widgets
        if "ai_result" in st.session_state:
            r = st.session_state.pop("ai_result")
            if r.get("nome"):    st.session_state["inp_nome"]    = r["nome"]
            if r.get("classificacao_cafe") in CLASSIFICACOES_CAFE:
                st.session_state["inp_classif"] = r["classificacao_cafe"]
            if r.get("regiao"):  st.session_state["inp_regiao"]  = r["regiao"]
            if r.get("notas"):   st.session_state["inp_notas"]   = r["notas"]
            if r.get("torra")  in ["Clara","Média","Escura"]:
                st.session_state["inp_torra"]   = r["torra"]
            if r.get("tipo")   in ["Grãos","Moído"]:
                st.session_state["inp_tipo"]    = r["tipo"]
            if r.get("tamanho_pacote") in [250, 500, 1000]:
                st.session_state["inp_tamanho"] = r["tamanho_pacote"]

        c1, c2 = st.columns(2, gap="large")

        with c1:
            intensidade = st.select_slider(
                "Intensidade", options=list(range(1, 13)), value=5,
                format_func=lambda x: f"{x}/12", key="inp_intensidade",
                help="Nível de intensidade do café (escala 1–12)")
            nome     = st.text_input("Nome do Café *", key="inp_nome",
                                     placeholder="Ex: Ethiopian Yirgacheffe")
            classificacao_cafe = st.selectbox(
                "Classificação do Café", CLASSIFICACOES_CAFE,
                key="inp_classif",
                help="Especial = pontuação SCA > 80")
            regiao   = st.text_input("Região",  key="inp_regiao",
                                     placeholder="Ex: Sul de Minas / Etiópia")
            data_tort = st.date_input("Data da Torra", value=None, format="DD/MM/YYYY")
            tamanho  = st.radio("Pacote", [250, 500, 1000], key="inp_tamanho",
                                horizontal=True, format_func=lambda x: f"{x}g")

        with c2:
            tipo    = st.radio("Tipo",  ["Grãos","Moído"], key="inp_tipo",  horizontal=True)
            torra   = st.radio("Torra", ["Clara","Média","Escura"], key="inp_torra",
                               horizontal=True)
            notas   = st.text_area("Notas de Sabor / Torra", key="inp_notas",
                                   placeholder="Ex: Blueberry, chocolate, floral...", height=108)
            class_c = st.slider("Classificação (0 = sem avaliação)", 0, 5, 0, key="class_cafe")
            foto_emb = st.file_uploader("Foto da Embalagem", type=["jpg","jpeg","png"],
                                        key="foto_emb")
            foto_emb_b64 = _b64(foto_emb) if foto_emb else None
            if foto_emb_b64:
                _img(foto_emb_b64, w=160)
                if st.button("🔍 Analisar Embalagem com IA",
                             use_container_width=True, key="btn_ai"):
                    with st.spinner("Lendo a embalagem..."):
                        try:
                            result = _analisar_embalagem(foto_emb_b64)
                            st.session_state["ai_result"] = result
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro na análise: {e}")

        # ── Seção Compra ──────────────────────────────────────────────────
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Compra</p>', unsafe_allow_html=True)
        cp1, cp2, cp3 = st.columns(3, gap="large")
        with cp1:
            _lc_sel = st.selectbox("Local de Compra", _LOCAIS_COMPRA,
                                   key="sel_local_compra")
            if _lc_sel == "Outros":
                local_compra = st.text_input("Qual local?",
                                             placeholder="Ex: Torrefação Orfeu, iFood...",
                                             key="inp_local_custom")
            else:
                local_compra = _lc_sel
        with cp2:
            valor_compra = st.number_input("Valor Pago (R$)", min_value=0.0,
                                           value=0.0, step=0.50, format="%.2f")
        with cp3:
            data_compra = st.date_input("Data da Compra", value=_today_local(),
                                        format="DD/MM/YYYY", key="data_compra")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        if st.button("Salvar Café", type="primary", use_container_width=True):
            if not nome.strip():
                st.error("Nome do café é obrigatório.")
            else:
                _run("""INSERT INTO coffees
                    (data_cadastro,nome,tipo,torra,notas,classificacao,
                     classificacao_cafe,regiao,data_torra,tamanho_pacote,
                     foto_embalagem,local_compra,valor_compra,data_compra,
                     intensidade,user_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (_today_local(), nome.strip(), tipo, torra, notas, class_c,
                     classificacao_cafe, regiao, data_tort, tamanho, foto_emb_b64,
                     local_compra.strip() or None,
                     valor_compra if valor_compra > 0 else None,
                     data_compra, intensidade, user_id))
                st.toast(f"☕ {nome} cadastrado com sucesso", icon="✅")
                st.balloons()
                st.rerun()  # reseta formulário e revalida lista sem duplicação

    # ── Tab 2 · Nova extração ──────────────────────────────────────────
    with tab2:
        # Modo Rápido / Completo
        _quick = st.toggle("⚡ Modo Rápido", value=False,
                           help="Modo simplificado: apenas os campos essenciais para registrar rápido")
        st.markdown('<p class="section-label">Registrar Extração</p>', unsafe_allow_html=True)

        # Receita aplicada a partir da aba Receitas
        if st.session_state.get("_recipe_applied"):
            _rap = st.session_state["_recipe_applied"]
            st.info(
                f"📖 Receita **{_rap['nome']}** aplicada — "
                f"dose {_rap['dose']}g · yield {_rap['yield']}g · {_rap['tempo']} · moagem {_rap['moagem']}",
                icon="✅")

        user_id = st.session_state.get('user_id')
        cafes = _fetch("SELECT id, nome, torra, data_torra FROM coffees WHERE user_id=%s ORDER BY nome",
                       (user_id,), _v=_v())
        if not cafes:
            _empty("☕", "Cadastre seu primeiro café",
                   "Para registrar uma extração você precisa ter pelo menos "
                   "um café cadastrado na sua biblioteca.",
                   hint="Vá em 'Novo Café' acima")
        else:
            cafe_map_full = {f"{c['nome']}  ·  {c['torra']}": c for c in cafes}
            sel    = st.selectbox("Café", list(cafe_map_full.keys()))
            _cafe_obj = cafe_map_full[sel]
            cid    = _cafe_obj['id']

            # Indicador de frescura pós-torra — exibido inline
            if _cafe_obj.get('data_torra'):
                _dias_torra = (_today_local() - _cafe_obj['data_torra']).days
                if _dias_torra < 0:
                    pass
                elif _dias_torra <= 4:
                    st.warning(f"💨 Este grão está há {_dias_torra}d pós-torra — ainda degaseificando. Ideal após o 5º dia.", icon="⏳")
                elif _dias_torra <= 21:
                    st.success(f"✨ Janela ideal! {_dias_torra} dias pós-torra — pico de sabor e aroma.", icon="☕")
                elif _dias_torra <= 45:
                    st.info(f"👍 {_dias_torra} dias pós-torra — ainda bom, aromas começando a decair.", icon="📅")
                else:
                    st.warning(f"⏳ {_dias_torra} dias pós-torra — priorize consumir logo.", icon="⚠️")

            metodo = st.selectbox("Método de Preparo", METODOS)

            # ── MODO RÁPIDO ───────────────────────────────────────────
            if _quick:
                _rq_col1, _rq_col2 = st.columns(2, gap="large")
                with _rq_col1:
                    _rq_dose   = st.number_input("Dose (g)", 1.0, 160.0, 18.0, 0.1, key="rq_dose")
                    _rq_yield  = st.number_input("Yield / Xícara (g)", 5.0, 2000.0, 36.0, 1.0, key="rq_yield")
                    _rq_tempo  = st.number_input("Tempo (s)", 1, 600, 28, 1, key="rq_tempo")
                with _rq_col2:
                    _rq_nota   = st.slider("Nota Final", 1, 5, 3, key="rq_nota")
                    _rq_notas  = st.text_area("Impressões rápidas", height=72, key="rq_notas_txt",
                                              placeholder="Acidez, doçura, corpo...")
                st.markdown('<p style="font-size:11px;color:#8A8278">Moedor, TDS, temperatura e avaliação detalhada ficam zerados no modo rápido. Use o modo completo para registros completos.</p>', unsafe_allow_html=True)

                # Cronômetro compacto
                components.html(_TIMER_HTML, height=80, scrolling=False)

                if st.button("✓ REGISTRAR (Rápido)", type="primary", use_container_width=True, key="btn_rq_save"):
                    _rq_m = CoffeeEngine.calc(_rq_dose, _rq_yield, None, _rq_tempo)
                    _rq_ey = CoffeeEngine.estimate_ey(
                        _rq_dose, _rq_yield, _rq_tempo,
                        torra=_cafe_obj.get("torra", "Média"), metodo=metodo)
                    _run("""INSERT INTO extracoes
                        (coffee_id,data,metodo,gramas,agua_alvo,tempo_extracao,brew_ratio,
                         ey,fluxo,nota_final_stars,classificacao,notas,user_id,data_hora_extracao)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (cid, _today_local(), metodo, _rq_dose, _rq_yield, _rq_tempo,
                         _rq_m.get("ratio", 0), _rq_ey, _rq_m.get("fluxo", 0),
                         _rq_nota, _rq_nota, _rq_notas, user_id, _now_local()))
                    st.toast("☕ Extração registrada (modo rápido)", icon="⚡")
                    st.session_state.pop("_recipe_applied", None)
                    st.rerun()

            if not _quick:
                # Guia de ratio por método — referência rápida de entusiasta
                _RATIO_GUIDE = {
                    "Espresso":     "1:2 (18g → 36g) · 25–32s · moagem fina",
                    "Pour Over":    "1:15–1:16 · 2:30–3:30 · moagem média-fina",
                    "Coado":        "1:15 (ex: 20g → 300g) · moagem média",
                    "French Press": "1:14 · 4 min de imersão · moagem grossa",
                    "Aeropress":    "1:13–1:16 · 1:30–2:30 · versátil",
                    "Chemex":       "1:16 · 3:30–4:30 · moagem média-grossa",
                    "Moka Pot":     "1:10 · fogo baixo · moagem fina-média",
                    "Cold Brew":    "1:8 concentrado · 12–18h · moagem grossa",
                }
                _hint = next((v for k, v in _RATIO_GUIDE.items() if k.lower() in metodo.lower()), None)
                st.caption(f"📐 Referência {metodo}: {_hint}" if _hint else "")
    
                # Última receita deste café — o coração do dial-in
                _last = _fetch("""SELECT gramas, agua_alvo, tempo_extracao, clicks_moedor,
                                         moedor, temp_real, nota_final_stars, ey, data
                                  FROM extracoes WHERE coffee_id=%s AND metodo=%s
                                  ORDER BY data DESC, created_at DESC LIMIT 1""",
                               (cid, metodo), _v=_v())
                _last_html = ""
                if _last:
                    lx = _last[0]
                    _ln = int(lx.get('nota_final_stars') or 0)
                    _ley = float(lx.get('ey') or 0)
                    _last_html = (
                        f'<div style="background:var(--mc-surface-2);border:1px solid var(--mc-border);'
                        f'border-left:3px solid var(--mc-orange);border-radius:0 10px 10px 0;'
                        f'padding:10px 14px;margin:4px 0 8px;font-size:13px;line-height:1.7;color:var(--mc-text)">'
                        f'<span style="font-size:11px;font-weight:700;color:var(--mc-orange);'
                        f'text-transform:uppercase;letter-spacing:.1em">🔁 Última receita ({_html.escape(metodo)})</span><br>'
                        f"<b>{float(lx['gramas'] or 0):.1f}g → {float(lx['agua_alvo'] or 0):.0f}g</b> · "
                        f"{int(lx['tempo_extracao'] or 0)}s · "
                        f"{int(lx['clicks_moedor'] or 0)} clicks ({_html.escape(lx['moedor'] or '—')}) · "
                        f"{float(lx['temp_real'] or 0):.0f}°C"
                        + (f" · EY {_ley:.1f}%" if _ley > 0 else "")
                        + (f" · {_stars(_ln)}" if _ln else "")
                        + f"<br><span style='color:var(--mc-text-3);font-size:12px'>"
                        f"{lx['data'].strftime('%d/%m/%Y')} — use como ponto de partida e ajuste 1 variável por vez</span>"
                        f'</div>')
                # Elemento sempre presente — estrutura estável
                st.markdown(_last_html, unsafe_allow_html=True)
    
                xicaras = st.radio("Número de Xícaras", [1, 2], horizontal=True, key="config_xicaras")
                multiplier = 1 if xicaras == 1 else 2
    
                # Parâmetros do Motor Barista (calculados cedo — usados como defaults nos dois lados)
                cafe_info = _fetch("SELECT tipo, torra FROM coffees WHERE id=%s AND user_id=%s LIMIT 1",
                                  (cid, user_id), _v=_v())
                params = _motor_barista_params(
                    cafe_info[0]["torra"] if cafe_info else "Média",
                    cafe_info[0]["tipo"]  if cafe_info else "Grãos")
    
                # ─────────────────────────────────────────────────────────────
                # SETUP DA SESSÃO — Moedor · Clicks · Data · Hora (no topo)
                # ─────────────────────────────────────────────────────────────
                st.markdown(
                    '<div style="background:var(--mc-surface);border:1px solid var(--mc-border);'
                    'border-radius:12px;padding:1.25rem 1.5rem 1rem;margin:0.75rem 0 1.75rem">'
                    '<p class="section-label" style="margin-bottom:1rem">Setup da Sessão</p>',
                    unsafe_allow_html=True)
    
                # Grinder persistence: primeiro busca perfil específico (café+torra+método),
                # senão usa o último global gravado em usuarios
                last_grinder, last_clicks = "", 0
                _cafe_torra = (cafe_info[0]["torra"] if cafe_info else "Média")
                if user_id:
                    ginfo = _fetch("SELECT last_grinder, last_clicks FROM usuarios WHERE id=%s",
                                  (user_id,), _v=_v())
                    if ginfo and ginfo[0]['last_grinder']:
                        last_grinder = ginfo[0]['last_grinder']
                        last_clicks  = ginfo[0]['last_clicks'] or 0

                sc1, sc2 = st.columns([2, 1], gap="medium")
                with sc1:
                    # Moedor: selectbox com opções pré-definidas + Outros
                    _moedor_opts = _MOEDORES
                    _default_idx = (_moedor_opts.index(last_grinder)
                                    if last_grinder in _moedor_opts else len(_moedor_opts) - 1)
                    _moedor_sel = st.selectbox("Moedor", _moedor_opts,
                                               index=_default_idx, key="sel_moedor")
                    if _moedor_sel == "Outros":
                        moedor = st.text_input("Qual moedor?",
                                               value=last_grinder if last_grinder not in _moedor_opts else "",
                                               placeholder="Ex: Wilfa Uniform, Fellow Ode...",
                                               key="inp_moedor_custom")
                    else:
                        moedor = _moedor_sel

                # Busca clicks do perfil específico (café + moedor + torra + método)
                _profile_clicks = last_clicks
                if user_id and moedor and cid:
                    _pf = _fetch("""
                        SELECT clicks FROM grinder_profiles
                        WHERE user_id=%s AND coffee_id=%s AND moedor=%s AND torra=%s AND metodo=%s
                        LIMIT 1
                    """, (user_id, cid, moedor, _cafe_torra, metodo), _v=_v())
                    if _pf:
                        _profile_clicks = int(_pf[0]["clicks"])
                        st.caption(f"💾 Clicks do perfil: **{_profile_clicks}** (café+moedor+torra+método)")

                with sc2:
                    clicks = st.number_input("Clicks", 0, 200, _profile_clicks, 1,
                                             help="Pré-preenchido pelo perfil deste café+moedor",
                                             key="inp_clicks")
                st.caption("🕐 Data e hora são registradas automaticamente no momento do registro.")
                st.markdown('</div>', unsafe_allow_html=True)
    
                # ═════════════════════════════════════════════════════════════
                # DIAL-IN AUTOMÁTICO — recomendação baseada no histórico
                # ═════════════════════════════════════════════════════════════
                _dialin = _dial_in_recomendacao(cid, metodo, user_id) if user_id else {"status": "sem_dados"}
                if _dialin["status"] == "ok":
                    _di_n     = _dialin["n_extracoes"]
                    _di_data  = _dialin.get("ultima_data", "")
                    _di_recs  = _dialin.get("recomendacoes", [])
                    _di_cards = ""
                    for _di_r in _di_recs:
                        _di_cards += (
                            f'<div style="display:flex;align-items:flex-start;gap:10px;'
                            f'background:var(--mc-surface-2);border-left:3px solid {_di_r["cor"]};'
                            f'border-radius:0 8px 8px 0;padding:10px 14px;margin:4px 0;'
                            f'font-size:13px;color:var(--mc-text)">'
                            f'<span style="font-size:20px;line-height:1">{_di_r["icone"]}</span>'
                            f'<div><b>{_di_r["titulo"]}</b><br>'
                            f'<span style="color:{_di_r["cor"]};font-weight:600">{_di_r["acao"]}</span>'
                            f'<span style="color:var(--mc-text-3)"> — {_di_r["alternativa"]}</span></div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div style="background:var(--mc-surface);border:1px solid var(--mc-border);'
                        f'border-radius:12px;padding:14px 18px;margin:0 0 1rem">'
                        f'<p style="margin:0 0 8px;font-size:11px;font-weight:700;'
                        f'color:var(--mc-orange);text-transform:uppercase;letter-spacing:.1em">'
                        f'📊 Dial-in Automático — {_di_n} extraç{"ão" if _di_n==1 else "ões"} '
                        f'({metodo}{f", última: {_di_data}" if _di_data else ""})</p>'
                        f'{_di_cards}</div>',
                        unsafe_allow_html=True)

                # ═════════════════════════════════════════════════════════════
                # 1) MOTOR BARISTA
                # ═════════════════════════════════════════════════════════════
                _step(1, "Motor Barista",
                      "Analise primeiro a melhor extração para este grão. "
                      "Os parâmetros se ajustam à torra e ao tipo do café selecionado.")
    
                # Receita sugerida — o melhor uso deste grão, antes de extrair
                _rs = params
                st.markdown(
                    f'<div style="background:var(--mc-orange-soft);border:1px solid var(--mc-orange);'
                    f'border-radius:12px;padding:14px 18px;margin:0 0 1rem">'
                    f'<span style="font-size:11px;font-weight:700;color:var(--mc-orange);'
                    f'text-transform:uppercase;letter-spacing:.1em">🎯 Receita sugerida para este grão</span>'
                    f'<div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:8px;font-size:14px;'
                    f'color:var(--mc-text)">'
                    f'<span><b>{_rs["dose"]}g</b> dose</span>'
                    f'<span><b>{_rs["yield"]}g</b> yield (1:{_rs["yield"]/_rs["dose"]:.1f})</span>'
                    f'<span><b>{_rs["time"]}s</b> tempo</span>'
                    f'<span><b>{_rs["temp"]}°C</b> água</span>'
                    f'<span><b>{_rs["pressure"]} bar</b> pressão</span>'
                    f'</div>'
                    + (
                        f'<div style="margin-top:10px;padding-top:8px;border-top:1px dashed '
                        f'var(--mc-orange);font-size:13px;color:var(--mc-text)">'
                        f'☕☕ <b>Ajuste para 2 xícaras:</b> dose <b>{_rs["dose"]*2:.1f}g</b> · '
                        f'yield total <b>{_rs["yield"]*2:.0f}g</b> dividido em '
                        f'<b>{_rs["yield"]:.0f}g por xícara</b> — mesmo ratio (1:{_rs["yield"]/_rs["dose"]:.1f}) '
                        f'e mesma concentração, tempo alvo {_rs["time"]}s.</div>'
                        if xicaras == 2 else
                        f'<div style="margin-top:10px;padding-top:8px;border-top:1px dashed '
                        f'var(--mc-orange);font-size:13px;color:var(--mc-text)">'
                        f'☕ <b>1 xícara:</b> volume integral de <b>{_rs["yield"]}g</b> na xícara — '
                        f'máxima concentração e corpo.</div>'
                      )
                    + '</div>', unsafe_allow_html=True)
    
                motor_html = (_MOTOR_BARISTA_HTML
                    .replace('value="18"', f'value="{params["dose"]}"')
                    .replace('value="36"', f'value="{params["yield"]}"')
                    .replace('value="28"', f'value="{params["time"]}"')
                    .replace('value="92"', f'value="{params["temp"]}"')
                    .replace('value="9"',  f'value="{params["pressure"]}"'))
                components.html(motor_html, height=660, scrolling=False)
    
                # Botão para propagar sugestão do Motor Barista → campos reais abaixo
                if st.button("↩ Redefinir campos com sugestão do Motor Barista",
                             key="btn_reset_to_motor", help="Preenche os campos abaixo com os valores sugeridos para este grão"):
                    st.session_state["ext_gramas"] = round(float(params["dose"])  * multiplier, 1)
                    st.session_state["ext_agua"]   = round(float(params["yield"]) * multiplier, 1)
                    st.session_state["ext_tempo"]  = int(params["time"])
                    st.session_state["ext_temp"]   = float(params["temp"])
                    st.session_state["ext_press"]  = float(params["pressure"])
                    st.session_state["_ext_seed"]  = None  # força reseed
                    st.rerun()
    
                # ═════════════════════════════════════════════════════════════
                # 2) PARÂMETROS DE EXTRAÇÃO (REALIDADE) + RADAR REAL
                #    Espelha exatamente os 5 campos do Motor Barista + TDS
                # ═════════════════════════════════════════════════════════════
                _step(2, "Parâmetros de Extração",
                      "Registre o que aconteceu de verdade — espelha os campos do Motor Barista.")
    
                col_params, col_radar_real = st.columns([1.2, 1], gap="large")
                with col_params:
                    # Widgets com key fixa: identidade estável entre reruns (evita
                    # que as abas voltem para a 1ª ao trocar xícaras/café).
                    # Os defaults são semeados via session_state quando café ou
                    # nº de xícaras mudam.
                    _seed_sig = (cid, multiplier)
                    if st.session_state.get("_ext_seed") != _seed_sig:
                        st.session_state["_ext_seed"]  = _seed_sig
                        st.session_state["ext_gramas"] = round(float(params["dose"])  * multiplier, 1)
                        st.session_state["ext_agua"]   = round(float(params["yield"]) * multiplier, 1)
                        st.session_state["ext_tempo"]  = int(params["time"])
                        st.session_state["ext_temp"]   = float(params["temp"])
                        st.session_state["ext_press"]  = float(params["pressure"])
                        st.session_state.setdefault("ext_tds", 0.0)
    
                    gramas       = st.number_input("Dose Real (g)", 1.0, 160.0,
                                                   step=0.1, key="ext_gramas",
                                                   help="Peso do pó medido na balança")
                    agua         = st.number_input("Yield / Volumetria na Xícara (g)", 5.0, 2000.0,
                                                   step=1.0, key="ext_agua",
                                                   help="Quantidade real que entrou na xícara (espresso: ~18-50g)")
                    tempo        = st.number_input("Tempo Real (s)", 1, 600, step=1, key="ext_tempo")
                    temp_real    = st.number_input("Temperatura Real (°C)", 60.0, 100.0,
                                                   step=0.5, key="ext_temp")
                    pressao_real = st.number_input("Pressão Real (bar)", 1.0, 20.0,
                                                   step=0.5, key="ext_press")
                    tds          = st.number_input("TDS Medido (%)", 0.0, 5.0,
                                                   step=0.01, key="ext_tds",
                                                   help="Opcional — refratômetro. Deixe 0 se não usar.")
    
                with col_radar_real:
                    m_real  = CoffeeEngine.calc(gramas, agua, tds if tds > 0 else None, tempo)
                    ey_real = m_real.get("ey", 0.0)
                    # EY estimado quando não há TDS (sem refratômetro)
                    _ey_estimado = 0.0
                    if tds == 0 and gramas > 0 and agua > 0:
                        _cafe_torra_real = (cafe_info[0]["torra"] if cafe_info else "Média")
                        _ey_estimado = CoffeeEngine.estimate_ey(gramas, agua, tempo,
                                                                 _cafe_torra_real, metodo)
                    st.markdown(
                        '<p style="font-size:11px;font-weight:700;color:var(--mc-orange);'
                        'letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.25rem">'
                        'Perfil Sensorial — Extração Real</p>',
                        unsafe_allow_html=True)
                    st.plotly_chart(_radar(CoffeeEngine.sensory(ey_real)),
                                    use_container_width=True, config={'displayModeBar': False})
                    foto_can = st.file_uploader("Foto da Caneca",
                                                type=["jpg","jpeg","png"],
                                                key="foto_can")
                    if foto_can:
                        _img(_b64(foto_can), w=200)
    
                notas_e = st.text_area("Notas da Extração",
                                       placeholder="Impressões sobre a extração...",
                                       height=90, key="notas_ext")
    
                # ═════════════════════════════════════════════════════════════
                # 3) DIAGNÓSTICO DA EXTRAÇÃO — delta Motor Barista vs Realidade
                # ═════════════════════════════════════════════════════════════
                _step(3, "Diagnóstico da Extração",
                      "Delta entre o que você planejou (Motor Barista) e o que aconteceu de verdade.")
    
                with st.expander("Ver diagnóstico completo", expanded=True):
                    # Estrutura FIXA de elementos: sempre 4 métricas iguais e um
                    # único markdown de diagnóstico. Se a quantidade de elementos
                    # variasse entre reruns, o Streamlit remontaria as abas e
                    # voltaria para a 1ª (bug clássico do st.tabs).
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("Brew Ratio",  m_real.get("ratio_text", "—"))
                    mc2.metric("Fluxo Médio", f"{m_real.get('fluxo',0):.2f} g/s")
                    mc3.metric("Tempo",       f"{tempo}s")
                    mc4.metric("Dose",        f"{gramas:.1f}g")
    
                    diagnosticos = []
    
                    dt_tempo = tempo - params["time"]
                    if abs(dt_tempo) >= 4:
                        dir_t   = "rápida" if dt_tempo < 0 else "lenta"
                        sugest  = "afine a moagem (mais fino)" if dt_tempo < 0 else "abra a moagem (mais grosso)"
                        diagnosticos.append(
                            f"⏱ <b>Fluxo {dir_t}:</b> você planejou {params['time']}s, "
                            f"mas extraiu em {tempo}s. Sugestão: {sugest}.")
    
                    dt_yield = agua - params["yield"] * multiplier
                    if abs(dt_yield) >= 5:
                        dir_y = "abaixo" if dt_yield < 0 else "acima"
                        diagnosticos.append(
                            f"💧 <b>Yield {dir_y} da meta:</b> planejou "
                            f"{params['yield']*multiplier:.0f}g, real {agua:.0f}g "
                            f"(Δ {dt_yield:+.0f}g).")
    
                    dt_temp = temp_real - params["temp"]
                    if abs(dt_temp) >= 1.5:
                        dir_tmp = "abaixo" if dt_temp < 0 else "acima"
                        diagnosticos.append(
                            f"🌡 <b>Temperatura {dir_tmp} do target:</b> planejou "
                            f"{params['temp']}°C, real {temp_real:.1f}°C (Δ {dt_temp:+.1f}°C).")
    
                    dt_press = pressao_real - params["pressure"]
                    if abs(dt_press) >= 0.8:
                        dir_p = "abaixo" if dt_press < 0 else "acima"
                        diagnosticos.append(
                            f"📊 <b>Pressão {dir_p} do target:</b> planejou "
                            f"{params['pressure']:.1f} bar, real {pressao_real:.1f} bar "
                            f"(Δ {dt_press:+.1f} bar).")
    
                    if ey_real > 0:
                        if ey_real < CoffeeEngine.EY_LOW:
                            diagnosticos.append(
                                f"⚡ <b>Sub-extração ({ey_real:.1f}%):</b> sabor raso e ácido — "
                                "experimente moagem mais fina ou tempo maior.")
                        elif ey_real > CoffeeEngine.EY_HIGH:
                            diagnosticos.append(
                                f"⚡ <b>Super-extração ({ey_real:.1f}%):</b> amargor e adstringência — "
                                "experimente moagem mais grossa ou tempo menor.")
                        else:
                            diagnosticos.append(
                                f"✅ <b>EY dentro da janela de ouro ({ey_real:.1f}%)</b> — extração equilibrada.")
                        diagnosticos.append(
                            f"🧪 <b>Extraction Yield: {ey_real:.2f}%</b> — {m_real.get('status','')}.")
                    elif _ey_estimado > 0:
                        # Sem refratômetro — mostra estimativa com aviso de margem
                        _ey_est_status = ("sub-extração estimada" if _ey_estimado < CoffeeEngine.EY_LOW
                                          else "super-extração estimada" if _ey_estimado > CoffeeEngine.EY_HIGH
                                          else "na janela ideal estimada")
                        diagnosticos.append(
                            f"🔬 <b>EY estimado (sem refratômetro): ~{_ey_estimado:.1f}%</b> — "
                            f"{_ey_est_status}. <span style='color:var(--mc-text-3)'>"
                            f"Margem ±2-3%. Para precisão real, use um refratômetro.</span>")
    
                    if not diagnosticos:
                        diagnosticos = ["✅ <b>Extração alinhada com o plano</b> — "
                                        "todos os parâmetros dentro da meta."]
                    # Um único elemento markdown, sempre presente
                    _diag_html = "".join(
                        f'<div style="background:var(--mc-surface-2);border-left:3px solid '
                        f'var(--mc-orange);padding:10px 14px;border-radius:0 8px 8px 0;'
                        f'margin:6px 0;font-size:13px;line-height:1.6;color:var(--mc-text)">'
                        f'{d}</div>' for d in diagnosticos)
                    st.markdown(f'<div style="margin-top:1rem">{_diag_html}</div>',
                                unsafe_allow_html=True)
    
                # ═════════════════════════════════════════════════════════════
                # 4) CLASSIFICAÇÃO SENSORIAL
                # ═════════════════════════════════════════════════════════════
                _step(4, "Classificação sensorial",
                      "Avalie cada dimensão de 1 a 5 estrelas. A Nota Final é o destaque do registro.")
    
                # Barras de progresso 1–5 (arraste para avaliar)
                col_s1, col_s2, col_s3, col_s4 = st.columns(4, gap="large")
                with col_s1:
                    crema_stars = st.slider("Crema", 1, 5, 3, key="crema_stars")
                with col_s2:
                    corpo_stars = st.slider("Corpo", 1, 5, 3, key="corpo_stars")
                with col_s3:
                    equilibrio_stars = st.slider("Equilíbrio", 1, 5, 3, key="equilibrio_stars")
                with col_s4:
                    acidez_stars = st.slider("Acidez", 1, 5, 3, key="acidez_stars")
    
                col_s5, col_s6, col_s7, col_s8 = st.columns(4, gap="large")
                with col_s5:
                    amargor_stars = st.slider("Amargor", 1, 5, 3, key="amargor_stars")
                with col_s6:
                    presenca_boca_stars = st.slider("Presença na Boca", 1, 5, 3, key="presenca_stars")
                with col_s7:
                    docura_stars = st.slider("Doçura", 1, 5, 3, key="docura_stars")
                with col_s8:
                    nota_final_stars = st.slider("Nota Final", 1, 5, 3, key="nota_final_stars")
    
                balanco_ideal = st.text_input("Balanço Perfeito (do diagnóstico)",
                                             placeholder="Ex: Crema 4, Corpo 4, Equilíbrio 5...",
                                             key="balanco_ideal")
    
                # ═════════════════════════════════════════════════════════════
                # 5) REGISTRAR
                # ═════════════════════════════════════════════════════════════
                _step(5, "Registrar extração",
                      "Salve esta extração no seu histórico para acompanhar a evolução.")
                if st.button("✓ REGISTRAR EXTRAÇÃO", type="primary", use_container_width=True):
                    data_hora = _now_local()
                    data_ext  = data_hora.date()
                    _run("""INSERT INTO extracoes
                        (coffee_id,data,metodo,gramas,moedor,clicks_moedor,agua_alvo,tds,
                         tempo_extracao,brew_ratio,ey,fluxo,foto_caneca,classificacao,notas,
                         crema_stars,corpo_stars,equilibrio_stars,acidez_stars,amargor_stars,
                         presenca_boca_stars,docura_stars,nota_final_stars,balanco_ideal,
                         data_hora_extracao,user_id,temp_real,pressao_real)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (cid, data_ext, metodo, gramas, moedor, clicks, agua, tds, tempo,
                         m_real.get("ratio",0), ey_real, m_real.get("fluxo",0),
                         _b64(foto_can) if foto_can else None, nota_final_stars, notas_e,
                         crema_stars, corpo_stars, equilibrio_stars, acidez_stars, amargor_stars,
                         presenca_boca_stars, docura_stars, nota_final_stars, balanco_ideal,
                         data_hora, user_id, temp_real, pressao_real))
                    if user_id and moedor:
                        _run("UPDATE usuarios SET last_grinder=%s, last_clicks=%s WHERE id=%s",
                             (moedor, clicks, user_id))
                        # Salva perfil específico: este café + moedor + torra + método
                        _run("""
                            INSERT INTO grinder_profiles (user_id, coffee_id, moedor, torra, metodo, clicks, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (user_id, coffee_id, moedor, torra, metodo)
                            DO UPDATE SET clicks=EXCLUDED.clicks, updated_at=NOW()
                        """, (user_id, cid, moedor, _cafe_torra, metodo, clicks))
                    # Limpa hora para próxima extração usar hora atual
                    st.session_state.pop("hora_ext", None)
                    st.toast("✓ Extração registrada com sucesso", icon="☕")
                    st.balloons()
                    st.rerun()

    # ── Tab 3 · Meus cafés ────────────────────────────────────────────
    with tab3:
        st.markdown('<p class="section-label">Biblioteca de Cafés</p>', unsafe_allow_html=True)

        cafes = _fetch("""
            SELECT c.*, COUNT(e.id) AS total_ext,
                   AVG(e.ey) AS avg_ey, AVG(e.classificacao) AS avg_nota
            FROM coffees c LEFT JOIN extracoes e ON e.coffee_id=c.id
            WHERE c.user_id=%s
            GROUP BY c.id ORDER BY c.data_cadastro DESC""", (user_id,), _v=_v())

        # P6: busca TODAS as extrações do usuário num único query — evita N+1
        all_extracts = _fetch("""
            SELECT * FROM extracoes
            WHERE user_id=%s
            ORDER BY data DESC, created_at DESC
        """, (user_id,), _v=_v())
        extracts_by_coffee = {}
        for ex in all_extracts:
            extracts_by_coffee.setdefault(ex['coffee_id'], []).append(ex)

        if not cafes:
            _empty("📦", "Sua biblioteca está vazia",
                   "Adicione cafés à sua biblioteca para começar a registrar "
                   "extrações e acompanhar a evolução do seu paladar.",
                   hint="Comece em 'Novo Café'")
        else:
            # ── Filtros Meus Cafés ────────────────────────────────────────
            _tc1, _tc2, _tc3 = st.columns([2, 1, 1], gap="medium")
            with _tc1:
                _search_cafe = st.text_input("🔍 Buscar café",
                                             placeholder="Nome, região...",
                                             key="tc_search")
            with _tc2:
                _torras_disp = ["Todas"] + sorted({c["torra"] for c in cafes if c.get("torra")})
                _filt_torra = st.selectbox("Torra", _torras_disp, key="tc_torra")
            with _tc3:
                _tipos_disp = ["Todos"] + sorted({c["tipo"] for c in cafes if c.get("tipo")})
                _filt_tipo = st.selectbox("Tipo", _tipos_disp, key="tc_tipo")
            _cafes_filtrados = [
                c for c in cafes
                if (_search_cafe.lower() in (c["nome"] or "").lower()
                    or _search_cafe.lower() in (c.get("regiao") or "").lower())
                and (_filt_torra == "Todas" or c.get("torra") == _filt_torra)
                and (_filt_tipo == "Todos"  or c.get("tipo")  == _filt_tipo)
            ]
            if not _cafes_filtrados:
                st.info("Nenhum café encontrado com esses filtros.")

            for c in _cafes_filtrados:
                with st.expander(f"{c['nome']}  ·  {c['torra']}  ·  {_stars(c['classificacao'] or 0)}"):
                    ca, cb, cc = st.columns([1, 2.2, 1.4], gap="large")
                    with ca:
                        if c["foto_embalagem"]:
                            _img(c["foto_embalagem"], w=150)
                        else:
                            st.markdown(_ph(), unsafe_allow_html=True)
                    with cb:
                        tags = (_tag(c['tipo']) + _tag(c['torra']) +
                                _tag(f"{c['tamanho_pacote']}g") +
                                (_tag("Torra " + c['data_torra'].strftime('%d/%m/%Y'), True)
                                 if c['data_torra'] else ""))
                        # Frescor da torra — janela de degaseificação/pico
                        if c['data_torra']:
                            _dias = (_today_local() - c['data_torra']).days
                            if _dias < 0:
                                _fresh = None
                            elif _dias <= 4:
                                _fresh = (f"💨 Em descanso ({_dias}d) — degaseificando, espere até o 5º dia", "#4A9EFF")
                            elif _dias <= 21:
                                _fresh = (f"✨ Janela ideal ({_dias}d pós-torra) — pico de sabor", "#3DD68C")
                            elif _dias <= 45:
                                _fresh = (f"👍 Ainda bom ({_dias}d) — aromas começando a decair", "#E8A33D")
                            else:
                                _fresh = (f"⏳ {_dias}d pós-torra — priorize consumir logo", "#E85D5D")
                            if _fresh:
                                tags += (f'<span style="display:inline-block;background:transparent;'
                                         f'border:1px solid {_fresh[1]};color:{_fresh[1]};'
                                         f'border-radius:20px;padding:3px 10px;font-size:11px;'
                                         f'font-weight:600;margin:2px 4px 2px 0">{_fresh[0]}</span>')
                        intens = c.get('intensidade') or 0
                        info = (_irow("Classificação", c.get('classificacao_cafe') or "—") +
                                _irow("Região",        c['regiao']  or "—") +
                                _irow("Intensidade",   f"{intens}/12" if intens else "—"))
                        # Info de compra (se preenchida)
                        if c.get("local_compra"):
                            info += _irow("Comprado em", c["local_compra"])
                        if c.get("data_compra"):
                            info += _irow("Data compra", c["data_compra"].strftime('%d/%m/%Y'))
                        note = (f'<div style="margin-top:10px;font-size:13px;color:#B8B0A8;'
                                f'font-style:italic;line-height:1.5;">{_html.escape(c["notas"])}</div>' if c["notas"] else "")
                        st.markdown(f'<div>{tags}</div><div style="margin-top:12px">{info}</div>{note}',
                                    unsafe_allow_html=True)
                    with cc:
                        st.metric("Extrações", int(c["total_ext"] or 0))
                        if c.get("valor_compra"):
                            lbl = (f"Comprado em {c['data_compra'].strftime('%d/%m/%Y')}"
                                   if c.get("data_compra") else "Valor Pago")
                            st.metric(lbl, f"R$ {c['valor_compra']:.2f}")
                            # Custo por xícara baseado na dose média das extrações
                            _cexts = extracts_by_coffee.get(c["id"], [])
                            _avg_dose = (sum(float(e["gramas"] or 0) for e in _cexts) / len(_cexts)
                                         if _cexts else None)
                            if _avg_dose and c.get("tamanho_pacote") and float(c["tamanho_pacote"]) > 0:
                                _custo_xic = (float(c["valor_compra"])
                                              / float(c["tamanho_pacote"]) * _avg_dose)
                                st.metric("Custo/Xícara", f"R$ {_custo_xic:.2f}",
                                          help=f"R${c['valor_compra']:.2f} ÷ {c['tamanho_pacote']}g × {_avg_dose:.1f}g/dose")
                        if c["avg_ey"]:   st.metric("EY Médio",   f"{c['avg_ey']:.1f}%")
                        if c["avg_nota"]: st.metric("Nota Média", _stars(round(c["avg_nota"])))

                    # ── Editar características do café ─────────────────────────
                    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
                    if st.button("✏️ Editar café", key=f"edit_c_btn_{c['id']}"):
                        st.session_state[f"edit_c_{c['id']}"] = True

                    if st.session_state.get(f"edit_c_{c['id']}"):
                        st.markdown('<p class="section-label">Editar Café</p>', unsafe_allow_html=True)
                        ec1, ec2 = st.columns(2, gap="large")
                        with ec1:
                            ed_nome = st.text_input("Nome do Café", value=c['nome'] or "",
                                                    key=f"ec_nome_{c['id']}")
                            try:
                                _ci = CLASSIFICACOES_CAFE.index(c.get('classificacao_cafe') or CLASSIFICACOES_CAFE[2])
                            except ValueError:
                                _ci = 2
                            ed_classif = st.selectbox("Classificação do Café",
                                                      CLASSIFICACOES_CAFE, index=_ci,
                                                      key=f"ec_classif_{c['id']}")
                            ed_regiao  = st.text_input("Região", value=c['regiao'] or "",
                                                       key=f"ec_regiao_{c['id']}")
                            ed_tipo    = st.radio("Tipo", ["Grãos","Moído"],
                                                  index=0 if c['tipo']=="Grãos" else 1,
                                                  horizontal=True, key=f"ec_tipo_{c['id']}")
                            ed_torra   = st.radio("Torra", ["Clara","Média","Escura"],
                                                  index=["Clara","Média","Escura"].index(c['torra']) if c['torra'] in ["Clara","Média","Escura"] else 1,
                                                  horizontal=True, key=f"ec_torra_{c['id']}")
                        with ec2:
                            _intens_val = int(c.get('intensidade') or 5)
                            _intens_val = max(1, min(12, _intens_val))
                            ed_intensidade = st.select_slider(
                                "Intensidade", options=list(range(1, 13)),
                                value=_intens_val,
                                format_func=lambda x: f"{x}/12",
                                key=f"ec_intens_{c['id']}")
                            ed_tamanho = st.radio("Pacote", [250, 500, 1000],
                                                  index=[250,500,1000].index(c['tamanho_pacote']) if c['tamanho_pacote'] in [250,500,1000] else 0,
                                                  horizontal=True, format_func=lambda x: f"{x}g",
                                                  key=f"ec_tam_{c['id']}")
                            _torra_dt_val = c['data_torra'] if c['data_torra'] else None
                            ed_data_torra = st.date_input("Data da Torra",
                                                          value=_torra_dt_val,
                                                          format="DD/MM/YYYY",
                                                          key=f"ec_torra_dt_{c['id']}")
                            _class_val = int(c['classificacao'] or 3)
                            _class_val = max(1, min(5, _class_val)) if _class_val else 3
                            ed_class_estr = st.slider("Classificação geral", 1, 5, _class_val, key=f"ec_class_{c['id']}")
                            ed_notas = st.text_area("Notas de Sabor / Torra",
                                                    value=c['notas'] or "", height=108,
                                                    key=f"ec_notas_{c['id']}")
                        # Seção de foto de embalagem
                        st.markdown("**Foto da Embalagem**")
                        ef_col1, ef_col2 = st.columns([1, 2], gap="large")
                        with ef_col1:
                            if c.get("foto_embalagem"):
                                _img(c["foto_embalagem"], w=130)
                            else:
                                st.markdown(_ph(), unsafe_allow_html=True)
                        with ef_col2:
                            ed_foto_emb_f = st.file_uploader(
                                "Substituir / Adicionar foto da embalagem",
                                type=["jpg","jpeg","png"],
                                key=f"ec_foto_{c['id']}")
                        # Mantém a foto atual se não fizer upload de nova
                        ed_foto_emb_b64 = _b64(ed_foto_emb_f) if ed_foto_emb_f else c.get("foto_embalagem")

                        # Seção de compra
                        st.markdown("**Compra**")
                        cp_a, cp_b, cp_c = st.columns(3)
                        with cp_a:
                            ed_local = st.text_input("Local de Compra",
                                                     value=c.get('local_compra') or "",
                                                     key=f"ec_local_{c['id']}")
                        with cp_b:
                            ed_valor = st.number_input("Valor Pago (R$)", min_value=0.0,
                                                       value=float(c.get('valor_compra') or 0),
                                                       step=0.50, format="%.2f",
                                                       key=f"ec_valor_{c['id']}")
                        with cp_c:
                            ed_dt_compra = st.date_input("Data da Compra",
                                                         value=c.get('data_compra') or _today_local(),
                                                         format="DD/MM/YYYY",
                                                         key=f"ec_dtcp_{c['id']}")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Salvar alterações", type="primary",
                                         key=f"ec_save_{c['id']}", use_container_width=True):
                                try:
                                    _run("""UPDATE coffees SET
                                            nome=%s, classificacao_cafe=%s, regiao=%s,
                                            tipo=%s, torra=%s, tamanho_pacote=%s,
                                            data_torra=%s, classificacao=%s, notas=%s,
                                            local_compra=%s, valor_compra=%s,
                                            data_compra=%s, intensidade=%s,
                                            foto_embalagem=%s
                                            WHERE id=%s AND user_id=%s""",
                                         (ed_nome.strip(), ed_classif, ed_regiao,
                                          ed_tipo, ed_torra, ed_tamanho,
                                          ed_data_torra if ed_data_torra else None,
                                          ed_class_estr, ed_notas,
                                          ed_local.strip() or None,
                                          ed_valor if ed_valor > 0 else None,
                                          ed_dt_compra,
                                          ed_intensidade,
                                          ed_foto_emb_b64,
                                          c['id'], user_id))
                                    st.session_state.pop(f"edit_c_{c['id']}", None)
                                    st.toast("Café atualizado", icon="✅")
                                    st.rerun()
                                except Exception as _save_err:
                                    st.error(f"Erro ao salvar: {_save_err}")
                        with col_cancel:
                            if st.button("← Cancelar", key=f"ec_cancel_{c['id']}",
                                         use_container_width=True):
                                st.session_state.pop(f"edit_c_{c['id']}", None)
                                st.rerun()

                    # ── Seção de Extrações ─────────────────────────────────────
                    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
                    st.markdown('<p class="section-label">Detalhes das Extrações</p>', unsafe_allow_html=True)

                    # P6: usa cache pré-carregado em vez de query por café
                    extracts = extracts_by_coffee.get(c["id"], [])

                    if not extracts:
                        st.markdown(
                            '<div style="text-align:center;padding:1.5rem;'
                            'background:#141414;border:1px dashed #3A3A3A;'
                            'border-radius:10px;color:#8A8278;font-size:13px;'
                            'font-weight:500">'
                            '☕ Ainda sem extrações deste café — vá em '
                            '<strong style="color:#E8722E">Nova Extração</strong> '
                            'para começar.</div>',
                            unsafe_allow_html=True)
                    else:
                        for e in extracts:
                            ex_header = (f"📅 {e['data'].strftime('%d/%m/%Y')}  ·  "
                                        f"{e['metodo']}  ·  {_stars(e['classificacao'] or 0)}")
                            st.markdown(f"**{ex_header}**")
                            ex_col1, ex_col2, ex_col3 = st.columns([1, 2, 1.5], gap="large")

                            # Foto da caneca
                            with ex_col1:
                                st.markdown("**Foto da Caneca**")
                                if e["foto_caneca"]:
                                    _img(e["foto_caneca"], w=140)
                                else:
                                    st.markdown(_ph(), unsafe_allow_html=True)
                                # Upload adicional de fotos
                                # Usamos flag no session_state para evitar loop:
                                # file_uploader mantém o arquivo após rerun,
                                # então sem o flag salvaria N vezes.
                                nova_foto = st.file_uploader(
                                    "Adicionar foto",
                                    type=["jpg","jpeg","png"],
                                    key=f"add_foto_{e['id']}"
                                )
                                _fkey = f"_foto_done_{e['id']}"
                                if nova_foto:
                                    if not st.session_state.get(_fkey):
                                        _img(_b64(nova_foto), w=100)
                                        if st.button("📸 Confirmar foto", key=f"save_foto_{e['id']}"):
                                            _run(
                                                "UPDATE extracoes SET foto_caneca=%s WHERE id=%s AND user_id=%s",
                                                (_b64(nova_foto), e["id"], user_id)
                                            )
                                            st.session_state[_fkey] = True
                                            st.toast("Foto adicionada", icon="📸")
                                            st.rerun()
                                else:
                                    st.session_state.pop(_fkey, None)

                            # Detalhes da extração
                            with ex_col2:
                                st.markdown("**Parâmetros**")
                                det_info = (_irow("Dose", f"{e['gramas']}g") +
                                           _irow("Água", f"{e['agua_alvo']}g") +
                                           _irow("Tempo", f"{e['tempo_extracao']}s") +
                                           _irow("TDS", f"{e['tds']}%" if e['tds'] else "—"))
                                if e['moedor']:
                                    det_info += _irow("Moedor", f"{e['moedor']}  ·  {e['clicks_moedor']} clicks")
                                st.markdown(det_info, unsafe_allow_html=True)

                                st.markdown("**Comentários**")
                                if e['notas']:
                                    st.markdown(f"*{e['notas']}*")
                                else:
                                    st.markdown("_Sem comentários_")

                            # Métricas
                            with ex_col3:
                                ratio_display = (f"1:{e['brew_ratio']:.1f}" if e['brew_ratio']
                                                 else f"1:{e['agua_alvo']/e['gramas']:.1f}")
                                st.metric("Brew Ratio", ratio_display)
                                if e['ey']:
                                    st.metric("EY", f"{e['ey']:.1f}%")
                                st.metric("Fluxo", f"{e['fluxo']:.2f}g/s" if e['fluxo'] else "—")

                            # Botão editar
                            st.markdown("---")
                            col_edit, col_del = st.columns(2)
                            with col_edit:
                                if st.button("✏️ Editar Extração", key=f"tab3_edit_e_{e['id']}", use_container_width=True):
                                    st.session_state[f"edit_ext_{e['id']}"] = True
                            with col_del:
                                if st.button("🗑️ Deletar", key=f"tab3_del_e_{e['id']}", use_container_width=True):
                                    st.session_state[f"confirm_del_e3_{e['id']}"] = True
                            if st.session_state.get(f"confirm_del_e3_{e['id']}"):
                                st.warning("Confirmar remoção desta extração?")
                                cya, cna = st.columns(2)
                                with cya:
                                    if st.button("✓ Remover", key=f"del_e3_ok_{e['id']}", type="primary"):
                                        _run("DELETE FROM extracoes WHERE id=%s AND user_id=%s", (e['id'], user_id))
                                        st.rerun()
                                with cna:
                                    if st.button("← Cancelar", key=f"del_e3_cancel_{e['id']}"):
                                        st.session_state.pop(f"confirm_del_e3_{e['id']}", None)
                                        st.rerun()

                            # Formulário de edição (se ativado)
                            if st.session_state.get(f"edit_ext_{e['id']}", False):
                                st.markdown("**Editar Extração**")
                                ed_col1, ed_col2 = st.columns(2)
                                with ed_col1:
                                    ed_gramas = st.number_input("Dose (g)", value=float(e['gramas']), key=f"tab3_ed_g_{e['id']}")
                                    ed_agua   = st.number_input("Água (g)", value=float(e['agua_alvo']), key=f"tab3_ed_a_{e['id']}")
                                    ed_tempo  = st.number_input("Tempo (s)", value=int(e['tempo_extracao']), key=f"tab3_ed_t_{e['id']}")
                                    ed_tds    = st.number_input("TDS (%)", value=float(e['tds'] or 0), step=0.01, key=f"tab3_ed_tds_{e['id']}")
                                with ed_col2:
                                    ed_moedor = st.text_input("Moedor", value=e['moedor'] or "", key=f"tab3_ed_m_{e['id']}")
                                    ed_clicks = st.number_input("Clicks", value=int(e['clicks_moedor'] or 0), key=f"tab3_ed_cl_{e['id']}")
                                    ed_temp   = st.number_input("Temperatura (°C)", value=float(e.get('temp_real') or 0), step=0.5, key=f"tab3_ed_tp_{e['id']}")
                                    ed_press  = st.number_input("Pressão (bar)", value=float(e.get('pressao_real') or 0), step=0.5, key=f"tab3_ed_pr_{e['id']}")
                                ed_notas = st.text_area("Comentários", value=e['notas'] or "", key=f"tab3_ed_n_{e['id']}", height=80)

                                if st.button("💾 Salvar Edição", key=f"tab3_save_e_{e['id']}", use_container_width=True):
                                    _run(
                                        """UPDATE extracoes SET
                                            gramas=%s, agua_alvo=%s, tempo_extracao=%s,
                                            tds=%s, moedor=%s, clicks_moedor=%s,
                                            temp_real=%s, pressao_real=%s, notas=%s
                                            WHERE id=%s AND user_id=%s""",
                                        (ed_gramas, ed_agua, ed_tempo, ed_tds,
                                         ed_moedor or None, ed_clicks,
                                         ed_temp if ed_temp > 0 else None,
                                         ed_press if ed_press > 0 else None,
                                         ed_notas, e['id'], user_id)
                                    )
                                    st.toast("Extração atualizada", icon="✅")
                                    st.session_state[f"edit_ext_{e['id']}"] = False
                                    st.rerun()

                    st.markdown("")
                    if st.button("🗑️ Remover café", key=f"del_c_{c['id']}"):
                        st.session_state[f"confirm_del_c_{c['id']}"] = True
                    if st.session_state.get(f"confirm_del_c_{c['id']}"):
                        st.warning(f"Tem certeza? Isso removerá **{c['nome']}** e todas as suas extrações.")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✓ Confirmar remoção", key=f"del_c_ok_{c['id']}", type="primary"):
                                _run("DELETE FROM coffees WHERE id=%s AND user_id=%s", (c["id"], user_id))
                                st.rerun()
                        with col_no:
                            if st.button("← Cancelar", key=f"del_c_cancel_{c['id']}"):
                                st.session_state.pop(f"confirm_del_c_{c['id']}", None)
                                st.rerun()

    # ── Tab 4 · Histórico ─────────────────────────────────────────────
    with tab4:
        st.markdown('<p class="section-label">Histórico de Extrações</p>', unsafe_allow_html=True)

        rows = _fetch("""
            SELECT e.*, c.nome AS cafe_nome, c.torra FROM extracoes e
            JOIN coffees c ON c.id=e.coffee_id
            WHERE e.user_id=%s
            ORDER BY e.data DESC, e.created_at DESC LIMIT 200""", (user_id,), _v=_v())

        if not rows:
            _empty("📈", "Seu histórico vai aparecer aqui",
                   "Cada extração registrada aparece aqui em ordem cronológica, "
                   "com todos os parâmetros e classificações para você revisar "
                   "e editar quando quiser.",
                   hint="Comece em 'Nova Extração'")
        else:
            # ── Métricas Agregadas ────────────────────────────────────────
            _ey_vals = [float(r["ey"]) for r in rows if r.get("ey") and float(r["ey"]) > 0]
            _nota_vals = [int(r["nota_final_stars"]) for r in rows if r.get("nota_final_stars") and int(r["nota_final_stars"]) > 0]
            _dose_vals = [float(r["gramas"]) for r in rows if r.get("gramas")]
            _metodos_count = {}
            for r in rows:
                _metodos_count[r["metodo"]] = _metodos_count.get(r["metodo"], 0) + 1
            _top_metodo = max(_metodos_count, key=_metodos_count.get) if _metodos_count else "—"
            _mh1, _mh2, _mh3, _mh4 = st.columns(4, gap="medium")
            _mh1.metric("Total de Extrações", len(rows))
            _mh2.metric("EY Médio", f"{sum(_ey_vals)/len(_ey_vals):.1f}%" if _ey_vals else "—",
                        help="Média do Extraction Yield das extrações com refratômetro")
            _mh3.metric("Nota Média", f"{sum(_nota_vals)/len(_nota_vals):.1f}/5" if _nota_vals else "—",
                        help="Média das notas finais registradas")
            _mh4.metric("Método Favorito", _top_metodo,
                        help=f"{_metodos_count.get(_top_metodo, 0)} extrações")
            st.markdown("")

            # ── Filtros ──────────────────────────────────────────────────
            _nomes_cafe = sorted({r["cafe_nome"] for r in rows})
            _metodos_hist = sorted({r["metodo"] for r in rows})
            filt_col1, filt_col2, filt_col3 = st.columns(3, gap="medium")
            with filt_col1:
                filt_cafe = st.multiselect("Café", _nomes_cafe,
                                           default=_nomes_cafe, key="h_filt_cafe")
            with filt_col2:
                filt_metodo = st.multiselect("Método", _metodos_hist,
                                             default=_metodos_hist, key="h_filt_metodo")
            with filt_col3:
                filt_nota = st.slider("Nota mínima", 0, 5, 0, key="h_filt_nota",
                                      help="0 = mostrar todas")
            _prev_filt = st.session_state.get("_hist_filt_sig")
            _cur_filt = (tuple(sorted(filt_cafe)), tuple(sorted(filt_metodo)), filt_nota)
            if _prev_filt != _cur_filt:
                st.session_state["_hist_page"] = 0
                st.session_state["_hist_filt_sig"] = _cur_filt
            rows = [r for r in rows
                    if r["cafe_nome"] in filt_cafe
                    and r["metodo"] in filt_metodo
                    and (filt_nota == 0 or (r.get("nota_final_stars") or 0) >= filt_nota)]

            st.markdown(
                f'<p style="color:#8A8278;font-size:12px;margin:-0.5rem 0 1rem;'
                f'font-weight:600">{len(rows)} extração(ões) — máximo 200 mais recentes</p>',
                unsafe_allow_html=True)

            # ── Gráfico de evolução EY ────────────────────────────────────
            _ey_rows = [r for r in rows if r.get("ey") and float(r["ey"]) > 0]
            if len(_ey_rows) >= 2:
                with st.expander("📈 Evolução do Extraction Yield (EY)", expanded=False):
                    _fig_ey = go.Figure()
                    _ey_by_cafe = {}
                    for _r in sorted(_ey_rows, key=lambda x: x["data"]):
                        _ey_by_cafe.setdefault(_r["cafe_nome"], {"x": [], "y": []})
                        _ey_by_cafe[_r["cafe_nome"]]["x"].append(str(_r["data"]))
                        _ey_by_cafe[_r["cafe_nome"]]["y"].append(float(_r["ey"]))
                    _colors = ["#D97732","#A0A0A0","#707070","#E8A060","#C0C0C0"]
                    for _ci, (_cname, _cdata) in enumerate(_ey_by_cafe.items()):
                        _fig_ey.add_trace(go.Scatter(
                            x=_cdata["x"], y=_cdata["y"],
                            mode="lines+markers", name=_cname,
                            line=dict(color=_colors[_ci % len(_colors)], width=2),
                            marker=dict(size=6)))
                    _fig_ey.add_hrect(y0=18, y1=22, fillcolor="#D97732",
                                      opacity=0.08, line_width=0,
                                      annotation_text="Janela ideal 18–22%",
                                      annotation_position="top left",
                                      annotation_font_size=11)
                    _fig_ey.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#C8C0B8", height=280, margin=dict(l=0,r=0,t=10,b=0),
                        legend=dict(font_size=11, bgcolor="rgba(0,0,0,0)"),
                        xaxis=dict(showgrid=False, tickfont_size=10),
                        yaxis=dict(gridcolor="#2A2420", ticksuffix="%", tickfont_size=10))
                    st.plotly_chart(_fig_ey, use_container_width=True,
                                    config={"displayModeBar": False})

            # ── Exportar CSV ──────────────────────────────────────────────
            if rows:
                import csv, io as _io
                _csv_buf = _io.StringIO()
                _csv_fields = ["data","cafe_nome","metodo","gramas","agua_alvo",
                                "tempo_extracao","tds","ey","brew_ratio","nota_final_stars",
                                "moedor","clicks_moedor","temp_real","pressao_real","notas"]
                _writer = csv.DictWriter(_csv_buf, fieldnames=_csv_fields, extrasaction="ignore")
                _writer.writeheader()
                _writer.writerows(rows)
                st.download_button(
                    "⬇️ Exportar CSV", data=_csv_buf.getvalue(),
                    file_name="historico_extracoes.csv", mime="text/csv",
                    use_container_width=True)

            # Paginação
            _PG = 20
            _hist_pg = st.session_state.get("_hist_page", 0)
            _total_pgs = max(1, (len(rows) + _PG - 1) // _PG)
            _hist_pg = min(_hist_pg, _total_pgs - 1)
            st.session_state["_hist_page"] = _hist_pg
            _rows_pg = rows[_hist_pg * _PG: (_hist_pg + 1) * _PG]
            if _total_pgs > 1:
                _pg1, _pg2, _pg3 = st.columns([1, 2, 1])
                with _pg1:
                    if st.button("← Anterior", disabled=_hist_pg == 0, key="hist_prev"):
                        st.session_state["_hist_page"] = _hist_pg - 1
                        st.rerun()
                with _pg2:
                    st.markdown(
                        f'<p style="text-align:center;color:#8A8278;font-size:12px;padding-top:8px">'
                        f'Página {_hist_pg + 1} de {_total_pgs}</p>', unsafe_allow_html=True)
                with _pg3:
                    if st.button("Próxima →", disabled=_hist_pg >= _total_pgs - 1, key="hist_next"):
                        st.session_state["_hist_page"] = _hist_pg + 1
                        st.rerun()

            for r in _rows_pg:
                # Monta header com data relativa + classificações
                nota = r.get('nota_final_stars') or r['classificacao'] or 0
                stars_str = ("  ·  " + _stars(int(nota))) if nota else ""
                when = _relative_date(r['data'])
                header = (f"{when}  ·  {r['cafe_nome']}  ·  {r['metodo']}{stars_str}")
                with st.expander(header):
                    ra, rb, rc = st.columns([1, 2.2, 1.4], gap="large")
                    with ra:
                        if r["foto_caneca"]:
                            _img(r["foto_caneca"], w=150)
                        else:
                            st.markdown(_ph(), unsafe_allow_html=True)
                    with rb:
                        tags = _tag(r['metodo'], True) + _tag(r['torra'])
                        info = (_irow("Dose",  f"{r['gramas']}g") +
                                _irow("Água",  f"{r['agua_alvo']}g") +
                                _irow("Tempo", f"{r['tempo_extracao']}s") +
                                _irow("TDS",   f"{r['tds']}%" if r['tds'] else "—") +
                                (_irow("Moedor", f"{r['moedor']}  ·  {r['clicks_moedor']} clicks")
                                 if r["moedor"] else ""))
                        note = (f'<div style="margin-top:10px;font-size:13px;color:#B8B0A8;'
                                f'font-style:italic;line-height:1.5;">{_html.escape(r["notas"])}</div>' if r["notas"] else "")
                        st.markdown(f'<div>{tags}</div><div style="margin-top:12px">{info}</div>{note}',
                                    unsafe_allow_html=True)
                    with rc:
                        if r["brew_ratio"]: st.metric("Brew Ratio", f"1 : {r['brew_ratio']:.1f}")
                        if r["ey"]:         st.metric("EY",         f"{r['ey']:.1f}%")
                        if r["fluxo"]:      st.metric("Fluxo",      f"{r['fluxo']:.2f} g/s")

                    # Classificações por Estrelas
                    st.markdown("---")
                    st.markdown("**⭐ Classificação Detalhada:**")
                    cols = st.columns(4, gap="small")
                    classificacoes = [
                        ("CREMA", r.get('crema_stars', 0)),
                        ("CORPO", r.get('corpo_stars', 0)),
                        ("EQUILÍBRIO", r.get('equilibrio_stars', 0)),
                        ("ACIDEZ", r.get('acidez_stars', 0)),
                        ("AMARGOR", r.get('amargor_stars', 0)),
                        ("PRESENÇA NA BOCA", r.get('presenca_boca_stars', 0)),
                        ("DOÇURA", r.get('docura_stars', 0)),
                        ("NOTA FINAL", r.get('nota_final_stars', 0)),
                    ]
                    for idx, (label, stars) in enumerate(classificacoes):
                        with cols[idx % 4]:
                            stars_str = "⭐" * (stars or 0) + "☆" * (5 - (stars or 0))
                            st.markdown(f"**{label}**\n{stars_str}", help=f"{label}: {stars or 0}/5")

                    # Balanco Ideal
                    if r.get('balanco_ideal'):
                        st.markdown(f"**Balanço Perfeito:** {r['balanco_ideal']}")

                    st.markdown("")
                    col_edit, col_share, col_del = st.columns([1, 1, 1])
                    with col_edit:
                        if st.button("✏️ Editar", key=f"tab4_edit_e_{r['id']}"):
                            st.session_state[f"editing_e_{r['id']}"] = True
                    with col_share:
                        _share_key = f"_share_{r['id']}"
                        if st.button("📋 Compartilhar", key=f"tab4_share_{r['id']}"):
                            st.session_state[_share_key] = not st.session_state.get(_share_key, False)
                        if st.session_state.get(_share_key):
                            _ey_line = f"EY: {float(r['ey']):.1f}%  " if r.get("ey") and float(r["ey"]) > 0 else ""
                            _nota_line = f"Nota: {r.get('nota_final_stars') or 0}/5  " if r.get("nota_final_stars") else ""
                            _notas_line = f"\nNotas: {r['notas']}" if r.get("notas") else ""
                            _share_text = (
                                f"☕ {r['cafe_nome']} — {r['metodo']}\n"
                                f"📅 {r['data'].strftime('%d/%m/%Y')}\n"
                                f"Dose: {float(r['gramas']):.1f}g → Yield: {float(r['agua_alvo']):.0f}g"
                                f"  (1:{float(r['agua_alvo'])/float(r['gramas']):.1f})\n"
                                f"Tempo: {int(r['tempo_extracao'])}s  "
                                f"Moagem: {int(r['clicks_moedor'] or 0)} clicks ({r['moedor'] or '—'})  "
                                f"{_ey_line}{_nota_line}"
                                f"{_notas_line}\n"
                                f"#MateúCoffee #CaféEspecial #Barista"
                            )
                            st.text_area("📋 Copie e compartilhe:", value=_share_text,
                                         height=160, key=f"share_txt_{r['id']}")
                    with col_del:
                        if st.button("🗑️ Remover", key=f"tab4_del_e_{r['id']}"):
                            st.session_state[f"confirm_del_e4_{r['id']}"] = True
                    if st.session_state.get(f"confirm_del_e4_{r['id']}"):
                        st.warning("Confirmar remoção desta extração?")
                        cya, cna = st.columns(2)
                        with cya:
                            if st.button("✓ Remover", key=f"del_e4_ok_{r['id']}", type="primary"):
                                _run("DELETE FROM extracoes WHERE id=%s AND user_id=%s", (r["id"], user_id))
                                st.rerun()
                        with cna:
                            if st.button("← Cancelar", key=f"del_e4_cancel_{r['id']}"):
                                st.session_state.pop(f"confirm_del_e4_{r['id']}", None)
                                st.rerun()

                    # Form de Edição completo (parâmetros + estrelas detalhadas)
                    if st.session_state.get(f"editing_e_{r['id']}"):
                        st.markdown("---")
                        st.markdown('<p class="section-label">Editar Extração</p>',
                                    unsafe_allow_html=True)

                        # 1) Parâmetros
                        edit_col1, edit_col2 = st.columns(2, gap="large")
                        with edit_col1:
                            ed_gramas = st.number_input("Dose (g)", value=float(r['gramas']),
                                                        key=f"edit_gramas_{r['id']}")
                            ed_agua = st.number_input("Água (g)", value=float(r['agua_alvo']),
                                                      key=f"edit_agua_{r['id']}")
                            ed_tempo = st.number_input("Tempo (s)", value=int(r['tempo_extracao']),
                                                       key=f"edit_tempo_{r['id']}")
                        with edit_col2:
                            ed_moedor = st.text_input("Moedor", value=r['moedor'] or "",
                                                      key=f"edit_moedor_{r['id']}")
                            ed_clicks = st.number_input("Clicks", value=int(r['clicks_moedor'] or 0),
                                                        key=f"edit_clicks_{r['id']}")
                            ed_tds = st.number_input("TDS (%)", value=float(r['tds'] or 0),
                                                     key=f"edit_tds_{r['id']}")

                        ed_notas = st.text_area("Notas", value=r['notas'] or "",
                                                key=f"edit_notas_{r['id']}", height=80)

                        # Foto da caneca (editável)
                        st.markdown("**Foto da Caneca**")
                        _foto_col1, _foto_col2 = st.columns([1, 2], gap="large")
                        with _foto_col1:
                            if r.get("foto_caneca"):
                                _img(r["foto_caneca"], w=120)
                            else:
                                st.markdown(_ph(), unsafe_allow_html=True)
                        with _foto_col2:
                            ed_foto_f = st.file_uploader(
                                "Substituir / Adicionar foto",
                                type=["jpg", "jpeg", "png"],
                                key=f"edit_foto_{r['id']}")
                        ed_foto_b64 = _b64(ed_foto_f) if ed_foto_f else r.get("foto_caneca")

                        # 2) Classificação detalhada em estrelas (editável)
                        st.markdown('<p class="section-label">⭐ Classificação Detalhada</p>',
                                    unsafe_allow_html=True)
                        STAR_OPTS = [1, 2, 3, 4, 5]
                        es1, es2, es3, es4 = st.columns(4, gap="large")
                        with es1:
                            ed_crema = st.slider("Crema", 1, 5, int(r.get('crema_stars') or 3), key=f"e4_crema_{r['id']}")
                        with es2:
                            ed_corpo = st.slider("Corpo", 1, 5, int(r.get('corpo_stars') or 3), key=f"e4_corpo_{r['id']}")
                        with es3:
                            ed_equil = st.slider("Equilíbrio", 1, 5, int(r.get('equilibrio_stars') or 3), key=f"e4_equil_{r['id']}")
                        with es4:
                            ed_acid = st.slider("Acidez", 1, 5, int(r.get('acidez_stars') or 3), key=f"e4_acid_{r['id']}")

                        es5, es6, es7, es8 = st.columns(4, gap="large")
                        with es5:
                            ed_amargor = st.slider("Amargor", 1, 5, int(r.get('amargor_stars') or 3), key=f"e4_amar_{r['id']}")
                        with es6:
                            ed_pres = st.slider("Presença na Boca", 1, 5, int(r.get('presenca_boca_stars') or 3), key=f"e4_pres_{r['id']}")
                        with es7:
                            ed_doc = st.slider("Doçura", 1, 5, int(r.get('docura_stars') or 3), key=f"e4_doc_{r['id']}")
                        with es8:
                            ed_nota = st.slider("Nota Final", 1, 5, int(r.get('nota_final_stars') or 3), key=f"e4_nota_{r['id']}")

                        if st.button("💾 Salvar Alterações", key=f"tab4_save_e_{r['id']}",
                                     type="primary"):
                            _run("""UPDATE extracoes SET
                                    gramas=%s, agua_alvo=%s, tempo_extracao=%s,
                                    moedor=%s, clicks_moedor=%s, tds=%s, notas=%s,
                                    foto_caneca=%s,
                                    crema_stars=%s, corpo_stars=%s, equilibrio_stars=%s,
                                    acidez_stars=%s, amargor_stars=%s, presenca_boca_stars=%s,
                                    docura_stars=%s, nota_final_stars=%s, classificacao=%s
                                    WHERE id=%s AND user_id=%s""",
                                 (ed_gramas, ed_agua, ed_tempo,
                                  ed_moedor, ed_clicks, ed_tds, ed_notas,
                                  ed_foto_b64,
                                  ed_crema, ed_corpo, ed_equil,
                                  ed_acid, ed_amargor, ed_pres,
                                  ed_doc, ed_nota, ed_nota,
                                  r['id'], user_id))
                            st.session_state.pop(f"editing_e_{r['id']}", None)
                            st.toast("Alterações salvas", icon="✅")
                            st.rerun()

    # ── Tab 5 · Biblioteca de Receitas ────────────────────────────────
    with tab5:
        st.markdown('<p class="section-label">📖 Biblioteca de Receitas</p>',
                    unsafe_allow_html=True)
        st.markdown(
            '<p style="color:#B8B0A8;font-size:14px;line-height:1.6;'
            'margin:0 0 1.5rem">10 receitas-referência dos métodos mais '
            'comentados pelos especialistas — James Hoffmann, World AeroPress '
            'Championship, padrões italianos clássicos e SCA. Todas pressupõem '
            '<strong style="color:#F5EDE8">grãos moídos na hora</strong> para '
            'extração ideal.</p>',
            unsafe_allow_html=True)

        # Filtro por categoria
        categorias = sorted({r["categoria"] for r in RECIPES})
        col_f1, col_f2 = st.columns([0.7, 0.3], gap="medium")
        with col_f1:
            cat_sel = st.multiselect("Filtrar por categoria",
                                     options=categorias, default=categorias,
                                     key="recipe_cat_filter",
                                     help="Filtrado · Pressão · Imersão · Com Leite")
        with col_f2:
            ordem = st.selectbox("Ordenar por",
                                 ["Sugerida", "Nome", "Dificuldade"],
                                 key="recipe_order")

        receitas = [r for r in RECIPES if r["categoria"] in cat_sel]
        if ordem == "Nome":
            receitas.sort(key=lambda x: x["nome"])
        elif ordem == "Dificuldade":
            ordem_dif = {"Iniciante": 0, "Intermediário": 1, "Avançado": 2}
            receitas.sort(key=lambda x: ordem_dif.get(x["dificuldade"], 9))

        if not receitas:
            _empty("📖", "Nenhuma receita corresponde ao filtro",
                   "Selecione ao menos uma categoria para ver as receitas.")
        else:
            st.markdown(
                f'<p style="color:#8A8278;font-size:12px;margin:1rem 0 0.5rem;'
                f'font-weight:600">Exibindo {len(receitas)} de '
                f'{len(RECIPES)} receitas</p>',
                unsafe_allow_html=True)

            for r in receitas:
                header = (f"{r['icon']}  {r['nome']}  ·  "
                          f"{r['metodo']}  ·  {r['dificuldade']}")
                with st.expander(header):
                    _render_recipe(r)

            st.markdown(
                '<p style="color:#8A8278;font-size:12px;text-align:center;'
                'margin:2rem 0 0.5rem;line-height:1.6">'
                'As receitas e ratios foram extraídos de fontes públicas e podem '
                'ser ajustados ao seu paladar. Use-as como ponto de partida — '
                'depois registre suas próprias variações em <strong>Nova Extração</strong>.</p>',
                unsafe_allow_html=True)

    # ── Tab 6 · Cápsulas ─────────────────────────────────────────────
    with tab6:
        MAQUINAS_CAPSULAS = ["Nespresso", "Dolce Gusto", "Três Corações", "DeltaQ", "Outra"]
        VOLUMES_CAPSULAS  = {25: "Ristretto · 25ml", 40: "Espresso · 40ml", 110: "Lungo · 110ml"}

        st.markdown('<p class="section-label">Cadastrar Cápsula</p>', unsafe_allow_html=True)

        # Aplica resultado da análise de IA nas cápsulas
        if "ai_cap_result" in st.session_state:
            rc = st.session_state.pop("ai_cap_result")
            if rc.get("nome"):   st.session_state["cap_nome"]  = rc["nome"]
            if rc.get("marca"):  st.session_state["cap_marca"] = rc["marca"]

        ca1, ca2 = st.columns(2, gap="large")
        with ca1:
            cap_nome     = st.text_input("Nome da Cápsula *", key="cap_nome",
                                         placeholder="Ex: Dharkan, Volluto, Lungo Intenso")
            cap_marca    = st.text_input("Marca", key="cap_marca",
                                         placeholder="Ex: Nespresso, Dolce Gusto, 3 Corações")
            cap_maquina  = st.selectbox("Tipo de Máquina", MAQUINAS_CAPSULAS, key="cap_maquina")
            cap_intens   = st.select_slider("Intensidade", options=list(range(1, 13)),
                                            value=8, format_func=lambda x: f"{x}/12",
                                            key="cap_intensidade")
        with ca2:
            cap_qtd      = st.number_input("Quantidade de Cápsulas", min_value=1,
                                           max_value=200, value=10, step=1, key="cap_qtd")
            cap_aluminio = st.radio("Cápsula de Alumínio?", ["Sim", "Não"],
                                    horizontal=True, key="cap_aluminio")
            cap_volume   = st.radio("Volume",
                                    list(VOLUMES_CAPSULAS.keys()),
                                    format_func=lambda x: VOLUMES_CAPSULAS[x],
                                    horizontal=True, key="cap_volume")
            cap_foto_f   = st.file_uploader("Foto da Embalagem",
                                            type=["jpg","jpeg","png"], key="cap_foto")
            cap_foto_b64 = _b64(cap_foto_f) if cap_foto_f else None
            if cap_foto_b64:
                _img(cap_foto_b64, w=160)
                if st.button("🔍 Analisar Embalagem com IA", key="btn_ai_cap",
                             use_container_width=True):
                    with st.spinner("Lendo a embalagem..."):
                        try:
                            rc = _analisar_embalagem(cap_foto_b64)
                            st.session_state["ai_cap_result"] = rc
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro na análise: {e}")

        # ── Classificação sensorial da cápsula ────────────────────────
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">⭐ Classificação Sensorial</p>', unsafe_allow_html=True)
        _SC = [1, 2, 3, 4, 5]
        csx1, csx2, csx3, csx4 = st.columns(4, gap="large")
        with csx1:
            cap_crema   = st.slider("Crema", 1, 5, 3, key="cap_crema")
        with csx2:
            cap_corpo   = st.slider("Corpo", 1, 5, 3, key="cap_corpo")
        with csx3:
            cap_equil   = st.slider("Equilíbrio", 1, 5, 3, key="cap_equil")
        with csx4:
            cap_acid    = st.slider("Acidez", 1, 5, 3, key="cap_acid")
        csx5, csx6, csx7, csx8 = st.columns(4, gap="large")
        with csx5:
            cap_amar    = st.slider("Amargor", 1, 5, 3, key="cap_amar")
        with csx6:
            cap_pres    = st.slider("Presença na Boca", 1, 5, 3, key="cap_pres")
        with csx7:
            cap_doc     = st.slider("Doçura", 1, 5, 3, key="cap_doc")
        with csx8:
            cap_nota    = st.slider("Nota Final", 1, 5, 3, key="cap_nota")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        if st.button("Salvar Cápsula", type="primary", use_container_width=True, key="btn_save_cap"):
            if not cap_nome.strip():
                st.error("Nome da cápsula é obrigatório.")
            else:
                try:
                    _run("""INSERT INTO capsulas
                            (user_id, nome, marca, maquina, intensidade, quantidade,
                             aluminio, volume_ml, foto_embalagem,
                             crema_stars, corpo_stars, equilibrio_stars, acidez_stars,
                             amargor_stars, presenca_boca_stars, docura_stars, nota_final_stars)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (user_id, cap_nome.strip(), cap_marca.strip() or None,
                          cap_maquina, cap_intens, int(cap_qtd),
                          cap_aluminio == "Sim", int(cap_volume), cap_foto_b64,
                          cap_crema, cap_corpo, cap_equil, cap_acid,
                          cap_amar, cap_pres, cap_doc, cap_nota))
                    st.toast(f"🫘 {cap_nome} cadastrada com sucesso", icon="✅")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar cápsula: {e}")

        # ── Lista de cápsulas cadastradas ─────────────────────────────
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Minhas Cápsulas</p>', unsafe_allow_html=True)

        caps = _fetch("""SELECT * FROM capsulas WHERE user_id=%s
                         ORDER BY created_at DESC""", (user_id,), _v=_v())

        if not caps:
            _empty("🫘", "Nenhuma cápsula cadastrada ainda",
                   "Cadastre suas cápsulas acima para acompanhar o estoque e as preferências.",
                   hint="Preencha o formulário acima")
        else:
            _low_stock = [c for c in caps if int(c.get("quantidade") or 0) <= 3]
            if _low_stock:
                _low_names = ", ".join(c["nome"] for c in _low_stock)
                st.warning(f"⚠️ Estoque baixo: **{_low_names}**")
            st.markdown(
                f'<p style="color:#8A8278;font-size:12px;margin:-0.5rem 0 1rem;'
                f'font-weight:600">{len(caps)} cápsula{"s" if len(caps) != 1 else ""} cadastrada{"s" if len(caps) != 1 else ""}</p>',
                unsafe_allow_html=True)

            for cap in caps:
                alum_label = "Alumínio ✓" if cap.get("aluminio") else "Não alumínio"
                vol_label  = VOLUMES_CAPSULAS.get(cap.get("volume_ml", 40), "—")
                header_cap = (f"🫘 {cap['nome']}"
                              f"{'  ·  ' + cap['marca'] if cap.get('marca') else ''}"
                              f"  ·  {cap['maquina']}  ·  {cap['intensidade']}/12")
                with st.expander(header_cap):
                    cc1, cc2, cc3 = st.columns([1, 2.2, 1.4], gap="large")
                    with cc1:
                        if cap.get("foto_embalagem"):
                            _img(cap["foto_embalagem"], w=150)
                        else:
                            st.markdown(_ph(), unsafe_allow_html=True)
                    with cc2:
                        c_info = (_irow("Máquina",    cap['maquina']) +
                                  _irow("Intensidade", f"{cap['intensidade']}/12") +
                                  _irow("Volume",      vol_label) +
                                  _irow("Alumínio",    alum_label))
                        if cap.get("marca"):
                            c_info = _irow("Marca", cap['marca']) + c_info
                        st.markdown(c_info, unsafe_allow_html=True)
                    with cc3:
                        _qtd_atual = int(cap.get("quantidade") or 0)
                        if _qtd_atual <= 3 and _qtd_atual > 0:
                            st.warning(f"⚠️ Estoque baixo: {_qtd_atual} un.")
                        elif _qtd_atual == 0:
                            st.error("❌ Sem estoque")
                        else:
                            st.metric("Estoque", f"{_qtd_atual} un.")
                        # Usar cápsulas — decremento rápido de estoque
                        _use_n = st.number_input("Usar", min_value=1, max_value=max(1, _qtd_atual),
                                                 value=1, step=1,
                                                 key=f"use_cap_n_{cap['id']}",
                                                 label_visibility="visible")
                        if st.button("☕ Registrar uso", key=f"use_cap_btn_{cap['id']}",
                                     disabled=_qtd_atual == 0):
                            _nova_qtd = max(0, _qtd_atual - _use_n)
                            _run("UPDATE capsulas SET quantidade=%s WHERE id=%s AND user_id=%s",
                                 (_nova_qtd, cap["id"], user_id))
                            st.toast(f"✓ {_use_n} cápsula(s) usada(s). Estoque: {_nova_qtd}")
                            st.rerun()
                        st.markdown("---")
                        _add_n = st.number_input("Reabastecer", min_value=1, max_value=500,
                                                 value=10, step=1, key=f"add_cap_n_{cap['id']}")
                        if st.button("📦 Reabastecer", key=f"add_cap_btn_{cap['id']}"):
                            _nova_qtd2 = _qtd_atual + _add_n
                            _run("UPDATE capsulas SET quantidade=%s WHERE id=%s AND user_id=%s",
                                 (_nova_qtd2, cap["id"], user_id))
                            st.toast(f"✅ +{_add_n} cápsula(s). Estoque: {_nova_qtd2}")
                            st.rerun()
                        if cap.get("nota_final_stars"):
                            st.metric("Nota Final", _stars(cap["nota_final_stars"]))
                        st.markdown(
                            f'<p style="font-size:11px;color:#8A8278;margin:4px 0 0">'
                            f'Cadastrado em {cap["created_at"].strftime("%d/%m/%Y")}</p>',
                            unsafe_allow_html=True)

                    # Classificação sensorial (se preenchida)
                    _cls_cap = [
                        ("CREMA",           cap.get("crema_stars", 0)),
                        ("CORPO",           cap.get("corpo_stars", 0)),
                        ("EQUILÍBRIO",      cap.get("equilibrio_stars", 0)),
                        ("ACIDEZ",          cap.get("acidez_stars", 0)),
                        ("AMARGOR",         cap.get("amargor_stars", 0)),
                        ("PRESENÇA NA BOCA",cap.get("presenca_boca_stars", 0)),
                        ("DOÇURA",          cap.get("docura_stars", 0)),
                        ("NOTA FINAL",      cap.get("nota_final_stars", 0)),
                    ]
                    if any(v for _, v in _cls_cap):
                        st.markdown("---")
                        st.markdown("**⭐ Classificação Sensorial:**")
                        _cls_cols = st.columns(4, gap="small")
                        for _idx, (_lbl, _sv) in enumerate(_cls_cap):
                            with _cls_cols[_idx % 4]:
                                st.markdown(f"**{_lbl}**\n{'⭐'*(_sv or 0)}{'☆'*(5-(_sv or 0))}")

                    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

                    # Form de edição
                    if st.button("✏️ Editar cápsula", key=f"cap_edit_btn_{cap['id']}"):
                        st.session_state[f"edit_cap_{cap['id']}"] = True

                    if st.session_state.get(f"edit_cap_{cap['id']}"):
                        st.markdown('<p class="section-label">Editar Cápsula</p>', unsafe_allow_html=True)
                        ce1, ce2 = st.columns(2, gap="large")
                        with ce1:
                            edc_nome   = st.text_input("Nome", value=cap['nome'] or "",
                                                       key=f"cedit_nome_{cap['id']}")
                            edc_marca  = st.text_input("Marca", value=cap.get('marca') or "",
                                                       key=f"cedit_marca_{cap['id']}")
                            _mi = MAQUINAS_CAPSULAS.index(cap['maquina']) if cap['maquina'] in MAQUINAS_CAPSULAS else 0
                            edc_maq    = st.selectbox("Máquina", MAQUINAS_CAPSULAS, index=_mi,
                                                      key=f"cedit_maq_{cap['id']}")
                        with ce2:
                            _ci2 = max(1, min(12, int(cap.get('intensidade') or 8)))
                            edc_intens = st.select_slider("Intensidade", options=list(range(1,13)),
                                                          value=_ci2, format_func=lambda x: f"{x}/12",
                                                          key=f"cedit_intens_{cap['id']}")
                            edc_qtd    = st.number_input("Quantidade", min_value=0,
                                                         value=int(cap.get('quantidade') or 10),
                                                         step=1, key=f"cedit_qtd_{cap['id']}")
                            edc_alum   = st.radio("Alumínio?", ["Sim","Não"],
                                                  index=0 if cap.get("aluminio") else 1,
                                                  horizontal=True, key=f"cedit_alum_{cap['id']}")
                            _vol_keys = list(VOLUMES_CAPSULAS.keys())
                            _vol_idx  = _vol_keys.index(cap.get("volume_ml", 40)) if cap.get("volume_ml", 40) in _vol_keys else 1
                            edc_vol    = st.radio("Volume", _vol_keys,
                                                  format_func=lambda x: VOLUMES_CAPSULAS[x],
                                                  index=_vol_idx, horizontal=True,
                                                  key=f"cedit_vol_{cap['id']}")

                        st.markdown('<p class="section-label">⭐ Classificação Sensorial</p>', unsafe_allow_html=True)
                        _SC2 = [1, 2, 3, 4, 5]
                        ces1, ces2, ces3, ces4 = st.columns(4, gap="large")
                        with ces1:
                            edc_crema = st.slider("Crema", 1, 5, int(cap.get("crema_stars") or 3), key=f"cedit_crema_{cap['id']}")
                        with ces2:
                            edc_corpo = st.slider("Corpo", 1, 5, int(cap.get("corpo_stars") or 3), key=f"cedit_corpo_{cap['id']}")
                        with ces3:
                            edc_equil = st.slider("Equilíbrio", 1, 5, int(cap.get("equilibrio_stars") or 3), key=f"cedit_equil_{cap['id']}")
                        with ces4:
                            edc_acid  = st.slider("Acidez", 1, 5, int(cap.get("acidez_stars") or 3), key=f"cedit_acid_{cap['id']}")
                        ces5, ces6, ces7, ces8 = st.columns(4, gap="large")
                        with ces5:
                            edc_amar  = st.slider("Amargor", 1, 5, int(cap.get("amargor_stars") or 3), key=f"cedit_amar_{cap['id']}")
                        with ces6:
                            edc_pres  = st.slider("Presença na Boca", 1, 5, int(cap.get("presenca_boca_stars") or 3), key=f"cedit_pres_{cap['id']}")
                        with ces7:
                            edc_doc   = st.slider("Doçura", 1, 5, int(cap.get("docura_stars") or 3), key=f"cedit_doc_{cap['id']}")
                        with ces8:
                            edc_nota  = st.slider("Nota Final", 1, 5, int(cap.get("nota_final_stars") or 3), key=f"cedit_nota_{cap['id']}")

                        cse1, cse2 = st.columns(2)
                        with cse1:
                            if st.button("💾 Salvar", type="primary",
                                         key=f"cap_save_{cap['id']}", use_container_width=True):
                                try:
                                    _run("""UPDATE capsulas SET
                                            nome=%s, marca=%s, maquina=%s, intensidade=%s,
                                            quantidade=%s, aluminio=%s, volume_ml=%s,
                                            crema_stars=%s, corpo_stars=%s, equilibrio_stars=%s,
                                            acidez_stars=%s, amargor_stars=%s,
                                            presenca_boca_stars=%s, docura_stars=%s,
                                            nota_final_stars=%s
                                            WHERE id=%s AND user_id=%s""",
                                         (edc_nome.strip(), edc_marca.strip() or None,
                                          edc_maq, edc_intens, int(edc_qtd),
                                          edc_alum == "Sim", int(edc_vol),
                                          edc_crema, edc_corpo, edc_equil,
                                          edc_acid, edc_amar, edc_pres,
                                          edc_doc, edc_nota,
                                          cap['id'], user_id))
                                    st.session_state.pop(f"edit_cap_{cap['id']}", None)
                                    st.toast("Cápsula atualizada", icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")
                        with cse2:
                            if st.button("← Cancelar", key=f"cap_cancel_{cap['id']}",
                                         use_container_width=True):
                                st.session_state.pop(f"edit_cap_{cap['id']}", None)
                                st.rerun()

                    # Deletar
                    if st.button("🗑️ Remover cápsula", key=f"cap_del_{cap['id']}"):
                        st.session_state[f"confirm_del_cap_{cap['id']}"] = True
                    if st.session_state.get(f"confirm_del_cap_{cap['id']}"):
                        st.warning(f"Remover **{cap['nome']}** definitivamente?")
                        cyd, cnd = st.columns(2)
                        with cyd:
                            if st.button("✓ Confirmar", type="primary",
                                         key=f"cap_del_ok_{cap['id']}"):
                                _run("DELETE FROM capsulas WHERE id=%s AND user_id=%s",
                                     (cap['id'], user_id))
                                st.rerun()
                        with cnd:
                            if st.button("← Cancelar", key=f"cap_del_cancel_{cap['id']}"):
                                st.session_state.pop(f"confirm_del_cap_{cap['id']}", None)
                                st.rerun()


    # ── Tab 7 · Backup ────────────────────────────────────────────────
    with tab7:
        st.markdown('<p class="section-label">Sistema de Backup</p>', unsafe_allow_html=True)

        st.info(
            "**Backups automáticos semanais** são criados toda vez que você acessa o app "
            "após 7 dias do último backup. Você também pode criar backups manuais "
            "e restaurar o banco de dados para qualquer ponto anterior.",
            icon="🛡️")

        # ── Criar backup manual ──────────────────────────────────────
        with st.expander("➕ Criar backup manual agora", expanded=False):
            notas_backup = st.text_input("Descrição (opcional)", key="bk_notas",
                                         placeholder="Ex: antes de apagar cafés antigos")
            if st.button("💾 Criar backup", type="primary", key="bk_criar"):
                with st.spinner("Criando backup…"):
                    ok = _backup_criar("manual", notas_backup, user_id)
                if ok:
                    st.success("Backup criado com sucesso!", icon="✅")
                    st.rerun()

        st.markdown("---")

        # ── Lista de backups ─────────────────────────────────────────
        backups = _backup_listar(user_id)
        if not backups:
            st.info("Nenhum backup encontrado. Crie o primeiro backup acima.")
        else:
            st.markdown(f"**{len(backups)} backup(s) disponíveis** (máx. 30 exibidos)")
            for bk in backups:
                criado = bk["criado_em"]
                if isinstance(criado, str):
                    criado = _dt.datetime.fromisoformat(criado)
                data_fmt = criado.strftime("%d/%m/%Y %H:%M")
                tipo_icon = {"manual": "🔵", "semanal": "🟢", "pre-restore": "🟡"}.get(bk["tipo"], "⚪")
                titulo = f"{tipo_icon} **{data_fmt}** — {bk['tipo'].upper()}"
                if bk.get("notas"):
                    titulo += f" — _{bk['notas']}_"
                stats = (f"☕ {bk['n_cafes']} cafés · "
                         f"⚗️ {bk['n_extracoes']} extrações · "
                         f"🫘 {bk['n_capsulas']} cápsulas")
                if bk.get("git_hash"):
                    stats += f" · git `{bk['git_hash']}`"

                with st.expander(titulo, expanded=False):
                    st.caption(stats)

                    if st.session_state.get(f"confirm_restore_{bk['id']}"):
                        st.warning(
                            "⚠️ Isso **substituirá todos os seus dados** pelos dados deste backup. "
                            "Um backup de segurança será criado automaticamente antes. Confirma?")
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            if st.button("✅ Confirmar restauração", type="primary",
                                         key=f"bk_restore_ok_{bk['id']}",
                                         use_container_width=True):
                                with st.spinner("Restaurando dados…"):
                                    ok = _backup_restaurar_dados(bk["id"], user_id)
                                st.session_state.pop(f"confirm_restore_{bk['id']}", None)
                                if ok:
                                    st.success("Dados restaurados com sucesso!", icon="✅")
                                    st.rerun()
                        with rc2:
                            if st.button("← Cancelar", key=f"bk_restore_cancel_{bk['id']}",
                                         use_container_width=True):
                                st.session_state.pop(f"confirm_restore_{bk['id']}", None)
                                st.rerun()
                    else:
                        if st.button("🔄 Restaurar este backup", key=f"bk_restore_{bk['id']}",
                                     use_container_width=True):
                            st.session_state[f"confirm_restore_{bk['id']}"] = True
                            st.rerun()


if __name__ == "__main__":
    main()
