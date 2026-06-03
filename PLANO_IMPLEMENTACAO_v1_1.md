# PLANO DE IMPLEMENTAÇÃO | Mateu Coffee v1.1

**Status**: ✅ APROVADO PARA EXECUÇÃO  
**Versão**: v1.1 CORRIGIDO  
**Data**: 2026-06-02  
**Tempo estimado**: 2-3 horas (setup + testes + deploy)

---

## 🎯 OBJETIVO

Colocar **Mateu Coffee v1.1 no ar** com todas as correções críticas aplicadas.

---

## 📋 PRÉ-REQUISITOS

- [ ] Git instalado: `git --version`
- [ ] Python3 instalado: `python3 --version`
- [ ] Conta GitHub (privada recomendada)
- [ ] Conta Neon.tech (gratuito)
- [ ] Conta Streamlit Cloud

---

## ⏱️ TIMELINE

| Fase | Duração | O que fazer |
|------|---------|------------|
| **1. Setup Local** | 20 min | Script de automação |
| **2. Testar v1.1** | 45 min | Validação em localhost |
| **3. GitHub + Deploy** | 30 min | Push + Streamlit Cloud |
| **4. Validação Final** | 15 min | Testes no ar |
| **TOTAL** | **~2h** | Aplicação 100% online |

---

## 🚀 FASE 1: SETUP LOCAL (20 MIN)

### **PASSO 1.1: Criar Estrutura do Projeto**

```bash
# Crie diretório
mkdir ~/mateu-coffee-v1_1
cd ~/mateu-coffee-v1_1

# Inicialize Git
git init
```

### **PASSO 1.2: Copiar Arquivos**

**Arquivo 1: app_cloud_CORRIGIDO.py → app_cloud.py**

```bash
# Copie o conteúdo completo de app_cloud_CORRIGIDO.py
# Salve como: ~/mateu-coffee-v1_1/app_cloud.py
```

**Arquivo 2: requirements.txt**

```bash
cat > requirements.txt << 'EOF'
streamlit==1.35.0
pandas==2.1.4
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pytz==2023.3.post1
EOF
```

**Arquivo 3: .gitignore**

```bash
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
```

### **PASSO 1.3: Criar Diretório Streamlit**

```bash
mkdir -p .streamlit
```

### **PASSO 1.4: Commit Local**

```bash
git add app_cloud.py requirements.txt .gitignore
git commit -m "Mateu Coffee v1.1 - Initial commit with production-grade validations"
```

---

## ✅ FASE 2: TESTAR v1.1 LOCALMENTE (45 MIN)

### **PASSO 2.1: Criar Banco PostgreSQL (Neon.tech)**

1. Acesse: https://neon.tech
2. Sign Up → Crie projeto PostgreSQL
3. Copie **Connection String** completa
4. Exemplo:
   ```
   postgresql://seu_usuario:sua_senha@ep-weathered-cell-123456.us-east-1.aws.neon.tech:5432/neondb?sslmode=require
   ```

### **PASSO 2.2: Criar Secrets Local**

```bash
cd ~/mateu-coffee-v1_1
mkdir -p .streamlit

cat > .streamlit/secrets.toml << 'EOF'
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu_host_do_neon.neon.tech"
port = 5432
database = "neon"
username = "seu_usuario"
password = "sua_senha"
EOF
```

⚠️ **Substitua pelos valores reais do Neon**

### **PASSO 2.3: Instalar Dependências**

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### **PASSO 2.4: Executar Localmente**

```bash
streamlit run app_cloud.py
```

Abre em: `http://localhost:8501`

### **PASSO 2.5: CHECKLIST DE TESTES**

Teste cada cenário:

- [ ] **Página carrega sem erro**
  - Esperado: 3 abas visíveis (Cadastro, Preparo, Histórico)

- [ ] **Validação de Inputs - Nome Vazio**
  - Aba "Cadastro" → Digite "  " (espaços) no nome
  - Clique "Registrar Grão"
  - Esperado: ⚠️ "Nome obrigatório" (erro visual)
  - ✅ Não registra no banco

