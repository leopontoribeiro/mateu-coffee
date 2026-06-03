import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import base64
import os
import json
from datetime import date
import hashlib
import secrets

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee Production",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_mobile_css():
    css_path = os.path.join(_DIR, ".streamlit", "static", "mateu_coffee_mobile.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def _show_daily_consumption():
    """Exibe widget com o consumo total de café do dia."""
    from datetime import datetime
    hoje = date.today()
    agora = datetime.now().strftime("%H:%M")

    # Soma todas as extrações de hoje
    result = _fetch("""
        SELECT COALESCE(SUM(gramas), 0) as total
        FROM extracoes
        WHERE DATE(data) = %s
    """, (hoje,), _v=_v())

    consumo_total = result[0]["total"] if result else 0

    st.markdown(
        f'<div style="background:#1E0E14;border:1px solid #271018;border-radius:8px;'
        f'padding:14px;margin-bottom:1.5rem;text-align:center">'
        f'<div style="font-size:12px;color:#6B3A4A;margin-bottom:6px">'
        f'📅 {hoje.strftime("%d/%m/%Y")} | ⏰ {agora}</div>'
        f'<div style="font-size:14px;font-weight:700;color:#F5EDE8;'
        f'text-transform:uppercase;letter-spacing:0.05em">'
        f'EU JÁ CONSUMI {consumo_total:.1f}g DE CAFÉ AUDITADOS PELO MATEU COFFEE</div>'
        f'</div>',
        unsafe_allow_html=True)

def _show_logo():
    logo_path = os.path.join(_DIR, "assets", "mateu_coffee_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    /* ORFEU ACAUÃ — Vinho #8B1A35  Laranja #D4561A  Branco #F5EDE8 */

    html, body, [class*="css"], .stApp, div, p, span, label,
    h1, h2, h3, h4, button, input, textarea, select {
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.01em;
    }

    .stApp { background-color: #0D0608; }
    .block-container { padding: 2rem 2.5rem 2rem !important; max-width: 1280px; }

    /* Header */
    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 0 0 2rem 0;
        border-bottom: 1px solid #271018;
        margin-bottom: 2rem;
    }
    .app-header-title {
        font-size: 22px;
        font-weight: 700;
        color: #F5EDE8;
        letter-spacing: -0.03em;
        margin: 0;
    }
    .app-header-sub {
        font-size: 12px;
        color: #6B3A4A;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 2px 0 0 0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #160C0F;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #271018;
        width: fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 7px;
        color: #6B3A4A;
        font-size: 13px;
        font-weight: 500;
        padding: 8px 20px;
        border: none;
        transition: all 0.15s;
    }
    .stTabs [aria-selected="true"] {
        background: #271018 !important;
        color: #F5EDE8 !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-panel"]  { padding-top: 2rem !important; }

    /* Section */
    .section-label {
        font-size: 11px;
        font-weight: 800;
        color: #6B3A4A;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 1.2rem 0;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #271018;
        margin: 2rem 0;
    }

    /* Tags e info rows */
    .tag {
        display: inline-block;
        background: #1E0E14;
        border: 1px solid #321420;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #9A6070;
        padding: 3px 10px;
        margin: 2px 3px 2px 0;
    }
    .tag-accent { border-color: #D4561A88; color: #D4561A; }
    .info-row   { display: flex; gap: 6px; align-items: baseline; margin: 7px 0; }
    .info-key   { font-size: 12px; color: #6B3A4A; font-weight: 600; min-width: 90px; }
    .info-val   { font-size: 14px; color: #F5EDE8; font-weight: 500; }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: #160C0F !important;
        border: 1px solid #271018 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 10px !important;
        font-weight: 700 !important;
        color: #6B3A4A !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #D4561A !important;
        letter-spacing: -0.02em !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 11px !important;
        font-weight: 500 !important;
    }

    /* Inputs */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input {
        background: #160C0F !important;
        border: 1px solid #271018 !important;
        border-radius: 8px !important;
        color: #F5EDE8 !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
        transition: border-color 0.15s !important;
    }
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus {
        border-color: #D4561A !important;
    }
    div[data-baseweb="select"] > div {
        background: #160C0F !important;
        border: 1px solid #271018 !important;
        border-radius: 8px !important;
        color: #F5EDE8 !important;
    }

    /* Labels */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stTextArea label, .stDateInput label, .stRadio label,
    .stFileUploader label, .stSlider label {
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #6B3A4A !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }

    /* Buttons */
    .stButton > button {
        background: #1E0E14 !important;
        border: 1px solid #321420 !important;
        border-radius: 8px !important;
        color: #C09090 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 10px 20px !important;
        transition: all 0.15s !important;
    }
    .stButton > button:hover {
        background: #271018 !important;
        border-color: #3D1828 !important;
        color: #F5EDE8 !important;
    }
    .stButton > button[kind="primary"] {
        background: #D4561A !important;
        border-color: #D4561A !important;
        color: #FFF8F4 !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #B84514 !important;
        border-color: #B84514 !important;
    }

    /* Radio chips */
    .stRadio > div { gap: 6px !important; }
    .stRadio > div label {
        background: #160C0F !important;
        border: 1px solid #271018 !important;
        border-radius: 7px !important;
        padding: 7px 14px !important;
        color: #9A6070 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        transition: all 0.12s !important;
    }
    .stRadio > div label:has(input:checked) {
        background: #2A1018 !important;
        border-color: #8B1A35 !important;
        color: #F5EDE8 !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: #160C0F !important;
        border: 1px solid #271018 !important;
        border-radius: 10px !important;
        color: #D0A090 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 14px 18px !important;
    }
    .streamlit-expanderContent {
        background: #120A0C !important;
        border: 1px solid #1E1018 !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 20px !important;
    }

    /* Misc */
    hr { border-color: #271018 !important; margin: 1.5rem 0 !important; }
    .stFileUploader > div {
        background: #160C0F !important;
        border: 1px dashed #321420 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 3px !important;
        font-size: 13px !important;
    }
    .stSlider > div > div { color: #D4561A !important; }
    ::-webkit-scrollbar       { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0D0608; }
    ::-webkit-scrollbar-thumb { background: #321420; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Database layer ─────────────────────────────────────────────────────
@st.cache_resource
def _get_conn():
    s = st.secrets["connections"]["postgresql"]
    return psycopg2.connect(
        host=s["host"], port=int(s["port"]), dbname=s["database"],
        user=s["username"], password=s["password"],
        sslmode="require", connect_timeout=10,
    )

def _conn():
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

def _run(query, params=()):
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

def _bump():
    st.session_state["_v"] = st.session_state.get("_v", 0) + 1

@st.cache_data(ttl=600, show_spinner=False)
def _fetch(query, params=(), _v=0):
    c   = _conn()
    cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        cur.close()
    return rows

def _v():
    return st.session_state.get("_v", 0)

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

def _login(email: str, senha: str, remember: bool = False) -> bool:
    """Valida credenciais e define sessão."""
    try:
        result = _fetch("SELECT id, email FROM usuarios WHERE email=%s LIMIT 1", (email,), _v=0)
        if not result:
            return False
        usuario = result[0]
        result_pwd = _fetch("SELECT senha_hash FROM usuarios WHERE id=%s", (usuario['id'],), _v=0)
        if not result_pwd or not _verify_senha(senha, result_pwd[0]['senha_hash']):
            return False
        st.session_state['user_id'] = usuario['id']
        st.session_state['user_email'] = usuario['email']

        if remember:
            token = secrets.token_urlsafe(32)
            from datetime import datetime, timedelta
            expira = datetime.now() + timedelta(days=30)
            _run(
                "UPDATE usuarios SET remember_token=%s, remember_token_created=%s WHERE id=%s",
                (token, expira, usuario['id'])
            )
            st.session_state['remember_token'] = token

        return True
    except:
        return False

def _check_remember_token():
    """Restaura sessão se token válido."""
    token = st.session_state.get('remember_token')
    if not token:
        return False
    try:
        from datetime import datetime
        result = _fetch(
            "SELECT id, email, remember_token_created FROM usuarios WHERE remember_token=%s",
            (token,), _v=0
        )
        if not result:
            return False
        usuario = result[0]
        if usuario['remember_token_created'] and datetime.fromisoformat(usuario['remember_token_created']) < datetime.now():
            return False
        st.session_state['user_id'] = usuario['id']
        st.session_state['user_email'] = usuario['email']
        return True
    except:
        return False

def _logout():
    """Limpa sessão e token."""
    user_id = st.session_state.get('user_id')
    if user_id:
        _run("UPDATE usuarios SET remember_token=NULL, remember_token_created=NULL WHERE id=%s", (user_id,))
    st.session_state.pop('user_id', None)
    st.session_state.pop('user_email', None)
    st.session_state.pop('remember_token', None)

def _init_db():
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
                remember_token_created TIMESTAMP
            );
        """)
        # Migrations para tabela existente
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token TEXT;")
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token_created TIMESTAMP;")
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
                ADD COLUMN IF NOT EXISTS local_compra  TEXT    DEFAULT '',
                ADD COLUMN IF NOT EXISTS valor_compra  FLOAT   DEFAULT 0,
                ADD COLUMN IF NOT EXISTS data_compra   DATE;
        """)
        conn.commit()
        st.session_state["_db_ready"] = True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

# ── Helpers ────────────────────────────────────────────────────────────
def _b64(f):
    if not f: return None
    d = f.read(); f.seek(0)
    return base64.b64encode(d).decode()

def _img(b64, w=170):
    if b64:
        st.markdown(
            f'<img src="data:image/jpeg;base64,{b64}" width="{w}" '
            f'style="border-radius:10px;margin-top:4px;display:block;">',
            unsafe_allow_html=True)

def _stars(n):
    n = int(n or 0)
    return "★" * n + "☆" * (5 - n)

def _tag(t, accent=False):
    return f'<span class="tag{" tag-accent" if accent else ""}">{t}</span>'

def _irow(k, v):
    return f'<div class="info-row"><span class="info-key">{k}</span><span class="info-val">{v}</span></div>'

def _ph():
    return ('<div style="width:150px;height:150px;background:#160C0F;border:1px solid #271018;'
            'border-radius:10px;display:flex;align-items:center;justify-content:center;'
            'color:#3D1828;font-size:28px;">☕</div>')

METODOS = ["Espresso","Pour Over","French Press","Aeropress",
           "Chemex","Moka Pot","Cold Brew","Sifão","Drip","Outro"]

# ── Coffee Engine ──────────────────────────────────────────────────────
class CoffeeEngine:
    ATTRS    = ("Doçura","Acidez","Corpo","Amargor","Finalização")
    TARGET   = (8, 7, 7, 4, 8)
    EY_LOW   = 18.0
    EY_HIGH  = 22.0

    @staticmethod
    def calc(coffee_g: float, water_g: float, tds: float | None, time_s: int) -> dict:
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
        name='Target', line_color='#8B1A35', fillcolor='rgba(139,26,53,0.15)'))
    fig.add_trace(go.Scatterpolar(
        r=profile, theta=attrs, fill='toself',
        name='Atual', line_color='#D4561A', fillcolor='rgba(212,86,26,0.18)'))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0,10], gridcolor='#271018',
                            linecolor='#271018', tickfont=dict(color='#6B3A4A', size=9)),
            angularaxis=dict(gridcolor='#271018', linecolor='#271018')),
        showlegend=True,
        legend=dict(font=dict(color='#9A6070', size=10), bgcolor='rgba(0,0,0,0)'),
        height=270, margin=dict(l=20,r=20,t=20,b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9A6070', size=11, family='Inter'),
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
    --bg:      #0D0608;
    --card:    #160a0e;
    --text:    #F5EDE8;
    --muted:   #6B3A4A;
    --accent:  #D4561A;
    --vinho:   #8B1A35;
    --border:  #271018;
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
  .results{margin-top:14px;background:#1a0a0f;border-radius:6px;padding:13px;border:1px solid var(--border)}
  .rt{font-size:9.5pt;font-weight:700;color:var(--accent);margin-bottom:8px}
  .vb{font-size:10.5pt;font-weight:600;color:#F5EDE8;background:#250d14;padding:9px 11px;border-radius:4px;border-left:4px solid var(--vinho);margin-bottom:8px}
  .vd{font-size:8.5pt;color:#c4a8b0;line-height:1.5}
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
      backgroundColor:'rgba(212,86,26,0.15)',
      borderColor:'rgba(212,86,26,1)',
      borderWidth:2,
      pointBackgroundColor:'rgba(139,26,53,1)',
      pointRadius:4
    }]
  },
  options:{
    responsive:true,maintainAspectRatio:false,
    scales:{r:{
      angleLines:{color:'#271018'},grid:{color:'#271018'},
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
    import anthropic
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

    # ── Autenticação ────────────────────────────────────────────────────
    # Tenta restaurar login via remember_token
    if 'user_id' not in st.session_state and 'remember_token' not in st.session_state:
        # Tenta carregar token do session_state (persistido via Streamlit secrets)
        try:
            import json
            from pathlib import Path
            secrets_file = Path.home() / ".mateu_coffee_auth"
            if secrets_file.exists():
                with open(secrets_file) as f:
                    auth_data = json.load(f)
                    st.session_state['remember_token'] = auth_data.get('token')
        except:
            pass

    if 'user_id' not in st.session_state:
        # Tenta restaurar com token
        if not _check_remember_token():
            # ── Página de Login ────────────────────────────────────
            st.markdown("""
                <style>
                .login-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    margin: 2rem auto;
                }
                .login-logo {
                    max-width: 280px;
                    margin-bottom: 2rem;
                }
                </style>
                <div class="login-container">
                    <img src="app/static/assets/mateu_coffee_logo.png" class="login-logo" alt="Mateu Coffee">
                </div>
            """, unsafe_allow_html=True)

            # Exibe logo usando file path direto
            logo_path = os.path.join(_DIR, "assets", "mateu_coffee_logo.png")
            if os.path.exists(logo_path):
                col_logo_center = st.columns([0.15, 0.7, 0.15])[1]
                with col_logo_center:
                    st.image(logo_path, use_container_width=True)

            st.markdown("---")
            tab_login, tab_cadastro = st.tabs(["Login", "Cadastro"])

            with tab_login:
                st.markdown("### 🔐 Entrar na Conta")
                email = st.text_input("Email", key="login_email", placeholder="seu@email.com")
                senha = st.text_input("Senha", type="password", key="login_senha")
                remember_me = st.checkbox("✓ Manter-me conectado", value=False, key="login_remember")

                if st.button("🔓 Entrar", use_container_width=True):
                    if _login(email, senha, remember=remember_me):
                        if remember_me:
                            # Salva token no arquivo local
                            try:
                                import json
                                from pathlib import Path
                                secrets_file = Path.home() / ".mateu_coffee_auth"
                                with open(secrets_file, 'w') as f:
                                    json.dump({'token': st.session_state.get('remember_token', '')}, f)
                            except:
                                pass
                        st.success("✅ Login realizado!")
                        st.rerun()
                    else:
                        st.error("❌ Email ou senha inválidos.")

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
                    except:
                        st.error("Email já cadastrado.")
        return

    # ── App Logado ──────────────────────────────────────────────────────
    _show_logo()
    _show_daily_consumption()

    # Botão Logout no topo
    col_logo, col_logout = st.columns([0.85, 0.15])
    with col_logout:
        if st.button("🚪 Sair", use_container_width=True, key="btn_logout"):
            _logout()
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs([
        "  Novo Café  ", "  Nova Extração  ", "  Meus Cafés  ", "  Histórico  "])

    # ── Tab 1 · Cadastrar café ─────────────────────────────────────────
    with tab1:
        st.markdown('<p class="section-label">Cadastrar Novo Café</p>', unsafe_allow_html=True)

        # Aplica resultado da análise de IA antes de renderizar os widgets
        if "ai_result" in st.session_state:
            r = st.session_state.pop("ai_result")
            if r.get("nome"):    st.session_state["inp_nome"]    = r["nome"]
            if r.get("fazenda"): st.session_state["inp_fazenda"] = r["fazenda"]
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
            fazenda  = st.text_input("Fazenda", key="inp_fazenda",
                                     placeholder="Ex: Fazenda Santa Inês")
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
            if foto_emb:
                _img(_b64(foto_emb), w=160)
                if st.button("🔍 Analisar Embalagem com IA",
                             use_container_width=True, key="btn_ai"):
                    with st.spinner("Lendo a embalagem..."):
                        try:
                            result = _analisar_embalagem(_b64(foto_emb))
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
                     fazenda,regiao,data_torra,tamanho_pacote,foto_embalagem,
                     local_compra,valor_compra,data_compra)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (data_cad, nome.strip(), tipo, torra, notas, class_c,
                     fazenda, regiao, data_tort, tamanho, _b64(foto_emb),
                     local_compra.strip() or None,
                     valor_compra if valor_compra > 0 else None,
                     data_compra))
                st.success(f"**{nome}** cadastrado com sucesso.")
                st.balloons()

    # ── Tab 2 · Nova extração ──────────────────────────────────────────
    with tab2:
        st.markdown('<p class="section-label">Registrar Extração</p>', unsafe_allow_html=True)

        cafes = _fetch("SELECT id, nome, torra FROM coffees ORDER BY nome", _v=_v())
        if not cafes:
            st.info("Cadastre um café primeiro na aba Novo Café.")
        else:
            cafe_map = {f"{c['nome']}  ·  {c['torra']}": c['id'] for c in cafes}
            sel    = st.selectbox("Café", list(cafe_map.keys()))
            cid    = cafe_map[sel]
            metodo = st.selectbox("Método de Preparo", METODOS)

            # ── Configuração de Xícaras ────────────────────────────────────
            xicaras = st.radio("Número de Xícaras", [1, 2], horizontal=True, key="config_xicaras")
            # Valores pré-definidos por número de xícaras (1:1 ratio padrão)
            gramas_default = 18.0 if xicaras == 1 else 36.0
            agua_default   = 300.0 if xicaras == 1 else 600.0

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">Parâmetros</p>', unsafe_allow_html=True)

            c1, c2 = st.columns(2, gap="large")
            with c1:
                gramas = st.number_input("Pó de Café (g)",       5.0,  80.0,  gramas_default, 0.1,
                                         help="Peso do pó medido na balança")
                agua   = st.number_input("Água Alvo (g)",        50.0, 2000.0, agua_default, 5.0)
                tds    = st.number_input("TDS Medido (%)",        0.0,  5.0,   0.0,  0.01,
                                         help="Deixe 0 se não usar refratômetro")
                tempo  = st.number_input("Tempo de Extração (s)", 1,    600,   150,  1)
            with c2:
                moedor   = st.text_input("Moedor", placeholder="Ex: Comandante C40")
                clicks   = st.number_input("Clicks do Moedor", 0, 200, 0, 1)
                data_ext = st.date_input("Data", value=date.today(), key="data_ext", format="DD/MM/YYYY")
                class_e  = st.select_slider("Classificação", options=[1,2,3,4,5],
                                            format_func=_stars, value=3, key="class_extracao")
                notas_e  = st.text_area("Notas", placeholder="Impressões da extração...",
                                        height=80)

            m  = CoffeeEngine.calc(gramas, agua, tds if tds > 0 else None, tempo)
            ey = m.get("ey", 0.0)

            # ── Análise em Tempo Real (Expander no Topo) ───────────────────
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
                    foto_can = st.file_uploader("Foto da Caneca", type=["jpg","jpeg","png"],
                                                key="foto_can")
                    if foto_can:
                        _img(_b64(foto_can), w=210)

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            if st.button("🔴 REGISTRAR EXTRAÇÃO", type="primary", use_container_width=True):
                _run("""INSERT INTO extracoes
                    (coffee_id,data,metodo,gramas,moedor,clicks_moedor,agua_alvo,tds,
                     tempo_extracao,brew_ratio,ey,fluxo,foto_caneca,classificacao,notas)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (cid, data_ext, metodo, gramas, moedor, clicks, agua, tds, tempo,
                     m.get("ratio",0), ey, m.get("fluxo",0),
                     _b64(foto_can) if foto_can else None, class_e, notas_e))
                st.success("Extração registrada!")
                st.rerun()

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">Motor Barista — Simulador de Extração</p>',
                        unsafe_allow_html=True)

            # ── Busca dados do café para pré-definir parâmetros ──────────────
            cafe_info = _fetch(f"SELECT tipo, torra FROM coffees WHERE id=%s LIMIT 1",
                              (cid,), _v=_v())
            if cafe_info:
                cafe_tipo = cafe_info[0]["tipo"]
                cafe_torra = cafe_info[0]["torra"]
                params = _motor_barista_params(cafe_torra, cafe_tipo)
            else:
                params = _motor_barista_params("Média", "Grãos")  # fallback

            # ── Motor Barista com parâmetros dinâmicos ──────────────────────
            motor_html = _MOTOR_BARISTA_HTML.replace(
                'value="18"', f'value="{params["dose"]}"'
            ).replace(
                'value="36"', f'value="{params["yield"]}"'
            ).replace(
                'value="28"', f'value="{params["time"]}"'
            ).replace(
                'value="92"', f'value="{params["temp"]}"'
            ).replace(
                'value="9"', f'value="{params["pressure"]}"'
            )
            components.html(motor_html, height=660, scrolling=False)

    # ── Tab 3 · Meus cafés ────────────────────────────────────────────
    with tab3:
        st.markdown('<p class="section-label">Biblioteca de Cafés</p>', unsafe_allow_html=True)

        cafes = _fetch("""
            SELECT c.*, COUNT(e.id) AS total_ext,
                   AVG(e.ey) AS avg_ey, AVG(e.classificacao) AS avg_nota
            FROM coffees c LEFT JOIN extracoes e ON e.coffee_id=c.id
            GROUP BY c.id ORDER BY c.data_cadastro DESC""", _v=_v())

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
                        info = (_irow("Fazenda",  c['fazenda'] or "—") +
                                _irow("Região",   c['regiao']  or "—") +
                                _irow("Cadastro", c['data_cadastro'].strftime('%d/%m/%Y')))
                        # Info de compra (se preenchida)
                        if c.get("local_compra"):
                            info += _irow("Comprado em", c["local_compra"])
                        if c.get("data_compra"):
                            info += _irow("Data compra", c["data_compra"].strftime('%d/%m/%Y'))
                        note = (f'<div style="margin-top:10px;font-size:12px;color:#6B3A4A;'
                                f'font-style:italic;">{c["notas"]}</div>' if c["notas"] else "")
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

                    # ── Seção de Extrações ─────────────────────────────────────
                    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
                    st.markdown('<p class="section-label">Detalhes das Extrações</p>', unsafe_allow_html=True)

                    extracts = _fetch("""
                        SELECT * FROM extracoes
                        WHERE coffee_id=%s
                        ORDER BY data DESC, created_at DESC
                    """, (c["id"],), _v=_v())

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
                                        "UPDATE extracoes SET foto_caneca=%s WHERE id=%s",
                                        (_b64(nova_foto), e["id"])
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
                                st.metric("Brew Ratio", f"1:{e['agua_alvo']/e['gramas']:.1f}")
                                if e['ey']:
                                    st.metric("EY", f"{e['ey']:.1f}%")
                                st.metric("Fluxo", f"{e['fluxo']:.2f}g/s" if e['fluxo'] else "—")

                            # Botão editar
                            st.markdown("---")
                            col_edit, col_del = st.columns(2)
                            with col_edit:
                                if st.button("✏️ Editar Extração", key=f"edit_e_{e['id']}", use_container_width=True):
                                    st.session_state[f"edit_ext_{e['id']}"] = True
                            with col_del:
                                if st.button("🗑️ Deletar", key=f"del_e_{e['id']}", use_container_width=True):
                                    _run("DELETE FROM extracoes WHERE id=%s", (e['id'],))
                                    st.rerun()

                            # Formulário de edição (se ativado)
                            if st.session_state.get(f"edit_ext_{e['id']}", False):
                                st.markdown("**Editar Extração**")
                                ed_col1, ed_col2 = st.columns(2)
                                with ed_col1:
                                    ed_gramas = st.number_input("Dose (g)", value=e['gramas'], key=f"ed_g_{e['id']}")
                                    ed_agua = st.number_input("Água (g)", value=e['agua_alvo'], key=f"ed_a_{e['id']}")
                                    ed_tempo = st.number_input("Tempo (s)", value=e['tempo_extracao'], key=f"ed_t_{e['id']}")
                                with ed_col2:
                                    ed_class = st.select_slider("Classificação", options=[1,2,3,4,5],
                                                               value=e['classificacao'] or 3,
                                                               format_func=_stars, key=f"ed_c_{e['id']}")
                                    ed_notas = st.text_area("Comentários", value=e['notas'] or "", key=f"ed_n_{e['id']}", height=80)

                                if st.button("💾 Salvar Edição", key=f"save_e_{e['id']}", use_container_width=True):
                                    _run(
                                        "UPDATE extracoes SET gramas=%s, agua_alvo=%s, tempo_extracao=%s, classificacao=%s, notas=%s WHERE id=%s",
                                        (ed_gramas, ed_agua, ed_tempo, ed_class, ed_notas, e['id'])
                                    )
                                    st.success("Extração atualizada!")
                                    st.session_state[f"edit_ext_{e['id']}"] = False
                                    st.rerun()

                    st.markdown("")
                    if st.button("Remover café", key=f"del_c_{c['id']}"):
                        _run("DELETE FROM coffees WHERE id=%s", (c["id"],))
                        st.rerun()

    # ── Tab 4 · Histórico ─────────────────────────────────────────────
    with tab4:
        st.markdown('<p class="section-label">Histórico de Extrações</p>', unsafe_allow_html=True)

        rows = _fetch("""
            SELECT e.*, c.nome AS cafe_nome, c.torra FROM extracoes e
            JOIN coffees c ON c.id=e.coffee_id
            ORDER BY e.data DESC, e.created_at DESC LIMIT 200""", _v=_v())

        if not rows:
            st.info("Nenhuma extração registrada ainda.")
        else:
            for r in rows:
                header = (f"{r['cafe_nome']}  ·  {r['metodo']}  ·  "
                          f"{r['data'].strftime('%d/%m/%Y')}  ·  {_stars(r['classificacao'] or 0)}")
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
                        note = (f'<div style="margin-top:10px;font-size:12px;color:#6B3A4A;'
                                f'font-style:italic;">{r["notas"]}</div>' if r["notas"] else "")
                        st.markdown(f'<div>{tags}</div><div style="margin-top:12px">{info}</div>{note}',
                                    unsafe_allow_html=True)
                    with rc:
                        if r["brew_ratio"]: st.metric("Brew Ratio", f"1 : {r['brew_ratio']:.1f}")
                        if r["ey"]:         st.metric("EY",         f"{r['ey']:.1f}%")
                        if r["fluxo"]:      st.metric("Fluxo",      f"{r['fluxo']:.2f} g/s")
                    st.markdown("")
                    if st.button("Remover extração", key=f"del_e_{r['id']}"):
                        _run("DELETE FROM extracoes WHERE id=%s", (r["id"],))
                        st.rerun()

if __name__ == "__main__":
    main()
