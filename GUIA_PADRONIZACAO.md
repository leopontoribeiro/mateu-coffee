# 📐 GUIA DE PADRONIZAÇÃO - MATEU BARISTA v1.1

## 🎯 Visão Geral

Este guia explica como o app foi totalmente padronizado com um **Sistema de Design unificado** baseado na identidade visual da marca.

---

## 📁 Estrutura de Arquivos

```
mateu-coffee/
├── design_system.py          # 🎨 Sistema de Design (reutilizável)
├── app_padronizado.py        # ☕ Aplicação Principal (padronizada)
├── requirements.txt          # 📦 Dependências
├── .streamlit/
│   ├── config.toml          # ⚙️ Configuração Streamlit
│   └── secrets.toml         # 🔐 Secrets PostgreSQL
├── streamlit_app.py         # ✓ Versão deploy (aponta para app_padronizado.py)
└── GUIA_PADRONIZACAO.md     # 📖 Este arquivo
```

---

## 🎨 PALETA DE CORES

### Primary (Laranja Quente)
```
Principal:    #FF8C42
Dark:         #FF7A28
Light:        #FFA866
Background:   #FFF5E6
```

### Secondary (Cinza Sofisticado)
```
Texto Principal:    #2A2A2A
Texto Secundário:   #606060
Texto Terciário:    #909090
Divisor/Borda:      #E8E8E8
Fundo Claro:        #F5F5F5
```

### Functional
```
Sucesso:     #4CAF50
Alerta:      #FF9800
Erro:        #FF6B6B
Info:        #87CEEB
```

---

## 📏 TIPOGRAFIA

### Hierarquia de Tamanhos
- **H1**: 32px Bold (Títulos Principais)
- **H2**: 24px Bold (Subtítulos/Seções)
- **H3**: 20px SemiBold (Sub-seções)
- **Body**: 14px Regular (Textos)
- **Caption**: 12px Regular (Metadados)
- **Label**: 12px Medium (Labels)

### Fontes Recomendadas
- Primária: **Inter**, Outfit (moderna, geométrica)
- Secundária: **Poppins** (amigável, legível mobile)

---

## 🧩 COMPONENTES REUTILIZÁVEIS

Todos os componentes estão em `design_system.py`:

### 1. **header_component()**
```python
from design_system import header_component

header_component(
    title="Dashboard",
    subtitle="Visão geral do seu sistema",
    icon="📊"
)
```

### 2. **stat_card()**
```python
stat_card(
    label="Grãos Cadastrados",
    value="24",
    icon="📦",
    change="+3 esta semana"
)
```

### 3. **success_button() / secondary_button()**
```python
if success_button("Salvar", key="btn_save"):
    # Ação quando clicado
    toast_message("Salvo com sucesso!", "success")
```

### 4. **info_box()**
```python
info_box(
    title="Nenhum preparo",
    content="Comece registrando seu primeiro preparo!",
    icon="📝",
    box_type="info"  # "info", "success", "warning", "error"
)
```

### 5. **separator()**
```python
separator()  # Divisor padronizado
```

### 6. **labeled_metric()**
```python
labeled_metric(
    label="Total de Grãos",
    value="24",
    unit="SKUs"
)
```

---

## 🚀 COMO USAR O DESIGN SYSTEM

### Import Básico
```python
from design_system import (
    apply_theme,              # Aplica CSS e tema global
    COLORS,                   # Acessa paleta de cores
    TYPOGRAPHY,               # Acessa tipografia
    SPACING,                  # Acessa espaçamento
    header_component,         # Componente de header
    stat_card,               # Componente de estatística
    success_button,          # Botão primário
    secondary_button,        # Botão secundário
    info_box,               # Caixa de informação
)

# Na inicialização do app
apply_theme()
```

### Acessar Cores Diretamente
```python
st.markdown(f"<p style='color: {COLORS.primary};'>Texto Colorido</p>",
           unsafe_allow_html=True)
```

### Usar Espaçamento
```python
st.markdown(f"<div style='padding: {SPACING.lg}; margin: {SPACING.md};'>
    Conteúdo com espaçamento padrão
</div>", unsafe_allow_html=True)
```

---

## 📱 RESPONSIVIDADE MOBILE

