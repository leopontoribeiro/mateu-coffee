# 🧪 TESTE LOCAL - Checklist Completo

## PRÉ-REQUISITOS

- [ ] Python 3.8+ instalado
- [ ] PostgreSQL/Neon/Supabase com acesso (credenciais em mãos)
- [ ] Pip atualizado: `pip install --upgrade pip`

---

## ETAPA 1: Setup Local (3 min)

```bash
cd ~/mateu-coffee

# Criar virtual environment (se não existir)
python3 -m venv venv
source venv/bin/activate  # ou: venv\Scripts\activate (Windows)

# Instalar dependências
pip install -r requirements.txt

# Aguarde conclusão...
```

**Esperado:**
```
✓ Successfully installed streamlit psycopg2-binary pandas plotly ...
```

---

## ETAPA 2: Criar Schema no Banco (3 min)

### Se usar Supabase:
1. Acesse https://app.supabase.com
2. Seu projeto → SQL Editor
3. Cole todo conteúdo de `schema.sql`
4. Clique "Run"
5. Aguarde ✓

### Se usar Neon:
1. Acesse https://console.neon.tech
2. Seu projeto → SQL Editor
3. Cole todo conteúdo de `schema.sql`
4. Clique "Execute"
5. Aguarde ✓

### Se usar PostgreSQL local:
```bash
psql -U seu_usuario -d seu_database -f schema.sql
```

**Verificar criação:**
```sql
SELECT * FROM information_schema.tables WHERE table_name IN ('usuarios', 'cafes', 'extractions');
```

Deve retornar 3 linhas ✓

---

## ETAPA 3: Criar secrets.toml (1 min)

```bash
# Criar diretório se não existir
mkdir -p .streamlit

# Criar arquivo secrets.toml
cat > .streamlit/secrets.toml << 'EOF'
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "sua_region.neon.tech"  # ou supabase host
port = 5432
database = "neondb"  # ou seu database
username = "seu_usuario"
password = "sua_senha_aqui"
EOF
```

**Exemplo real (Neon):**
```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "ep-weathered-cell-123456.us-east-1.aws.neon.tech"
port = 5432
database = "neondb"
username = "neondb_owner"
password = "AbCd1234EfGh5678"
```

**NÃO COMMITÁ ESTE ARQUIVO:**
- Ele está em `.gitignore` ✓
- Secrets.toml é apenas local

---

## ETAPA 4: Rodá App Localmente (2 min)

```bash
# Certifique-se que venv está ativo
source venv/bin/activate

# Rodar app
streamlit run streamlit_app.py
```

**Esperado na primeira execução:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.X.X:8501
```

---

## ETAPA 5: TESTE DO APP - Checklist

### 5.1 Verificar Carregamento
- [ ] Página abre sem erros em http://localhost:8501
- [ ] Vê tela de login/registro
- [ ] Sem erro "ModuleNotFoundError"
- [ ] Sem erro "Connection refused"

### 5.2 Teste de Registro
```
1. Clique em campo "Email" (direito)
2. Digite: teste@mateu.com
3. Nome: Barista Teste
4. Senha: Senha123
5. Confirmar Senha: Senha123
6. Clique "Criar Conta"
```

**Esperado:**
- [ ] Sucesso: "Conta criada! Faça login para continuar."
- [ ] Ou erro se email já existe (esperado na 2ª tentativa)

### 5.3 Teste de Login
```
1. Email: teste@mateu.com
2. Senha: Senha123
3. Clique "Entrar"
```

**Esperado:**
- [ ] Página muda para Home
- [ ] Vê 4 cards com estatísticas (todos com 0 inicialmente)
- [ ] Vê 3 abas: "📦 Cafés", "☕ Extrações", "📊 Histórico"

### 5.4 Teste de Café
```
ABA: Cafés (lado direito - "Novo Café")
1. Nome: Etiópia Yirgacheffe
2. Origem: Etiópia
3. Tipo: Filtrado
4. Torrefação: Leve
5. Preço/kg: 85.50
6. Notas: Notas florais, acidez brilhante
7. Clique "Adicionar Café"
```

**Esperado:**
- [ ] Mensagem: "Café adicionado com sucesso"
- [ ] Café aparece na listagem (lado esquerdo)
- [ ] Botão "Deletar" disponível

### 5.5 Teste de Extração
```
ABA: Extrações
1. Café: Etiópia Yirgacheffe (dropdown)
2. Data: Hoje
3. Gramas de Café: 18.5
4. Gramas de Água: 300
5. Tempo: 28
6. Temperatura: 92.5
7. Pressão: 9.0
8. Método: Espresso
9. Notas: Extração perfeita, crema dourada
10. Clique "Registrar Extração"
```

**Esperado:**
- [ ] Mensagem: "Extração registrada com sucesso"
- [ ] Extração aparece na listagem (lado direito)
- [ ] Cards da Home agora mostram dados:
  - [ ] "Consumo Hoje" = 18.5g
  - [ ] "Esta Semana" = 18.5g

### 5.6 Teste de Histórico
```
ABA: Histórico
```

**Esperado:**
- [ ] DataFrame com 1 linha
- [ ] Colunas: Data, Café, Gramas, Método, Tempo, Temp
- [ ] "Total Consumido" = 18.5g
- [ ] "Média por Extração" = 18.5g

### 5.7 Teste de Deleção
```
ABA: Extrações (lado direito)
- Clique "Deletar" na extração
```

**Esperado:**
- [ ] Extração some
- [ ] Cards Home voltam a 0
- [ ] Histórico vazio novamente

### 5.8 Teste de Logout
```
Home (topo direito)
- Clique "Sair"
```

**Esperado:**
- [ ] Volta à tela de login
- [ ] Session limpa

---

## ETAPA 6: VALIDAÇÃO BANCO DE DADOS

Após testes, verifique dados no banco:

```sql
-- Verificar usuários
SELECT id, email, nome FROM usuarios;
-- Deve ter: 1 | teste@mateu.com | Barista Teste

