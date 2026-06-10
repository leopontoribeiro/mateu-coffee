# Deployment v2.0 - Instrucoes Completas

## Pre-Deployment Checklist

### Local Development
- [x] Código testado localmente
- [x] Todos os testes passaram
- [x] Sem erros de sintaxe
- [x] Performance OK
- [x] Responsividade validada

### Git
- [ ] Código commitado
- [ ] Branch atualizado
- [ ] Sem merge conflicts
- [ ] Ready para push

---

## PASSO 1: Atualizar Database Schema

### 1.1 - Conectar ao PostgreSQL

```bash
# Production
psql -U [produser] -h [prod-host] -d mateu_coffee

# Local Testing
psql -U postgres -d mateu_coffee
```

### 1.2 - Executar Schema Update

```bash
# Opção 1: Via arquivo SQL
\i schema.sql

# Opção 2: Via comando direto
psql -U [user] -h [host] -d mateu_coffee -f schema.sql
```

### 1.3 - Verificar Migracao

```sql
-- Verificar novas colunas em extractions
SELECT column_name FROM information_schema.columns 
WHERE table_name='extractions' ORDER BY ordinal_position;

-- Esperado ver:
-- aroma
-- acidez
-- corpo
-- sabor_notas
-- nota_geral

-- Verificar nova tabela
SELECT * FROM shared_recipes LIMIT 1;
-- Esperado: (vazio ou com dados)

-- Verificar índices
SELECT * FROM pg_indexes WHERE tablename='shared_recipes';
```

### 1.4 - Backup (Recomendado)

```bash
# Antes de migrar
pg_dump mateu_coffee > backup_antes_v2.sql

# Depois de migrar
pg_dump mateu_coffee > backup_depois_v2.sql
```

---

## PASSO 2: Deploy em Streamlit Cloud

### 2.1 - Preparar Repositório GitHub

```bash
# Verificar estrutura
ls -la
# Esperado:
# streamlit_app_final.py (main app)
# database.py
# auth.py
# schema.sql
# requirements.txt
# .streamlit/secrets.toml (gitignore)
```

### 2.2 - Atualizar .gitignore

```bash
echo ".streamlit/secrets.toml" >> .gitignore
git add .gitignore
git commit -m "Update gitignore for secrets"
```

### 2.3 - Verificar requirements.txt

```txt
streamlit==1.35.0
plotly==5.22.0
psycopg2-binary==2.9.9
anthropic>=0.28.0
Pillow>=10.0.0
extra-streamlit-components>=0.1.71
pandas>=2.0.0
```

### 2.4 - Fazer Git Push

```bash
git add streamlit_app_final.py database.py schema.sql
git commit -m "Mateu Coffee v2.0 - Nova análise sensorial, comunidade e recomendações"
git push origin main
```

---

## PASSO 3: Configurar Streamlit Cloud

### 3.1 - Acessar Streamlit Cloud

https://share.streamlit.io

### 3.2 - Criar App Novo ou Atualizar Existente

**Nova App:**
1. Click "Create app"
2. Selecionar GitHub repository
3. Selecionar branch: main
4. Selecionar main file: `streamlit_app_final.py`
5. Click "Deploy"

**App Existente:**
1. Click no app em questão
2. Settings → Rerun ou atualiza automaticamente

### 3.3 - Configurar Secrets

1. Na Streamlit Cloud, click gear icon (Settings)
2. Click "Secrets"
3. Adicionar:

```toml
# .streamlit/secrets.toml
[connections.postgresql]
host = "your-db-host"
user = "your-db-user"
password = "your-db-password"
database = "mateu_coffee"
port = 5432

# Ou use DATABASE_URL
database_url = "postgresql://user:pass@host/mateu_coffee"
```

### 3.4 - Deploy

1. Salvar secrets
2. Streamlit Cloud faz auto-deploy
3. Aguardar ~2-3 minutos
4. Acessar URL: `https://share.streamlit.io/seu-usuario/seu-repo`

---

## PASSO 4: Verificar Deployment

### 4.1 - Health Check

```bash
# Acessar app
https://share.streamlit.io/[user]/[repo]

# Esperado: Login page com "Mateu Coffee" e 2 formulários
```

### 4.2 - Teste Rápido

1. Registrar conta nova
2. Fazer login
3. Ver tutorial
4. Criar café
5. Criar extração
6. Ver análises

**Esperado:** Tudo funciona em 2-3 minutos

### 4.3 - Verificar Database Connection

No Streamlit Cloud logs:
```
INFO:root:Connected to database successfully
```

Se erro:
```
ERROR:root:Database connection failed
```

---

## PASSO 5: Monitorar Deployment

### 5.1 - Logs do Streamlit Cloud

1. Dashboard → seu app
2. "Logs" tab (se não aparece, está OK)
3. Procurar por erros

### 5.2 - Erros Comuns

**Erro 1: ModuleNotFoundError: pandas**
```
Solução: Adicionar pandas>=2.0.0 em requirements.txt
```

**Erro 2: psycopg2 connection failed**
```
Solução: Verificar secrets.toml (host, user, password, database)
```

**Erro 3: Port 5432 refused**
```
Solução: Database offline? Verificar com admin
```

**Erro 4: st.connection error**
```
Solução: DATABASE_URL formato incorreto
Esperado: postgresql://user:pass@host/db
```

### 5.3 - Performance Monitoring