O design system já inclui media queries:
```css
@media (max-width: 640px) {
    button {
        width: 100% !important;
    }
    ...
}
```

### Dicas para Mobile:
- Use `st.columns(2)` no desktop, `st.columns(1)` no mobile
- Botões sempre em largura máxima (`use_container_width=True`)
- Padding menor em cards no mobile
- Fontes legíveis (mínimo 14px)

---

## ♿ ACESSIBILIDADE

- ✓ Contraste mínimo **AAA** (4.5:1)
- ✓ Touch targets de **48x48px**
- ✓ Font size mínimo de **14px**
- ✓ Line height de **1.5** para legibilidade
- ✓ Suporte a dark mode (em desenvolvimento)

---

## 🔧 CONFIGURAÇÃO DO STREAMLIT

### `.streamlit/config.toml`
```toml
[theme]
primaryColor="#FF8C42"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F5F5F5"
textColor="#2A2A2A"
font="sans serif"

[client]
showErrorDetails = false

[server]
port = 8501
headless = true
```

---

## 🌐 DEPLOYMENT NO STREAMLIT CLOUD

### Passos:
1. **Atualize `streamlit_app.py`** para usar `app_padronizado.py`:
```python
# streamlit_app.py
from app_padronizado import *
```

2. **Adicione secrets em `Manage Secrets`**:
```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg"
host = "seu-host.neon.tech"
port = 5432
database = "neondb"
username = "neondb_owner"
password = "sua-senha"
```

3. **Envie para GitHub**:
```bash
git add design_system.py app_padronizado.py
git commit -m "feat: sistema de design padronizado"
git push origin main
```

4. **Deploy automático no Streamlit Cloud** (se configurado)

---

## 🎨 PERSONALIZANDO O DESIGN SYSTEM

### Para mudar cores (todo o app):
1. Abra `design_system.py`
2. Modifique `ColorPalette` (linhas 12-40)
3. Exemplo:
```python
@dataclass
class ColorPalette:
    primary: str = "#SEU_NOVO_COR"
    primary_dark: str = "#SUA_VARIANTE"
    # ...
```

### Para mudar tipografia:
```python
@dataclass
class Typography:
    h1: int = 36  # Aumentar de 32 para 36
    body: int = 16  # Aumentar de 14 para 16
    # ...
```

---

## ✅ CHECKLIST DE QUALIDADE

- [ ] Todos os botões usam `success_button()` ou `secondary_button()`
- [ ] Headers usam `header_component()`
- [ ] Mensagens de status usam `toast_message()`
- [ ] Informações importantes usam `info_box()`
- [ ] Espaçamento usa constantes de `SPACING`
- [ ] Cores usam `COLORS.*`
- [ ] Mobile testado em 375px width
- [ ] Contraste verificado com acessibilidade
- [ ] Sem hardcoded de cores (#FF8C42 deve ser `COLORS.primary`)

---

## 📊 MÉTRICAS DO DESIGN SYSTEM

| Métrica | Valor |
|---------|-------|
| Cores Principais | 13 |
| Componentes Reutilizáveis | 8 |
| Pontos de Espaçamento | 6 |
| Tipos de Tipografia | 6 |
| Linhas de CSS | 300+ |

---

## 🚨 TROUBLESHOOTING

### Cores não aparecem?
- Certifique-se de usar `unsafe_allow_html=True`
- Verifique se está importando `COLORS` de `design_system`

### Botões desalinhados?
- Use `use_container_width=True` em botões
- Ajuste `st.columns()` conforme tela

### Componentes quebrados?
- Verifique imports no topo do arquivo
- Restart do Streamlit: `streamlit run app_padronizado.py --logger.level=debug`

---

## 📞 SUPORTE

Para dúvidas ou sugestões:
- Documente a mudança desejada
- Abra issue no repositório
- Submeta PR com melhorias ao design system

---

## 🎓 Recursos Adicionais

- 📖 [Streamlit Docs](https://docs.streamlit.io)
- 🎨 [Design System Tokens](./design_system.py) (veja `ColorPalette`, `Typography`, `Spacing`)
- 💻 [Componentes Implementados](./app_padronizado.py) (veja Dashboard, Grãos, Preparos, etc.)

---

**Versão**: 1.0
**Última atualização**: Junho 2024
**Status**: ✅ Produção
