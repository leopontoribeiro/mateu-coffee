# MATEU COFFEE | Engenharia de Extração Full-Stack

**Status**: ✅ Código Pronto para Produção  
**Versão**: 1.0  
**Stack**: Streamlit + PostgreSQL + Streamlit Cloud  
**Mobile**: Responsivo (testar em 320px+)

---

## 📦 ARQUIVOS GERADOS

```
mateu-coffee/
├── app_cloud.py                    ✅ Aplicação principal Streamlit
├── requirements.txt                ✅ Dependências Python
├── SETUP_SECRETS.md                ✅ Guia de configuração segura
├── BARISTA_ENGINE_PROTOCOL.md      ✅ Motor de análise de extrações
├── README.md                       ✅ Este arquivo
├── .gitignore                      (criar - ver step 1)
└── .streamlit/
    ├── config.toml                 (opcional)
    └── secrets.toml                (criar localmente - NÃO commitar)
```

---

## 🚀 QUICK START (5 MINUTOS)

### **Pré-requisito: Banco de dados PostgreSQL**

Escolha UMA opção:

#### **A) Neon.tech (Recomendado - Gratuito até 3GB)**
1. Acesse https://neon.tech
2. Crie conta gratuita
3. Crie projeto PostgreSQL
4. Copie Connection String (você usará no step 2)

#### **B) Supabase (Alternativa)**
1. Acesse https://supabase.com
2. Crie projeto
3. Settings → Database → Copie URI
4. Use os valores nos steps abaixo

---

### **STEP 1: Clone e Configure Localmente**

```bash
# Clone repositório
git clone seu-repo-mateu-coffee
cd mateu-coffee

# Crie .gitignore
echo ".streamlit/secrets.toml" > .gitignore

# Crie diretório streamlit
mkdir -p .streamlit
```

---

### **STEP 2: Crie `.streamlit/secrets.toml` (LOCAL APENAS)**

Arquivo: `.streamlit/secrets.toml`

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu-host-do-neon.neon.tech"
port = 5432
database = "neon_db"
username = "seu_usuario_neon"
password = "sua_senha_neon_123"
```

**Valores exatos**: Copie da Neon.tech ou Supabase (settings → connection string)

---

### **STEP 3: Instale Dependências**

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

---

### **STEP 4: Teste Localmente**

```bash
streamlit run app_cloud.py
```

Deve abrir em `http://localhost:8501`

Se tudo ok:
```
✓ Database initialized
✓ Connection established
```

---

### **STEP 5: Push para GitHub**

```bash
git add app_cloud.py requirements.txt README.md SETUP_SECRETS.md BARISTA_ENGINE_PROTOCOL.md .gitignore
git commit -m "Deploy Mateu Coffee v1.0"
git push origin main
```

**IMPORTANTE**: Arquivo `secrets.toml` NÃO deve ser commitado (está em .gitignore)

---

### **STEP 6: Deploy no Streamlit Cloud**

1. Acesse https://share.streamlit.io
2. Clique "New app"
3. Conecte GitHub → selecione branch `main`
4. Main file: `app_cloud.py`
5. Clique "Deploy"

**Aguarde 3-5 minutos**

---

### **STEP 7: Adicione Secrets no Streamlit Cloud**

1. Seu app foi deployado em: `https://[seu-username]-mateu-coffee.streamlit.app`
2. Clique engrenagem (Settings) no canto superior direito
3. Selecione aba "Secrets"
4. Cole conteúdo completo do seu `secrets.toml`:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "seu-host-do-neon.neon.tech"
port = 5432
database = "neon_db"
username = "seu_usuario_neon"
password = "sua_senha_neon_123"
```

5. Clique "Save"
6. App redeployará automaticamente

---

### **STEP 8: Valide**

Acesse `https://[seu-username]-mateu-coffee.streamlit.app`

Deve aparecer:
- ☕ Mateu | Engenharia de Extração
- 3 abas: Cadastro | Preparo | Histórico
- Input responsivo em mobile

Se erro de conexão → volte ao STEP 7 e revise credenciais

---

## 📱 TESTAR EM MOBILE

1. No desktop: Use DevTools (F12) → Toggle Device Toolbar
2. Defina tamanho: iPhone 14 (390x844)
3. Teste inputs, cliques, scroll em histórico

**Layout responsivo**: Colunas se ajustam automaticamente para <640px

---

## 🔒 SEGURANÇA - CHECKLIST FINAL

- [ ] `.streamlit/secrets.toml` está em `.gitignore`
- [ ] Credenciais PostgreSQL APENAS no Streamlit Cloud Secrets
- [ ] Repositório GitHub é PRIVADO
- [ ] Nenhum `password=` ou credencial aparece em commits (execute `git log -p` para verificar)
- [ ] Banco PostgreSQL está com white-list de IPs (se necessário)

