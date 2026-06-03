# 🚀 EXECUTE AGORA | 3 Etapas para Colocar Mateu Coffee no Ar

**Tempo total: ~15 minutos**

---

## ✅ PRÉ-REQUISITO

- [ ] Git instalado: `git --version`
- [ ] Python3 instalado: `python3 --version`
- [ ] Conta GitHub (gratuito): https://github.com
- [ ] Conta Neon.tech (gratuito): https://neon.tech

---

## 🎯 ETAPA 1: SETUP LOCAL (5 MIN)

Execute este comando no terminal:

```bash
bash DEPLOY_AUTOMATION.sh
```

**O que faz:**
- ✅ Cria diretório `~/mateu-coffee`
- ✅ Copia todos os arquivos da aplicação
- ✅ Instala dependências Python
- ✅ Inicializa repositório Git local

**Resultado esperado:**
```
✅ SETUP LOCAL COMPLETO
Diretório do projeto: /Users/eusouleandroribeiro/mateu-coffee
```

---

## 🎯 ETAPA 2: CRIAR BANCO PostgreSQL (3 MIN)

### **A. Neon.tech (Recomendado)**

1. Acesse: https://neon.tech
2. Clique "Sign Up" (gratuito)
3. Use sua conta Google/GitHub
4. Crie projeto novo (defaults estão OK)
5. Aguarde criação (30 seg)
6. Clique em seu projeto
7. Copie a **Connection String** (parece assim):

```
postgresql://seu_usuario:sua_senha@sua_region.neon.tech:5432/neon?sslmode=require
```

**Extraia estes valores:**
- `host`: `sua_region.neon.tech`
- `port`: `5432`
- `database`: `neon`
- `username`: `seu_usuario`
- `password`: `sua_senha`

### **B. Ou use Supabase (Alternativa)**

1. Acesse: https://supabase.com
2. Crie projeto (mesmo processo)
3. Vai em Settings → Database → Connection pooling
4. Copia URI e extrai os mesmos valores acima

---

## 🎯 ETAPA 3: DEPLOY (7 MIN)

### **PASSO 1: Criar Secrets Local**

Execute (substitua pelos seus valores do Neon):

```bash
cd ~/mateu-coffee
mkdir -p .streamlit

cat > .streamlit/secrets.toml << 'EOF'
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "sua_region.neon.tech"
port = 5432
database = "neon"
username = "seu_usuario_neon"
password = "sua_senha_neon"
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
username = "neonuser"
password = "AbCd1234EfGh5678"
```

### **PASSO 2: Testar Localmente**

```bash
cd ~/mateu-coffee
source venv/bin/activate
streamlit run app_cloud.py
```

Abre em `http://localhost:8501`

**Checklist:**
- [ ] Página carrega sem erros
- [ ] 3 abas visíveis (Cadastro, Preparo, Histórico)
- [ ] Consegue digitar nos inputs
- [ ] Tabela "Histórico" aparece (vazia é normal)

Se OK → Aperte `Ctrl+C` para parar

### **PASSO 3: Push para GitHub**

1. Acesse https://github.com/new
2. Crie repositório:
   - Nome: `mateu-coffee`
   - Private: **SIM**
   - Clique "Create repository"

3. Copie os comandos que aparecem (vai ser algo assim):

```bash
cd ~/mateu-coffee
git remote add origin https://github.com/SEU_USUARIO/mateu-coffee.git
git branch -M main
git push -u origin main
```

4. Execute no terminal
5. Digite seu GitHub token (gere em https://github.com/settings/tokens)

**Verificação:**
- [ ] Acesse https://github.com/seu_usuario/mateu-coffee
- [ ] Vê 7 arquivos: app_cloud.py, requirements.txt, .gitignore, etc
- [ ] **NÃO vê arquivo `secrets.toml`** ✅ (está em .gitignore)

### **PASSO 4: Deploy Streamlit Cloud**

1. Acesse https://share.streamlit.io
2. Clique "New app" (canto superior direito)
3. Preencha:
   - **GitHub repo**: SEU_USUARIO/mateu-coffee
   - **Branch**: main
   - **Main file path**: app_cloud.py
4. Clique "Deploy"
5. Aguarde 3-5 minutos

**Status esperado:**
```
Running... ⏳
✅ App deployed successfully
```

### **PASSO 5: Adicionar Secrets no Cloud**

1. Seu app está em: `https://seu-username-mateu-coffee.streamlit.app`
2. Clique engrenagem ⚙️ (canto superior direito)
3. Aba "Secrets"
4. Cole **exatamente** o mesmo conteúdo do `.streamlit/secrets.toml`:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "ep-weathered-cell-123456.us-east-1.aws.neon.tech"
port = 5432
database = "neondb"
username = "neonuser"
password = "AbCd1234EfGh5678"
```

5. Clique "Save"
6. App redeployará (2-3 min)

### **PASSO 6: Validar**

Acesse seu URL: `https://seu-username-mateu-coffee.streamlit.app`

**Checklist:**
- [ ] Página carrega sem erros
- [ ] 3 abas carregam
- [ ] Consegue cadastrar um café
- [ ] Consegue registrar um preparo
- [ ] Histórico mostra os dados

✅ **SE TUDO OK: APLICAÇÃO ESTÁ NO AR**

---

## 🔒 SEGURANÇA: CHECKLIST FINAL

- [ ] `.streamlit/secrets.toml` **NUNCA** foi commitado no GitHub (verificar em /settings/secrets on Streamlit Cloud, não no GitHub)
- [ ] Repositório GitHub é **PRIVATE**
- [ ] Credenciais estão **APENAS** no Streamlit Cloud Secrets Manager
- [ ] Você consegue acessar a URL pública sem erros

---

## ❌ SE ALGO DER ERRADO

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError: psycopg2` | Rode `pip install -r requirements.txt` novamente |
| `Connection refused` no app | Verifique secrets.toml (host, port, user, password) |
| `ERROR in logs: FATAL: password authentication failed` | Copie credenciais EXATAS do Neon |
| App carrega mas tabelas vazias | Normal na 1ª vez. Cadastre um café. |
| GitHub diz `permission denied` | Crie token em https://github.com/settings/tokens (repo scope) |

---

## 📱 TESTAR EM MOBILE

1. Abra seu URL em celular
2. Vá em Safari/Chrome → Menu → "Desktop Site" para desativar
3. Layout responsivo ativa automaticamente

---

## 🎯 PRÓXIMOS PASSOS

Após tudo online:

1. Cadastre 3-5 cafés diferentes
2. Registre extrações variadas (teste parâmetros diferentes)
3. Envie dados para Barista Engine para análise
4. Itere: teste recomendações → registre novos dados

---

## 📞 PRECISA DE HELP?

- **Erro de deploy**: Veja logs em Streamlit Cloud → Settings → Logs
- **Erro de banco**: Teste credenciais direto em Neon.tech → SQL Editor
- **Código não funciona**: Verifique `app_cloud.py` está idêntico ao arquivo gerado

---

**EXECUTE AGORA:** `bash DEPLOY_AUTOMATION.sh` 🚀

Tempo estimado: 15 min até ter aplicativo no ar.
