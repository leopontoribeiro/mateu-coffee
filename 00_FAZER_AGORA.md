# ⚡ FAZER AGORA - 3 PASSOS (5 minutos)

## 🎯 VOCÊ ESTÁ AQUI

App redesenhado, design system implementado, código pronto no repositório local.

**Faltam apenas 3 ações manuais para colocar em produção.**

---

## PASSO 1️⃣ - PUSH PARA GITHUB (1 min)

**Abra Terminal e execute:**

```bash
cd ~/mateu-coffee-v1_1
git push origin main
```

**Se der erro**, use GitHub Desktop:
1. Abra GitHub Desktop
2. Selecione "mateu-coffee"
3. Clique "Push origin"

---

## PASSO 2️⃣ - DEPLOY STREAMLIT CLOUD (2 min)

**Vá para**: https://share.streamlit.io/

1. Clique "New app"
2. Preencha:
   - Repository: `leopontoribeiro/mateu-coffee`
   - Branch: `main`
   - Main file: `streamlit_app.py`
3. Clique "Deploy"

**Aguarde 1-2 minutos enquanto Streamlit faz deploy...**

---

## PASSO 3️⃣ - CONFIGURAR SECRETS (1 min)

**Após deploy aparecer:**

1. Clique no seu app na lista
2. Clique ⚙️ **Settings** (canto superior direito)
3. Clique **Secrets** (sidebar esquerdo)
4. Cole isto com seus dados:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg"
host = "SEU_HOST.neon.tech"
port = 5432
database = "neondb"
username = "neondb_owner"
password = "SUA_SENHA_AQUI"
```

5. Clique "Save"

**App reinicia automaticamente ✓**

---

## ✅ PRONTO!

Seu app estará em:

```
https://share.streamlit.io/leopontoribeiro/mateu-coffee/streamlit_app.py
```

---

## 🧪 TESTE

Verifique:
- ☕ Dashboard carrega
- 📦 Adicionar/remover grãos
- ☕ Calcular ratio
- 📊 Ver histórico
- ⚙️ Config acessível

---

## ⏱️ TEMPO TOTAL

| Ação | Tempo |
|------|-------|
| Push | 1 min |
| Deploy | 2 min |
| Secrets | 1 min |
| **Total** | **~5 min** |

---

## 🚀 VAMOS LÁ!

Execute PASSO 1 agora! ⬆️

---

*Documentação completa em ENTREGA_FINAL.md*
