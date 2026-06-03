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
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    h1, h2, h3 { font-family: monospace; font-weight: 700; color: #F3F4F6; }
    .stMetric { background-color: #1F2937; padding: 12px; border-radius: 8px; border: 1px solid #374151; }
    div[data-testid="stMetricValue"] { font-size: 18pt; font-family: monospace; color: #10B981; }
</style>
""", unsafe_allow_html=True)

# ======================================================================
# DATABASE
# ======================================================================
@st.cache_resource
def get_conn():
    s = st.secrets["connections"]["postgresql"]
    return psycopg2.connect(
        host=s["host"], port=s["port"], dbname=s["database"],
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
            f'style="border-radius:8px;margin-top:4px;">',
            unsafe_allow_html=True
        )

def stars(n):
    n = int(n or 0)
    return "⭐" * n + "☆" * (5 - n)

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
                out["status"] = "Subextraído (Under)"
                out["delta_color"] = "inverse"
            elif ey <= 22.0:
                out["status"] = "Ideal ✓ Sweet Spot"
                out["delta_color"] = "off"
            else:
                out["status"] = "Superextraído (Over)"
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
        name='Target', line_color='#4B5563', opacity=0.5))
    fig.add_trace(go.Scatterpolar(
        r=profile, theta=attrs, fill='toself',
        name='Atual', line_color='#10B981'))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=True, height=260,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF', size=11),
    )
    return fig

# ======================================================================
# MAIN
# ======================================================================
def main():
    init_db()

    st.title("☕ MATEU COFFEE PRODUCTION")
    st.caption("Cadastro de Cafés · Controle de Extração · Histórico | Railway Pro")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Novo Café",
        "☕ Nova Extração",
        "📋 Meus Cafés",
        "📊 Histórico",
    ])

    # ──────────────────────────────────────────────────────────────────
    # TAB 1 — CADASTRAR CAFÉ
    # ──────────────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Cadastrar Novo Café")

        c1, c2 = st.columns(2)

        with c1:
            data_cad  = st.date_input("Data de Cadastro", value=date.today())
            nome      = st.text_input("Nome do Café *", placeholder="Ex: Ethiopian Yirgacheffe")
            fazenda   = st.text_input("Fazenda", placeholder="Ex: Fazenda Santa Inês")
            regiao    = st.text_input("Região", placeholder="Ex: Sul de Minas / Etiópia")
            data_tort = st.date_input("Data da Torra", value=None)
            tamanho   = st.radio("Pacote", [250, 500, 1000], horizontal=True, format_func=lambda x: f"{x}g")

        with c2:
            tipo      = st.radio("Forma", ["Grãos", "Moído"], horizontal=True)
            torra     = st.radio("Torra", ["Clara", "Média", "Escura"], horizontal=True)
            notas     = st.text_area("Notas de Sabor / Torra",
                                     placeholder="Ex: Blueberry, chocolate, floral...", height=100)
            class_c   = st.select_slider("Classificação",
                                         options=[1, 2, 3, 4, 5], format_func=stars, value=3)
            st.markdown("**Foto da Embalagem**")
            foto_emb  = st.file_uploader("Embalagem", type=["jpg","jpeg","png"],
                                         label_visibility="collapsed", key="foto_emb")
            if foto_emb:
                show_img(to_b64(foto_emb))

        st.divider()
        if st.button("✅ Salvar Café", type="primary", use_container_width=True):
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
                st.success(f"☕ **{nome}** cadastrado com sucesso!")
                st.balloons()

    # ──────────────────────────────────────────────────────────────────
    # TAB 2 — NOVA EXTRAÇÃO
    # ──────────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Registrar Extração")

        cafes = fetch("SELECT id, nome, torra FROM coffees ORDER BY nome")
        if not cafes:
            st.info("Cadastre um café primeiro na aba **📦 Novo Café**.")
        else:
            cafe_map = {f"{c['nome']} ({c['torra']})": c['id'] for c in cafes}
            sel      = st.selectbox("Café Utilizado *", list(cafe_map.keys()))
            cid      = cafe_map[sel]

            metodo   = st.selectbox("Método", METODOS)

            st.markdown("---")
            c1, c2 = st.columns(2)

            with c1:
                gramas = st.number_input("Pó de Café (g)",        5.0,  50.0,  18.0, 0.1,  help="Precisão de balança")
                agua   = st.number_input("Água Alvo (g)",          50.0, 1000.0,300.0, 5.0)
                tds    = st.number_input("TDS Medido (%)",         0.0,  5.0,   0.0,  0.01, help="Deixe 0 se não usar refratômetro")
                tempo  = st.number_input("Tempo de Extração (s)",  1,    600,   150,  1)

            with c2:
                moedor    = st.text_input("Moedor Utilizado", placeholder="Ex: Comandante C40")
                clicks    = st.number_input("Clicks do Moedor", 0, 200, 0, 1)
                data_ext  = st.date_input("Data", value=date.today(), key="data_ext")
                class_e   = st.select_slider("Classificação da Extração",
                                             options=[1,2,3,4,5], format_func=stars, value=3)
                notas_e   = st.text_area("Notas", placeholder="Impressões...", height=80)

            m     = Engine.calc(gramas, agua, tds if tds > 0 else None, tempo)
            ey    = m.get("ey", 0.0)

            st.markdown("---")
            st.subheader("Análise em Tempo Real")

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Brew Ratio",       m.get("ratio_text", "---"))
            mc2.metric("Extraction Yield", f"{ey:.2f}%" if ey > 0 else "---",
                       delta=m.get("status") if ey > 0 else None,
                       delta_color=m.get("delta_color", "off"))
            mc3.metric("Fluxo Médio",      f"{m.get('fluxo', 0):.2f} g/s")
            mc4.metric("Status",           m.get("status", "—"))

            col_r, col_p = st.columns([1.5, 1])
            with col_r:
                st.plotly_chart(radar(sensory(ey)), use_container_width=True,
                                config={'displayModeBar': False})
            with col_p:
                st.markdown("**Foto da Caneca**")
                foto_can = st.file_uploader("Caneca", type=["jpg","jpeg","png"],
                                            label_visibility="collapsed", key="foto_can")
                if foto_can:
                    show_img(to_b64(foto_can), width=200)

            st.divider()
            if st.button("✅ Salvar Extração", type="primary", use_container_width=True):
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
                st.success("Extração registrada!")

    # ──────────────────────────────────────────────────────────────────
    # TAB 3 — MEUS CAFÉS
    # ──────────────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Meus Cafés")

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
            st.info("Nenhum café cadastrado ainda. Use a aba **📦 Novo Café**.")
        else:
            for c in cafes:
                label = (f"☕ {c['nome']}  |  Torra: {c['torra']}  |  "
                         f"{stars(c['classificacao'] or 0)}  |  "
                         f"{c['data_cadastro'].strftime('%d/%m/%y')}")
                with st.expander(label):
                    ca, cb, cc = st.columns([1, 2, 1.5])

                    with ca:
                        show_img(c["foto_embalagem"], width=155) if c["foto_embalagem"] \
                            else st.caption("Sem foto")

                    with cb:
                        st.markdown(f"**Fazenda:** {c['fazenda'] or '—'}")
                        st.markdown(f"**Região:** {c['regiao'] or '—'}")
                        st.markdown(f"**Tipo:** {c['tipo']}  |  **Pacote:** {c['tamanho_pacote']}g")
                        st.markdown(f"**Torra:** {c['torra']}  |  "
                                    f"**Data Torra:** {c['data_torra'].strftime('%d/%m/%y') if c['data_torra'] else '—'}")
                        if c["notas"]:
                            st.caption(f"📝 {c['notas']}")

                    with cc:
                        st.metric("Extrações",  int(c["total_ext"] or 0))
                        if c["avg_ey"]:
                            st.metric("EY Médio", f"{c['avg_ey']:.1f}%")
                        if c["avg_nota"]:
                            st.metric("Nota Média", stars(round(c["avg_nota"])))

                    if st.button("🗑️ Remover café", key=f"del_c_{c['id']}"):
                        run("DELETE FROM coffees WHERE id=%s", (c["id"],))
                        st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # TAB 4 — HISTÓRICO
    # ──────────────────────────────────────────────────────────────────
    with tab4:
        st.subheader("Histórico de Extrações")

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
                label = (f"☕ {r['cafe_nome']}  |  {r['metodo']}  |  "
                         f"{r['data'].strftime('%d/%m/%y')}  |  {stars(r['classificacao'] or 0)}")
                with st.expander(label):
                    ra, rb, rc = st.columns([1, 2, 1.5])

                    with ra:
                        show_img(r["foto_caneca"], width=155) if r["foto_caneca"] \
                            else st.caption("Sem foto")

                    with rb:
                        st.markdown(f"**Método:** {r['metodo']}")
                        st.markdown(f"**Dose:** {r['gramas']}g  |  **Água:** {r['agua_alvo']}g")
                        if r["moedor"]:
                            st.markdown(f"**Moedor:** {r['moedor']}  |  **Clicks:** {r['clicks_moedor']}")
                        st.markdown(f"**Tempo:** {r['tempo_extracao']}s  |  "
                                    f"**TDS:** {r['tds'] or '—'}%")
                        if r["notas"]:
                            st.caption(f"📝 {r['notas']}")

                    with rc:
                        if r["brew_ratio"]:
                            st.metric("Brew Ratio", f"1:{r['brew_ratio']:.1f}")
                        if r["ey"]:
                            st.metric("EY", f"{r['ey']:.1f}%")
                        if r["fluxo"]:
                            st.metric("Fluxo", f"{r['fluxo']:.2f} g/s")

                    if st.button("🗑️ Remover extração", key=f"del_e_{r['id']}"):
                        run("DELETE FROM extracoes WHERE id=%s", (r["id"],))
                        st.rerun()

if __name__ == "__main__":
    main()
