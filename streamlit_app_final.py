import streamlit as st
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import base64
from datetime import date

# ======================================================================
# PAGE CONFIG
# ======================================================================
st.set_page_config(
    page_title="Mateu Coffee Production",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ── Base ───────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput,
.stNumberInput, .stSelectbox, .stTextArea, .stRadio, .stDateInput,
.stFileUploader, .stButton, .stMetric, div, p, span, label, h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em;
}

.stApp { background-color: #0C0C0C; }
.block-container { padding: 2rem 2.5rem 2rem !important; max-width: 1280px; }

/* ── Header ─────────────────────────────────────────────────────── */
.app-header {
    display: flex; align-items: center; gap: 14px;
    padding: 0 0 2rem 0;
    border-bottom: 1px solid #1E1E1E;
    margin-bottom: 2rem;
}
.app-header-icon { font-size: 32px; line-height: 1; }
.app-header-title {
    font-size: 22px; font-weight: 700; color: #F5F5F5;
    letter-spacing: -0.03em; margin: 0;
}
.app-header-sub {
    font-size: 12px; font-weight: 400; color: #555;
    letter-spacing: 0.06em; text-transform: uppercase; margin: 2px 0 0 0;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: #111; border-radius: 10px;
    padding: 4px; border: 1px solid #1E1E1E; width: fit-content;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 7px;
    color: #666; font-size: 13px; font-weight: 500;
    padding: 8px 20px; border: none; transition: all .15s;
}
.stTabs [aria-selected="true"] {
    background: #1E1E1E !important; color: #F5F5F5 !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 2rem !important; }

/* ── Section labels ──────────────────────────────────────────────── */
.section-label {
    font-size: 10px; font-weight: 700; color: #555;
    letter-spacing: 0.12em; text-transform: uppercase;
    margin: 0 0 1.2rem 0;
}
.section-divider {
    border: none; border-top: 1px solid #1E1E1E;
    margin: 2rem 0;
}

/* ── Cards ───────────────────────────────────────────────────────── */
.metric-card {
    background: #111; border: 1px solid #1E1E1E;
    border-radius: 12px; padding: 16px 20px;
}
.metric-label {
    font-size: 11px; font-weight: 600; color: #555;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;
}
.metric-value {
    font-size: 22px; font-weight: 700; color: #10B981;
    letter-spacing: -0.03em;
}
.metric-sub { font-size: 12px; color: #666; margin-top: 4px; }

.coffee-card {
    background: #111; border: 1px solid #1E1E1E;
    border-radius: 14px; padding: 20px 24px; margin: 10px 0;
}
.tag {
    display: inline-block; background: #1A1A1A;
    border: 1px solid #2A2A2A; border-radius: 6px;
    font-size: 11px; font-weight: 500; color: #999;
    padding: 3px 10px; margin: 2px 3px 2px 0;
}
.tag-accent { border-color: #10B98155; color: #10B981; }
.info-row {
    display: flex; gap: 6px; align-items: baseline;
    margin: 6px 0;
}
.info-key { font-size: 11px; color: #555; font-weight: 500; min-width: 80px; }
.info-val { font-size: 13px; color: #D0D0D0; font-weight: 500; }

/* ── Native Streamlit metrics ────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #111 !important; border: 1px solid #1E1E1E !important;
    border-radius: 12px !important; padding: 16px 20px !important;
}
div[data-testid="stMetricLabel"] p {
    font-size: 10px !important; font-weight: 700 !important;
    color: #555 !important; text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
div[data-testid="stMetricValue"] {
    font-size: 20px !important; font-weight: 700 !important;
    color: #10B981 !important; letter-spacing: -0.02em !important;
}
div[data-testid="stMetricDelta"] {
    font-size: 11px !important; font-weight: 500 !important;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input {
    background: #111 !important; border: 1px solid #242424 !important;
    border-radius: 8px !important; color: #E0E0E0 !important;
    font-size: 14px !important; font-weight: 400 !important;
    padding: 10px 14px !important;
    transition: border-color .15s !important;
}
.stTextInput input:focus, .stNumberInput input:focus,
.stTextArea textarea:focus { border-color: #10B981 !important; }

.stSelectbox select, div[data-baseweb="select"] {
    background: #111 !important; border: 1px solid #242424 !important;
    border-radius: 8px !important;
}
div[data-baseweb="select"] > div {
    background: #111 !important; border: 1px solid #242424 !important;
    border-radius: 8px !important; color: #E0E0E0 !important;
}

/* ── Labels ──────────────────────────────────────────────────────── */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stTextArea label, .stDateInput label, .stRadio label,
.stFileUploader label, .stSlider label {
    font-size: 11px !important; font-weight: 600 !important;
    color: #666 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important; margin-bottom: 4px !important;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
.stButton > button {
    background: #1A1A1A !important; border: 1px solid #2A2A2A !important;
    border-radius: 8px !important; color: #D0D0D0 !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 10px 20px !important; transition: all .15s !important;
}
.stButton > button:hover {
    background: #222 !important; border-color: #333 !important;
    color: #F5F5F5 !important;
}
.stButton > button[kind="primary"] {
    background: #10B981 !important; border-color: #10B981 !important;
    color: #000 !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #0D9E6E !important; border-color: #0D9E6E !important;
}

/* ── Radio ───────────────────────────────────────────────────────── */
.stRadio > div { gap: 6px !important; }
.stRadio > div label {
    background: #111 !important; border: 1px solid #1E1E1E !important;
    border-radius: 7px !important; padding: 7px 14px !important;
    color: #999 !important; font-size: 13px !important;
    font-weight: 500 !important; cursor: pointer !important;
    text-transform: none !important; letter-spacing: 0 !important;
    transition: all .12s !important;
}
.stRadio > div label:has(input:checked) {
    background: #1A2A22 !important; border-color: #10B981 !important;
    color: #10B981 !important;
}

/* ── Expander ────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #111 !important; border: 1px solid #1E1E1E !important;
    border-radius: 10px !important; color: #C0C0C0 !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 14px 18px !important;
}
.streamlit-expanderContent {
    background: #0E0E0E !important; border: 1px solid #1A1A1A !important;
    border-top: none !important; border-radius: 0 0 10px 10px !important;
    padding: 20px !important;
}

/* ── Divider ─────────────────────────────────────────────────────── */
hr { border-color: #1A1A1A !important; margin: 1.5rem 0 !important; }

/* ── File uploader ───────────────────────────────────────────────── */
.stFileUploader > div {
    background: #111 !important; border: 1px dashed #2A2A2A !important;
    border-radius: 10px !important;
}

/* ── Alerts ──────────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 10px !important; border-left-width: 3px !important;
    font-size: 13px !important;
}

/* ── Select slider ───────────────────────────────────────────────── */
.stSlider > div > div { color: #10B981 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0C0C0C; }
::-webkit-scrollbar-thumb { background: #2A2A2A; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ======================================================================
# DATABASE
# ======================================================================
@st.cache_resource
def get_conn():
    s = st.secrets["connections"]["postgresql"]
    return psycopg2.connect(
        host=s["host"], port=int(s["port"]), dbname=s["database"],
        user=s["username"], password=s["password"], sslmode="require"
    )

def conn():
    c = get_conn()
    if c.closed:
        st.cache_resource.clear()
        c = get_conn()
    return c

def init_db():
    cur = conn().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coffees (
            id              SERIAL PRIMARY KEY,
            data_cadastro   DATE    NOT NULL DEFAULT CURRENT_DATE,
            nome            TEXT    NOT NULL,
            tipo            TEXT    NOT NULL DEFAULT 'Grãos',
            torra           TEXT    NOT NULL DEFAULT 'Média',
            notas           TEXT    DEFAULT '',
            classificacao   INTEGER DEFAULT 0,
            fazenda         TEXT    DEFAULT '',
            regiao          TEXT    DEFAULT '',
            data_torra      DATE,
            tamanho_pacote  INTEGER DEFAULT 250,
            foto_embalagem  TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS extracoes (
            id              SERIAL PRIMARY KEY,
            coffee_id       INTEGER REFERENCES coffees(id) ON DELETE CASCADE,
            data            DATE    NOT NULL DEFAULT CURRENT_DATE,
            metodo          TEXT    NOT NULL DEFAULT 'Espresso',
            gramas          FLOAT   NOT NULL DEFAULT 18,
            moedor          TEXT    DEFAULT '',
            clicks_moedor   INTEGER DEFAULT 0,
            agua_alvo       FLOAT   NOT NULL DEFAULT 300,
            tds             FLOAT   DEFAULT 0,
            tempo_extracao  INTEGER NOT NULL DEFAULT 150,
            brew_ratio      FLOAT   DEFAULT 0,
            ey              FLOAT   DEFAULT 0,
            fluxo           FLOAT   DEFAULT 0,
            foto_caneca     TEXT,
            classificacao   INTEGER DEFAULT 0,
            notas           TEXT    DEFAULT '',
            created_at      TIMESTAMP DEFAULT NOW()
        );
    """)
    conn().commit()
    cur.close()

def fetch(query, params=()):
    cur = conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return rows

def run(query, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(query, params)
    c.commit()
    cur.close()

# ======================================================================
# HELPERS
# ======================================================================
def to_b64(f):
    if f is None:
        return None
    data = f.read()
    f.seek(0)
    return base64.b64encode(data).decode()

def show_img(b64, width=170):
    if b64:
        st.markdown(
            f'<img src="data:image/jpeg;base64,{b64}" width="{width}" '
            f'style="border-radius:10px;margin-top:4px;display:block;">',
            unsafe_allow_html=True
        )

def stars(n):
    n = int(n or 0)
    return "★" * n + "☆" * (5 - n)

def tag(text, accent=False):
    cls = "tag tag-accent" if accent else "tag"
    return f'<span class="{cls}">{text}</span>'

def info_row(key, val):
    return f'<div class="info-row"><span class="info-key">{key}</span><span class="info-val">{val}</span></div>'

METODOS = ["Espresso", "Pour Over", "French Press", "Aeropress",
           "Chemex", "Moka Pot", "Cold Brew", "Sifão", "Drip", "Outro"]

# ======================================================================
# COFFEE ENGINE
# ======================================================================
class Engine:
    @staticmethod
    def calc(coffee_g, water_g, tds=None, time_s=1):
        if coffee_g <= 0:
            return {}
        ratio = water_g / coffee_g
        fluxo = water_g / max(time_s, 1)
        out = {
            "ratio_text": f"1 : {ratio:.1f}",
            "ratio": ratio,
            "ey": 0.0,
            "status": "Aguardando TDS",
            "delta_color": "off",
            "fluxo": fluxo,
        }
        if tds and tds > 0:
            bev = max(water_g - 2.0 * coffee_g, 0)
            ey = (bev * tds) / coffee_g
            out["ey"] = ey
            if ey < 18.0:
                out["status"] = "Subextraído"
                out["delta_color"] = "inverse"
            elif ey <= 22.0:
                out["status"] = "Ideal — Sweet Spot"
                out["delta_color"] = "off"
            else:
                out["status"] = "Superextraído"
                out["delta_color"] = "inverse"
        return out

@st.cache_data(ttl=86400)
def _wheel():
    return ["Doçura", "Acidez", "Corpo", "Amargor", "Finalização"]

def sensory(ey):
    if ey <= 0:  return [7, 7, 7, 5, 7]
    if ey < 18:  return [4, 9, 4, 3, 5]
    if ey > 22:  return [3, 4, 8, 9, 4]
    return [9, 8, 8, 4, 9]

def radar(profile):
    attrs = _wheel()
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[8, 7, 7, 4, 8], theta=attrs, fill='toself',
        name='Target', line_color='#2A2A2A', fillcolor='rgba(42,42,42,0.4)'))
    fig.add_trace(go.Scatterpolar(
        r=profile, theta=attrs, fill='toself',
        name='Atual', line_color='#10B981', fillcolor='rgba(16,185,129,0.15)'))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0, 10],
                            gridcolor='#1E1E1E', linecolor='#1E1E1E',
                            tickfont=dict(color='#444', size=9)),
            angularaxis=dict(gridcolor='#1E1E1E', linecolor='#1E1E1E')
        ),
        showlegend=True,
        legend=dict(font=dict(color='#666', size=10), bgcolor='rgba(0,0,0,0)'),
        height=270,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888', size=11, family='Inter'),
    )
    return fig

# ======================================================================
# MAIN
# ======================================================================
def main():
    init_db()

    st.markdown("""
    <div class="app-header">
        <div class="app-header-icon">☕</div>
        <div>
            <div class="app-header-title">Mateu Coffee Production</div>
            <div class="app-header-sub">Cadastro · Extração · Análise · Histórico</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "  Novo Café  ",
        "  Nova Extração  ",
        "  Meus Cafés  ",
        "  Histórico  ",
    ])

    # ──────────────────────────────────────────────────────────────────
    # TAB 1 — CADASTRAR CAFÉ
    # ──────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown('<p class="section-label">Cadastrar Novo Café</p>', unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="large")

        with c1:
            data_cad  = st.date_input("Data de Cadastro", value=date.today())
            nome      = st.text_input("Nome do Café *", placeholder="Ex: Ethiopian Yirgacheffe")
            fazenda   = st.text_input("Fazenda", placeholder="Ex: Fazenda Santa Inês")
            regiao    = st.text_input("Região", placeholder="Ex: Sul de Minas / Etiópia")
            data_tort = st.date_input("Data da Torra", value=None)
            tamanho   = st.radio("Pacote", [250, 500, 1000], horizontal=True,
                                 format_func=lambda x: f"{x}g")

        with c2:
            tipo    = st.radio("Tipo", ["Grãos", "Moído"], horizontal=True)
            torra   = st.radio("Torra", ["Clara", "Média", "Escura"], horizontal=True)
            notas   = st.text_area("Notas de Sabor / Torra",
                                   placeholder="Ex: Blueberry, chocolate, floral...", height=108)
            class_c = st.select_slider("Classificação",
                                       options=[1, 2, 3, 4, 5], format_func=stars, value=3)
            foto_emb = st.file_uploader("Foto da Embalagem", type=["jpg","jpeg","png"],
                                        key="foto_emb")
            if foto_emb:
                show_img(to_b64(foto_emb), width=160)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        if st.button("Salvar Café", type="primary", use_container_width=True):
            if not nome.strip():
                st.error("Nome do café é obrigatório.")
            else:
                run("""
                    INSERT INTO coffees
                        (data_cadastro, nome, tipo, torra, notas, classificacao,
                         fazenda, regiao, data_torra, tamanho_pacote, foto_embalagem)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (data_cad, nome.strip(), tipo, torra, notas, class_c,
                      fazenda, regiao, data_tort, tamanho, to_b64(foto_emb)))
                st.success(f"**{nome}** cadastrado com sucesso.")
                st.balloons()

    # ──────────────────────────────────────────────────────────────────
    # TAB 2 — NOVA EXTRAÇÃO
    # ──────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown('<p class="section-label">Registrar Extração</p>', unsafe_allow_html=True)

        cafes = fetch("SELECT id, nome, torra FROM coffees ORDER BY nome")
        if not cafes:
            st.info("Cadastre um café primeiro na aba Novo Café.")
        else:
            cafe_map = {f"{c['nome']}  ·  {c['torra']}": c['id'] for c in cafes}
            sel = st.selectbox("Café", list(cafe_map.keys()))
            cid = cafe_map[sel]
            metodo = st.selectbox("Método de Preparo", METODOS)

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">Parâmetros</p>', unsafe_allow_html=True)

            c1, c2 = st.columns(2, gap="large")
            with c1:
                gramas = st.number_input("Pó de Café (g)",        5.0,  50.0,  18.0, 0.1,
                                         help="Peso do pó medido na balança")
                agua   = st.number_input("Água Alvo (g)",         50.0, 1000.0,300.0, 5.0)
                tds    = st.number_input("TDS Medido (%)",         0.0,  5.0,   0.0,  0.01,
                                         help="Deixe 0 se não usar refratômetro")
                tempo  = st.number_input("Tempo de Extração (s)",  1,    600,   150,  1)

            with c2:
                moedor   = st.text_input("Moedor", placeholder="Ex: Comandante C40")
                clicks   = st.number_input("Clicks do Moedor", 0, 200, 0, 1)
                data_ext = st.date_input("Data", value=date.today(), key="data_ext")
                class_e  = st.select_slider("Classificação",
                                            options=[1,2,3,4,5], format_func=stars, value=3)
                notas_e  = st.text_area("Notas", placeholder="Impressões da extração...", height=80)

            # ── Análise em tempo real ──────────────────────────────
            m  = Engine.calc(gramas, agua, tds if tds > 0 else None, tempo)
            ey = m.get("ey", 0.0)

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">Análise em Tempo Real</p>', unsafe_allow_html=True)

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Brew Ratio",       m.get("ratio_text", "—"))
            mc2.metric("Extraction Yield", f"{ey:.2f}%" if ey > 0 else "—",
                       delta=m.get("status") if ey > 0 else None,
                       delta_color=m.get("delta_color", "off"))
            mc3.metric("Fluxo Médio",      f"{m.get('fluxo', 0):.2f} g/s")
            mc4.metric("Status",           m.get("status", "—"))

            col_r, col_p = st.columns([1.6, 1], gap="large")
            with col_r:
                st.plotly_chart(radar(sensory(ey)), use_container_width=True,
                                config={'displayModeBar': False})
            with col_p:
                foto_can = st.file_uploader("Foto da Caneca", type=["jpg","jpeg","png"],
                                            key="foto_can")
                if foto_can:
                    show_img(to_b64(foto_can), width=210)

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            if st.button("Salvar Extração", type="primary", use_container_width=True):
                run("""
                    INSERT INTO extracoes
                        (coffee_id, data, metodo, gramas, moedor, clicks_moedor,
                         agua_alvo, tds, tempo_extracao, brew_ratio, ey, fluxo,
                         foto_caneca, classificacao, notas)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (cid, data_ext, metodo, gramas, moedor, clicks,
                      agua, tds, tempo,
                      m.get("ratio", 0), ey, m.get("fluxo", 0),
                      to_b64(foto_can) if foto_can else None,
                      class_e, notas_e))
                st.success("Extração registrada.")

    # ──────────────────────────────────────────────────────────────────
    # TAB 3 — MEUS CAFÉS
    # ──────────────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<p class="section-label">Biblioteca de Cafés</p>', unsafe_allow_html=True)

        cafes = fetch("""
            SELECT c.*,
                   COUNT(e.id)           AS total_ext,
                   AVG(e.ey)             AS avg_ey,
                   AVG(e.classificacao)  AS avg_nota
            FROM coffees c
            LEFT JOIN extracoes e ON e.coffee_id = c.id
            GROUP BY c.id
            ORDER BY c.data_cadastro DESC
        """)

        if not cafes:
            st.info("Nenhum café cadastrado ainda.")
        else:
            for c in cafes:
                nota_str = stars(c['classificacao'] or 0)
                header = f"{c['nome']}  ·  {c['torra']}  ·  {nota_str}"
                with st.expander(header):
                    ca, cb, cc = st.columns([1, 2.2, 1.4], gap="large")

                    with ca:
                        if c["foto_embalagem"]:
                            show_img(c["foto_embalagem"], width=150)
                        else:
                            st.markdown(
                                '<div style="width:150px;height:150px;background:#111;'
                                'border:1px solid #1E1E1E;border-radius:10px;display:flex;'
                                'align-items:center;justify-content:center;color:#333;font-size:28px;">☕</div>',
                                unsafe_allow_html=True
                            )

                    with cb:
                        tags_html = (
                            tag(c['tipo']) +
                            tag(c['torra']) +
                            tag(f"{c['tamanho_pacote']}g") +
                            (tag("Torra: " + c['data_torra'].strftime('%d/%m/%y'), accent=True)
                             if c['data_torra'] else "")
                        )
                        rows_html = (
                            info_row("Fazenda", c['fazenda'] or "—") +
                            info_row("Região",  c['regiao']  or "—") +
                            info_row("Cadastro", c['data_cadastro'].strftime('%d/%m/%y'))
                        )
                        notes_html = (
                            f'<div style="margin-top:10px;font-size:12px;color:#666;'
                            f'font-style:italic;">{c["notas"]}</div>'
                            if c["notas"] else ""
                        )
                        st.markdown(
                            f'<div>{tags_html}</div>'
                            f'<div style="margin-top:12px;">{rows_html}</div>'
                            f'{notes_html}',
                            unsafe_allow_html=True
                        )

                    with cc:
                        st.metric("Extrações",  int(c["total_ext"] or 0))
                        if c["avg_ey"]:
                            st.metric("EY Médio", f"{c['avg_ey']:.1f}%")
                        if c["avg_nota"]:
                            st.metric("Nota Média", stars(round(c["avg_nota"])))

                    st.markdown("")
                    if st.button("Remover café", key=f"del_c_{c['id']}"):
                        run("DELETE FROM coffees WHERE id=%s", (c["id"],))
                        st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # TAB 4 — HISTÓRICO
    # ──────────────────────────────────────────────────────────────────
    with tab4:
        st.markdown('<p class="section-label">Histórico de Extrações</p>', unsafe_allow_html=True)

        rows = fetch("""
            SELECT e.*, c.nome AS cafe_nome, c.torra
            FROM extracoes e
            JOIN coffees c ON c.id = e.coffee_id
            ORDER BY e.data DESC, e.created_at DESC
            LIMIT 200
        """)

        if not rows:
            st.info("Nenhuma extração registrada ainda.")
        else:
            for r in rows:
                nota_str = stars(r['classificacao'] or 0)
                header = f"{r['cafe_nome']}  ·  {r['metodo']}  ·  {r['data'].strftime('%d/%m/%y')}  ·  {nota_str}"
                with st.expander(header):
                    ra, rb, rc = st.columns([1, 2.2, 1.4], gap="large")

                    with ra:
                        if r["foto_caneca"]:
                            show_img(r["foto_caneca"], width=150)
                        else:
                            st.markdown(
                                '<div style="width:150px;height:150px;background:#111;'
                                'border:1px solid #1E1E1E;border-radius:10px;display:flex;'
                                'align-items:center;justify-content:center;color:#333;font-size:28px;">☕</div>',
                                unsafe_allow_html=True
                            )

                    with rb:
                        tags_html = tag(r['metodo'], accent=True) + tag(r['torra'])
                        rows_html = (
                            info_row("Dose",    f"{r['gramas']}g") +
                            info_row("Água",    f"{r['agua_alvo']}g") +
                            info_row("Tempo",   f"{r['tempo_extracao']}s") +
                            info_row("TDS",     f"{r['tds']}%" if r['tds'] else "—") +
                            (info_row("Moedor", f"{r['moedor']}  ·  {r['clicks_moedor']} clicks")
                             if r["moedor"] else "")
                        )
                        notes_html = (
                            f'<div style="margin-top:10px;font-size:12px;color:#666;'
                            f'font-style:italic;">{r["notas"]}</div>'
                            if r["notas"] else ""
                        )
                        st.markdown(
                            f'<div>{tags_html}</div>'
                            f'<div style="margin-top:12px;">{rows_html}</div>'
                            f'{notes_html}',
                            unsafe_allow_html=True
                        )

                    with rc:
                        if r["brew_ratio"]:
                            st.metric("Brew Ratio", f"1 : {r['brew_ratio']:.1f}")
                        if r["ey"]:
                            st.metric("EY", f"{r['ey']:.1f}%")
                        if r["fluxo"]:
                            st.metric("Fluxo", f"{r['fluxo']:.2f} g/s")

                    st.markdown("")
                    if st.button("Remover extração", key=f"del_e_{r['id']}"):
                        run("DELETE FROM extracoes WHERE id=%s", (r["id"],))
                        st.rerun()

if __name__ == "__main__":
    main()
