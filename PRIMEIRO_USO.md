# MATEU COFFEE | Guia de Primeiro Uso

---

## 📱 ACESSAR A APLICAÇÃO

1. Acesse: `https://[seu-username]-mateu-coffee.streamlit.app`
2. App carrega em segundos
3. Você verá 3 abas: **Cadastro | Preparo | Histórico**

---

## 🔧 WORKFLOW COMPLETO (PASSO A PASSO)

### **1️⃣ CADASTRO DO CAFÉ**

Clique na aba **"📝 Cadastro de Grãos"**

Preencha os campos:

```
Nome do Café:           Etíopia Yirgacheffe Natural
Tipo de Grão:           Arábica
Perfil de Torra:        Full City
Local de Origem:        Etíopia, Região Yirgacheffe
Categoria:              Specialty
Intensidade:            Forte
Peso da Embalagem:      250g
Preço:                  R$ 45,00
Data de Compra:         Hoje (auto-filled)
Data de Torra:          Hoje (ou data real da torra)
Perfil de Sabor:        Notas de chocolate, amêndoa, frutas vermelhas
```

Clique no botão **"✅ Registrar Grão"**

**Resultado esperado:**
- Mensagem verde: "✅ Grão 'Etíopia Yirgacheffe Natural' registrado com sucesso!"
- Café fica disponível para preparos

---

### **2️⃣ PRIMEIRO PREPARO**

Clique na aba **"⚙️ Registrar Preparo"**

#### **2.1 Selecione o Grão**
- Dropdown "Selecione o Grão" mostra: `Etíopia Yirgacheffe Natural`
- Clique e selecione

#### **2.2 Configure Parâmetros de Extração**

```
Método de Preparo:      Espresso
Peso do Café:           18.0g
Moagem (Cliques):       20 (slider)
Tempo de Contato:       30 segundos
Volume Final:           42ml (será a bebida que sai da máquina)
Tipo de Xícara:         Espresso (30-50ml)
```

#### **2.3 Observe o Cálculo Automático de Brew Ratio**

Logo abaixo dos inputs, você verá:

```
📊 Brew Ratio: 2.33:1
Interpretação: 1g de café para 2.33ml de bebida
```

Este valor é calculado automaticamente como: `Volume (42ml) ÷ Dose (18g) = 2.33:1`

#### **2.4 Avalie os Atributos Sensoriais**

Depois de tomar o café, selecione os checkboxes que correspondem ao que você sentiu:

Exemplo de café bem extraído:
- ☑️ Forte
- ☑️ Intenso
- ☑️ Saboroso
- ☑️ Crema

Exemplo de café subextraído:
- ☑️ Fraco
- ☑️ Sem Sabor

Exemplo de café superextraído:
- ☑️ Amargo
- ☑️ Queimado

#### **2.5 Avalie com Estrelas**

Deslize o slider **"Avaliação"** de 0 a 5 ⭐

Exemplo: Se sentiu um bom espresso → `⭐⭐⭐⭐` (4 ou 4.5)

#### **2.6 Notas Adicionais**

Campo texto opcional para comentários:

```
Crema dourado, bebida cremosa, aftertaste de chocolate agradável.
```

#### **2.7 Registre o Preparo**

Clique **"✅ Registrar Preparo"**

**Resultado esperado:**
```
✅ Preparo registrado | Brew Ratio: 2.33:1 | ⭐ 4.0
```

---

### **3️⃣ VISUALIZAR HISTÓRICO**

Clique na aba **"📊 Histórico & Métricas"**

Você verá:

#### **A. Resumo Analítico (Cards superiores)**

```
Total de Extrações:     1
Avaliação Média:        4.0⭐
Tempo Médio:            30s
Brew Ratio Médio:       2.33:1
```

#### **B. Tabela de Histórico**

Coluna por coluna:

| ID | Grão | Data/Hora | Método | Dose(g) | Cliques | Tempo(s) | Volume(ml) | Ratio | ⭐ | Atributos |
|----|----|-----------|--------|---------|---------|---------|-----------|-------|----|----|
| 1 | Etíopia... | 02/06 15:30 | Espresso | 18.0 | 20 | 30 | 42 | 2.33:1 | 4.0 | Forte, Intenso, Saboroso, Crema |

#### **C. Exportar Dados**

Botão **"📥 Exportar CSV"** baixa um arquivo para análise em planilha.

---

## 📊 SEGUNDO PREPARO (COM ANÁLISE DO BARISTA)

### **Cenário: Café saiu fraco**

Você registra:

