# 🚀 INSTRUÇÕES DE DEPLOY - MATEU BARISTA v1.1

## ✅ O QUE JÁ FOI FEITO

- ✓ Design system implementado (design_system.py)
- ✓ App padronizado (app_padronizado.py)
- ✓ Configuração Streamlit (.streamlit/config.toml)
- ✓ Arquivos copiados para repositório
- ✓ Git commit realizado (**ad611a2**)
- ✓ Commit pronto para push

---

## ⚠️ PRÓXIMOS PASSOS (Manual)

### 1️⃣ **Fazer Push para GitHub**

**Opção A: Via GitHub Desktop ou Git CLI**

```bash
cd ~/mateu-coffee-v1_1
git push origin main
```

Ou no GitHub Desktop:
1. Abra GitHub Desktop
2. Selecione repositório `mateu-coffee`
3. Clique em "Push origin"

**Opção B: Via GitHub Web**

Se o push local não funcionar:
1. Vá para https://github.com/leopontoribeiro/mateu-coffee
2. Copie os arquivos manualmente para a branch `main`:
   - design_system.py
   - app_padronizado.py
   - streamlit_app.py
   - .streamlit/config.toml

---

### 2️⃣ **Configurar no Streamlit Cloud**

Após fazer push (ou após upload manual):

#### A. Acessar Streamlit Cloud
```
https://share.streamlit.io/
```

#### B. Criar Novo App
1. Clique em "New app"
2. Selecione seu GitHub account
3. Escolha repositório: `mateu-coffee`
4. Selecione branch: `main`
5. Caminho do app: `streamlit_app.py`
6. Clique em "Deploy"

#### C. Configurar Secrets
Após o deploy inicial, clique em "Advanced settings" > "Secrets":

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg"
host = "SEU_HOST.neon.tech"
port = 5432
database = "neondb"
username = "neondb_owner"
password = "SUA_SENHA"
```

---

## 📊 ARQUIVOS NO REPOSITÓRIO

```
mateu-coffee/
├── design_system.py           (1.100+ linhas)
├── app_padronizado.py         (500+ linhas)
├── streamlit_app.py           (4 linhas - entry point)
├── requirements.txt           (com psycopg==3.0.0)
├── .streamlit/
│   ├── config.toml           (tema + configurações)
│   └── secrets.toml          (⚠️ NÃO commitar!)
├── .gitignore                (protege secrets)
└── [outros arquivos]
```

---

## 🎯 VERIFICAÇÃO PRÉ-DEPLOY

- ✅ Arquivos copiados corretamente
- ✅ Commit realizado (ad611a2)
- ✅ .gitignore protege secrets.toml
- ✅ Design system importável
- ✅ App pronto para produção

---

## 🔐 CHECKLIST DE SEGURANÇA

Antes de fazer deploy, verifique:

- [ ] `.streamlit/secrets.toml` NÃO está no repositório
- [ ] Credenciais PostgreSQL estão apenas em `Manage Secrets` do Streamlit Cloud
- [ ] Nenhuma senha/chave em código commitado
- [ ] `.gitignore` está atualizado
- [ ] Arquivo `streamlit_app.py` aponta para `app_padronizado.py`

---

## 📱 APÓS DEPLOY

### Testar a Aplicação

1. **URL será**: `https://share.streamlit.io/leopontoribeiro/mateu-coffee/streamlit_app.py`
2. **Aguarde o carregamento** (primeira vez leva 1-2 min)
3. **Teste todas as seções**:
   - Dashboard (deve carregar 4 cards)
   - Grãos (formulário e lista)
   - Preparos (seleção e cálculo de ratio)
   - Histórico (tabela)
   - Configurações (perfil)

### Se Houver Erro

**Erro**: "ModuleNotFoundError: No module named 'design_system'"
- **Solução**: Certifique-se que design_system.py está no repositório

**Erro**: "psycopg2.OperationalError: connection failed"
- **Solução**: Verifique as credenciais PostgreSQL em `Manage Secrets`

**Erro**: "Streamlit config file not found"
- **Solução**: Confirme que `.streamlit/config.toml` está no repositório

---

## 📊 STATUS ATUAL

| Fase | Status | Ação |
|------|--------|------|
| Design System | ✅ Pronto | - |
| App Refatorizado | ✅ Pronto | - |
| Commit Local | ✅ Pronto | - |
| **Push GitHub** | ⏳ Manual | Fazer push |
| **Streamlit Deploy** | ⏳ Aguardando | Deploy após push |
| **Configurar Secrets** | ⏳ Após deploy | Adicionar credenciais |
| **Teste em Produção** | ⏳ Final | Validar funcionamento |

---

## 🎓 DICAS FINAIS

1. **Se der erro no push local**: Use GitHub Desktop ou web uploader
2. **Deploy leva 2-3 minutos**: Paciência é importante
3. **Primeiro acesso é lento**: Cache está sendo gerado
4. **Logs do Streamlit**: Clique em "View logs" para debug

---

## 📞 PRÓXIMOS PASSOS

1. ✅ Push dos arquivos para GitHub
2. ✅ Deploy no Streamlit Cloud
3. ✅ Adicionar secrets PostgreSQL
4. ✅ Testar aplicação completa
5. ✅ Monitorar performance

---

**Commit Hash**: ad611a2
**Data de Criação**: Junho 3, 2024
**Status**: 🟡 **AGUARDANDO PUSH**

**Próximo**: Fazer push para GitHub! 🚀
