import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz
import json
import time

# ====== CONFIG PAGE ======
st.set_page_config(
    page_title="Mateu Coffee | Extração",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====== CUSTOM CSS RESPONSIVO ======
st.markdown("""
    <style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .main {
        max-width: 100%;
        padding: 1rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    input, textarea, select {
        font-size: 16px !important;
    }
    .brew-ratio-box {
        background-color: #f0f8ff;
        border-left: 4px solid #1f77b4;
        padding: 20px;
        border-radius: 5px;
        margin: 20px 0;
    }
    .brew-ratio-value {
        font-size: 32px;
        color: #1f77b4;
        font-weight: bold;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
    }
    @media (max-width: 640px) {
        .main { padding: 0.5rem; }
        [data-testid="stColumn"] { margin: 0 !important; }
        .brew-ratio-box { padding: 15px; }
        .brew-ratio-value { font-size: 24px; }
    }
    </style>
""", unsafe_allow_html=True)

# ====== VALIDAÇÃO DE INPUTS ======
class Validador:
    """Validação rigorosa de dados"""

    @staticmethod
    def validar_grao(nome, origem, peso, preco, data_torra):
        """Valida cadastro de grão"""
        erros = []

        if not nome or not nome.strip():
            erros.append("Nome do café obrigatório")
        elif len(nome.strip()) > 100:
            erros.append("Nome muito longo (máximo 100 caracteres)")

        if not origem or not origem.strip():
            erros.append("Local de origem obrigatório")
        elif len(origem.strip()) > 100:
            erros.append("Origem muito longa")

        if peso <= 0 or peso > 5000:
            erros.append("Peso deve estar entre 100g e 5000g")

        if preco < 0:
            erros.append("Preço não pode ser negativo")

        if data_torra > datetime.now().date():
            erros.append("Data de torra não pode ser futura")

        return len(erros) == 0, erros

    @staticmethod
    def validar_preparo(metodo, dose, cliques, tempo, volume):
        """Valida registro de preparo"""
        erros = []
        avisos = []

        if dose <= 0 or dose > 100:
            erros.append("Dose deve estar entre 1g e 100g")

        if tempo <= 0 or tempo > 300:
            erros.append("Tempo deve estar entre 1s e 300s")

        if volume <= 0 or volume > 500:
            erros.append("Volume deve estar entre 1ml e 500ml")

        if cliques <= 0 or cliques > 40:
            erros.append("Cliques devem estar entre 1 e 40")

        # Avisos (validação soft - não bloqueia)
        zones = {
            "Espresso": {"dose": (14, 22), "cliques": (18, 25), "tempo": (25, 35), "volume": (36, 50)},
            "Pour Over": {"dose": (18, 32), "cliques": (15, 22), "tempo": (180, 240), "volume": (250, 400)},
            "French Press": {"dose": (25, 35), "cliques": (6, 10), "tempo": (240, 300), "volume": (400, 600)},
            "AeroPress": {"dose": (10, 20), "cliques": (15, 25), "tempo": (30, 50), "volume": (200, 300)},
        }

        if metodo in zones:
            zone = zones[metodo]
            if not (zone["dose"][0] <= dose <= zone["dose"][1]):
                avisos.append(f"⚠️ Dose ideal para {metodo}: {zone['dose'][0]}-{zone['dose'][1]}g")
            if not (zone["cliques"][0] <= cliques <= zone["cliques"][1]):
                avisos.append(f"⚠️ Cliques ideais para {metodo}: {zone['cliques'][0]}-{zone['cliques'][1]}")
            if not (zone["tempo"][0] <= tempo <= zone["tempo"][1]):
                avisos.append(f"⚠️ Tempo ideal para {metodo}: {zone['tempo'][0]}-{zone['tempo'][1]}s")

        return len(erros) == 0, erros, avisos

# ====== DATABASE CONNECTION COM VALIDAÇÃO ======
@st.cache_resource
def init_db_connection():
    """Conexão com validação de saúde"""
    try:
        conn = st.connection("postgresql", type="sql")
        cursor = conn.cursor()

        # Testa conexão
        cursor.execute("SELECT 1")
        cursor.close()

        st.session_state.db_healthy = True
        return conn
    except Exception as e:
        st.session_state.db_healthy = False
        st.error(f"❌ **Banco de dados offline**: {str(e)}")
        st.stop()

# ====== CRIAR TABELAS E ÍNDICES ======
def init_database(conn):
    """Cria tabelas e índices"""
    cursor = conn.cursor()

    # Tabela de Grãos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE,
            tipo_grao VARCHAR(50),
            torra VARCHAR(30),
            local_origem VARCHAR(100) NOT NULL,
            categoria VARCHAR(50),
            perfil_sabor TEXT,
            intensidade VARCHAR(20),
            peso_embalagem_g INT,
            data_compra DATE,
            data_torra DATE,
            preco DECIMAL(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Preparos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preparos (
            id SERIAL PRIMARY KEY,
            grao_id INT REFERENCES graos(id) ON DELETE CASCADE,
            data_preparo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metodo_preparo VARCHAR(50),
            peso_cafe_g DECIMAL(10, 2),
            moagem_cliques INT,
            tempo_segundos INT,
            volume_bebida_ml INT,
            tipo_volume_xicara VARCHAR(30),
            atributos_sensoriais TEXT,
            avaliacao_estrelas DECIMAL(2, 1),
            brew_ratio DECIMAL(5, 2),
            notas TEXT
        )
    """)

    # Criar Índices para Performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_preparos_grao_id
        ON preparos(grao_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_preparos_data_desc
        ON preparos(data_preparo DESC);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_graos_nome
        ON graos(nome);
    """)

    conn.commit()
    cursor.close()

# ====== INICIALIZAR SESSÃO ======
if "conn" not in st.session_state:
    st.session_state.conn = init_db_connection()
    init_database(st.session_state.conn)
    st.session_state.db_healthy = True

# ====== HEADER ======
col1, col2 = st.columns([1, 3])
with col1:
    st.markdown("# ☕ Mateu")
with col2:
    st.markdown("## Engenharia de Extração")

st.divider()

# ====== TABS ======
tab1, tab2, tab3 = st.tabs(["📝 Cadastro de Grãos", "⚙️ Registrar Preparo", "📊 Histórico"])

# =============== ABA 1: CADASTRO DE GRÃOS ===============
with tab1:
    st.subheader("Novo Lote de Café")

    col1, col2 = st.columns(2)
    with col1:
        nome_grao = st.text_input("Nome do Café", placeholder="Ex: Etíopia Natural Yirgacheffe", max_chars=100)
        tipo_grao = st.selectbox("Tipo de Grão", ["Arábica", "Robusta", "Blend"])
        torra = st.selectbox("Perfil de Torra", ["Cinnamon", "City", "Full City", "French", "Italian"])
        local_origem = st.text_input("Local de Origem", placeholder="Ex: Etíopia, Região Yirgacheffe", max_chars=100)

    with col2:
        categoria = st.selectbox("Categoria", ["Specialty", "Premium", "Comercial"])
        intensidade = st.selectbox("Intensidade", ["Leve", "Médio", "Forte", "Muito Forte"])
        peso_embalagem_g = st.number_input("Peso da Embalagem (g)", min_value=100, max_value=5000, step=50, value=250)
        preco = st.number_input("Preço (R$)", min_value=0.0, step=0.50, format="%.2f")

    col1, col2 = st.columns(2)
    with col1:
        data_compra = st.date_input("Data de Compra", value=datetime.now().date())
        data_torra = st.date_input("Data de Torra", value=datetime.now().date())

    perfil_sabor = st.text_area("Perfil de Sabor", placeholder="Ex: Notas de chocolate, amêndoa, frutas vermelhas", height=80)

    if st.button("✅ Registrar Grão", use_container_width=True, type="primary"):
        valid, erros = Validador.validar_grao(nome_grao, local_origem, peso_embalagem_g, preco, data_torra)

        if not valid:
            for erro in erros:
                st.error(f"⚠️ {erro}")
        else:
            with st.spinner("⏳ Salvando grão..."):
                try:
                    cursor = st.session_state.conn.cursor()
                    cursor.execute("""
                        INSERT INTO graos
                        (nome, tipo_grao, torra, local_origem, categoria, perfil_sabor,
                         intensidade, peso_embalagem_g, data_compra, data_torra, preco)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (nome_grao.strip(), tipo_grao, torra, local_origem.strip(), categoria, perfil_sabor,
                          intensidade, peso_embalagem_g, data_compra, data_torra, preco))
                    st.session_state.conn.commit()
                    cursor.close()
                    st.success(f"✅ Grão '{nome_grao}' registrado com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                except psycopg2.IntegrityError:
                    st.error("⚠️ Café com este nome já existe. Use outro nome.")
                except Exception as e:
                    st.error(f"❌ Erro ao registrar: {str(e)}")

# =============== ABA 2: REGISTRAR PREPARO ===============
with tab2:
    st.subheader("Novo Registro de Extração")

    # Buscar grãos cadastrados
    try:
        cursor = st.session_state.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, nome FROM graos ORDER BY id DESC")
        graos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        st.error(f"Erro ao carregar grãos: {e}")
        graos = []

    if not graos:
        st.warning("⚠️ Nenhum grão cadastrado. Cadastre um café antes de registrar um preparo.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            grao_options = {g['nome']: g['id'] for g in graos}
            grao_selecionado = st.selectbox("Selecione o Grão", options=list(grao_options.keys()))
            grao_id = grao_options[grao_selecionado]

            metodo_preparo = st.selectbox("Método de Preparo",
                                         ["Espresso", "Pour Over", "French Press", "AeroPress", "Moka", "Turco"])
            peso_cafe_g = st.number_input("Peso do Café (g)", min_value=5.0, max_value=100.0, step=0.5, value=18.0)
            moagem_cliques = st.slider("Moagem (Cliques)", min_value=1, max_value=40, value=20)

        with col2:
            tempo_segundos = st.number_input("Tempo de Contato (seg)", min_value=10, max_value=300, step=5, value=30)
            volume_bebida_ml = st.number_input("Volume Final (ml)", min_value=30, max_value=500, step=10, value=200)
            tipo_volume_xicara = st.selectbox("Tipo de Xícara",
                                             ["Espresso (30-50ml)", "Ristretto (20-30ml)", "Lungo (150-250ml)",
                                              "Café Coado (150-300ml)", "Chávena Grande (300-500ml)"])

        # ====== CÁLCULO DE BREW RATIO EM TEMPO REAL ======
        if peso_cafe_g > 0:
            brew_ratio = volume_bebida_ml / peso_cafe_g
        else:
            brew_ratio = 0

        # Destacar Brew Ratio (KPI Principal)
        st.markdown(f"""
        <div class="brew-ratio-box">
            <h3>📊 Brew Ratio: <span class="brew-ratio-value">{brew_ratio:.2f}:1</span></h3>
            <p><strong>Interpretação:</strong> 1g de café para <strong>{brew_ratio:.2f}ml</strong> de bebida</p>
        </div>
        """, unsafe_allow_html=True)

        # Validação soft: aviso se fora da zona ideal
        valid, erros, avisos = Validador.validar_preparo(metodo_preparo, peso_cafe_g, moagem_cliques, tempo_segundos, volume_bebida_ml)

        if avisos:
            for aviso in avisos:
                st.markdown(f'<div class="warning-box">{aviso}</div>', unsafe_allow_html=True)

        st.divider()

        # ====== ATRIBUTOS SENSORIAIS (CHECKBOXES) ======
        st.markdown("#### 👅 Atributos Sensoriais Detectados")

        # Mobile: stack vertical | Desktop: 2 colunas
        is_mobile = st.session_state.get("viewport_width", 800) < 640

        if is_mobile:
            check_forte = st.checkbox("🔥 Forte")
            check_fraco = st.checkbox("💧 Fraco")
            check_amargo = st.checkbox("😊 Amargo")
            check_intenso = st.checkbox("⚡ Intenso")
            check_queimado = st.checkbox("🔥 Queimado")
            check_crema = st.checkbox("☁️ Crema")
            check_saboroso = st.checkbox("😋 Saboroso")
            check_sem_sabor = st.checkbox("❌ Sem Sabor")
        else:
            col1, col2 = st.columns(2)
            with col1:
                check_forte = st.checkbox("🔥 Forte")
                check_fraco = st.checkbox("💧 Fraco")
                check_amargo = st.checkbox("😊 Amargo")
                check_intenso = st.checkbox("⚡ Intenso")

            with col2:
                check_queimado = st.checkbox("🔥 Queimado")
                check_crema = st.checkbox("☁️ Crema")
                check_saboroso = st.checkbox("😋 Saboroso")
                check_sem_sabor = st.checkbox("❌ Sem Sabor")

        atributos_lista = []
        if check_forte: atributos_lista.append("Forte")
        if check_fraco: atributos_lista.append("Fraco")
        if check_amargo: atributos_lista.append("Amargo")
        if check_intenso: atributos_lista.append("Intenso")
        if check_queimado: atributos_lista.append("Queimado")
        if check_crema: atributos_lista.append("Crema")
        if check_saboroso: atributos_lista.append("Saboroso")
        if check_sem_sabor: atributos_lista.append("Sem Sabor")

        atributos_sensoriais = ", ".join(atributos_lista) if atributos_lista else "Nenhum selecionado"

        st.divider()

        # ====== AVALIAÇÃO E NOTAS ======
        col1, col2 = st.columns(2)
        with col1:
            avaliacao_estrelas = st.slider("Avaliação", min_value=0.0, max_value=5.0, step=0.5, value=3.5)
        with col2:
            notas = st.text_area("Notas Adicionais", placeholder="Observações sobre a extração...", height=80)

        # ====== BOTÃO REGISTRAR COM SPINNER ======
        if st.button("✅ Registrar Preparo", use_container_width=True, type="primary"):
            with st.spinner("⏳ Salvando preparo..."):
                try:
                    cursor = st.session_state.conn.cursor()
                    cursor.execute("""
                        INSERT INTO preparos
                        (grao_id, metodo_preparo, peso_cafe_g, moagem_cliques, tempo_segundos,
                         volume_bebida_ml, tipo_volume_xicara, atributos_sensoriais, avaliacao_estrelas, brew_ratio, notas)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (grao_id, metodo_preparo, peso_cafe_g, moagem_cliques, tempo_segundos,
                          volume_bebida_ml, tipo_volume_xicara, atributos_sensoriais, avaliacao_estrelas, brew_ratio, notas))
                    st.session_state.conn.commit()
                    cursor.close()
                    st.success(f"✅ Preparo registrado | Brew Ratio: {brew_ratio:.2f}:1 | ⭐ {avaliacao_estrelas}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao registrar: {str(e)}")

# =============== ABA 3: HISTÓRICO & MÉTRICAS ===============
with tab3:
    st.subheader("Histórico de Extrações")

    try:
        cursor = st.session_state.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT
                p.id,
                g.nome as grao,
                p.data_preparo,
                p.metodo_preparo,
                p.peso_cafe_g,
                p.moagem_cliques,
                p.tempo_segundos,
                p.volume_bebida_ml,
                p.atributos_sensoriais,
                p.avaliacao_estrelas,
                p.brew_ratio
            FROM preparos p
            JOIN graos g ON p.grao_id = g.id
            ORDER BY p.id DESC
            LIMIT 100
        """)
        preparos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        preparos = []

    if not preparos:
        st.info("📭 Nenhum preparo registrado ainda.")
    else:
        # ====== RESUMO ANALÍTICO ======
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Extrações", len(preparos))
        with col2:
            avaliacao_media = pd.DataFrame(preparos)['avaliacao_estrelas'].mean()
            st.metric("Avaliação Média", f"{avaliacao_media:.1f}⭐")
        with col3:
            tempo_medio = pd.DataFrame(preparos)['tempo_segundos'].mean()
            st.metric("Tempo Médio", f"{tempo_medio:.0f}s")
        with col4:
            brew_ratio_medio = pd.DataFrame(preparos)['brew_ratio'].mean()
            st.metric("Brew Ratio Médio", f"{brew_ratio_medio:.2f}:1")

        st.divider()

        # ====== TABELA HISTÓRICO ======
        df_preparos = pd.DataFrame(preparos)
        df_preparos['data_preparo'] = pd.to_datetime(df_preparos['data_preparo']).dt.strftime('%d/%m %H:%M')

        display_df = df_preparos[[
            'id', 'grao', 'data_preparo', 'metodo_preparo', 'peso_cafe_g',
            'moagem_cliques', 'tempo_segundos', 'volume_bebida_ml',
            'brew_ratio', 'avaliacao_estrelas', 'atributos_sensoriais'
        ]].copy()

        display_df.columns = ['ID', 'Grão', 'Data/Hora', 'Método', 'Dose(g)',
                             'Cliques', 'Tempo(s)', 'Volume(ml)', '⭐ Ratio', 'Nota', 'Atributos']

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()

        # ====== EXPORT OPTIONS ======
        col1, col2 = st.columns(2)

        with col1:
            csv = df_preparos.to_csv(index=False)
            st.download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"mateu_coffee_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        with col2:
            # Backup JSON completo
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "graos": [],
                "preparos": [dict(p) for p in preparos]
            }
            cursor = st.session_state.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM graos")
            backup_data["graos"] = [dict(g) for g in cursor.fetchall()]
            cursor.close()

            backup_json = json.dumps(backup_data, indent=2, default=str)
            st.download_button(
                label="📦 Backup JSON",
                data=backup_json,
                file_name=f"mateu_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# ====== FOOTER ======
st.divider()
st.markdown("""
<div style="text-align: center; font-size: 12px; color: #666;">
    Mateu Coffee v1.1 | Engenharia de Extração | Banco de Dados Privado PostgreSQL
</div>
""", unsafe_allow_html=True)