- [ ] **Validação de Inputs - Peso Inválido**
  - Digite "0" em "Peso da Embalagem"
  - Esperado: ⚠️ "Peso deve estar entre 100g e 5000g"

- [ ] **Validação de Inputs - Data Futura**
  - "Data de Torra" → Selecione data futura
  - Esperado: ⚠️ "Data de torra não pode ser futura"

- [ ] **Cadastro OK - Grão Válido**
  - Nome: "Etíopia Yirgacheffe"
  - Origem: "Etíopia"
  - Clique "Registrar Grão"
  - Esperado: ✅ "Grão registrado com sucesso!"

- [ ] **Preparo OK - Brew Ratio Cálculo**
  - Selecione o café criado
  - Dose: 18g, Volume: 42ml
  - Esperado: Brew Ratio mostra "2.33:1" (com destaque visual azul)

- [ ] **Preparo - Validação Soft (Aviso)**
  - Método: "Espresso"
  - Cliques: "35" (fora da zona ideal 18-25)
  - Esperado: ⚠️ "Cliques ideais para Espresso: 18-25" (em caixa amarela, mas permite continuar)

- [ ] **Preparo - Double-Click Test**
  - Preencha tudo, clique "Registrar Preparo"
  - Rapidamente clique 2 vezes no botão
  - Esperado: Spinner aparece, botão desabilitado, apenas 1 preparo registrado

- [ ] **Histórico - Métricas Aparecem**
  - Aba "Histórico"
  - Esperado: 
    - Total de Extrações: 1
    - Avaliação Média: X⭐
    - Brew Ratio Médio: X:1
    - Tabela com dados

- [ ] **Export Options**
  - Botão "📥 Exportar CSV" → download funciona
  - Botão "📦 Backup JSON" → download funciona
  - Esperado: Arquivos baixam com timestamp

- [ ] **Mobile Layout**
  - DevTools → Toggle Device Toolbar → iPhone 14 (390x844)
  - Checkboxes em stack vertical (um por linha)
  - Esperado: Fácil tocar com dedo, sem horizontal scroll

- [ ] **Error Handling**
  - Feche temporariamente o banco (ou desconecte internet)
  - Recarregue página
  - Esperado: ❌ "Banco de dados offline" no startup, app para

**Resultado esperado**: ✅ Todos os testes passed

### **PASSO 2.6: Apagar Secrets Local (Segurança)**

```bash
rm .streamlit/secrets.toml
# ✅ Não vai mais para GitHub
```

---

## 📤 FASE 3: GITHUB + DEPLOY (30 MIN)

### **PASSO 3.1: Criar Repositório GitHub**

1. Acesse: https://github.com/new
2. Preencha:
   - Repository name: `mateu-coffee`
   - Description: "Mateu Coffee | Engenharia de Extração de Cafés"
   - **Private**: ✅ SIM
   - **Initialize this repository**: ❌ NÃO (vamos fazer via CLI)
3. Clique "Create repository"

### **PASSO 3.2: Push para GitHub**

```bash
cd ~/mateu-coffee-v1_1

# Adicione origem remota
git remote add origin https://github.com/SEU_USUARIO/mateu-coffee.git

# Renomeie branch para main
git branch -M main

# Push
git push -u origin main
```