Streamlit Cloud Dashboard:
- Memory usage (esperado: 200-400MB)
- CPU usage (esperado: 10-30% idle)
- Response time (esperado: <2s por operação)

---

## PASSO 6: Post-Deployment

### 6.1 - Testar Fluxo Completo

Usar guia em `GUIA_TESTES_RAPIDOS_V2.md`

### 6.2 - Mobile Testing

1. iPhone Safari
2. Chrome Android
3. DevTools mobile emulation

### 6.3 - Recolher Feedback

1. Share link com beta testers
2. Coletar feedback sobre:
   - Performance
   - Usabilidade
   - Funcionalidades
   - Design

---

## PASSO 7: Rollback (Se Necessário)

### 7.1 - Rollback no Streamlit Cloud

```bash
# Opção 1: Voltar commit anterior
git revert HEAD
git push origin main
# Streamlit auto-redeploys em ~30 segundos

# Opção 2: Via Dashboard
Streamlit Cloud → Settings → Redeploy commit [anterior]
```

### 7.2 - Rollback Database

```bash
# Se algo deu errado com schema
psql -U [user] -d mateu_coffee -f backup_antes_v2.sql

# Verificar integridade
SELECT COUNT(*) FROM extractions;
SELECT COUNT(*) FROM cafes;
```

---

## PASSO 8: Otimizacoes Pos-Deploy

### 8.1 - Cache Optimization

No `streamlit_app_final.py`, adicionar:
```python
@st.cache_data(ttl=3600)
def listar_cafes_cached(user_id):
    return listar_cafes(user_id)
```

### 8.2 - Lazy Loading

Implementar apenas se performance degradar:
```python
if "carregou_cafes" not in st.session_state:
    st.session_state.carregou_cafes = False
```

### 8.3 - Database Connection Pooling

Se muitos usuários simultâneos:
```python
# database.py - adicionar pool
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(1, 20, ...)
```

---

## PASSO 9: Manutencao Continua

### 9.1 - Monitoramento Diário

- Verificar logs (0 erros esperado)
- Testar login/logout
- Testar criar café
- Testar registrar extração

### 9.2 - Updates de Dependências

```bash
# Anualmente ou quando patches saem
pip install --upgrade streamlit plotly psycopg2-binary
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

### 9.3 - Database Maintenance

```bash
# Mensal: VACUUM e ANALYZE
psql -U [user] -d mateu_coffee -c "VACUUM ANALYZE;"

# Anual: Full backup
pg_dump mateu_coffee > backup_$(date +%Y%m%d).sql
```

---

## CONFIGURACOES FINAIS

### Streamlit Config (`~/.streamlit/config.toml`)

```toml
[client]
showErrorDetails = false
toolbarMode = "minimal"

[logger]
level = "error"

[server]
headless = true
port = 8501
maxUploadSize = 200
enableCORS = true
```

### Nginx Reverse Proxy (Se behind proxy)

```nginx
location /mateu-coffee {
    proxy_pass http://localhost:8501;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

## TIMELINE ESTIMADO

| Fase | Tempo | Status |
|------|-------|--------|
| 1. Database Schema | 5 min | Imediato |
| 2. Git Commit/Push | 5 min | Imediato |
| 3. Streamlit Cloud Setup | 10 min | < 5 min deploy |
| 4. Health Check | 5 min | Auto |
| 5. Monitoring Setup | 5 min | Opcional |
| 6. Full Testing | 30 min | Manual |
| **TOTAL** | **60 min** | **~15 min auto** |

---

## CHECKLIST FINAL DE DEPLOYMENT

### Pre-Deploy
- [ ] Tests lokali passaram
- [ ] Code review feito
- [ ] Database backup criado
- [ ] Git commits limpos

### Deploy
- [ ] Schema SQL executado
- [ ] Git pushed
- [ ] Streamlit Cloud atualizado
- [ ] Secrets configurados

### Post-Deploy
- [ ] Health check OK
- [ ] Testes rápidos passaram
- [ ] Logs monitorados
- [ ] Feedback coletado

### Manutencao
- [ ] Monitoring ativo
- [ ] Backup schedule criado
- [ ] Update policy definida

---

## Endpoints para Testar

```bash
# Local
http://localhost:8501

# Streamlit Cloud
https://share.streamlit.io/[seu-usuario]/mateu-coffee

# Health check
curl -I https://share.streamlit.io/[seu-usuario]/mateu-coffee
# Esperado: HTTP 200
```

---

## Suporte & Troubleshooting

### Problemas Comuns & Soluções

1. **White screen**
   - Solução: Limpar cache (Ctrl+Shift+R)
   - Solução: Verificar console (F12)

2. **Database connection error**
   - Solução: Verificar secrets.toml
   - Solução: Testar psql conecta ao banco

3. **Slow performance**
   - Solução: Verificar query times
   - Solução: Adicionar @st.cache_data

4. **Module not found**
   - Solução: pip install [module]
   - Solução: requirements.txt atualizado

### Contatos Úteis

- Streamlit Support: https://discuss.streamlit.io
- PostgreSQL Support: https://www.postgresql.org/support
- GitHub Issues: Seu repositório

---

## Conclusão

Deployment v2.0 está completo quando:
✓ Database schema atualizado
✓ Code pushed para main branch
✓ Streamlit Cloud redeploys automaticamente
✓ Health check passa
✓ Testes rápidos funcionam

**Status Final: PRODUCTION READY**

---

Data: 2026-06-09
Versão: 2.0
Autor: Mateu Coffee Team
