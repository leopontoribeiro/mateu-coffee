#!/bin/bash
# MATEU COFFEE | Deploy Automation Script
# Executa: Clone → Setup → Test → GitHub Push → Streamlit Deploy

set -e  # Exit on error

echo "=========================================="
echo "🚀 MATEU COFFEE | DEPLOY AUTOMATION v1.0"
echo "=========================================="
echo ""

# ====== STEP 1: VERIFICAR PRÉ-REQUISITOS ======
echo "📋 STEP 1: Verificando pré-requisitos..."

if ! command -v git &> /dev/null; then
    echo "❌ Git não instalado. Instale: https://git-scm.com/"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não instalado."
    exit 1
fi

echo "✅ Git e Python3 detectados"
echo ""

# ====== STEP 2: CRIAR DIRETÓRIO DO PROJETO ======
echo "📁 STEP 2: Criando diretório do projeto..."

PROJECT_DIR="$HOME/mateu-coffee"
if [ -d "$PROJECT_DIR" ]; then
    read -p "⚠️  $PROJECT_DIR já existe. Deletar? (s/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf "$PROJECT_DIR"
    else
        echo "Abortado."
        exit 1
    fi
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "✅ Diretório criado: $PROJECT_DIR"
echo ""

# ====== STEP 3: COPIAR ARQUIVOS ======
echo "📄 STEP 3: Copiando arquivos da aplicação..."

