"""
Mateu Coffee - Premium Coffee Tracking Dashboard
Versao: 3.0 - Motor Barista, foto embalagem, avaliacao sensorial
"""
import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import base64
from datetime import date, datetime, timedelta
from auth import verificar_login, criar_usuario, obter_usuario_por_id
from database import (
    init_db,
    criar_cafe, listar_cafes, obter_cafe, atualizar_cafe, deletar_cafe,
    criar_extracao, listar_extractions, deletar_extracao,
    obter_estatisticas, salvar_motor_barista,
    obter_melhor_receita_por_metodo, obter_notas_por_metodo,
    obter_evolucao_notas, criar_receita_compartilhada,
    listar_receitas_compartilhadas
)

# ── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── DB Init ──────────────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = init_db()

# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --mc-bg: #0A0A0A;
    --mc-surface: #1A1A1A;
    --mc-surface-2: #252525;
    --mc-surface-3: #2F2F2F;
    --mc-border: #3A3A3A;
    --mc-border-strong: #4A4A4A;
    --mc-text: #E8E8E8;
    --mc-text-2: #B8B0A8;
    --mc-text-3: #6B6B6B;
    --mc-orange: #E8722E;
    --mc-orange-hover: #F08040;
    --mc-orange-soft: #2D1F18;
    --mc-orange-glow: rgba(232, 114, 46, 0.2);
}
body { background: var(--mc-bg) !important; color: var(--mc-text) !important; }
.main { background: var(--mc-bg) !important; }
.stApp { background: var(--mc-bg) !important; }

