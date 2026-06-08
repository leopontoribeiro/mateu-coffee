"""
Mateu Coffee - Dashboard de produção com autenticação real e CRUD funcional.
"""
import streamlit as st
import psycopg2
from datetime import date, datetime, timedelta
from auth import verificar_login, criar_usuario, obter_usuario_por_id
from database import (
    criar_cafe, listar_cafes, obter_cafe, atualizar_cafe, deletar_cafe,
    criar_extracao, listar_extractions, deletar_extracao,
    obter_estatisticas
)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────
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
}

.mc-stat {
    background: var(--mc-surface);
    border: 1px solid var(--mc-border);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}

.mc-stat-value { font-size: 32px; font-weight: 700; color: var(--mc-orange); }
.mc-stat-label { font-size: 12px; color: var(--mc-text-2); text-transform: uppercase; }

.stButton > button {
    background: var(--mc-orange) !important;
    color: #0A0A0A !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

.stButton > button:hover {
    background: var(--mc-orange-hover) !important;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox select,
.stTextArea textarea {
    background: var(--mc-surface) !important;
    color: var(--mc-text) !important;
    border: 1px solid var(--mc-border) !important;
    border-radius: 8px !important;
}

.stDataFrame { background: var(--mc-surface) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "email" not in st.session_state:
    st.session_state.email = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ── LOGIN ──────────────────────────────────────────────────────────────
def page_login():
    """Página de login e registro."""
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<h2 style='text-align: center; color: var(--mc-orange); margin-bottom: 30px;'>☕ Mateu Coffee</h2>", unsafe_allow_html=True)

        st.subheader("Login")
        email_login = st.text_input("Email", key="login_email")
        senha_login = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar", use_container_width=True):
            if email_login and senha_login:
                sucesso, user_id, msg = verificar_login(email_login, senha_login)
                if sucesso:
                    st.session_state.user_id = user_id
                    st.session_state.email = email_login
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Preencha email e senha")

    with col2:
        st.subheader("Criar Conta")
        email_reg = st.text_input("Email", key="reg_email")
        nome_reg = st.text_input("Nome", key="reg_nome")
        senha_reg = st.text_input("Senha", type="password", key="reg_senha")
        senha_conf = st.text_input("Confirmar Senha", type="password", key="reg_conf")

        if st.button("Criar Conta", use_container_width=True):
            if not email_reg or not senha_reg:
                st.error("Preencha email e senha")
            elif senha_reg != senha_conf:
                st.error("Senhas não conferem")
            else:
                sucesso, msg = criar_usuario(email_reg, senha_reg, nome_reg)
                if sucesso:
                    st.success("Conta criada! Faça login para continuar.")
                else:
                    st.error(msg)

# ── HOME ───────────────────────────────────────────────────────────────
def page_home():
    """Home com estatísticas reais."""
    usuario = obter_usuario_por_id(st.session_state.user_id)

    # Header
    col1, col2 = st.columns([1, 0.2])
    with col1:
        st.markdown(f"<h1 style='color: var(--mc-orange);'>☕ Olá, {usuario['nome'] or usuario['email']}</h1>", unsafe_allow_html=True)
    with col2:
        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.page = "login"
            st.rerun()

    # Estatísticas
    stats = obter_estatisticas(st.session_state.user_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['total_cafes']}</div>
            <div class='mc-stat-label'>Cafés Cadastrados</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['total_extractions']}</div>
            <div class='mc-stat-label'>Extrações</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['consumo_hoje']:.0f}g</div>
            <div class='mc-stat-label'>Consumo Hoje</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['consumo_semana']:.0f}g</div>
            <div class='mc-stat-label'>Esta Semana</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Abas
    tab1, tab2, tab3 = st.tabs(["📦 Cafés", "☕ Extrações", "📊 Histórico"])

    # ── ABA 1: CAFÉS ──
    with tab1:
        col1, col2 = st.columns([0.7, 0.3])

        with col1:
            st.subheader("Cafés Cadastrados")
            cafes = listar_cafes(st.session_state.user_id)

            if cafes:
                for cafe in cafes:
                    with st.container(border=True):
                        col_a, col_b, col_c = st.columns([0.6, 0.2, 0.2])
                        with col_a:
                            st.markdown(f"**{cafe['nome']}**")
                            st.caption(f"Origem: {cafe['origem'] or 'N/A'} | Tipo: {cafe['tipo'] or 'N/A'}")
                            if cafe['notas']:
                                st.caption(f"Notas: {cafe['notas']}")
                        with col_b:
                            st.caption(f"R$ {cafe['preco_kg']:.2f}/kg" if cafe['preco_kg'] else "Sem preço")
                        with col_c:
                            if st.button("Deletar", key=f"del_cafe_{cafe['id']}", use_container_width=True):
                                deletar_cafe(cafe['id'], st.session_state.user_id)
                                st.rerun()
            else:
                st.info("Nenhum café cadastrado ainda")

        with col2:
            st.subheader("Novo Café")
            nome = st.text_input("Nome do Café")
            origem = st.text_input("Origem")
            tipo = st.selectbox("Tipo", ["Espresso", "Filtrado", "Coado", "Outro"])
            torrefacao = st.selectbox("Torrefação", ["Leve", "Média", "Escura"])
            preco = st.number_input("Preço/kg", min_value=0.0, step=1.0)
            notas = st.text_area("Notas", height=80)

            if st.button("Adicionar Café", use_container_width=True):
                if nome:
                    sucesso, msg = criar_cafe(st.session_state.user_id, nome, origem, tipo, torrefacao, preco, notas)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Nome do café é obrigatório")

    # ── ABA 2: EXTRAÇÕES ──
    with tab2:
        col1, col2 = st.columns([0.6, 0.4])

        with col1:
            st.subheader("Registrar Extração")
            cafes = listar_cafes(st.session_state.user_id)
            cafe_opts = {c['nome']: c['id'] for c in cafes}

            cafe_nome = st.selectbox("Café", list(cafe_opts.keys()) if cafe_opts else ["Nenhum café"])
            data_extr = st.date_input("Data", value=date.today())
            gramas = st.number_input("Gramas de Café", min_value=0.0, step=0.1)
            gramas_agua = st.number_input("Gramas de Água", min_value=0.0, step=0.1)
            tempo = st.number_input("Tempo (segundos)", min_value=0, step=1)
            temp = st.number_input("Temperatura (°C)", min_value=0.0, step=0.1)
            pressao = st.number_input("Pressão (bar)", min_value=0.0, step=0.1)
            metodo = st.selectbox("Método", ["Espresso", "V60", "Prensa Francesa", "Moka", "Outro"])
            notas_extr = st.text_area("Notas", height=80)

            if st.button("Registrar Extração", use_container_width=True):
                if cafe_opts and gramas > 0:
                    cafe_id = cafe_opts[cafe_nome]
                    sucesso, msg = criar_extracao(
                        st.session_state.user_id, cafe_id, data_extr, gramas,
                        gramas_agua, tempo, temp, pressao, metodo, notas_extr
                    )
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Selecione um café e gramas")

        with col2:
            st.subheader("Últimas Extrações")
            extractions = listar_extractions(st.session_state.user_id, dias=30)

            if extractions:
                for ext in extractions[:10]:
                    with st.container(border=True):
                        st.caption(f"{ext['data']} | {ext.get('cafe_nome', 'N/A')}")
                        st.markdown(f"☕ **{ext['gramas_cafe']:.1f}g** | {ext['metodo'] or 'N/A'}")
                        if ext.get('tempo_segundos'):
                            st.caption(f"⏱ {ext['tempo_segundos']}s | {ext.get('temperatura', 0):.1f}°C")
                        if st.button("Deletar", key=f"del_ext_{ext['id']}", use_container_width=True):
                            deletar_extracao(ext['id'], st.session_state.user_id)
                            st.rerun()
            else:
                st.info("Nenhuma extração registrada")

    # ── ABA 3: HISTÓRICO ──
    with tab3:
        st.subheader("Histórico de Extrações")
        dias_filtro = st.slider("Últimos (dias)", 7, 365, 30)
        extractions = listar_extractions(st.session_state.user_id, dias=dias_filtro)

        if extractions:
            df_data = []
            for ext in extractions:
                df_data.append({
                    "Data": ext['data'],
                    "Café": ext.get('cafe_nome', 'N/A'),
                    "Gramas": f"{ext['gramas_cafe']:.1f}g",
                    "Método": ext.get('metodo', 'N/A'),
                    "Tempo": f"{ext.get('tempo_segundos', 0)}s" if ext.get('tempo_segundos') else "-",
                    "Temp": f"{ext.get('temperatura', 0):.1f}°C" if ext.get('temperatura') else "-",
                })

            import pandas as pd
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.metric("Total Consumido", f"{sum(e['gramas_cafe'] for e in extractions):.0f}g")
            st.metric("Média por Extração", f"{sum(e['gramas_cafe'] for e in extractions) / len(extractions):.1f}g")
        else:
            st.info(f"Nenhuma extração nos últimos {dias_filtro} dias")

# ── MAIN ───────────────────────────────────────────────────────────────
if st.session_state.user_id:
    page_home()
else:
    page_login()
