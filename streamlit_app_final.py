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
import extra_streamlit_components as stx

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee Production",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_mobile_css() -> None:
    css_path = os.path.join(_DIR, ".streamlit", "static", "mateu_coffee_mobile.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def _load_logo(max_width: int = 300) -> bool:
    """Carrega logo com fallback para emoji."""
    try:
        logo_path = os.path.join(_DIR, "assets", "mateu_coffee_logo.png")
        if os.path.exists(logo_path):
            img = st.image(logo_path, use_container_width=True)
            return True
        else:
            st.markdown("<h2 style='text-align:center'>☕ MATEU COFFEE</h2>", unsafe_allow_html=True)
            return False
    except Exception as e:
        st.markdown("<h2 style='text-align:center'>☕ MATEU COFFEE</h2>", unsafe_allow_html=True)
        return False

def _show_daily_consumption() -> None:
    """Exibe widget com o consumo total de café do dia (apenas do usuário logado)."""
    hoje = date.today()
    agora = datetime.now().strftime("%H:%M")
    user_id = st.session_state.get('user_id')

    result = _fetch("""
        SELECT COALESCE(SUM(gramas), 0) as total
        FROM extracoes
        WHERE data = %s AND user_id = %s
    """, (hoje, user_id), _v=_v())

    consumo_total = result[0]["total"] if result else 0

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#141414 0%,#1C1C1C 100%);'
        f'border:1px solid #2A2A2A;border-left:4px solid #E8722E;border-radius:10px;'
        f'padding:16px 20px;margin:0 0 1.75rem 0">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">'
        f'<div style="font-size:11px;color:#8A8278;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">'
        f'📅 {hoje.strftime("%d/%m/%Y")} · ⏰ {agora}</div>'
        f'<div style="font-size:13px;font-weight:600;color:#B8B0A8">'
        f'Consumo do dia: <span style="color:#E8722E;font-weight:800;font-size:18px">'
        f'{consumo_total:.1f}g</span></div>'
        f'</div></div>',
        unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _logo_b64() -> Optional[str]:
    """Lê o logo uma vez e cacheia indefinidamente (arquivo estático)."""
    logo_path = os.path.join(_DIR, "assets", "mateu_coffee_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def _show_logo() -> None:
    b64 = _logo_b64()
    if b64:
        st.markdown(
            f'<div class="mc-hero-full">'
            f'<img src="data:image/png;base64,{b64}" alt="Mateu Coffee">'
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

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
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

    /* ─── Mobile ──────────────────────────────────────────────── */
    @media (max-width: 640px) {
        .block-container { padding: 1rem 1rem 2rem !important; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        .stTabs [data-baseweb="tab"] { padding: 8px 14px; font-size: 12px; }
        .stButton > button { width: 100%; }
    }
</style>
""", unsafe_allow_html=True)

# ── Database layer ─────────────────────────────────────────────────────
@st.cache_resource
def _get_conn() -> "psycopg2.extensions.connection":
    s = st.secrets["connections"]["postgresql"]
    return psycopg2.connect(
        host=s["host"], port=int(s["port"]), dbname=s["database"],
        user=s["username"], password=s["password"],
        sslmode="require", connect_timeout=10,
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

def _cm() -> "stx.CookieManager":
    """Singleton cacheado entre reruns. Sem isso a 1ª chamada por sessão
    sempre retorna None — porque a leitura do cookie é assíncrona via JS."""
    if "_cookie_mgr" not in st.session_state:
        st.session_state["_cookie_mgr"] = stx.CookieManager(key="mc_cookies")
    return st.session_state["_cookie_mgr"]

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
            "SELECT id, email, senha_hash FROM usuarios WHERE email=%s LIMIT 1",
            (email,), _v=0,
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
            # Cookie persistente no browser (30 dias) — sobrevive a fechar a aba
            try:
                _cm().set(_COOKIE_NAME, token, expires_at=expira, key="set_remember")
            except Exception:
                pass
        except Exception:
            # login funcionou, mas remember-me falhou — não bloqueia a sessão
            pass

    return LoginResult.OK

def _check_remember_token() -> bool:
    """Restaura sessão se houver token válido em cookie OU session_state.

    Fluxo:
    1. Tenta ler cookie do browser (persistente, sobrevive a fechar a aba)
    2. Fallback para st.session_state (caso de SSR/preview rápido)
    3. Valida token no DB e respeita data de expiração
    """
    if st.session_state.get('_token_checked'):
        return False

    # 1) Cookie persistente
    token = None
    try:
        token = _cm().get(_COOKIE_NAME)
    except Exception:
        token = None
    # 2) Fallback session_state
    if not token:
        token = st.session_state.get('remember_token')

    if not token:
        st.session_state['_token_checked'] = True
        return False

    try:
        result = _fetch(
            "SELECT id, email, remember_token_expires FROM usuarios WHERE remember_token=%s",
            (token,), _v=0
        )
        if not result:
            st.session_state['_token_checked'] = True
            return False
        usuario = result[0]
        expiry = usuario['remember_token_expires']
        if expiry and expiry < datetime.now():
            st.session_state['_token_checked'] = True
            return False
        st.session_state['user_id'] = usuario['id']
        st.session_state['user_email'] = usuario['email']
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
    # Apaga cookie persistente
    try:
        _cm().delete(_COOKIE_NAME, key="del_remember")
    except Exception:
        pass
    st.session_state.pop('user_id', None)
    st.session_state.pop('user_email', None)
    st.session_state.pop('remember_token', None)
    st.session_state.pop('_token_checked', None)

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
                ADD COLUMN IF NOT EXISTS classificacao_cafe TEXT DEFAULT '';
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

        conn.commit()
        st.session_state["_db_ready"] = True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

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

# Classificação oficial do café (substitui o campo Fazenda na UI)
CLASSIFICACOES_CAFE = [
    "Especial (>80 pts)",
    "Gourmet",
    "Superior",
    "Tradicional",
    "Extraforte",
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
            "status": "Aguardando TDS",
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
      <input type="range" id="iy" min="20" max="60" step="1" value="36">
      <div class="ht">Peso final do líquido extraído. Define a taxa de concentração (Ratio).</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Tempo de Extração</label><span id="vt">28 s</span></div>
      <input type="range" id="it" min="15" max="45" step="1" value="28">
      <div class="ht">Tempos baixos subextraem; altos superextraem.</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Temperatura da Água</label><span id="vp">92.0 °C</span></div>
      <input type="range" id="ip" min="85" max="98" step="0.5" value="92">
      <div class="ht">Temperaturas elevadas dissolvem mais amargor; baixas geram acidez crua.</div>
    </div>

    <div class="cg">
      <div class="cl"><label>Pressão da Bomba</label><span id="vb">9.0 bar</span></div>
      <input type="range" id="ib" min="6" max="12" step="0.5" value="9">
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
    api_key = (st.secrets.get("ANTHROPIC_API_KEY")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada.")

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

# ── Main ───────────────────────────────────────────────────────────────
def main():
    _init_db()

    # Instancia cookie manager ANTES de checar sessão. A leitura é
    # assíncrona via JS — em casos extremos pode exigir 1 rerun, mas
    # o singleton em session_state cobre o caso normal.
    _cm()

    # ── Autenticação ────────────────────────────────────────────────────
    if 'user_id' not in st.session_state:
        # Tenta restaurar com token
        if not _check_remember_token():
            # ── Página de Login ────────────────────────────────────
            # Exibe logo centralizada
            col_logo_center = st.columns([0.15, 0.7, 0.15])[1]
            with col_logo_center:
                _load_logo()

            st.markdown("---")

            tab_login, tab_cadastro = st.tabs(["Login", "Cadastro"])

            with tab_login:
                st.markdown("### 🔐 Entrar na Conta")
                email = st.text_input("Email", key="login_email", placeholder="seu@email.com")
                senha = st.text_input("Senha", type="password", key="login_senha")
                remember_me = st.checkbox("✓ Manter-me conectado", value=False, key="login_remember")

                if st.button("🔓 Entrar", use_container_width=True):
                    outcome = _login(email, senha, remember=remember_me)
                    if outcome == LoginResult.OK:
                        st.success("✅ Login realizado!")
                        st.rerun()
                    elif outcome == LoginResult.INVALID:
                        st.error("❌ E-mail ou senha incorretos.")
                    else:
                        st.error("⚠️ Erro ao acessar o banco de dados. Tente novamente em instantes.")

            with tab_cadastro:
                st.markdown("### Criar Conta")
                new_email = st.text_input("Email", key="cadastro_email")
                new_senha = st.text_input("Senha", type="password", key="cadastro_senha")
                new_senha_conf = st.text_input("Confirmar Senha", type="password", key="cadastro_senha_conf")

                if st.button("✅ Cadastrar", use_container_width=True):
                    if not new_email or not new_senha:
                        st.error("Preencha todos os campos.")
                    elif new_senha != new_senha_conf:
                        st.error("Senhas não conferem.")
                    elif len(new_senha) < 6:
                        st.error("Senha deve ter pelo menos 6 caracteres.")
                    else:
                        try:
                            hash_pwd = _hash_senha(new_senha)
                            _run("INSERT INTO usuarios (email, senha_hash) VALUES (%s, %s)",
                                 (new_email, hash_pwd))
                            st.success("Cadastro realizado! Faça login.")
                            st.rerun()
                        except Exception:
                            st.error("Email já cadastrado.")
        return

    # ── App Logado ──────────────────────────────────────────────────────
    _show_logo()
    _show_daily_consumption()

    # Barra de usuário logado
    col_logo, col_user, col_logout = st.columns([0.72, 0.18, 0.10])
    with col_user:
        user_email_display = st.session_state.get('user_email', '')
        st.markdown(
            f'<div style="text-align:right;font-size:12px;color:#B8B0A8;'
            f'padding-top:10px;font-weight:600;letter-spacing:0.02em">'
            f'👤 {user_email_display}</div>',
            unsafe_allow_html=True)
    with col_logout:
        if st.button("🚪 Sair", use_container_width=True, key="btn_logout"):
            _logout()
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs([
        "  Novo Café  ", "  Nova Extração  ", "  Meus Cafés  ", "  Histórico  "])

    user_id = st.session_state['user_id']

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
            data_cad = st.date_input("Data de Cadastro", value=date.today(), format="DD/MM/YYYY")
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
            class_c = st.select_slider("Classificação", options=[1,2,3,4,5],
                                       format_func=_stars, value=3, key="class_cafe")
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
            local_compra = st.text_input("Local de Compra",
                                         placeholder="Ex: Torrefação Orfeu, iFood, Mercado...")
        with cp2:
            valor_compra = st.number_input("Valor Pago (R$)", min_value=0.0,
                                           value=0.0, step=0.50, format="%.2f")
        with cp3:
            data_compra = st.date_input("Data da Compra", value=date.today(),
                                        format="DD/MM/YYYY", key="data_compra")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        if st.button("Salvar Café", type="primary", use_container_width=True):
            if not nome.strip():
                st.error("Nome do café é obrigatório.")
            else:
                _run("""INSERT INTO coffees
                    (data_cadastro,nome,tipo,torra,notas,classificacao,
                     classificacao_cafe,regiao,data_torra,tamanho_pacote,
                     foto_embalagem,local_compra,valor_compra,data_compra,user_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (data_cad, nome.strip(), tipo, torra, notas, class_c,
                     classificacao_cafe, regiao, data_tort, tamanho, foto_emb_b64,
                     local_compra.strip() or None,
                     valor_compra if valor_compra > 0 else None,
                     data_compra, user_id))
                st.success(f"**{nome}** cadastrado com sucesso.")
                st.balloons()

    # ── Tab 2 · Nova extração ──────────────────────────────────────────
    with tab2:
        st.markdown('<p class="section-label">Registrar Extração</p>', unsafe_allow_html=True)

        user_id = st.session_state.get('user_id')
        cafes = _fetch("SELECT id, nome, torra FROM coffees WHERE user_id=%s ORDER BY nome",
                       (user_id,), _v=_v())
        if not cafes:
            st.info("Cadastre um café primeiro na aba Novo Café.")
        else:
            cafe_map = {f"{c['nome']}  ·  {c['torra']}": c['id'] for c in cafes}
            sel    = st.selectbox("Café", list(cafe_map.keys()))
            cid    = cafe_map[sel]
            metodo = st.selectbox("Método de Preparo", METODOS)

            # ── Configuração de Xícaras ────────────────────────────────────
            xicaras = st.radio("Número de Xícaras", [1, 2], horizontal=True, key="config_xicaras")
            gramas_default = 18.0 if xicaras == 1 else 36.0
            agua_default   = 300.0 if xicaras == 1 else 600.0

            # ═══════════════════════════════════════════════════════════════
            # 1) MOTOR BARISTA — agora no TOPO da aba (acima de tudo)
            # ═══════════════════════════════════════════════════════════════
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">🧪 Motor Barista — Simulador de Extração</p>',
                        unsafe_allow_html=True)

            cafe_info = _fetch("SELECT tipo, torra FROM coffees WHERE id=%s AND user_id=%s LIMIT 1",
                              (cid, user_id), _v=_v())
            if cafe_info:
                params = _motor_barista_params(cafe_info[0]["torra"], cafe_info[0]["tipo"])
            else:
                params = _motor_barista_params("Média", "Grãos")

            motor_html = (_MOTOR_BARISTA_HTML
                .replace('value="18"', f'value="{params["dose"]}"')
                .replace('value="36"', f'value="{params["yield"]}"')
                .replace('value="28"', f'value="{params["time"]}"')
                .replace('value="92"', f'value="{params["temp"]}"')
                .replace('value="9"',  f'value="{params["pressure"]}"'))
            components.html(motor_html, height=660, scrolling=False)

            # ═══════════════════════════════════════════════════════════════
            # 2) PARÂMETROS DA EXTRAÇÃO
            # ═══════════════════════════════════════════════════════════════
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">⚙️ Parâmetros</p>', unsafe_allow_html=True)

            # Carrega último moedor do usuário (sempre pré-preenchido, editável)
            last_grinder = ""
            last_clicks = 0
            if user_id:
                ginfo = _fetch("SELECT last_grinder, last_clicks FROM usuarios WHERE id=%s",
                              (user_id,), _v=0)
                if ginfo and ginfo[0]['last_grinder']:
                    last_grinder = ginfo[0]['last_grinder']
                    last_clicks  = ginfo[0]['last_clicks'] or 0

            c1, c2 = st.columns(2, gap="large")
            with c1:
                gramas = st.number_input("Café Moído (g)",       5.0,  80.0,  gramas_default, 0.1,
                                         help="Peso do pó medido na balança")
                agua   = st.number_input("Água Alvo (g)",        50.0, 2000.0, agua_default, 5.0)
                tds    = st.number_input("TDS Medido (%)",        0.0,  5.0,   0.0,  0.01,
                                         help="Deixe 0 se não usar refratômetro")
                tempo  = st.number_input("Tempo de Extração (s)", 1,    600,   150,  1)
            with c2:
                # Moedor: sempre pré-preenchido com o último, livre para editar
                moedor = st.text_input("Moedor", value=last_grinder,
                                       placeholder="Ex: Comandante C40",
                                       help="Pré-preenchido com o último moedor usado",
                                       key="inp_moedor")
                clicks = st.number_input("Clicks do Moedor", 0, 200, last_clicks, 1,
                                         help="Pré-preenchido com o último valor")
                # Data e Hora lado a lado, em colunas internas
                cdh1, cdh2 = st.columns(2)
                with cdh1:
                    data_ext = st.date_input("Data", value=date.today(),
                                             key="data_ext", format="DD/MM/YYYY")
                with cdh2:
                    hora_ext = st.time_input("Hora", value=datetime.now().time(),
                                             key="hora_ext")

            # 3) NOTAS — full-width (de uma ponta à outra)
            notas_e = st.text_area("Notas da Extração",
                                   placeholder="Impressões sobre a extração...",
                                   height=90, key="notas_ext")

            m  = CoffeeEngine.calc(gramas, agua, tds if tds > 0 else None, tempo)
            ey = m.get("ey", 0.0)

            # ═══════════════════════════════════════════════════════════════
            # 4) ANÁLISE EM TEMPO REAL
            # ═══════════════════════════════════════════════════════════════
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            with st.expander("📊 ANÁLISE EM TEMPO REAL", expanded=True):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Brew Ratio",       m.get("ratio_text", "—"))
                mc2.metric("Extraction Yield", f"{ey:.2f}%" if ey > 0 else "—",
                           delta=m.get("status") if ey > 0 else None,
                           delta_color=m.get("delta_color", "off"))
                mc3.metric("Fluxo Médio",      f"{m.get('fluxo',0):.2f} g/s")
                mc4.metric("Status",           m.get("status", "—"))

                col_r, col_p = st.columns([1.6, 1], gap="large")
                with col_r:
                    st.plotly_chart(_radar(CoffeeEngine.sensory(ey)),
                                    use_container_width=True, config={'displayModeBar': False})
                with col_p:
                    foto_can = st.file_uploader("Foto da Caneca",
                                                type=["jpg","jpeg","png"],
                                                key="foto_can")
                    if foto_can:
                        _img(_b64(foto_can), w=210)

            # ═══════════════════════════════════════════════════════════════
            # 5) CLASSIFICAÇÃO DA EXTRAÇÃO (estrelas)
            # ═══════════════════════════════════════════════════════════════
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">⭐ Classificação da Extração</p>',
                        unsafe_allow_html=True)

            STAR_OPTS = [1, 2, 3, 4, 5]
            col_s1, col_s2, col_s3, col_s4 = st.columns(4, gap="large")
            with col_s1:
                crema_stars = st.select_slider("Crema", options=STAR_OPTS,
                                               format_func=_stars, value=3, key="crema_stars")
            with col_s2:
                corpo_stars = st.select_slider("Corpo", options=STAR_OPTS,
                                               format_func=_stars, value=3, key="corpo_stars")
            with col_s3:
                equilibrio_stars = st.select_slider("Equilíbrio", options=STAR_OPTS,
                                                    format_func=_stars, value=3, key="equilibrio_stars")
            with col_s4:
                acidez_stars = st.select_slider("Acidez", options=STAR_OPTS,
                                                format_func=_stars, value=3, key="acidez_stars")

            col_s5, col_s6, col_s7, col_s8 = st.columns(4, gap="large")
            with col_s5:
                amargor_stars = st.select_slider("Amargor", options=STAR_OPTS,
                                                 format_func=_stars, value=3, key="amargor_stars")
            with col_s6:
                presenca_boca_stars = st.select_slider("Presença na Boca", options=STAR_OPTS,
                                                       format_func=_stars, value=3, key="presenca_stars")
            with col_s7:
                docura_stars = st.select_slider("Doçura", options=STAR_OPTS,
                                                format_func=_stars, value=3, key="docura_stars")
            with col_s8:
                nota_final_stars = st.select_slider("Nota Final", options=STAR_OPTS,
                                                    format_func=_stars, value=3, key="nota_final_stars")

            balanco_ideal = st.text_input("Balanço Perfeito (do diagnóstico)",
                                         placeholder="Ex: Crema 4, Corpo 4, Equilíbrio 5...",
                                         key="balanco_ideal")

            # ═══════════════════════════════════════════════════════════════
            # 6) REGISTRAR
            # ═══════════════════════════════════════════════════════════════
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            if st.button("✓ REGISTRAR EXTRAÇÃO", type="primary", use_container_width=True):
                data_hora = datetime.combine(data_ext, hora_ext)
                _run("""INSERT INTO extracoes
                    (coffee_id,data,metodo,gramas,moedor,clicks_moedor,agua_alvo,tds,
                     tempo_extracao,brew_ratio,ey,fluxo,foto_caneca,classificacao,notas,
                     crema_stars,corpo_stars,equilibrio_stars,acidez_stars,amargor_stars,
                     presenca_boca_stars,docura_stars,nota_final_stars,balanco_ideal,
                     data_hora_extracao,user_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (cid, data_ext, metodo, gramas, moedor, clicks, agua, tds, tempo,
                     m.get("ratio",0), ey, m.get("fluxo",0),
                     _b64(foto_can) if foto_can else None, nota_final_stars, notas_e,
                     crema_stars, corpo_stars, equilibrio_stars, acidez_stars, amargor_stars,
                     presenca_boca_stars, docura_stars, nota_final_stars, balanco_ideal,
                     data_hora, user_id))
                if user_id and moedor:
                    _run("UPDATE usuarios SET last_grinder=%s, last_clicks=%s WHERE id=%s",
                         (moedor, clicks, user_id))
                st.success("Extração registrada!")
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
            st.info("Nenhum café cadastrado ainda.")
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
                        info = (_irow("Classificação", c.get('classificacao_cafe') or "—") +
                                _irow("Região",        c['regiao']  or "—") +
                                _irow("Cadastro",      c['data_cadastro'].strftime('%d/%m/%Y')))
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
                            # Pré-seleciona classificação se já existir
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
                            ed_tamanho = st.radio("Pacote", [250, 500, 1000],
                                                  index=[250,500,1000].index(c['tamanho_pacote']) if c['tamanho_pacote'] in [250,500,1000] else 0,
                                                  horizontal=True, format_func=lambda x: f"{x}g",
                                                  key=f"ec_tam_{c['id']}")
                            ed_data_torra = st.date_input("Data da Torra",
                                                          value=c['data_torra'],
                                                          format="DD/MM/YYYY",
                                                          key=f"ec_torra_dt_{c['id']}")
                            ed_class_estr = st.select_slider("Classificação geral",
                                                             options=[1,2,3,4,5],
                                                             format_func=_stars,
                                                             value=c['classificacao'] or 3,
                                                             key=f"ec_class_{c['id']}")
                            ed_notas = st.text_area("Notas de Sabor / Torra",
                                                    value=c['notas'] or "", height=108,
                                                    key=f"ec_notas_{c['id']}")
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
                                                         value=c.get('data_compra') or date.today(),
                                                         format="DD/MM/YYYY",
                                                         key=f"ec_dtcp_{c['id']}")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Salvar alterações", type="primary",
                                         key=f"ec_save_{c['id']}", use_container_width=True):
                                _run("""UPDATE coffees SET
                                        nome=%s, classificacao_cafe=%s, regiao=%s,
                                        tipo=%s, torra=%s, tamanho_pacote=%s,
                                        data_torra=%s, classificacao=%s, notas=%s,
                                        local_compra=%s, valor_compra=%s, data_compra=%s
                                        WHERE id=%s AND user_id=%s""",
                                     (ed_nome.strip(), ed_classif, ed_regiao,
                                      ed_tipo, ed_torra, ed_tamanho,
                                      ed_data_torra, ed_class_estr, ed_notas,
                                      ed_local.strip() or None,
                                      ed_valor if ed_valor > 0 else None,
                                      ed_dt_compra,
                                      c['id'], user_id))
                                st.session_state.pop(f"edit_c_{c['id']}", None)
                                st.success("Café atualizado!")
                                st.rerun()
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
                        st.info("Nenhuma extração registrada para este café ainda.")
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
                                nova_foto = st.file_uploader(
                                    "Adicionar foto",
                                    type=["jpg","jpeg","png"],
                                    key=f"add_foto_{e['id']}"
                                )
                                if nova_foto:
                                    _run(
                                        "UPDATE extracoes SET foto_caneca=%s WHERE id=%s AND user_id=%s",
                                        (_b64(nova_foto), e["id"], user_id)
                                    )
                                    st.success("Foto adicionada!")
                                    st.rerun()

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
                                    ed_class = st.select_slider("Classificação", options=[1,2,3,4,5],
                                                               value=e['classificacao'] or 3,
                                                               format_func=_stars, key=f"tab3_ed_c_{e['id']}")
                                    ed_notas = st.text_area("Comentários", value=e['notas'] or "", key=f"tab3_ed_n_{e['id']}", height=80)

                                if st.button("💾 Salvar Edição", key=f"tab3_save_e_{e['id']}", use_container_width=True):
                                    _run(
                                        "UPDATE extracoes SET gramas=%s, agua_alvo=%s, tempo_extracao=%s, classificacao=%s, notas=%s WHERE id=%s AND user_id=%s",
                                        (ed_gramas, ed_agua, ed_tempo, ed_class, ed_notas, e['id'], user_id)
                                    )
                                    st.success("Extração atualizada!")
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
            st.info("Nenhuma extração registrada ainda.")
        else:
            for r in rows:
                # Monta header com classificações
                stars_display = f"⭐{r.get('nota_final_stars', r['classificacao'] or 0)}" if (r.get('nota_final_stars') or r['classificacao']) else ""
                header = (f"{r['cafe_nome']}  ·  {r['metodo']}  ·  "
                          f"{r['data'].strftime('%d/%m/%Y')}  {stars_display}")
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

                        # 2) Classificação detalhada em estrelas (editável)
                        st.markdown('<p class="section-label">⭐ Classificação Detalhada</p>',
                                    unsafe_allow_html=True)
                        STAR_OPTS = [1, 2, 3, 4, 5]
                        es1, es2, es3, es4 = st.columns(4, gap="large")
                        with es1:
                            ed_crema = st.select_slider("Crema", options=STAR_OPTS,
                                                        format_func=_stars,
                                                        value=int(r.get('crema_stars') or 3),
                                                        key=f"e4_crema_{r['id']}")
                        with es2:
                            ed_corpo = st.select_slider("Corpo", options=STAR_OPTS,
                                                        format_func=_stars,
                                                        value=int(r.get('corpo_stars') or 3),
                                                        key=f"e4_corpo_{r['id']}")
                        with es3:
                            ed_equil = st.select_slider("Equilíbrio", options=STAR_OPTS,
                                                        format_func=_stars,
                                                        value=int(r.get('equilibrio_stars') or 3),
                                                        key=f"e4_equil_{r['id']}")
                        with es4:
                            ed_acid = st.select_slider("Acidez", options=STAR_OPTS,
                                                       format_func=_stars,
                                                       value=int(r.get('acidez_stars') or 3),
                                                       key=f"e4_acid_{r['id']}")

                        es5, es6, es7, es8 = st.columns(4, gap="large")
                        with es5:
                            ed_amargor = st.select_slider("Amargor", options=STAR_OPTS,
                                                          format_func=_stars,
                                                          value=int(r.get('amargor_stars') or 3),
                                                          key=f"e4_amar_{r['id']}")
                        with es6:
                            ed_pres = st.select_slider("Presença na Boca", options=STAR_OPTS,
                                                       format_func=_stars,
                                                       value=int(r.get('presenca_boca_stars') or 3),
                                                       key=f"e4_pres_{r['id']}")
                        with es7:
                            ed_doc = st.select_slider("Doçura", options=STAR_OPTS,
                                                      format_func=_stars,
                                                      value=int(r.get('docura_stars') or 3),
                                                      key=f"e4_doc_{r['id']}")
                        with es8:
                            ed_nota = st.select_slider("Nota Final", options=STAR_OPTS,
                                                       format_func=_stars,
                                                       value=int(r.get('nota_final_stars') or 3),
                                                       key=f"e4_nota_{r['id']}")

                        if st.button("💾 Salvar Alterações", key=f"tab4_save_e_{r['id']}",
                                     type="primary"):
                            _run("""UPDATE extracoes SET
                                    gramas=%s, agua_alvo=%s, tempo_extracao=%s,
                                    moedor=%s, clicks_moedor=%s, tds=%s, notas=%s,
                                    crema_stars=%s, corpo_stars=%s, equilibrio_stars=%s,
                                    acidez_stars=%s, amargor_stars=%s, presenca_boca_stars=%s,
                                    docura_stars=%s, nota_final_stars=%s, classificacao=%s
                                    WHERE id=%s AND user_id=%s""",
                                 (ed_gramas, ed_agua, ed_tempo,
                                  ed_moedor, ed_clicks, ed_tds, ed_notas,
                                  ed_crema, ed_corpo, ed_equil,
                                  ed_acid, ed_amargor, ed_pres,
                                  ed_doc, ed_nota, ed_nota,
                                  r['id'], user_id))
                            st.session_state.pop(f"editing_e_{r['id']}", None)
                            st.success("Alterações salvas!")
                            st.rerun()

if __name__ == "__main__":
    main()
