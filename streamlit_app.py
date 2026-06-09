"""
Mateu Coffee - Premium Coffee Tracking Dashboard
Versao: 2.0 - Com analise sensorial, comunidade e recomendacoes
"""
import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from auth import verificar_login, criar_usuario, obter_usuario_por_id
from database import (
    criar_cafe, listar_cafes, obter_cafe, atualizar_cafe, deletar_cafe,
    criar_extracao, listar_extractions, deletar_extracao,
    obter_estatisticas, atualizar_analise_sensorial,
    obter_melhor_receita_por_metodo, obter_notas_por_metodo,
    obter_evolucao_notas, criar_receita_compartilhada,
    listar_receitas_compartilhadas
)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mateu Coffee",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS AVANCADO ────────────────────────────────────────────────────────
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

.mc-card:hover {
    border-color: var(--mc-orange);
    box-shadow: 0 0 16px var(--mc-orange-glow);
}

.mc-stat {
    background: var(--mc-surface);
    border: 1px solid var(--mc-border);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    transition: all 150ms ease;
}

.mc-stat:hover {
    border-color: var(--mc-orange);
    background: var(--mc-surface-2);
}

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

.stTextInput input,
.stNumberInput input,
.stSelectbox select,
.stTextArea textarea,
.stSlider input {
    background: var(--mc-surface) !important;
    color: var(--mc-text) !important;
    border: 1px solid var(--mc-border) !important;
    border-radius: 8px !important;
    min-height: 44px !important;
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stSelectbox select:focus,
.stTextArea textarea:focus {
    border-color: var(--mc-orange) !important;
    box-shadow: 0 0 8px var(--mc-orange-glow) !important;
}

.stDataFrame { background: var(--mc-surface) !important; }

.mc-tutorial {
    background: linear-gradient(135deg, #2D1F18 0%, #1E232D 100%);
    border: 1px solid var(--mc-orange);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 0 20px var(--mc-orange-glow);
}

.mc-recipe-card {
    background: var(--mc-surface-2);
    border: 1px solid var(--mc-border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 150ms ease;
}

.mc-recipe-card:hover {
    border-color: var(--mc-orange);
    background: var(--mc-surface-3);
}

@media (max-width: 768px) {
    .stButton > button {
        min-height: 52px !important;
        font-size: 18px !important;
    }
    .mc-stat-value { font-size: 24px; }
}
</style>
""", unsafe_allow_html=True)

# ── Session State Initialization ────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "email" not in st.session_state:
    st.session_state.email = None
if "page" not in st.session_state:
    st.session_state.page = "home"
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "show_tutorial" not in st.session_state:
    st.session_state.show_tutorial = False

# ── LOGIN PAGE ──────────────────────────────────────────────────────────
def page_login():
    """Pagina de login e registro com tutorial."""
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<h2 style='text-align: center; color: var(--mc-orange); margin-bottom: 30px;'>Mateu Coffee</h2>", unsafe_allow_html=True)
        st.subheader("Login")
        email_login = st.text_input("Email", key="login_email")
        senha_login = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar", use_container_width=True):
            if email_login and senha_login:
                with st.spinner("Verificando credenciais..."):
                    sucesso, user_id, msg = verificar_login(email_login, senha_login)
                if sucesso:
                    st.session_state.user_id = user_id
                    st.session_state.email = email_login
                    st.session_state.show_tutorial = True
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
                st.error("Senhas nao conferem")
            else:
                with st.spinner("Criando conta..."):
                    sucesso, msg = criar_usuario(email_reg, senha_reg, nome_reg)
                if sucesso:
                    st.success("Conta criada! Faca login para continuar.")
                else:
                    st.error(msg)

# ── HOME PAGE ───────────────────────────────────────────────────────────
def page_home():
    """Home com dashboard completo."""
    usuario = obter_usuario_por_id(st.session_state.user_id)

    # Header com theme toggle
    col1, col2, col3 = st.columns([1, 1, 0.15])
    with col1:
        st.markdown(f"<h1 style='color: var(--mc-orange);'>Ola, {usuario['nome'] or usuario['email']}</h1>", unsafe_allow_html=True)
    with col3:
        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.show_tutorial = False
            st.session_state.page = "login"
            st.rerun()

    # Tutorial ao primeiro uso
    if st.session_state.show_tutorial:
        st.markdown("""
        <div class='mc-tutorial'>
            <h3 style='color: var(--mc-orange);'>Bem-vindo ao Mateu Coffee!</h3>
            <p>Dicas rapidas para comeco:</p>
            <ul>
                <li><strong>Novo Cafe:</strong> Registre seus cafes favoritos com origem e aroma</li>
                <li><strong>Nova Extracao:</strong> Registre cada cafe que voce faz com dados sensoriais</li>
                <li><strong>Comunidade:</strong> Compartilhe suas melhores receitas</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("Entendi!", use_container_width=True):
                st.session_state.show_tutorial = False
                st.rerun()

    # Estatisticas
    with st.spinner("Carregando estatisticas..."):
        stats = obter_estatisticas(st.session_state.user_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['total_cafes']}</div>
            <div class='mc-stat-label'>Cafes Cadastrados</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='mc-stat'>
            <div class='mc-stat-value'>{stats['total_extractions']}</div>
            <div class='mc-stat-label'>Extracoes</div>
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

    # Abas principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Cafes", "Extracoes", "Analises", "Comunidade", "Recomendacoes"
    ])

    # ── ABA 1: CAFES ──
    with tab1:
        col1, col2 = st.columns([0.7, 0.3])

        with col1:
            st.subheader("Cafes Cadastrados")
            with st.spinner("Carregando cafes..."):
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
                            st.caption(f"R$ {cafe['preco_kg']:.2f}/kg" if cafe['preco_kg'] else "Sem preco")
                        with col_c:
                            if st.button("Deletar", key=f"del_cafe_{cafe['id']}", use_container_width=True):
                                with st.spinner("Deletando..."):
                                    deletar_cafe(cafe['id'], st.session_state.user_id)
                                st.success("Cafe deletado!")
                                st.rerun()
            else:
                st.info("Nenhum cafe cadastrado. Crie um para comeco!")

        with col2:
            st.subheader("Novo Cafe")
            nome = st.text_input("Nome do Cafe")
            origem = st.text_input("Origem")
            tipo = st.selectbox("Tipo", ["Espresso", "Filtrado", "Coado", "Outro"])
            torrefacao = st.selectbox("Torrefacao", ["Leve", "Media", "Escura"])
            preco = st.number_input("Preco/kg", min_value=0.0, step=1.0)
            notas = st.text_area("Notas", height=80)

            if st.button("Adicionar Cafe", use_container_width=True):
                if nome:
                    with st.spinner("Salvando cafe..."):
                        sucesso, msg = criar_cafe(st.session_state.user_id, nome, origem, tipo, torrefacao, preco, notas)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Nome do cafe e obrigatorio")

    # ── ABA 2: EXTRACOES ──
    with tab2:
        col1, col2 = st.columns([0.6, 0.4])

        with col1:
            st.subheader("Registrar Extracao")
            with st.spinner("Carregando cafes..."):
                cafes = listar_cafes(st.session_state.user_id)
            cafe_opts = {c['nome']: c['id'] for c in cafes}

            cafe_nome = st.selectbox("Cafe", list(cafe_opts.keys()) if cafe_opts else ["Nenhum cafe"])
            data_extr = st.date_input("Data", value=date.today())
            gramas = st.number_input("Gramas de Cafe", min_value=0.0, step=0.1)
            gramas_agua = st.number_input("Gramas de Agua", min_value=0.0, step=0.1)
            tempo = st.number_input("Tempo (segundos)", min_value=0, step=1)
            temp = st.number_input("Temperatura (C)", min_value=0.0, step=0.1)
            pressao = st.number_input("Pressao (bar)", min_value=0.0, step=0.1)
            metodo = st.selectbox("Metodo", ["Espresso", "V60", "Prensa Francesa", "Moka", "Outro"])
            notas_extr = st.text_area("Notas", height=80)

            if st.button("Registrar Extracao", use_container_width=True):
                if cafe_opts and gramas > 0:
                    with st.spinner("Registrando extracao..."):
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
                    st.error("Selecione um cafe e gramas")

        with col2:
            st.subheader("Ultimas Extracoes")
            with st.spinner("Carregando extracoes..."):
                extractions = listar_extractions(st.session_state.user_id, dias=30)

            if extractions:
                for ext in extractions[:10]:
                    with st.container(border=True):
                        st.caption(f"{ext['data']} | {ext.get('cafe_nome', 'N/A')}")
                        st.markdown(f"**{ext['gramas_cafe']:.1f}g** | {ext['metodo'] or 'N/A'}")
                        if ext.get('tempo_segundos'):
                            st.caption(f"Tempo: {ext['tempo_segundos']}s | Temp: {ext.get('temperatura', 0):.1f}C")
                        if st.button("Deletar", key=f"del_ext_{ext['id']}", use_container_width=True):
                            with st.spinner("Deletando..."):
                                deletar_extracao(ext['id'], st.session_state.user_id)
                            st.rerun()
            else:
                st.info("Nenhuma extracao registrada")

    # ── ABA 3: ANALISES SENSORIAIS ──
    with tab3:
        st.subheader("Analises Sensoriais")
        with st.spinner("Carregando dados..."):
            extractions = listar_extractions(st.session_state.user_id, dias=60)

        if extractions:
            for idx, ext in enumerate(extractions[:10]):
                with st.container(border=True):
                    col_a, col_b = st.columns([0.7, 0.3])
                    with col_a:
                        st.markdown(f"**{ext.get('cafe_nome', 'Cafe')}** - {ext['data']}")
                        st.caption(f"Metodo: {ext['metodo']} | {ext['gramas_cafe']:.1f}g")

                    with col_b:
                        st.metric("Nota Geral", f"{ext.get('nota_geral', 0):.1f}/10")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        aroma = st.slider("Aroma", 1, 10, int(ext.get('aroma', 5)), key=f"aroma_{ext['id']}")
                    with col2:
                        acidez = st.slider("Acidez", 1, 10, int(ext.get('acidez', 5)), key=f"acidez_{ext['id']}")
                    with col3:
                        corpo = st.slider("Corpo", 1, 10, int(ext.get('corpo', 5)), key=f"corpo_{ext['id']}")

                    sabor = st.text_input("Notas de Sabor (ex: chocolate, frutado)", value=ext.get('sabor_notas', ''), key=f"sabor_{ext['id']}")
                    nota_final = st.slider("Nota Final", 0.0, 10.0, float(ext.get('nota_geral', 5.0)), key=f"nota_{ext['id']}")

                    if st.button("Salvar Analise", key=f"save_analise_{ext['id']}", use_container_width=True):
                        with st.spinner("Salvando analise..."):
                            atualizar_analise_sensorial(ext['id'], st.session_state.user_id, aroma, acidez, corpo, sabor, nota_final)
                        st.success("Analise salva!")
                        st.rerun()

            # Graficos de analise
            st.divider()
            st.subheader("Graficos de Desempenho")

            notas_por_metodo = obter_notas_por_metodo(st.session_state.user_id)
            if notas_por_metodo:
                df_metodos = pd.DataFrame(notas_por_metodo)
                fig_metodos = go.Figure(data=[
                    go.Bar(x=df_metodos['metodo'], y=df_metodos['nota_media'], marker_color='#E8722E')
                ])
                fig_metodos.update_layout(
                    title="Nota Media por Metodo",
                    xaxis_title="Metodo",
                    yaxis_title="Nota Media",
                    template="plotly_dark",
                    paper_bgcolor="#0A0A0A",
                    plot_bgcolor="#1A1A1A"
                )
                st.plotly_chart(fig_metodos, use_container_width=True)

            evolucao = obter_evolucao_notas(st.session_state.user_id, dias=60)
            if evolucao:
                df_evolucao = pd.DataFrame(evolucao)
                fig_evolucao = go.Figure(data=[
                    go.Scatter(x=df_evolucao['data'], y=df_evolucao['nota_geral'], mode='lines+markers', marker_color='#E8722E')
                ])
                fig_evolucao.update_layout(
                    title="Evolucao de Notas",
                    xaxis_title="Data",
                    yaxis_title="Nota",
                    template="plotly_dark",
                    paper_bgcolor="#0A0A0A",
                    plot_bgcolor="#1A1A1A"
                )
                st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("Registre extracoes para ver analises")

    # ── ABA 4: COMUNIDADE ──
    with tab4:
        col1, col2 = st.columns([0.5, 0.5])

        with col1:
            st.subheader("Compartilhar Receita")
            cafe_comp = st.text_input("Nome do Cafe")
            metodo_comp = st.selectbox("Metodo", ["Espresso", "V60", "Prensa Francesa", "Moka", "Outro"], key="comp_metodo")
            dose_comp = st.number_input("Dose (gramas)", min_value=0.0, step=0.1, key="comp_dose")
            agua_comp = st.number_input("Agua (ml)", min_value=0.0, step=1.0, key="comp_agua")
            nota_comp = st.slider("Sua Nota", 1, 10, 7, key="comp_nota")

            if st.button("Compartilhar Receita", use_container_width=True):
                if cafe_comp and dose_comp > 0:
                    with st.spinner("Compartilhando receita..."):
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
            with st.spinner("Carregando receitas..."):
                receitas = listar_receitas_compartilhadas(limite=20)

            if receitas:
                for receita in receitas:
                    st.markdown(f"""
                    <div class='mc-recipe-card'>
                        <strong>{receita['cafe_nome']}</strong><br>
                        {receita['metodo']} | {receita['dose_gramas']:.1f}g + {receita['agua_ml']:.0f}ml<br>
                        <span style='color: var(--mc-orange);'>Nota: {receita['nota']}/10</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma receita compartilhada ainda")

    # ── ABA 5: RECOMENDACOES ──
    with tab5:
        st.subheader("Recomendacoes Personalizadas")

        metodos = ["Espresso", "V60", "Prensa Francesa", "Moka"]
        for metodo in metodos:
            with st.spinner(f"Buscando melhor receita para {metodo}..."):
                melhor = obter_melhor_receita_por_metodo(st.session_state.user_id, metodo)
            if melhor:
                st.markdown(f"""
                <div class='mc-card'>
                    <h4 style='color: var(--mc-orange);'>{metodo}</h4>
                    <p><strong>Cafe:</strong> {melhor['cafe'] or 'N/A'}</p>
                    <p><strong>Receita:</strong> {melhor['gramas_cafe']:.1f}g + {melhor['gramas_agua']:.0f}g agua</p>
                    <p><strong>Nota Media:</strong> {melhor['nota_media']:.1f}/10</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='mc-card'>
                    <p>{metodo}: Registre extracoes para ter recomendacoes</p>
                </div>
                """, unsafe_allow_html=True)

# ── MAIN ───────────────────────────────────────────────────────────────
if st.session_state.user_id:
    page_home()
else:
    page_login()