-- Verificar cafés
SELECT id, user_id, nome, origem FROM cafes;
-- Deve ter: 1 | 1 | Etiópia Yirgacheffe | Etiópia

-- Verificar extractions (se não foi deletada)
SELECT id, user_id, cafe_id, gramas_cafe, data FROM extractions;
-- Vazio ou 1 linha (depende se deletou)
```

---

## ✅ SUCESSO = TODAS ESTAS CAIXAS MARCADAS

- [ ] App rodou sem erros
- [ ] Conta criada com sucesso
- [ ] Login funcionou
- [ ] Café adicionado e listado
- [ ] Extração registrada
- [ ] Dados aparecem em Home
- [ ] Histórico mostra dados reais
- [ ] Deleção funciona
- [ ] Logout funciona
- [ ] Banco tem dados corretos

---

## ❌ SE DER ERRO

### Erro: `ModuleNotFoundError: No module named 'streamlit'`
```bash
pip install -r requirements.txt
```

### Erro: `Connection refused` ou `could not connect to server`
```bash
1. Verifique credentials em .streamlit/secrets.toml
2. Teste conexão direta:
   psql -h seu_host -U seu_user -d seu_db
3. Se errar ali também, credenciais estão erradas
```

### Erro: `FATAL: password authentication failed`
```bash
1. Copie credenciais EXATAMENTE do Neon/Supabase
2. Sem espaços extras
3. Sem caracteres especiais não escapados
```

### Erro: `relation "usuarios" does not exist`
```bash
1. schema.sql não foi executado
2. Volte à ETAPA 2
3. Verifique com: SELECT * FROM information_schema.tables
```

### App roda mas tudo está vazio
```bash
1. Esperado na 1ª vez
2. Crie um café e uma extração
3. Os dados aparecerão
```

### Erro: `psycopg2.OperationalError: timeout`
```bash
1. Banco pode estar offline
2. Ou internet ruim
3. Aguarde 30 seg e tente novamente
```

---

## 📸 SCREENSHOT ESPERADO (Home após testes)

```
┌─────────────────────────────────────────────────┐
│ ☕ Olá, Barista Teste                     [Sair] │
├─────────────────────────────────────────────────┤
│
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │    1     │  │    1     │  │  18.5g   │  │  18.5g   │
│  │ Cafés    │  │Extrações │  │ Consumo  │  │Esta      │
│  │Cadastr.  │  │          │  │Hoje      │  │Semana    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│
│  [📦 Cafés]  [☕ Extrações]  [📊 Histórico]
│  
│  (Conteúdo da aba selecionada...)
│
└─────────────────────────────────────────────────┘
```

---

## 🚀 APÓS SUCESSO NO TESTE LOCAL

1. Commit: `git add -A && git commit -m "Local test: ✓ All features working"`
2. Push: Via GitHub Desktop (PUSH_GITHUB_DESKTOP_INSTRUCOES.md)
3. Deploy: Streamlit Cloud (00_FAZER_AGORA.md)

---

**Tempo estimado:** 15 minutos | **Dificuldade:** Baixa

Se tudo passar → **PRONTO PARA PRODUÇÃO** 🎉