cat > app_cloud.py << 'EOF'
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz

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
    @media (max-width: 640px) {
        .main { padding: 0.5rem; }
        [data-testid="stColumn"] { margin: 0 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ====== DATABASE CONNECTION ======
@st.cache_resource
def get_db_connection():
    """Conexão segura via st.connection"""
    return st.connection("postgresql", type="sql")

# ====== CREATE TABLES ======
def init_database(conn):
    """Cria tabelas se não existirem"""
    cursor = conn.cursor()

    # Tabela de Grãos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            tipo_grao VARCHAR(50),
            torra VARCHAR(30),
            local_origem VARCHAR(100),
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

    conn.commit()
    cursor.close()

# ====== INICIALIZAR SESSÃO ======
if "conn" not in st.session_state:
    st.session_state.conn = get_db_connection()
    init_database(st.session_state.conn)

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
        nome_grao = st.text_input("Nome do Café", placeholder="Ex: Etíopia Natural Yirgacheffe")
        tipo_grao = st.selectbox("Tipo de Grão", ["Arábica", "Robusta", "Blend"])
        torra = st.selectbox("Perfil de Torra", ["Cinnamon", "City", "Full City", "French", "Italian"])
        local_origem = st.text_input("Local de Origem", placeholder="Ex: Etíopia, Região Yirgacheffe")

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
        if nome_grao and local_origem:
            cursor = st.session_state.conn.cursor()
            cursor.execute("""
                INSERT INTO graos
                (nome, tipo_grao, torra, local_origem, categoria, perfil_sabor,
                 intensidade, peso_embalagem_g, data_compra, data_torra, preco)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nome_grao, tipo_grao, torra, local_origem, categoria, perfil_sabor,
                  intensidade, peso_embalagem_g, data_compra, data_torra, preco))
            st.session_state.conn.commit()
            cursor.close()
            st.success(f"✅ Grão '{nome_grao}' registrado com sucesso!")
            st.rerun()
        else:
            st.error("⚠️ Preencha Nome do Café e Local de Origem obrigatoriamente")

# =============== ABA 2: REGISTRAR PREPARO ===============
with tab2:
    st.subheader("Novo Registro de Extração")

    # Buscar grãos cadastrados
    cursor = st.session_state.conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, nome FROM graos ORDER BY id DESC")
    graos = cursor.fetchall()
    cursor.close()

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
        brew_ratio = volume_bebida_ml / peso_cafe_g if peso_cafe_g > 0 else 0

        st.markdown(f"""
        ### 📊 Brew Ratio: **{brew_ratio:.2f}:1**
        **Interpretação**: 1g de café para {brew_ratio:.2f}ml de bebida
        """)

        st.divider()

        # ====== ATRIBUTOS SENSORIAIS (CHECKBOXES) ======
        st.markdown("#### 👅 Atributos Sensoriais Detectados")

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

        # ====== BOTÃO REGISTRAR ======
        if st.button("✅ Registrar Preparo", use_container_width=True, type="primary"):
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
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao registrar: {str(e)}")

# =============== ABA 3: HISTÓRICO & MÉTRICAS ===============
with tab3:
    st.subheader("Histórico de Extrações")

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
                             'Cliques', 'Tempo(s)', 'Volume(ml)', 'Ratio', '⭐', 'Atributos']

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # ====== EXPORTAR ======
        csv = df_preparos.to_csv(index=False)
        st.download_button(
            label="📥 Exportar CSV",
            data=csv,
            file_name=f"mateu_coffee_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ====== FOOTER ======
st.divider()
st.markdown("""
<div style="text-align: center; font-size: 12px; color: #666;">
    Mateu Coffee v1.0 | Engenharia de Extração | Banco de Dados Privado PostgreSQL
</div>
""", unsafe_allow_html=True)
EOF

cat > requirements.txt << 'EOF'
streamlit==1.35.0
pandas==2.1.4
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pytz==2023.3.post1
EOF

cat > .gitignore << 'EOF'
.streamlit/secrets.toml
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
.pytest_cache/
.coverage
htmlcov/
*.db
*.sqlite
*.sqlite3
*.log
logs/
.env
.env.local
*.bak
EOF

mkdir -p .streamlit

echo "✅ Arquivos criados"
echo ""

# ====== STEP 4: INICIALIZAR GIT ======
echo "🔧 STEP 4: Inicializando Git..."

git init
git add app_cloud.py requirements.txt .gitignore
git commit -m "Initial Mateu Coffee deployment"

echo "✅ Repositório Git inicializado"
echo ""

# ====== STEP 5: CRIAR VIRTUAL ENV ======
echo "🐍 STEP 5: Criando ambiente Python..."

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "✅ Dependências instaladas"
echo ""

# ====== STEP 6: INFORMAÇÕES PARA PRÓXIMAS ETAPAS ======
echo "=========================================="
echo "✅ SETUP LOCAL COMPLETO"
echo "=========================================="
echo ""
echo "📋 PRÓXIMAS ETAPAS:"
echo ""
echo "1️⃣  CRIAR BANCO PostgreSQL (Neon.tech)"
echo "   • Acesse: https://neon.tech"
echo "   • Crie projeto PostgreSQL"
echo "   • Copie Connection String"
echo ""
echo "2️⃣  CRIAR SECRETS LOCAL"
echo "   • Arquivo: $PROJECT_DIR/.streamlit/secrets.toml"
echo "   • Conteúdo:"
echo ""
echo "   [connections.postgresql]"
echo "   dialect = \"postgresql\""
echo "   driver = \"psycopg2\""
echo "   host = \"seu-host-neon.neon.tech\""
echo "   port = 5432"
echo "   database = \"neon_db\""
echo "   username = \"seu_usuario\""
echo "   password = \"sua_senha\""
echo ""
echo "3️⃣  TESTAR LOCALMENTE"
echo "   • cd $PROJECT_DIR"
echo "   • source venv/bin/activate"
echo "   • streamlit run app_cloud.py"
echo ""
echo "4️⃣  PUSH PARA GITHUB"
echo "   • Crie repositório privado em github.com"
echo "   • Execute:"
echo "   cd $PROJECT_DIR"
echo "   git remote add origin https://github.com/seu-usuario/mateu-coffee.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "5️⃣  DEPLOY STREAMLIT CLOUD"
echo "   • Acesse: https://share.streamlit.io"
echo "   • New app → GitHub → seu-usuario/mateu-coffee → main → app_cloud.py"
echo "   • Settings → Secrets → Cole credenciais PostgreSQL"
echo ""
echo "=========================================="
echo ""
echo "Diretório do projeto: $PROJECT_DIR"
echo ""
