# 📤 INSTRUÇÕES: PUSH PARA GITHUB (GitHub Desktop)

Como o ambiente de workspace não permite push via CLI (erro 403 proxy), use **GitHub Desktop** para fazer o push.

---

## PASSO 1: Abrir GitHub Desktop

1. Abra o app **GitHub Desktop** (já instalado)
2. Você verá a lista de repositórios locais

---

## PASSO 2: Selecionar Repositório

1. Na lista esquerda, clique em **"mateu-coffee"**
2. Você verá na aba "Changes" os arquivos modificados:
   ```
   - schema.sql (NOVO)
   - auth.py (NOVO)
   - database.py (NOVO)
   - streamlit_app_final.py (MODIFICADO)
   - requirements.txt (MODIFICADO)
   - PRIORIDADES_IMPLEMENTADAS.md (NOVO)
   - RESUMO_EXECUCAO_4_PRIORIDADES.txt (NOVO)
   ```

---

## PASSO 3: Revisar Mudanças

1. Clique em cada arquivo para ver as mudanças (aba "Changes")
2. Verifique que estão corretos:
   - `schema.sql`: Deve ter 82 linhas (tabelas + índices + triggers)
   - `auth.py`: Deve ter ~100 linhas (funções de autenticação)
   - `database.py`: Deve ter ~240 linhas (CRUD e estatísticas)
   - `streamlit_app_final.py`: Deve ter ~478 linhas (reescrito com integração)
   - `requirements.txt`: Deve ter `pandas>=2.0.0` adicionado

---

## PASSO 4: Fazer Commit Local

1. No canto inferior esquerdo, você verá:
   - Campo "Summary" (obrigatório)
   - Campo "Description" (opcional)

2. No "Summary", escreva:
   ```
   PRIORIDADE 1-4: Schema PostgreSQL, Autenticação Real, CRUD Funcional e Dashboard com Dados Reais
   ```

3. No "Description" (opcional, mas recomendado):
   ```
   Schema PostgreSQL com tabelas usuarios, cafes, extractions
   Autenticação com hash PBKDF2-SHA256 + salt
   CRUD funcional para cafés e extrações com isolamento user_id
   Dashboard com dados reais do PostgreSQL
   4 abas: Cafés, Extrações, Histórico
   Pronto para deploy automático no Streamlit Cloud/Render
   
   5 files changed, 758 insertions(+)
   - schema.sql (novo)
   - auth.py (novo)
   - database.py (novo)
   - streamlit_app_final.py (reescrito)
   - requirements.txt (atualizado)
   ```

4. Clique no botão **"Commit to main"**
   - Você verá: "✓ Committed 1 commit"

---

## PASSO 5: Push para GitHub

1. Após o commit, você verá um botão **"Push origin"** no topo
2. Clique nele
3. Aguarde alguns segundos
4. Você verá: "✓ Pushed 1 commit to origin"

---

## PASSO 6: Verificar no GitHub Web

1. Abra https://github.com/leopontoribeiro/mateu-coffee
2. Você deve ver:
   - Os 5 arquivos novos/modificados no commit mais recente
   - A mensagem do commit que copiou
   - "Last commit: agora mesmo" (ou poucos minutos atrás)

---

## ✅ PRONTO PARA DEPLOY!

Após o push ser bem-sucedido, prossiga com:

### OPÇÃO A: Streamlit Cloud
1. Acesse https://share.streamlit.io/
2. Clique "New app"
3. Preencha:
   - GitHub repo: `leopontoribeiro/mateu-coffee`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
4. Clique "Deploy"
5. Aguarde 3-5 minutos
6. Vá em Settings → Secrets → adicione credenciais PostgreSQL

### OPÇÃO B: Render
1. Acesse https://render.com
2. New Web Service
3. Connect GitHub repo (mateu-coffee)
4. Branch: main
5. Build: `pip install -r requirements.txt`
6. Start: `streamlit run streamlit_app.py`
7. Environment variables: DATABASE_URL

---

## ❌ SE DER ERRO

### Erro: "Nothing to commit"
- Significa que os arquivos já foram commitados
- Você pode fazer push direto (Passo 5)

### Erro: "Push failed - authentication"
- Verifique se você está logado no GitHub Desktop
- Menu: File → Options → Accounts
- Clique "Sign Out" e "Sign In" novamente

### Erro: "Permission denied"
- Verifique se o repositório é Público ou você tem acesso
- Ou use GitHub Web interface (web.github.com)

### Erro: "HEAD.lock exists"
- Não é problema do GitHub Desktop
- Ele vai resolver automaticamente no próximo push

---

## 📞 CHECKLIST FINAL

- [ ] Abri GitHub Desktop
- [ ] Selecionei "mateu-coffee"
- [ ] Vi os 5 arquivos na aba "Changes"
- [ ] Revisei as mudanças
- [ ] Fiz commit com mensagem clara
- [ ] Cliquei "Push origin" e esperou ✓
- [ ] Verifiquei em https://github.com/leopontoribeiro/mateu-coffee
- [ ] Pronto para deploy!

---

**Data:** 8 Jun 2026 | **Tempo estimado:** 2-3 minutos

Se tudo correr bem, em ~5-10 minutos seu app estará no ar no Streamlit Cloud! 🚀