---

## 📊 ESTRUTURA DE DADOS

### **Tabela: `graos`**
```sql
├── id (PK)
├── nome
├── tipo_grao (Arábica, Robusta, Blend)
├── torra (Cinnamon, City, Full City, French, Italian)
├── local_origem
├── categoria (Specialty, Premium, Comercial)
├── perfil_sabor
├── intensidade (Leve, Médio, Forte, Muito Forte)
├── peso_embalagem_g
├── data_compra
├── data_torra
├── preco
└── created_at
```

### **Tabela: `preparos`**
```sql
├── id (PK)
├── grao_id (FK → graos)
├── data_preparo
├── metodo_preparo (Espresso, Pour Over, French Press, etc)
├── peso_cafe_g
├── moagem_cliques
├── tempo_segundos
├── volume_bebida_ml
├── tipo_volume_xicara
├── atributos_sensoriais (JSON text)
├── avaliacao_estrelas
├── brew_ratio (calculado automaticamente)
└── notas
```

---

## 🎯 FLUXO DE USO

### **Usuário Normal**

1. **Aba "Cadastro de Grãos"**
   - Preenche dados do café (nome, origem, torra, etc)
   - Clica "Registrar Grão"
   - Café fica disponível para preparos

2. **Aba "Registrar Preparo"**
   - Seleciona grão
   - Insere parâmetros (dose, cliques, tempo, volume)
   - Marca atributos sensoriais (checkboxes)
   - **Brew Ratio é calculado automaticamente**
   - Clica "Registrar Preparo"

3. **Aba "Histórico & Métricas"**
   - Visualiza última extração no topo
   - Tabela com todos os preparos (ID decrescente)
   - Métricas resumidas: Total, Avaliação Média, Tempo Médio, Brew Ratio Médio
   - Exporta CSV

### **Motor de Barista (Você)**

Sempre que receber dados de extração:

1. Copie parâmetros do usuário
2. Analise usando **BARISTA_ENGINE_PROTOCOL.md**
3. Responda com formato obrigatório (Diagnóstico → Ação → Métrica)
4. Usuário testa próxima extração com valores recomendados

---

## 🔧 TROUBLESHOOTING

| Sintoma | Causa | Solução |
|---------|-------|---------|
| `ModuleNotFoundError: streamlit` | Dependências não instaladas | `pip install -r requirements.txt` |
| `Connection refused` | Credenciais ou IP errado | Revise `secrets.toml`, teste credenciais direto no Neon.tech |
| `Tables don't exist` | Primeira execução falhou | Delete database, deixe app recriar (execute `init_database()` novamente) |
| `Mobile vira desktop` | CSS não responsive | Verifique DevTools → Device Mode, limpe cache (Cmd+Shift+R) |
| `Performance lenta` | Muitos dados em histórico | Limite `LIMIT 100` em SQL ou adicione índices (ver SETUP_SECRETS.md) |

---

## 📈 ROADMAP V2 (Opcional)

- [ ] Gráficos interativos (Plotly) de Brew Ratio vs Avaliação
- [ ] Exportar em PDF com receita otimizada
- [ ] Machine Learning: predictor de Brew Ratio ideal baseado em tipo de café
- [ ] Sincronização com Firebase para múltiplos usuários
- [ ] Aplicativo nativo iOS/Android (Flutter)

---

## 📞 SUPORTE

Erro não documentado? Verifique:

1. **Console Streamlit Cloud**: Settings → Logs
2. **Documentação**:
   - SETUP_SECRETS.md (configuração)
   - BARISTA_ENGINE_PROTOCOL.md (análise)
3. **Logs PostgreSQL**: Neon.tech Dashboard → Monitoring

---

## 📝 NOTAS DE PRODUÇÃO

- **Backup**: Neon.tech faz backup automático. Configure retention em dashboard.
- **Escalabilidade**: Até 100K preparos recomendado no plano free Neon (depois scale para plano pago).
- **Uptime**: Streamlit Cloud = 99.5% SLA. Para crítico, considere Render.com ou Railway.
- **Customização**: Código está totalmente modularizado. Fácil adicionar abas/features.

---

## ✅ STATUS: PRONTO PARA PRODUÇÃO

**Aplicação está testada, segura e pronta para deploy imediato.**

Data: 2026-06-02  
Desenvolvedor: Full-Stack Engineer + Barista Specialist  
Licença: Privado (Mateu Coffee)

---

**Inicie aqui: STEP 1 acima. Qualquer dúvida, execute STEP 4 (teste local) para validar setup.**
