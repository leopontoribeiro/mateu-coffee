import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import base64
import os
import json
from datetime import date, datetime, timedelta
from io import BytesIO
import hashlib
import secrets
from typing import Optional
import anthropic
from PIL import Image

# ── Barista Expert AI ──────────────────────────────────────────────────
# Integração de IA especializada em café com Claude API
def ask_barista_expert(pergunta: str) -> str:
    """Pergunta ao Barista Expert usando Claude API com knowledge base."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ Variável ANTHROPIC_API_KEY não configurada"

    try:
        # Carregar knowledge base
        with open("coffee_knowledge.json", "r", encoding="utf-8") as f:
            kb = json.load(f)
        kb_text = json.dumps(kb, indent=2, ensure_ascii=False)

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = f"""Você é um Barista Expert — especialista em café com 15+ anos de experiência.

Use a seguinte base de conhecimento:
{kb_text}

Instruções:
1. Responda em português brasileiro, prático e direto
2. Use especificações exatas da knowledge base
3. Dê dicas actionáveis que o usuário possa executar já
4. Se não souber, admita e sugira experimentação
5. Refira-se à knowledge base quando relevante
6. Responda como um barista experiente explicando para outro café."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": pergunta}]
        )
        return message.content[0].text
    except FileNotFoundError:
        return "⚠️ Knowledge base de café não encontrada"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

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
    """Widget de consumo: hoje + semana + média + total — apenas do usuário logado."""
    hoje = _today_local()
    user_id = st.session_state.get('user_id')

    stats = _fetch("""
        SELECT
          COALESCE(SUM(CASE WHEN data = %s THEN gramas ELSE 0 END), 0) AS hoje_g,
          COALESCE(SUM(CASE WHEN data >= %s THEN gramas ELSE 0 END), 0) AS semana_g,
          COUNT(CASE WHEN data >= %s THEN 1 END)                       AS semana_n,
          COUNT(*)                                                     AS total_n
        FROM extracoes WHERE user_id = %s
    """, (hoje, hoje - timedelta(days=6), hoje - timedelta(days=6), user_id), _v=_v())

    s = stats[0] if stats else {"hoje_g": 0, "semana_g": 0, "semana_n": 0, "total_n": 0}
    media_dia = (s["semana_g"] / 7) if s["semana_g"] else 0

    st.markdown(
        f'<div class="mc-consumo">'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Hoje</p>'
        f'    <p class="mc-consumo-value accent">{s["hoje_g"]:.0f}<span style="font-size:13px;font-weight:600">g</span></p>'
        f'    <p class="mc-consumo-sub">{hoje.strftime("%d/%m/%Y")}</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Esta Semana</p>'
        f'    <p class="mc-consumo-value">{s["semana_g"]:.0f}<span style="font-size:13px;font-weight:600">g</span></p>'
        f'    <p class="mc-consumo-sub">{s["semana_n"]} extraç{"ões" if s["semana_n"] != 1 else "ão"}</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Média/dia</p>'
        f'    <p class="mc-consumo-value">{media_dia:.0f}<span style="font-size:13px;font-weight:600">g</span></p>'
        f'    <p class="mc-consumo-sub">últimos 7 dias</p>'
        f'  </div>'
        f'  <div class="mc-consumo-cell">'
        f'    <p class="mc-consumo-label">Total Histórico</p>'
        f'    <p class="mc-consumo-value">{s["total_n"]}</p>'
        f'    <p class="mc-consumo-sub">extrações registradas</p>'
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
<link rel="manifest" href="data:application/json;charset=utf-8,%7B%22name%22%3A%22Mateu%20Coffee%22%2C%22short_name%22%3A%22Mateu%22%2C%22start_url%22%3A%22%2F%22%2C%22display%22%3A%22standalone%22%2C%22background_color%22%3A%22%230A0A0A%22%2C%22theme_color%22%3A%22%23E8722E%22%2C%22orientation%22%3A%22portrait%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22https%3A%2F%2Fi.imgur.com%2FyQkZ1.png%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fpng%22%7D%5D%7D">
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">
<style>
    /* ═══════════════════════════════════════════════════════════════
       MATEU COFFEE — DESIGN TOKENS
       Paleta extraída do logo oficial: gato + xícara em laranja vibrante
       sobre preto puro, com "COFFEE" em cinza quente.
       ═══════════════════════════════════════════════════════════════ */
    :root {
        --mc-bg: #0A0A0A;
        --mc-surface: #141414;
        --mc-surface-2: #1C1C1C;
        --mc-surface-3: #242424;
        --mc-border: #2A2A2A;
        --mc-border-strong: #3A3A3A;

        --mc-orange: #E8722E;
        --mc-orange-hover: #F08842;
        --mc-orange-soft: #3A1E10;
        --mc-orange-glow: rgba(232, 114, 46, 0.18);

        --mc-text: #F5EDE8;
        --mc-text-2: #B8B0A8;
        --mc-text-3: #8A8278;
        --mc-text-muted: #6C6660;

        --mc-success: #4CAF6F;
        --mc-error: #E55A4C;
        --mc-warning: #E8A23E;
        --mc-info: #5BB0E8;
    }

    /* ─── Tipografia base ─────────────────────────────────────────── */
    html, body, [class*="css"], .stApp, div, p, span, label,
    h1, h2, h3, h4, h5, h6, button, input, textarea, select {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
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
        font-size: 28px !important;
        font-weight: 800 !important;
        color: var(--mc-text) !important;
        letter-spacing: -0.025em !important;
        margin: 0 0 1rem 0 !important;
    }
    h2 {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: var(--mc-text) !important;
        letter-spacing: -0.02em !important;
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
        border-bottom: 1px solid var(--mc-border);
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

    /* ─── Tabs (navegação principal) ────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--mc-surface);
        border-radius: 12px;
        padding: 6px;
        border: 1px solid var(--mc-border);
        width: fit-content;
        margin-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: var(--mc-text-2);
        font-size: 13px;
        font-weight: 600;
        padding: 9px 22px;
        border: none;
        transition: all 0.18s ease;
        letter-spacing: 0;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--mc-surface-2);
        color: var(--mc-text);
    }
    .stTabs [aria-selected="true"] {
        background: var(--mc-orange) !important;
        color: #0A0A0A !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px var(--mc-orange-glow) !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-panel"]  { padding-top: 2rem !important; }

    /* ─── Section labels (eyebrow) ──────────────────────────────── */
    .section-label {
        font-size: 11px;
        font-weight: 700;
        color: var(--mc-orange);
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin: 0 0 1.25rem 0;
        display: inline-block;
        padding-bottom: 6px;
        border-bottom: 2px solid var(--mc-orange);
    }
    .section-divider {
        border: none;
        border-top: 1px solid var(--mc-border);
        margin: 2.25rem 0;
    }

    /* ─── Tags / chips ─────────────────────────────────────────── */
    .tag {
        display: inline-block;
        background: var(--mc-surface-2);
        border: 1px solid var(--mc-border);
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
        border: 1px solid var(--mc-border) !important;
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
        font-size: 22px !important;
        font-weight: 800 !important;
        color: var(--mc-orange) !important;
        letter-spacing: -0.025em !important;
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
        border: 1px solid var(--mc-border) !important;
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
        border: 1px solid var(--mc-border) !important;
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
        border: 1px solid var(--mc-border) !important;
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
        border: 1px solid var(--mc-border) !important;
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
        color: #0A0A0A !important;
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
        border: 1px solid var(--mc-border) !important;
        color: var(--mc-text) !important;
    }

    /* ─── Radio chips ─────────────────────────────────────────── */
    .stRadio > div { gap: 8px !important; }
    .stRadio > div > label {
        background: var(--mc-surface) !important;
        border: 1px solid var(--mc-border) !important;
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
        border: 1px solid var(--mc-border) !important;
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
        border-top: 1px solid var(--mc-border) !important;
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
        border: 1px solid var(--mc-border) !important;
    }

    /* ─── Tooltips ────────────────────────────────────────────── */
    div[role="tooltip"] {
        background: var(--mc-surface-3) !important;
        color: var(--mc-text) !important;
        border: 1px solid var(--mc-border-strong) !important;
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
        background: linear-gradient(180deg, var(--mc-surface) 0%, var(--mc-bg) 100%);
        border: 1px dashed var(--mc-border-strong);
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
        border: 1px solid var(--mc-orange);
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
        border-bottom: 1px solid var(--mc-border);
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
        border: 1px solid var(--mc-border);
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

        /* Tabs: barra fixa no topo, rolável na horizontal, sem quebra */
        .stTabs [data-baseweb="tab-list"] {
            width: 100% !important;
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            position: sticky;
            top: 0;
            z-index: 999;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            gap: 2px;
            padding: 5px;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 13px;
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
def _get_conn() -> "psycopg2.extensions.connection":
    # Prioridade 1: variável de ambiente DATABASE_URL (Railway, Render, Heroku)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url, sslmode="require", connect_timeout=10)
    # Prioridade 2: st.secrets (Streamlit Cloud)
    try:
        s = st.secrets["connections"]["postgresql"]
        return psycopg2.connect(
            host=s["host"], port=int(s["port"]), dbname=s["database"],
            user=s["username"], password=s["password"],
            sslmode="require", connect_timeout=10,
        )
    except Exception:
        pass
    # Prioridade 3: variáveis de ambiente individuais
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
        connect_timeout=10,
    )

def _conn() -> "psycopg2.extensions.connection":
    """Retorna conexão ativa. Reconecta automaticamente se a conexão
    estiver fechada ou morta (desconexão server-side não detectada por c.closed)."""
    c = _get_conn()
    try:
        # Ping leve — detecta conexões mortas que o servidor fechou
        cur = c.cursor()
        cur.execute("SELECT 1")
        cur.close()
        c.rollback()          # descarta transação implícita do ping
    except Exception:
        st.cache_resource.clear()
        c = _get_conn()
    return c

def _run(query: str, params: tuple = ()) -> None:
    c = _conn()
    cur = c.cursor()
    try:
        cur.execute(query, params)
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        cur.close()
    _bump()

def _bump() -> None:
    st.session_state["_v"] = st.session_state.get("_v", 0) + 1
    _fetch.clear()  # invalida cache cross-session — evita dados obsoletos após F5

@st.cache_data(ttl=600, show_spinner=False)
def _fetch(query: str, params: tuple = (), _v: int = 0) -> list:
    c   = _conn()
    cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        cur.close()
    return rows

def _v() -> int:
    return st.session_state.get("_v", 0)

# ─── Cookie manager para persistência real do "Manter-me conectado" ───
# st.session_state é EFÊMERO (vive só enquanto a aba está aberta).
# Cookie no browser é o único jeito de manter sessão entre visitas.
_COOKIE_NAME = "mc_remember"

def _set_cookie_js(token: str, days: int = 30) -> None:
    """Grava cookie via JS nativo (iframe same-origin) — sem libs externas."""
    components.html(
        f"<script>window.parent.document.cookie="
        f"'{_COOKIE_NAME}={token}; max-age={days*86400}; path=/; SameSite=Lax';</script>",
        height=0)

def _clear_cookie_js() -> None:
    components.html(
        f"<script>window.parent.document.cookie="
        f"'{_COOKIE_NAME}=; max-age=0; path=/';</script>", height=0)

def _read_cookie() -> Optional[str]:
    """Lê o cookie enviado pelo browser na conexão (st.context, Streamlit 1.37+)."""
    try:
        return st.context.cookies.get(_COOKIE_NAME)
    except Exception:
        return None

def _hash_senha(senha: str, salt: str = "") -> str:
    """Hash simples com salt."""
    if not salt:
        salt = secrets.token_hex(8)
    h = hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()
    return f"{salt}${h}"

def _verify_senha(senha: str, hash_stored: str) -> bool:
    """Verifica senha contra hash."""
    salt = hash_stored.split("$")[0]
    return _hash_senha(senha, salt) == hash_stored

class LoginResult:
    OK = "ok"
    INVALID = "invalid"          # credenciais inválidas (esperado)
    ERROR = "error"              # falha de infra (banco, rede)

def _login(email: str, senha: str, remember: bool = False) -> str:
    """Valida credenciais. Retorna LoginResult.{OK, INVALID, ERROR}.

    Distingue credencial inválida (esperado) de erro de infra
    para que o usuário não veja 'senha inválida' quando o banco caiu.
    """
    try:
        result = _fetch(
            "SELECT id, email, senha_hash FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1",
            (email.strip(),), _v=0,
        )
    except Exception:
        return LoginResult.ERROR

    if not result:
        return LoginResult.INVALID
    usuario = result[0]
    if not _verify_senha(senha, usuario['senha_hash']):
        return LoginResult.INVALID

    st.session_state['user_id'] = usuario['id']
    st.session_state['user_email'] = usuario['email']

    if remember:
        try:
            token = secrets.token_urlsafe(32)
            expira = datetime.now() + timedelta(days=30)
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
    """Restaura sessão se houver token válido em cookie OU session_state.

    Fluxo:
    1. Se user_id já está na sessão → logado, retorna True imediatamente
    2. Tenta ler cookie do browser (persistente entre visitas)
    3. Fallback para remember_token em session_state
    4. Valida token no DB
    5. Permite até 3 tentativas sem token antes de desistir (cookie é async)
    """
    # Já logado nesta sessão — não precisa checar nada
    if st.session_state.get('user_id'):
        return True

    # Já confirmamos que não há token válido nesta sessão
    if st.session_state.get('_token_checked'):
        return False

    # 1) Cookie persistente do browser (síncrono via st.context — sem reruns)
    token = _read_cookie() or st.session_state.get('remember_token')
    if not token:
        st.session_state['_token_checked'] = True
        return False

    # Temos um token — valida no banco
    try:
        result = _fetch(
            "SELECT id, email, remember_token_expires FROM usuarios WHERE remember_token=%s",
            (token,), _v=0)
        if not result:
            st.session_state['_token_checked'] = True
            return False
        usuario = result[0]
        expiry = usuario['remember_token_expires']
        if expiry and expiry < datetime.now():
            st.session_state['_token_checked'] = True
            return False
        # Login restaurado com sucesso
        st.session_state['user_id']       = usuario['id']
        st.session_state['user_email']    = usuario['email']
        st.session_state['remember_token'] = token
        st.session_state['_token_checked'] = True
        return True
    except Exception:
        st.session_state['_token_checked'] = True
        return False

def _logout() -> None:
    """Limpa sessão, token no DB e cookie no browser."""
    user_id = st.session_state.get('user_id')
    if user_id:
        try:
            _run("UPDATE usuarios SET remember_token=NULL, remember_token_expires=NULL WHERE id=%s", (user_id,))
        except Exception:
            pass
    # Cookie é apagado no próximo run (página de login), onde o JS executa
    st.session_state['_clear_cookie'] = True
    st.session_state.pop('user_id', None)
    st.session_state.pop('user_email', None)
    st.session_state.pop('remember_token', None)
    st.session_state.pop('_token_checked', None)
    st.session_state.pop('_cookie_attempts', None)

def _init_db() -> None:
    if st.session_state.get("_db_ready"):
        return
    conn = _conn()
    cur  = conn.cursor()
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
        # Migrations para tabela existente (compatível com schemas antigos)
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
        # Migração incremental — adiciona colunas novas sem recriar a tabela
        cur.execute("""
            ALTER TABLE coffees
                ADD COLUMN IF NOT EXISTS local_compra      TEXT  DEFAULT '',
                ADD COLUMN IF NOT EXISTS valor_compra      FLOAT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS data_compra       DATE,
                ADD COLUMN IF NOT EXISTS classificacao_cafe TEXT DEFAULT '',
                ADD COLUMN IF NOT EXISTS intensidade       INTEGER DEFAULT 5;
        """)
        # Tabela de cápsulas
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

        # ── P3: Multi-tenancy — atribui cafés/extrações ao seu dono ──
        cur.execute("""
            ALTER TABLE coffees    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id);
            ALTER TABLE extracoes  ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES usuarios(id);
            CREATE INDEX IF NOT EXISTS idx_coffees_user_id   ON coffees(user_id);
            CREATE INDEX IF NOT EXISTS idx_extracoes_user_id ON extracoes(user_id);
        """)
        # Backfill seguro: só atribui registros órfãos se houver exatamente 1 usuário
        # (cenário single-user retroativo — sem ambiguidade)
        cur.execute("SELECT COUNT(*) FROM usuarios")
        if cur.fetchone()[0] == 1:
            cur.execute("SELECT id FROM usuarios LIMIT 1")
            sole_user = cur.fetchone()[0]
            cur.execute("UPDATE coffees   SET user_id=%s WHERE user_id IS NULL", (sole_user,))
            cur.execute("UPDATE extracoes SET user_id=%s WHERE user_id IS NULL", (sole_user,))

        # ── P4: rename remember_token_created → remember_token_expires (semântica correta) ──
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

        # ── P5: rename doçura_stars → docura_stars (encoding-safe) ──
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

        # ── P6: campos reais espelhando Motor Barista ──
        cur.execute("""
            ALTER TABLE extracoes
                ADD COLUMN IF NOT EXISTS temp_real    FLOAT DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS pressao_real FLOAT DEFAULT NULL;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id           SERIAL PRIMARY KEY,
                tipo         TEXT NOT NULL DEFAULT 'manual',
                criado_em    TIMESTAMP DEFAULT NOW(),
                notas        TEXT DEFAULT '',
                coffees_data JSONB DEFAULT '[]',
                extracoes_data JSONB DEFAULT '[]',
                capsulas_data  JSONB DEFAULT '[]',
                usuarios_data  JSONB DEFAULT '[]',
                app_code     TEXT DEFAULT '',
                git_hash     TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_backups_criado_em ON backups(criado_em DESC);
        """)

        conn.commit()
        st.session_state["_db_ready"] = True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

# ── Backup ─────────────────────────────────────────────────────────────
import json as _json
import os as _os

def _backup_criar(tipo: str = "manual", notas: str = "") -> bool:
    """Cria snapshot completo dos dados + código do app."""
    try:
        coffees    = _fetch("SELECT * FROM coffees", _v=_v())
        extracoes  = _fetch("SELECT * FROM extracoes", _v=_v())
        capsulas   = _fetch("SELECT * FROM capsulas", _v=_v())
        usuarios   = _fetch("SELECT id, email, nome, criado_em FROM usuarios", _v=_v())

        def _rows_to_json(rows):
            out = []
            for r in rows:
                d = dict(r)
                for k, val in d.items():
                    if hasattr(val, 'isoformat'):
                        d[k] = val.isoformat()
                    elif val is None:
                        d[k] = None
                out.append(d)
            return _json.dumps(out, ensure_ascii=False)

        app_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "streamlit_app_final.py")
        try:
            with open(app_path, "r", encoding="utf-8") as f:
                app_code = f.read()
        except Exception:
            app_code = ""

        try:
            import subprocess
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=_os.path.dirname(app_path), stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            git_hash = ""

        _run("""INSERT INTO backups
                    (tipo, notas, coffees_data, extracoes_data, capsulas_data, usuarios_data, app_code, git_hash)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s)""",
             (tipo, notas,
              _rows_to_json(coffees), _rows_to_json(extracoes),
              _rows_to_json(capsulas), _rows_to_json(usuarios),
              app_code, git_hash))
        return True
    except Exception as e:
        st.error(f"Erro ao criar backup: {e}")
        return False


def _backup_listar() -> list:
    return _fetch("""SELECT id, tipo, criado_em, notas, git_hash,
                            jsonb_array_length(coffees_data)   AS n_cafes,
                            jsonb_array_length(extracoes_data) AS n_extracoes,
                            jsonb_array_length(capsulas_data)  AS n_capsulas
                     FROM backups ORDER BY criado_em DESC LIMIT 30""", _v=_v())


def _backup_restaurar_dados(backup_id: int) -> bool:
    """Restaura apenas os DADOS (tabelas coffees, extracoes, capsulas) do backup.
    Cria um backup 'pre-restore' automaticamente antes de alterar qualquer coisa."""
    try:
        rows = _fetch("SELECT coffees_data, extracoes_data, capsulas_data FROM backups WHERE id=%s",
                      (backup_id,), _v=_v())
        if not rows:
            st.error("Backup não encontrado.")
            return False

        _backup_criar("pre-restore", f"Auto-backup antes de restaurar backup #{backup_id}")

        b = rows[0]
        coffees   = _json.loads(b["coffees_data"])
        extracoes = _json.loads(b["extracoes_data"])
        capsulas  = _json.loads(b["capsulas_data"])

        conn = _conn()
        cur  = conn.cursor()
        try:
            cur.execute("DELETE FROM extracoes")
            cur.execute("DELETE FROM capsulas")
            cur.execute("DELETE FROM coffees")

            for c in coffees:
                cols = [k for k in c if c[k] is not None or k in ("id",)]
                placeholders = ", ".join(["%s"] * len(cols))
                col_str = ", ".join(cols)
                vals = [c[k] for k in cols]
                cur.execute(f"INSERT INTO coffees ({col_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", vals)

            for e in extracoes:
                cols = [k for k in e]
                placeholders = ", ".join(["%s"] * len(cols))
                col_str = ", ".join(cols)
                vals = [e[k] for k in cols]
                cur.execute(f"INSERT INTO extracoes ({col_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", vals)

            for cap in capsulas:
                cols = [k for k in cap]
                placeholders = ", ".join(["%s"] * len(cols))
                col_str = ", ".join(cols)
                vals = [cap[k] for k in cols]
                cur.execute(f"INSERT INTO capsulas ({col_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", vals)

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


def _auto_backup_check(user_id: int) -> None:
    """Cria backup semanal automático se o último foi há mais de 7 dias."""
    if st.session_state.get("_auto_backup_done"):
        return
    st.session_state["_auto_backup_done"] = True
    try:
        rows = _fetch("SELECT criado_em FROM backups WHERE tipo='semanal' ORDER BY criado_em DESC LIMIT 1", _v=_v())
        import datetime as _dt
        now = _dt.datetime.utcnow()
        if not rows or (now - rows[0]["criado_em"]).days >= 7:
            _backup_criar("semanal", "Backup automático semanal")
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
    return f'<div class="info-row"><span class="info-key">{k}</span><span class="info-val">{v}</span></div>'

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
    """Lê ANTHROPIC_API_KEY de env (Render) ou secrets (Streamlit Cloud)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("ANTHROPIC_API_KEY", "") or ""
        except Exception:
            key = ""
    return key

def _comentario_motor_barista(coffee_info: dict, params: dict) -> str:
    """Gera comentário curto sobre o que esperar deste café com estes parâmetros."""
    api_key = _get_api_key()
    if not api_key:
        return ""
    try:
        client = anthropic.Anthropic(api_key=api_key)
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
        resp = client.messages.create(
            model="claude-haiku-4-5", max_tokens=180,
            messages=[{"role": "user", "content": prompt}])
        return resp.content[0].text.strip()
    except Exception:
        return ""

def _diagnostico_barista_ia(coffee_info: dict, params: dict,
                             real: dict, m_real: dict) -> str:
    """Análise minuciosa como barista sênior — variáveis, resultados e dicas."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada no Render.")
    client = anthropic.Anthropic(api_key=api_key)
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
1. Como as características deste café (torra, origem, notas) afetam o perfil esperado e como os parâmetros planejados foram adequados para ele
2. O que os desvios entre planejado vs real revelam sobre a moagem e a máquina
3. O que o EY e o fluxo indicam sobre sub/super-extração ou equilíbrio
4. Dicas práticas e específicas para a PRÓXIMA extração (moagem, temperatura, tempo, pressão, dose)

Seja técnico, direto e acessível. Use linguagem de barista treinando alguém.
Responda em português brasileiro. Entre 250 e 380 palavras."""

    resp = client.messages.create(
        model="claude-opus-4-5", max_tokens=700,
        messages=[{"role": "user", "content": prompt}])
    return resp.content[0].text.strip()

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

def _wordmark(size: str = "hero", with_tag: bool = True) -> None:
    """Atalho que renderiza o wordmark direto via st.markdown."""
    st.markdown(_wordmark_html(size, with_tag), unsafe_allow_html=True)

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

def _pill_when(d) -> str:
    """Pill HTML de data relativa para usar em headers."""
    text = _relative_date(d)
    cls = "mc-when today" if text == "Hoje" else "mc-when"
    return f'<span class="{cls}">📅 {text}</span>'

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

# ── Vision · leitura de embalagem ──────────────────────────────────────
def _analisar_embalagem(b64_img: str) -> dict:
    # Prioriza env var (Render/Railway/Heroku) — st.secrets lança FileNotFoundError
    # quando não há secrets.toml (plataformas sem Streamlit Cloud config).
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or ""
        except Exception:
            api_key = ""
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada. Defina a variável de ambiente no painel do Render.")

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_img}},
                {"type": "text",
                 "text": (
                    "Analise esta embalagem de café. "
                    "Retorne APENAS um JSON com os campos:\n"
                    "  nome: string (marca + nome do café),\n"
                    "  fazenda: string ou null,\n"
                    "  regiao: string ou null (país/estado de origem),\n"
                    "  torra: \"Clara\" | \"Média\" | \"Escura\",\n"
                    "  tipo: \"Grãos\" | \"Moído\",\n"
                    "  notas: string (notas de sabor se visíveis, senão null),\n"
                    "  tamanho_pacote: 250 | 500 | 1000 (em g, ou null).\n"
                    "Se um campo não for identificável, use null. "
                    "Responda SOMENTE o JSON, sem markdown."
                 )}
            ]
        }]
    )

    raw = resp.content[0].text.strip()
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)

_APP_VERSION = "3.3.3"

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

    # Dialog "Sobre" — aberto pelo clique na marca (?about=1), em qualquer estado
    if "about" in st.query_params:
        del st.query_params["about"]
        _about_dialog()

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
                    '<p style="text-align:center;font-family:Georgia,\'Times New Roman\','
                    'serif;font-style:italic;font-size:19px;line-height:1.6;'
                    'color:var(--mc-text-2);max-width:420px;margin:0.5rem auto 0">'
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
                            st.toast("Login realizado", icon="✅")
                            st.rerun()
                        elif outcome == LoginResult.INVALID:
                            st.error("E-mail ou senha incorretos. Verifique e tente de novo.")
                        else:
                            st.error("Erro ao acessar o banco de dados. Tente novamente em instantes.")

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

    col_brand, col_user, col_logout = st.columns([0.65, 0.25, 0.10], gap="small")
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
    with col_logout:
        if st.button("Sair", use_container_width=True, key="btn_logout",
                     help="Sair da conta"):
            _logout()
            st.rerun()

    # Widget de consumo (hoje · semana · média · total)
    _show_daily_consumption()

    _auto_backup_check(st.session_state['user_id'])

    # 🚀 BARISTA EXPERT FULLY INTEGRATED - REBUILD v3
    st.markdown("---")

    tab_barista, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "  ✨ Barista Expert  ", "  Novo Café  ", "  Nova Extração  ", "  Meus Cafés  ",
        "  Histórico  ", "  📖 Receitas  ", "  🫘 Cápsulas  ", "  🛡️ Backup  "])

    user_id = st.session_state['user_id']

    # ── Tab Barista Expert ─────────────────────────────────────────────
    with tab_barista:
        st.success("🚀 BARISTA EXPERT - NOVO SISTEMA AO VIVO!")
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
                    <p style="margin:0 0 8px;font-weight:700;color:var(--mc-orange);font-size:14px">{bc['nome']}</p>
                    <p style="margin:0;color:var(--mc-text-2);font-size:12px">
                    <strong>Torra:</strong> {bc['torra']} | <strong>Intensidade:</strong> {bc['intensidade']}/12
                    </p>
                    <p style="margin:6px 0 0;color:var(--mc-text-3);font-size:12px">{bc['regiao'] or '—'}</p>
                    <p style="margin:8px 0 0;color:var(--mc-text);font-size:11px">{bc['notas'] or '(sem notas)'}</p>
                    <p style="margin:8px 0 0;font-size:18px;color:var(--mc-orange)">{'⭐' * int(bc['classificacao'])}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:20px;color:var(--mc-text-3)">'
                    '<p>Cadastre e avalie seus primeiros cafés</p>'
                    '</div>', unsafe_allow_html=True)

        # Promoções do dia / Destaques
        with col_promo:
            st.markdown('<p class="info-key" style="margin-bottom:0.5rem">Destaque do Dia</p>', unsafe_allow_html=True)
            st.markdown("""
            <div style="background:linear-gradient(135deg, #E8722E 0%, #F08842 100%);
            border-radius:12px;padding:16px;margin:0;color:#0A0A0A">
                <p style="margin:0 0 8px;font-weight:700;font-size:14px">🎯 Dica Barista</p>
                <p style="margin:0;font-size:12px;line-height:1.6">
                Quando notar notas de acidez agressiva, experimente aumentar a temperatura
                da água em 2°C ou afinar um pouco mais a moagem.
                </p>
                <p style="margin:12px 0 0;font-size:11px;opacity:0.9">💡 Use o chat abaixo para perguntas específicas</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # ── Chat do Barista Expert
        st.markdown('<p class="section-label">Chat com Barista Expert</p>', unsafe_allow_html=True)

        # Inicializar session state para o chat
        if "barista_messages" not in st.session_state:
            st.session_state.barista_messages = []

        # Container para mensagens
        chat_container = st.container()

        # Input do usuário
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
            # Adicionar pergunta do usuário
            st.session_state.barista_messages.append({"role": "user", "content": pergunta})

            # Obter resposta do Barista Expert
            with st.spinner("🤔 Barista Expert pensando..."):
                resposta = ask_barista_expert(pergunta)
                st.session_state.barista_messages.append({"role": "assistant", "content": resposta})

            st.rerun()

        # Renderizar histórico de mensagens
        with chat_container:
            if st.session_state.barista_messages:
                for msg in st.session_state.barista_messages:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-end;margin:8px 0">
                            <div style="background:var(--mc-orange);color:#0A0A0A;
                            border-radius:12px;border-bottom-right-radius:0;
                            padding:12px 16px;max-width:70%;font-size:14px;line-height:1.5">
                            {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-start;margin:8px 0">
                            <div style="background:var(--mc-surface);border:1px solid var(--mc-border);
                            border-radius:12px;border-bottom-left-radius:0;
                            padding:12px 16px;max-width:70%;font-size:14px;line-height:1.6;color:var(--mc-text)">
                            {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:40px 20px;color:var(--mc-text-3)">'
                    '<p style="font-size:14px">Faça uma pergunta sobre café, equipamentos, técnicas ou defeitos de extração...</p>'
                    '</div>', unsafe_allow_html=True)

        # Botão para limpar chat
        if st.session_state.barista_messages:
            if st.button("🔄 Novo Chat", use_container_width=True):
                st.session_state.barista_messages = []
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
            class_c = st.slider("Classificação", 1, 5, 3, key="class_cafe")
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
        st.markdown('<p class="section-label">Registrar Extração</p>', unsafe_allow_html=True)

        user_id = st.session_state.get('user_id')
        cafes = _fetch("SELECT id, nome, torra FROM coffees WHERE user_id=%s ORDER BY nome",
                       (user_id,), _v=_v())
        if not cafes:
            _empty("☕", "Cadastre seu primeiro café",
                   "Para registrar uma extração você precisa ter pelo menos "
                   "um café cadastrado na sua biblioteca.",
                   hint="Vá em 'Novo Café' acima")
        else:
            cafe_map = {f"{c['nome']}  ·  {c['torra']}": c['id'] for c in cafes}
            sel    = st.selectbox("Café", list(cafe_map.keys()))
            cid    = cafe_map[sel]
            metodo = st.selectbox("Método de Preparo", METODOS)

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
                    f'text-transform:uppercase;letter-spacing:.1em">🔁 Última receita ({metodo})</span><br>'
                    f"<b>{float(lx['gramas'] or 0):.1f}g → {float(lx['agua_alvo'] or 0):.0f}g</b> · "
                    f"{int(lx['tempo_extracao'] or 0)}s · "
                    f"{int(lx['clicks_moedor'] or 0)} clicks ({lx['moedor'] or '—'}) · "
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

            # Grinder persistence: invalida cache junto com _v() para refletir updates
            last_grinder, last_clicks = "", 0
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
            with sc2:
                clicks = st.number_input("Clicks", 0, 200, last_clicks, 1,
                                         help="Pré-preenchido com o último valor",
                                         key="inp_clicks")
            st.caption("🕐 Data e hora são registradas automaticamente no momento do registro.")
            st.markdown('</div>', unsafe_allow_html=True)

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

                if ey_real > 0:
                    diagnosticos.append(
                        f"🧪 <b>Extraction Yield: {ey_real:.2f}%</b> — {m_real.get('status','')}.")

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
            for c in cafes:
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
                                f'font-style:italic;line-height:1.5;">{c["notas"]}</div>' if c["notas"] else "")
                        st.markdown(f'<div>{tags}</div><div style="margin-top:12px">{info}</div>{note}',
                                    unsafe_allow_html=True)
                    with cc:
                        st.metric("Extrações", int(c["total_ext"] or 0))
                        if c.get("valor_compra"):
                            lbl = (f"Comprado em {c['data_compra'].strftime('%d/%m/%Y')}"
                                   if c.get("data_compra") else "Valor Pago")
                            st.metric(lbl, f"R$ {c['valor_compra']:.2f}")
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
                                        _run(
                                            "UPDATE extracoes SET foto_caneca=%s WHERE id=%s AND user_id=%s",
                                            (_b64(nova_foto), e["id"], user_id)
                                        )
                                        st.session_state[_fkey] = True
                                        st.toast("Foto adicionada", icon="📸")
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
                                    ed_gramas = st.number_input("Dose (g)", value=e['gramas'], key=f"tab3_ed_g_{e['id']}")
                                    ed_agua = st.number_input("Água (g)", value=e['agua_alvo'], key=f"tab3_ed_a_{e['id']}")
                                    ed_tempo = st.number_input("Tempo (s)", value=e['tempo_extracao'], key=f"tab3_ed_t_{e['id']}")
                                with ed_col2:
                                    ed_class = st.slider("Classificação", 1, 5,
                                                         e['classificacao'] or 3,
                                                         key=f"tab3_ed_c_{e['id']}")
                                    ed_notas = st.text_area("Comentários", value=e['notas'] or "", key=f"tab3_ed_n_{e['id']}", height=80)

                                if st.button("💾 Salvar Edição", key=f"tab3_save_e_{e['id']}", use_container_width=True):
                                    _run(
                                        "UPDATE extracoes SET gramas=%s, agua_alvo=%s, tempo_extracao=%s, classificacao=%s, notas=%s WHERE id=%s AND user_id=%s",
                                        (ed_gramas, ed_agua, ed_tempo, ed_class, ed_notas, e['id'], user_id)
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
            # Mostra contagem como subheader
            st.markdown(
                f'<p style="color:#8A8278;font-size:12px;margin:-0.5rem 0 1rem;'
                f'font-weight:600">{len(rows)} extrações registradas — exibindo '
                f'as 200 mais recentes</p>',
                unsafe_allow_html=True)

            for r in rows:
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
                                f'font-style:italic;line-height:1.5;">{r["notas"]}</div>' if r["notas"] else "")
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
                    col_edit, col_del = st.columns([1, 1])
                    with col_edit:
                        if st.button("✏️ Editar", key=f"tab4_edit_e_{r['id']}"):
                            st.session_state[f"editing_e_{r['id']}"] = True
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
                        st.metric("Estoque", f"{cap['quantidade']} un.")
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
                    ok = _backup_criar("manual", notas_backup)
                if ok:
                    st.success("Backup criado com sucesso!", icon="✅")
                    st.rerun()

        st.markdown("---")

        # ── Lista de backups ─────────────────────────────────────────
        backups = _backup_listar()
        if not backups:
            st.info("Nenhum backup encontrado. Crie o primeiro backup acima.")
        else:
            st.markdown(f"**{len(backups)} backup(s) disponíveis** (máx. 30 exibidos)")
            import datetime as _dt2
            for bk in backups:
                criado = bk["criado_em"]
                if isinstance(criado, str):
                    criado = _dt2.datetime.fromisoformat(criado)
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
                                    ok = _backup_restaurar_dados(bk["id"])
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