```
Método:                 Espresso
Dose:                   18g
Cliques:                22 (moagem mais grossa que antes)
Tempo:                  25s (tempo curto)
Volume:                 38ml
Atributos:              ☑️ Fraco, ☑️ Sem Sabor
Avaliação:              ⭐⭐.0
Brew Ratio:             2.11:1
```

### **Você envia os dados para o Motor de Barista:**

Copie e envie:

```
Café: Etíopia Yirgacheffe
Torra: Hoje (0 dias - acabou de torrar)
Método: Espresso
Dose: 18g | Cliques: 22 | Tempo: 25s | Volume: 38ml
Atributos: Fraco, Sem Sabor
Avaliação: ⭐⭐.0
Brew Ratio: 2.11:1
```

### **Motor de Barista Responde:**

```
## 🔍 ANÁLISE #001

### 1️⃣ DIAGNÓSTICO TÉCNICO
SUBextração: Moagem excessivamente grossa
- Brew Ratio Real: 2.11:1 (acima do ideal)
- Brew Ratio Alvo: 2.33:1 a 2.5:1
- Problema: Água passou rápido demais, pouco sólido dissolvido

### 2️⃣ AÇÃO CORRETIVA IMEDIATA
Alterar: **Moagem (Cliques)**
- De: 22 cliques
- Para: 18 cliques (-4 cliques)
- Racional: Reduzir granulometria = aumentar superfície de contato

### 3️⃣ MÉTRICA ALVO (PRÓXIMO TESTE)
| Parâmetro | Alvo |
|-----------|------|
| Dose | 18g |
| Cliques | 18 |
| Tempo | 30s (+5s) |
| Volume | 42-45ml |
| Brew Ratio | 2.33:1 a 2.5:1 |
| Avaliação Esperada | ⭐⭐⭐⭐ |
```

### **Você testa novamente:**

Volta ao app e registra novo preparo **com os valores recomendados:**

```
Método:                 Espresso (mesmo)
Dose:                   18g (mesmo)
Cliques:                18 (ALTEROU - era 22)
Tempo:                  30s (ALTEROU - era 25s)
Volume:                 44ml (resultado esperado)
Atributos:              ☑️ Saboroso, ☑️ Intenso, ☑️ Crema
Avaliação:              ⭐⭐⭐⭐ (4 ou mais)
```

Clique **"✅ Registrar Preparo"**

---

## 💡 DICAS DE USO

### **Mobile (Celular)**

- Layout automático se adapta a telas pequenas
- Sliders funcionam com toque/swipe
- Checkboxes grandes para dedo

Teste em seu celular visitando o link da aplicação.

### **Melhor Horário para Testar**

- Use café **entre 7 e 30 dias pós-torra** (pico de sabor)
- Mesma hora do dia = resultados mais consistentes
- Mesma temperatura ambiente = menos variáveis

### **Registre SEMPRE Mesmo Que "Ruim"**

Até uma extração miserável gera dados úteis para análise.

---

## ❌ PROBLEMAS COMUNS

### **"App disse 'Nenhum grão cadastrado'"**

→ Você está na aba "Preparo" mas nunca foi à aba "Cadastro"  
→ **Solução**: Registre um grão primeiro, depois faça o preparo

### **"Brew Ratio mostra 0.00:1"**

→ Você deixou "Peso do Café" como 0  
→ **Solução**: Insira um valor > 0 (ex: 18g)

### **"Histórico vazio"**

→ Nenhum preparo registrado ainda  
→ **Solução**: Complete o workflow acima (Cadastro → Preparo → Histórico)

### **Botão "Registrar" não responde**

→ Algum campo obrigatório está vazio  
→ **Solução**: Revise todos os inputs (especialmente Grão selecionado)

---

## 🎯 PRÓXIMAS ETAPAS

1. **Registre 5-10 preparos** do mesmo café com parâmetros diferentes
2. **Envie dados ao Barista** para análise comparativa
3. **Identifique padrão**: Qual combinação de cliques + tempo = melhor avaliação?
4. **Documente receita**: Guarde a combinação vencedora para reproduzir

---

## 📞 PRECISA DE HELP?

- **Erro de conexão no app**: Verifique se Streamlit Cloud está online (status.streamlit.io)
- **Dúvida técnica sobre café**: Consulte BARISTA_ENGINE_PROTOCOL.md
- **Dúvida sobre deploy**: Consulte SETUP_SECRETS.md

---

**Você está pronto. Faça seu primeiro café!** ☕

Data: 2026-06-02  
Versão: 1.0
