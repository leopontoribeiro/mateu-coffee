# SETUP MATEU COFFEE - STREAMLIT SECRETS CONFIGURATION

## 📋 PRÉ-REQUISITOS

1. **Banco de Dados PostgreSQL** (Neon.tech ou Supabase)
2. **Streamlit Account** com repositório GitHub conectado
3. **Variáveis de Ambiente** da conexão PostgreSQL

---

## 🔐 STEP 1: GERAR ARQUIVO `secrets.toml` LOCAL

Crie um arquivo `.streamlit/secrets.toml` **localmente** na raiz do seu projeto (este arquivo é ignorado pelo git automaticamente):

```
.streamlit/
├── secrets.toml       ← Criar este arquivo localmente
└── config.toml        ← Opcional
```

### Conteúdo do `secrets.toml`:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu-host-neon.neon.tech"
port = 5432
database = "sua_database"
username = "seu_usuario"
password = "sua_senha_postgres"
```

### Como obter as credenciais:

#### **Se usando Neon.tech:**
1. Login em https://console.neon.tech
2. Selecione seu projeto
3. Clique em "Connection string"
4. Copie a string do tipo:
   ```
   postgresql://user:password@host:5432/database
   ```
5. Extraia os valores individuais

#### **Se usando Supabase:**
1. Login em https://supabase.com
2. Projeto → Settings → Database
3. Copie "Connection string" → "URI"
4. Extraia os valores de `host`, `username`, `password`, `database`

---

## 🌐 STEP 2: UPLOAD PARA STREAMLIT CLOUD (COM SEGURANÇA)

### **Método Recomendado: Secrets Manager do Streamlit Cloud**

1. Acesse https://share.streamlit.io
2. Selecione seu app
3. Clique em **Settings** (ícone de engrenagem)
4. Abra a aba **Secrets**
5. Cole o conteúdo do seu `secrets.toml`:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu-host-neon.neon.tech"
port = 5432
database = "sua_database"
username = "seu_usuario"
password = "sua_senha_postgres"
```

6. Clique **Save**
7. O Streamlit Cloud criptografa automaticamente e faz deploy

### **IMPORTANTE: NUNCA faça commit de `secrets.toml` no GitHub**

Adicione ao `.gitignore`:
```
.streamlit/secrets.toml
```

---

## ✅ STEP 3: VALIDAR CONEXÃO

Execute localmente:

```bash
cd seu-projeto-mateu-coffee
streamlit run app_cloud.py
```

Se aparecer no terminal:
```
✓ Connection string loaded from secrets
✓ Database tables initialized
```

Está funcionando. Se erro:
```
ConnectionError: cannot connect to server
```

Verifique:
- Credenciais corretas no `secrets.toml`
- IP do servidor PostgreSQL autorizado (whitelist no Neon/Supabase)

---

## 🚀 STEP 4: DEPLOY NO STREAMLIT CLOUD

1. Faça push do repositório **SEM** o arquivo `secrets.toml`:
   ```bash
   git add .
   git commit -m "Initial Mateu Coffee deployment"
   git push origin main
   ```

2. No Streamlit Cloud:
   - Clique "New app"
   - Conecte ao repositório GitHub
   - Selecione branch `main`
   - Main file: `app_cloud.py`
   - Clique "Deploy"

3. Após deploy, volte em **Settings → Secrets** e adicione novamente as credenciais PostgreSQL

---

## 🔒 SEGURANÇA - CHECKLIST

- [ ] `.streamlit/secrets.toml` está em `.gitignore`
- [ ] Credenciais PostgreSQL estão APENAS no Streamlit Cloud Secrets Manager
- [ ] Repositório GitHub é **Privado**
- [ ] Usuário PostgreSQL tem **permissões mínimas** (only INSERT, SELECT, UPDATE necessários)
- [ ] IP do servidor PostgreSQL restringe acesso apenas ao IP do Streamlit Cloud (se aplicável)

---

## 📊 ESTRUTURA FINAL DO PROJETO

```
mateu-coffee/
├── app_cloud.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml          (NÃO COMMITAR)
└── README.md
```

### Conteúdo de `.gitignore`:
```
.streamlit/secrets.toml
__pycache__/
*.pyc
.venv/
venv/
```

---

## 🔧 TROUBLESHOOTING

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError: psycopg2` | Verifique se `requirements.txt` está atualizado e rode `pip install -r requirements.txt` |
| `Connection refused` | IP não autorizado no PostgreSQL. Adicione IP do Streamlit Cloud à whitelist |
| `Password authentication failed` | Credenciais incorretas. Copie novamente da Neon/Supabase |
| `Relations do not exist` | Tables não foram criadas. Execute `init_database()` manualmente ou delete/recrie |
| `Timeout on streaming SQL query` | Database muito lento. Adicione índices em `grao_id` na tabela `preparos` |

---

## 📌 ÍNDICES RECOMENDADOS (opcional, para performance)

Após primeira execução, execute no PostgreSQL:

```sql
CREATE INDEX IF NOT EXISTS idx_preparos_grao_id ON preparos(grao_id);
CREATE INDEX IF NOT EXISTS idx_preparos_data ON preparos(data_preparo DESC);
CREATE INDEX IF NOT EXISTS idx_graos_nome ON graos(nome);
```

---

## ✨ PRONTO PARA OPERAÇÃO

Após deploy bem-sucedido:
- ✅ App acessível em `https://your-username-mateu-coffee.streamlit.app`
- ✅ Banco de dados privado e criptografado
- ✅ Mobile responsivo ativado
- ✅ Pronto para receber dados de extração