.mc-card {
    background: var(--mc-surface);
    border: 1px solid var(--mc-border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: all 150ms ease;
}
.mc-card:hover { border-color: var(--mc-orange); box-shadow: 0 0 16px var(--mc-orange-glow); }

.mc-stat {
    background: var(--mc-surface);
    border: 1px solid var(--mc-border);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    transition: all 150ms ease;
}
.mc-stat:hover { border-color: var(--mc-orange); background: var(--mc-surface-2); }
.mc-stat-value { font-size: 32px; font-weight: 700; color: var(--mc-orange); }
.mc-stat-label { font-size: 12px; color: var(--mc-text-2); text-transform: uppercase; }

.stButton > button {
    background: var(--mc-orange) !important;
    color: #0A0A0A !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    min-height: 48px !important;
    font-size: 16px !important;
    padding: 12px 20px !important;
    transition: all 150ms ease !important;
}
.stButton > button:hover {
    background: var(--mc-orange-hover) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(232, 114, 46, 0.3) !important;
}
.stTextInput input, .stNumberInput input, .stSelectbox select,
.stTextArea textarea, .stSlider input {
    background: var(--mc-surface) !important;
    color: var(--mc-text) !important;
    border: 1px solid var(--mc-border) !important;
    border-radius: 8px !important;
    min-height: 44px !important;
}
.stTextInput input:focus, .stNumberInput input:focus,
.stTextArea textarea:focus { border-color: var(--mc-orange) !important; }

.mc-logo-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
}
.mc-brand-title {
    font-size: 36px;
    font-weight: 800;
    color: var(--mc-orange);
    letter-spacing: 2px;
    margin-top: 16px;
    text-align: center;
}
.mc-brand-subtitle {
    font-size: 14px;
    color: var(--mc-text-2);
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 4px;
    text-align: center;
}
.motor-barista-box {
    background: linear-gradient(135deg, #1A1A1A 0%, #2D1F18 100%);
    border: 1px solid var(--mc-orange);
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    box-shadow: 0 0 20px var(--mc-orange-glow);
}
.estrela-label { font-size: 13px; color: var(--mc-text-2); margin-bottom: 4px; }
@media (max-width: 768px) {
    .stButton > button { min-height: 52px !important; font-size: 18px !important; }
    .mc-stat-value { font-size: 24px; }
}
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────
for k, v in [("user_id", None), ("email", None), ("page", "home"), ("show_tutorial", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────
def _logo_b64() -> str:
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "mateu_coffee_logo.png")
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _img_to_b64(uploaded) -> str:
    return base64.b64encode(uploaded.read()).decode()

def _motor_barista_previsao(gramas: float, agua: float, tempo: int, pressao: float, metodo: str) -> dict:
    """Calcula previsão do Motor Barista com base nos parâmetros."""
    ratio = agua / gramas if gramas > 0 else 2.0
    # Scores base em escala 1-5
    crema    = min(5, max(1, round(5 - abs(pressao - 9) * 0.4))) if pressao > 0 else 3
    corpo    = min(5, max(1, round(5 - (ratio - 2) * 0.5))) if metodo == "Espresso" else min(5, max(1, round(3 + (ratio - 15) * 0.1)))
    acidez   = min(5, max(1, round(3 + (tempo - 25) * 0.05))) if metodo == "Espresso" else min(5, max(1, round(3 - (tempo - 180) * 0.01)))
    amargor  = min(5, max(1, round(3 + (tempo - 25) * 0.06))) if metodo == "Espresso" else min(5, max(1, round(2 + (tempo - 120) * 0.01)))
    docura   = min(5, max(1, 6 - crema))
    volume   = min(5, max(1, round(agua / 15))) if metodo == "Espresso" else min(5, max(1, 3))
    return {"crema": crema, "corpo": corpo, "acidez": acidez,
            "amargor": amargor, "docura": docura, "volume_xicara": volume}

def _radar_chart(previsao: dict, avaliacao: dict = None):
    cats = ["Volume\nXícara", "Crema", "Corpo", "Acidez", "Amargor", "Doçura"]
    prev = [previsao["volume_xicara"], previsao["crema"], previsao["corpo"],
            previsao["acidez"], previsao["amargor"], previsao["docura"]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=prev + [prev[0]], theta=cats + [cats[0]],
        fill="toself", name="Previsão Motor",
        line=dict(color="#E8722E", width=2, dash="dash"),
        fillcolor="rgba(232,114,46,0.15)"
    ))
    if avaliacao:
        av = [avaliacao.get("volume_xicara", 0), avaliacao.get("crema", 0),
              avaliacao.get("corpo", 0), avaliacao.get("acidez", 0),
              avaliacao.get("amargor", 0), avaliacao.get("docura", 0)]
        if any(v > 0 for v in av):
            fig.add_trace(go.Scatterpolar(
                r=av + [av[0]], theta=cats + [cats[0]],
                fill="toself", name="Sua Avaliação",
                line=dict(color="#F5EDE8", width=2),
                fillcolor="rgba(245,237,232,0.1)"
            ))
    fig.update_layout(
        polar=dict(
            bgcolor="#1A1A1A",
            radialaxis=dict(visible=True, range=[0, 5], tickfont=dict(color="#6B6B6B"), gridcolor="#3A3A3A"),
            angularaxis=dict(tickfont=dict(color="#B8B0A8"), gridcolor="#3A3A3A"),
        ),
        showlegend=True,
        legend=dict(font=dict(color="#B8B0A8"), bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="#0A0A0A",
        plot_bgcolor="#0A0A0A",
        margin=dict(l=40, r=40, t=40, b=40),
        height=350,
    )
    return fig

# ── LOGIN PAGE ────────────────────────────────────────────────────────────
def page_login():
    logo_b64 = _logo_b64()
    col_brand, col_forms = st.columns([1, 1])

    with col_brand:
        if logo_b64:
            st.markdown(f"""
            <div class='mc-logo-container'>
                <img src='data:image/png;base64,{logo_b64}' width='200' style='border-radius:12px;'>
                <div class='mc-brand-title'>MATEU COFFEE</div>
                <div class='mc-brand-subtitle'>Rastreamento Premium</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<div class='mc-brand-title'>MATEU COFFEE</div>", unsafe_allow_html=True)

    with col_forms:
        tab_login, tab_reg = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            email_login = st.text_input("Email", key="login_email")
            senha_login = st.text_input("Senha", type="password", key="login_senha")
            if st.button("Entrar", use_container_width=True, key="btn_entrar"):
                if email_login and senha_login:
                    with st.spinner("Verificando..."):
                        sucesso, user_id, msg = verificar_login(email_login, senha_login)
                    if sucesso:
                        st.session_state.user_id = user_id
                        st.session_state.email = email_login
                        st.session_state.show_tutorial = False
                        st.session_state.page = "home"
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Preencha email e senha")

        with tab_reg:
            email_reg = st.text_input("Email", key="reg_email")
            nome_reg = st.text_input("Nome", key="reg_nome")
            senha_reg = st.text_input("Senha", type="password", key="reg_senha")
            senha_conf = st.text_input("Confirmar Senha", type="password", key="reg_conf")
            if st.button("Criar Conta", use_container_width=True, key="btn_criar_conta"):
                if not email_reg or not senha_reg:
                    st.error("Preencha email e senha")
                elif senha_reg != senha_conf:
                    st.error("Senhas nao conferem")
                else:
                    with st.spinner("Criando conta..."):
                        sucesso, msg = criar_usuario(email_reg, senha_reg, nome_reg)
                    if sucesso:
                        st.success("Conta criada! Faca login.")
                    else:
                        st.error(msg)

# ── HOME PAGE ─────────────────────────────────────────────────────────────
def page_home():
    usuario = obter_usuario_por_id(st.session_state.user_id)
    nome_exibir = (usuario.get("nome") or usuario.get("email", "")) if usuario else st.session_state.email

    col1, col2, col3 = st.columns([1, 1, 0.15])
    with col1:
        logo_b64 = _logo_b64()
        if logo_b64:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:12px;'>
                <img src='data:image/png;base64,{logo_b64}' width='48' style='border-radius:8px;'>
                <span style='font-size:22px;font-weight:800;color:#E8722E;'>MATEU COFFEE</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<p style='color:#B8B0A8;margin-top:4px;'>Olá, {nome_exibir}</p>", unsafe_allow_html=True)
    with col3:
        if st.button("Sair", use_container_width=True, key="btn_sair"):
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.page = "login"
            st.rerun()

    # Estatísticas
    stats = obter_estatisticas(st.session_state.user_id)
    col1, col2, col3, col4 = st.columns(4)
    for col, val, label in [
        (col1, stats["total_cafes"], "Cafes Cadastrados"),
        (col2, stats["total_extractions"], "Extracoes"),
        (col3, f"{stats['consumo_hoje']:.0f}g", "Consumo Hoje"),
        (col4, f"{stats['consumo_semana']:.0f}g", "Esta Semana"),
    ]:
        with col:
            st.markdown(f"""
            <div class='mc-stat'>
                <div class='mc-stat-value'>{val}</div>
                <div class='mc-stat-label'>{label}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Meus Cafes", "Registrar Extracao", "Motor Barista", "Analises", "Comunidade"
    ])

    # ── ABA 1: CAFES ──────────────────────────────────────────────────────
    with tab1:
        col_list, col_form = st.columns([0.65, 0.35])

        with col_list:
            st.subheader("Cafes Cadastrados")
            cafes = listar_cafes(st.session_state.user_id)
            if cafes:
                for cafe in cafes:
                    with st.container(border=True):
                        ca, cb, cc = st.columns([0.55, 0.25, 0.20])
                        with ca:
                            st.markdown(f"**{cafe['nome']}**")
                            st.caption(f"Origem: {cafe.get('origem') or 'N/A'} | Tipo: {cafe.get('tipo') or 'N/A'} | Torra: {cafe.get('torrefacao') or 'N/A'}")
                            if cafe.get("local_compra"):
                                st.caption(f"Local: {cafe['local_compra']}")
                            if cafe.get("notas"):
                                with st.expander("Notas"):
                                    st.write(cafe["notas"])
                            # foto
                            if cafe.get("foto_embalagem"):
                                try:
                                    img_data = base64.b64decode(cafe["foto_embalagem"])
                                    st.image(img_data, width=120)
                                except Exception:
                                    pass
                        with cb:
                            preco_exib = cafe.get("preco_kg") or 0
                            st.caption(f"R$ {preco_exib:.2f}/kg" if preco_exib else "Sem preco")
                        with cc:
                            if st.button("Deletar", key=f"del_cafe_{cafe['id']}", use_container_width=True):
                                deletar_cafe(cafe["id"], st.session_state.user_id)
                                st.rerun()
            else:
                st.info("Nenhum cafe cadastrado.")

        with col_form:
            st.subheader("Novo Cafe")
            nome = st.text_input("Nome do Cafe *", key="cafe_nome")
            local_compra = st.text_input("Local de Compra", key="cafe_local")
            origem = st.text_input("Origem / Fazenda", key="cafe_origem")
            tipo = st.selectbox("Tipo", ["Graos", "Moido", "Capsula", "Outro"], key="cafe_tipo")
            torrefacao = st.selectbox("Torra", ["Clara", "Media", "Escura"], key="cafe_torrefacao")
            preco = st.number_input("Preco pago (R$)", min_value=0.0, step=0.5, key="cafe_preco")
            notas = st.text_area("Notas / Descricao", height=80, key="cafe_notas")
            foto = st.file_uploader("Foto da Embalagem", type=["jpg", "jpeg", "png"], key="cafe_foto")

            if st.button("Adicionar Cafe", use_container_width=True, key="btn_add_cafe"):
                if nome:
                    foto_b64 = _img_to_b64(foto) if foto else None
                    sucesso, msg = criar_cafe(
                        st.session_state.user_id, nome, origem, tipo, torrefacao,
                        preco, notas, local_compra, foto_b64
                    )
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Nome do cafe e obrigatorio")

    # ── ABA 2: EXTRACOES ──────────────────────────────────────────────────
    with tab2:
        col_form, col_list = st.columns([0.5, 0.5])

        with col_form:
            st.subheader("Registrar Extracao")
            cafes = listar_cafes(st.session_state.user_id)
            cafe_opts = {c["nome"]: c["id"] for c in cafes}

            cafe_selecionado = st.selectbox("Cafe", list(cafe_opts.keys()) if cafe_opts else ["Nenhum cafe"], key="extr_cafe")
            data_str = st.text_input("Data (DD/MM/AAAA)", value=date.today().strftime("%d/%m/%Y"), key="extr_data")
            num_xicaras = st.selectbox("Numero de Xicaras", [1, 2], key="extr_xicaras")
            metodo = st.selectbox("Metodo", ["Espresso", "V60", "Prensa Francesa", "Moka", "Coado", "Outro"], key="extr_metodo")
            gramas = st.number_input("Dose de Cafe (g)", min_value=0.0, step=0.5, key="extr_gramas")
            gramas_agua = st.number_input("Agua (ml/g)", min_value=0.0, step=1.0, key="extr_agua")
            tempo = st.number_input("Tempo de Extracao (segundos)", min_value=0, step=1, key="extr_tempo")
            temp = st.number_input("Temperatura (C)", min_value=0.0, step=0.5, key="extr_temp")
            pressao = st.number_input("Pressao (bar)", min_value=0.0, step=0.5, key="extr_pressao")
            notas_extr = st.text_area("Notas", height=80, key="extr_notas")

            if st.button("Registrar Extracao", use_container_width=True, key="btn_reg_extr"):
                if cafe_opts and gramas > 0:
                    try:
                        data_extr = datetime.strptime(data_str, "%d/%m/%Y").date()
                    except ValueError:
                        st.error("Data invalida. Use DD/MM/AAAA")
                        st.stop()
                    cafe_id = cafe_opts[cafe_selecionado]
                    sucesso, msg = criar_extracao(
                        st.session_state.user_id, cafe_id, data_extr, gramas,
                        gramas_agua, tempo, temp, pressao, metodo, notas_extr, num_xicaras
                    )
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Selecione um cafe e informe a dose")

        with col_list:
            st.subheader("Ultimas Extracoes")
            extractions = listar_extractions(st.session_state.user_id, dias=90)
            if extractions:
                for ext in extractions[:10]:
                    with st.container(border=True):
                        d = ext["data"]
                        data_fmt = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
                        xic = ext.get("num_xicaras") or 1
                        st.caption(f"{data_fmt} | {ext.get('cafe_nome','N/A')} | {xic} xicara(s)")
                        gramas_exib = ext.get("gramas_cafe") or 0
                        st.markdown(f"**{gramas_exib:.1f}g** cafe | {ext.get('metodo') or 'N/A'}")
                        if ext.get("tempo_segundos"):
                            temp_val = ext.get("temperatura") or 0
                            st.caption(f"Tempo: {ext['tempo_segundos']}s | Temp: {temp_val:.1f}C")
                        if st.button("Deletar", key=f"del_ext_{ext['id']}", use_container_width=True):
                            deletar_extracao(ext["id"], st.session_state.user_id)
                            st.rerun()
            else:
                st.info("Nenhuma extracao registrada")

    # ── ABA 3: MOTOR BARISTA ─────────────────────────────────────────────
    with tab3:
        st.subheader("Motor Barista")
        st.caption("Selecione uma extracao para ver a previsao e registrar sua avaliacao sensorial")

        extractions = listar_extractions(st.session_state.user_id, dias=180)
        if not extractions:
            st.info("Registre extracoes para usar o Motor Barista.")
        else:
            opcoes = {f"{(ext['data'].strftime('%d/%m/%Y') if hasattr(ext['data'],'strftime') else str(ext['data']))} — {ext.get('cafe_nome','?')} ({ext['metodo']})": ext for ext in extractions[:20]}
            selecionada_label = st.selectbox("Extracao", list(opcoes.keys()), key="mb_extr_sel")
            ext = opcoes[selecionada_label]

            # Previsão do motor — protege NULLs do banco
            previsao = _motor_barista_previsao(
                gramas=float(ext.get("gramas_cafe") or 0),
                agua=float(ext.get("gramas_agua") or 0),
                tempo=int(ext.get("tempo_segundos") or 0),
                pressao=float(ext.get("pressao") or 0),
                metodo=ext.get("metodo") or "Espresso"
            )

            col_radar, col_aval = st.columns([0.55, 0.45])

            with col_radar:
                avaliacao_atual = {
                    "volume_xicara": ext.get("volume_xicara") or 0,
                    "crema": ext.get("crema") or 0,
                    "corpo": ext.get("corpo") or 0,
                    "acidez": ext.get("acidez") or 0,
                    "amargor": ext.get("amargor") or 0,
                    "docura": ext.get("docura") or 0,
                }
                st.plotly_chart(_radar_chart(previsao, avaliacao_atual), use_container_width=True)
                _gc = float(ext.get('gramas_cafe') or 0)
                _ga = float(ext.get('gramas_agua') or 0)
                _ts = int(ext.get('tempo_segundos') or 0)
                _pr = float(ext.get('pressao') or 0)
                st.markdown(f"""
                <div class='motor-barista-box'>
                    <b style='color:#E8722E;'>Previsao do Motor Barista</b><br>
                    Dose: {_gc:.1f}g | Agua: {_ga:.0f}ml
                    | Tempo: {_ts}s | Pressao: {_pr:.1f}bar
                    | Metodo: {ext.get('metodo') or '—'}<br>
                    <small style='color:#6B6B6B;'>Resultado esperado baseado nos parametros da extracao</small>
                </div>
                """, unsafe_allow_html=True)

            with col_aval:
                st.markdown("**Sua Avaliacao Sensorial**")
                vol  = st.slider("Volume na Xicara", 1, 5, int(ext.get("volume_xicara") or previsao["volume_xicara"]), key=f"mb_vol_{ext['id']}")
                cre  = st.slider("Crema", 1, 5, int(ext.get("crema") or previsao["crema"]), key=f"mb_cre_{ext['id']}")
                cor  = st.slider("Corpo", 1, 5, int(ext.get("corpo") or previsao["corpo"]), key=f"mb_cor_{ext['id']}")
                aci  = st.slider("Acidez", 1, 5, int(ext.get("acidez") or previsao["acidez"]), key=f"mb_aci_{ext['id']}")
                ama  = st.slider("Amargor", 1, 5, int(ext.get("amargor") or previsao["amargor"]), key=f"mb_ama_{ext['id']}")
                doc  = st.slider("Docura", 1, 5, int(ext.get("docura") or previsao["docura"]), key=f"mb_doc_{ext['id']}")
                nf   = st.slider("Nota Final", 1, 5, int(ext.get("nota_final") or 3), key=f"mb_nf_{ext['id']}")
                obs  = st.text_area("Observacoes", value=ext.get("sabor_notas") or "", key=f"mb_obs_{ext['id']}", height=80)

                if st.button("Salvar Avaliacao", use_container_width=True, key=f"mb_save_{ext['id']}"):
                    sucesso, msg = salvar_motor_barista(
                        ext["id"], st.session_state.user_id,
                        vol, cre, cor, aci, ama, doc, nf, obs
                    )
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # ── ABA 4: ANALISES ──────────────────────────────────────────────────
    with tab4:
        st.subheader("Analises de Desempenho")
        extractions = listar_extractions(st.session_state.user_id, dias=90)

        notas_por_metodo = obter_notas_por_metodo(st.session_state.user_id)
        if notas_por_metodo:
            df = pd.DataFrame(notas_por_metodo)
            fig = go.Figure(data=[go.Bar(x=df["metodo"], y=df["nota_media"], marker_color="#E8722E")])
            fig.update_layout(title="Nota Media por Metodo", template="plotly_dark",
                              paper_bgcolor="#0A0A0A", plot_bgcolor="#1A1A1A")
            st.plotly_chart(fig, use_container_width=True)

        evolucao = obter_evolucao_notas(st.session_state.user_id, dias=90)
        if evolucao:
            df2 = pd.DataFrame(evolucao)
            fig2 = go.Figure(data=[go.Scatter(x=df2["data"], y=df2["nota_geral"],
                                              mode="lines+markers", marker_color="#E8722E")])
            fig2.update_layout(title="Evolucao de Notas", template="plotly_dark",
                               paper_bgcolor="#0A0A0A", plot_bgcolor="#1A1A1A")
            st.plotly_chart(fig2, use_container_width=True)

        if not notas_por_metodo and not evolucao:
            st.info("Registre extracoes e avaliações no Motor Barista para ver analises.")

    # ── ABA 5: COMUNIDADE ────────────────────────────────────────────────
    with tab5:
        col1, col2 = st.columns([0.5, 0.5])

        with col1:
            st.subheader("Compartilhar Receita")
            cafe_comp = st.text_input("Nome do Cafe", key="comp_cafe_nome")
            metodo_comp = st.selectbox("Metodo", ["Espresso", "V60", "Prensa Francesa", "Moka", "Coado", "Outro"], key="comp_metodo")
            dose_comp = st.number_input("Dose (g)", min_value=0.0, step=0.5, key="comp_dose")
            agua_comp = st.number_input("Agua (ml)", min_value=0.0, step=1.0, key="comp_agua")
            nota_comp = st.slider("Sua Nota", 1, 10, 7, key="comp_nota")
            if st.button("Compartilhar Receita", use_container_width=True, key="btn_comp"):
                if cafe_comp and dose_comp > 0:
                    sucesso, msg = criar_receita_compartilhada(
                        st.session_state.user_id, cafe_comp, metodo_comp, dose_comp, agua_comp, nota_comp
                    )
                    if sucesso:
                        st.success("Receita compartilhada!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Preencha cafe e dose")

        with col2:
            st.subheader("Receitas da Comunidade")
            receitas = listar_receitas_compartilhadas(limite=20)
            if receitas:
                for r in receitas:
                    st.markdown(f"""
                    <div class='mc-card'>
                        <strong>{r['cafe_nome']}</strong><br>
                        {r['metodo']} | {r['dose_gramas']:.1f}g + {r['agua_ml']:.0f}ml<br>
                        <span style='color:#E8722E;'>Nota: {r['nota']}/10</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma receita compartilhada ainda")

# ── MAIN ─────────────────────────────────────────────────────────────────
if st.session_state.user_id:
    page_home()
else:
    page_login()