Se pedir credenciais:
- Username: seu_usuario_github
- Password: seu_token_github (gere em https://github.com/settings/tokens)

### **PASSO 3.3: Verificar GitHub**

1. Acesse: https://github.com/seu_usuario/mateu-coffee
2. Verifique:
   - [ ] 3 arquivos visíveis: app_cloud.py, requirements.txt, .gitignore
   - [ ] ❌ **NÃO vê** `.streamlit/secrets.toml` (está em .gitignore)

---

## 🚀 FASE 4: DEPLOY STREAMLIT CLOUD (30 MIN)

### **PASSO 4.1: Deploy do Repositório**

1. Acesse: https://share.streamlit.io
2. Clique "New app" (canto superior direito)
3. Preencha:
   - **GitHub repo**: seu_usuario/mateu-coffee
   - **Branch**: main
   - **Main file path**: app_cloud.py
4. Clique "Deploy"

**Status esperado:**
```
Running... ⏳ (aguarde 3-5 minutos)
✅ App is live at: https://seu-username-mateu-coffee.streamlit.app
```

### **PASSO 4.2: Adicionar Secrets no Streamlit Cloud**

1. Seu app está online em: `https://seu-username-mateu-coffee.streamlit.app`
2. Clique ⚙️ (engrenagem, canto superior direito)
3. Aba "Secrets"
4. Cole **exatamente** o mesmo conteúdo (credenciais Neon):

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu_host_do_neon.neon.tech"
port = 5432
database = "neon"
username = "seu_usuario"
password = "sua_senha"
```

5. Clique "Save"

**App redeployará automaticamente** (2-3 min)

---

## ✨ FASE 5: VALIDAÇÃO FINAL (15 MIN)

### **PASSO 5.1: Testar URL Pública**

Acesse: `https://seu-username-mateu-coffee.streamlit.app`

### **PASSO 5.2: Repetir CHECKLIST TESTES (Fase 2.5)**

Execute os mesmos 12 testes, agora na URL pública.

**Resultado esperado**: ✅ Todos os testes passed (mesmo que local)

### **PASSO 5.3: Teste Geral**

1. Cadastre 2 cafés diferentes
2. Registre 3 preparos variados
3. Veja histórico e métricas
4. Exporte CSV + JSON
5. Acesse no celular

**Esperado**: Tudo funciona perfeitamente

---

## 📝 CHECKLIST FINAL PRÉ-PRODUÇÃO

- [ ] **Local**: Todos os 12 testes passaram
- [ ] **GitHub**: Repositório private, sem secrets
- [ ] **Streamlit Cloud**: App online e funcionando
- [ ] **Secrets**: Credenciais adicionadas no Cloud
- [ ] **URL Pública**: Todos os 12 testes passaram novamente
- [ ] **Mobile**: Testado em celular, responsive OK
- [ ] **Backup**: CSV e JSON exportam sem erros
- [ ] **Database**: Índices criados (automático no init)

✅ **Se todos os itens marcados → PRONTO PARA PRODUÇÃO**

---

## 🎯 RESUMO EXECUTIVO

| Fase | Tempo | Status |
|------|-------|--------|
| Setup Local | 20 min | ✅ Script pronto |
| Testes v1.1 | 45 min | ✅ 12 cenários |
| GitHub + Deploy | 30 min | ✅ Automático |
| Validação | 15 min | ✅ Checklist |
| **TOTAL** | **~2h** | **✅ ONLINE** |

---

## 🔐 SEGURANÇA - CONFIRMADO

- ✅ Secrets NUNCA commitados (em .gitignore)
- ✅ Credenciais PostgreSQL APENAS no Streamlit Cloud
- ✅ Repositório GitHub é PRIVADO
- ✅ App protegido por validações rigorosas
- ✅ Índices criados para performance
- ✅ Backup JSON automático

---

## 📞 SUPORTE DURANTE EXECUÇÃO

Se erro aparecer:

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError: streamlit` | `pip install -r requirements.txt` |
| `Connection refused` | Credenciais Neon incorretas em secrets.toml |
| `FATAL: password auth failed` | Copie credenciais EXATAS do Neon |
| `Name already exists` | Cafe com mesmo nome já cadastrado (esperado) |
| App quebra ao registrar | Banco offline, tente refresh |

---

## ✅ PRÓXIMA AÇÃO

**Você está pronto para executar este plano.**

**Tempo: 2-3 horas até estar no ar.**

**Comece agora:**

```bash
# PASSO 1.1
mkdir ~/mateu-coffee-v1_1
cd ~/mateu-coffee-v1_1
git init
```

**Após terminar toda a timeline, você terá:**
- ✅ App rodando localmente
- ✅ Código no GitHub
- ✅ URL pública funcionando
- ✅ Pronto para usar

---

**Qual próxima ação? (Execute agora ou tem dúvidas?)**

