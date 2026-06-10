# Guia de Testes Rapidos - Mateu Coffee v2.0

## Setup Inicial

```bash
# 1. Atualizar schema SQL
psql -U [user] -d mateu_coffee -f schema.sql

# 2. Instalar requirements
pip install -r requirements.txt

# 3. Executar app
streamlit run streamlit_app_final.py

# 4. Acessar
http://localhost:8501
```

---

## TESTE 1: Tutorial ao Primeiro Uso

### Passos
1. Criar nova conta (registrar.novo@email.com / senha123)
2. Fazer login
3. Verificar se tutorial aparece

### O que esperar
- Card com fundo gradiente (laranja + azul escuro)
- Texto: "Bem-vindo ao Mateu Coffee!"
- 3 bullet points sobre funcionalidades
- Botão "Entendi!" bem visível

### Validacao
- [x] Tutorial aparece após login novo
- [x] Fundo tem gradiente
- [x] Botão funciona e desaparece
- [x] Layout responsivo

---

## TESTE 2: Feedback Visual (Spinners)

### Teste 2.1 - Login
1. Inserir email/senha
2. Clicar "Entrar"
3. Observar spinner

**Esperado:** Spinner "Verificando credenciais..." aparece por ~1-2 segundos

### Teste 2.2 - Criar Café
1. Ir para aba "Cafés"
2. Preencher campos (Nome obrigatório)
3. Clicar "Adicionar Café"

**Esperado:** Spinner "Salvando café..." + mensagem de sucesso

### Teste 2.3 - Registrar Extração
1. Ir para aba "Extrações"
2. Preencher campos (Café e Gramas obrigatórios)
3. Clicar "Registrar Extração"

**Esperado:** Spinner "Registrando extração..." + sucesso

### Validacao
- [x] Spinners aparecem
- [x] Mensagens são descritivas
- [x] Desaparecem após conclusão
- [x] Success/error messages aparecem

---

## TESTE 3: Tamanho de Botoes (Mobile)

### Desktop (1024px+)
1. Abrir DevTools (F12)
2. Desabilitar Device Toolbar
3. Verificar botões
4. Medir altura (deve ser ~48px)

### Mobile (368px - max-width)
1. Abrir DevTools (F12)
2. Habilitar Device Toolbar
3. Selecionar iPhone 12 (375px)
4. Verificar botões
5. Medir altura (deve ser ~52px)

### Validacao
- [x] Desktop: 48px min-height
- [x] Mobile: 52px min-height
- [x] Todos botões full-width
- [x] Fonte legível (16px desktop, 18px mobile)
- [x] Padding adequado (12px 20px)

---

## TESTE 4: Analise Sensorial

### Passos
1. Registrar pelo menos 1 café
2. Registrar 1 extração desse café
3. Ir para aba "Análises"
4. Preencher análise sensorial

### Dados a preencher
```
Aroma: 7
Acidez: 5
Corpo: 8
Notas de Sabor: chocolate, caramelo
Nota Final: 8.5
```

### O que esperar
- 4 sliders aparecem (Aroma, Acidez, Corpo, Nota Final)
- Input de texto para "Notas de Sabor"
- Botão "Salvar Análise" funciona
- Mensagem "Análise salva!"
- Dados são salvos no banco

### Validacao
- [x] Sliders funcionam (1-10)
- [x] Nota Final aceita decimais (0-10)
- [x] Textos são salvos
- [x] Dados persistem após reload

---

## TESTE 5: Graficos de Analise

### Pré-requisitos
Registrar 3+ extrações com notas diferentes:
```
Espresso (nota 9)
V60 (nota 7)
Prensa Francesa (nota 8)
```

### Passos
1. Ir para aba "Análises"
2. Rolar até "Gráficos de Desempenho"
3. Verificar 2 gráficos

### O que esperar

**Gráfico 1: Bar Chart (Nota média por método)**
- X-axis: Métodos (Espresso, V60, Prensa Francesa)
- Y-axis: Notas médias (0-10)
- Barras em laranja (#E8722E)
- Fundo escuro (#0A0A0A)

**Gráfico 2: Line Chart (Evolução de notas)**
- X-axis: Datas
- Y-axis: Notas
- Linha em laranja com markers
- Período: últimos 60 dias

### Validacao
- [x] Bar chart renderiza
- [x] Line chart renderiza
- [x] Cores estão corretas
- [x] Dados corretos
- [x] Responsivo em mobile

---

## TESTE 6: Comunidade

### Passos

#### Parte A: Compartilhar Receita
1. Ir para aba "Comunidade"
2. Preencher formulário à esquerda:
   - Café: "Café da Manhã Premium"
   - Método: "V60"
   - Dose: "20g"
   - Água: "300ml"
   - Nota: "8"
3. Clicar "Compartilhar Receita"

**Esperado:** Spinner + mensagem "Receita compartilhada!"

#### Parte B: Visualizar Comunidade
1. Recarregar página (F5)
2. Ir para "Comunidade"
3. Verificar lado direito "Receitas da Comunidade"

**Esperado:** 
- Cards com receitas
- Mostra: Café, Método, Dose, Água, Nota
- Hover effect (borda laranja)

### Validacao
- [x] Formulário funciona
- [x] Dados são salvos
- [x] Cards aparecem
- [x] Hover effect funciona
- [x] Informações corretas

---

## TESTE 7: Recomendacoes

### Pré-requisitos
Registrar extrações com boas notas:
```
Espresso: 9/10, 8.5/10, 9.5/10
V60: 7/10, 7.5/10
Prensa Francesa: 6/10
Moka: 8/10, 8/10, 8.5/10
```

### Passos
1. Ir para aba "Recomendações"
2. Visualizar cards para cada método

### O que esperar

Para cada método (Espresso, V60, Prensa Francesa, Moka):
- Card com "Melhor receita para [Método]"
- Mostra: Café, Método, Dose/Água, Nota Média
- Se sem dados: "Registre extrações para ter recomendações"

### Validacao
- [x] Cards aparecem para cada método
- [x] Mostra melhor receita (nota média mais alta)
- [x] Dados são corretos
- [x] Fallback mensagem aparece quando sem dados

---

## TESTE 8: Hover Effects

### Teste 8.1 - Botões
1. Desktop: Hover sobre botão
2. Observar: cor muda (F08040), sombra aparece, move para cima

**CSS esperado:**
- background: #F08040
- transform: translateY(-2px)
- box-shadow: 0 4px 12px rgba(232, 114, 46, 0.3)

### Teste 8.2 - Cards
1. Desktop: Hover sobre cards (Análises, Comunidade)
2. Observar: borda fica laranja, sombra aparece

**CSS esperado:**
- border-color: #E8722E
- box-shadow: 0 0 16px var(--mc-orange-glow)

### Teste 8.3 - Recipe Cards
1. Ir para "Comunidade"
2. Hover sobre card de receita
3. Observar: background escurece, borda laranja

### Teste 8.4 - Stats
1. Desktop: Hover sobre cards de estatísticas
2. Observar: borda laranja, background muda

### Validacao
- [x] Transições são suaves (150ms)
- [x] Cores corretas
- [x] Não quebra layout
- [x] Mobile: sem hover effects (natural)

---

## TESTE 9: Responsividade

### Desktop (1024px+)
1. Abrir em resolução 1440x900
2. Verificar layout

**Esperado:**
- 4 colunas para stats
- 2 colunas para abas (lista + formulário)
- Sem overflow horizontal
- Botões 48px

### Tablet (768px - 1024px)
1. Device Toolbar: iPad Air (820px)
2. Verificar layout

**Esperado:**
- 2 colunas para stats (2x2)
- Abas se reorganizam
- Scroll vertical OK

### Mobile (max-width: 768px)
1. Device Toolbar: iPhone 12 (375px)
2. Verificar layout

**Esperado:**
- 1 coluna para stats
- Stacked layout
- Botões 52px
- Sem scroll horizontal
- Texto legível

### Validacao
- [x] Layout responsivo
- [x] Sem overflow
- [x] Botões adaptam tamanho
- [x] Textos legíveis

---

## TESTE 10: Dark Mode

### Pré-requisito
Abrir em navegador novo (sem cookies)

### Cores esperadas

**Background:**
- Esperado: #0A0A0A (preto puro)
- Verificar com DevTools

**Surface:**
- Esperado: #1A1A1A (cinza escuro)
- Verificar cards

**Orange:**
- Esperado: #E8722E (laranja queimado)
- Verificar botões, texto

**Text:**
- Esperado: #E8E8E8 (branco leve)
- Verificar legibilidade

### Validacao
- [x] Cores estão corretas
- [x] Contraste adequado
- [x] Sem glare/brightness excessivo
- [x] Olhos confortáveis

---

## TESTE 11: Performance

### Teste 11.1 - Carregamento
1. Ir para aba "Análises"
2. Observar spinners
3. Medir tempo aproximado: **< 2 segundos**

### Teste 11.2 - Criação de Registros
1. Registrar 10 extrações
2. Medir tempo para completar: **< 10 segundos**

### Teste 11.3 - Carregamento de Gráficos
1. Ir para "Análises"
2. Rolar até gráficos
3. Medir tempo render: **< 3 segundos**

### Teste 11.4 - Mobile Performance
1. Device Toolbar: iPhone 12
2. Testar interações
3. Não deve ficar travado

### Validacao
- [x] Sem delays perceptíveis
- [x] Spinners aparecem em I/O
- [x] Gráficos renderizam rápido
- [x] Mobile responsivo

---

## TESTE 12: Error Handling

### Teste 12.1 - Validação de Campos
1. Clicar "Adicionar Café" sem preencher nome
2. Esperado: "Nome do café é obrigatório"

### Teste 12.2 - Senhas Diferentes
1. Registrar com senhas diferentes
2. Clicar "Criar Conta"
3. Esperado: "Senhas não conferem"

### Teste 12.3 - Email Duplicado
1. Registrar 2x mesmo email
2. Na segunda vez
3. Esperado: "Email já existe"

### Teste 12.4 - Credentials Inválidas
1. Login com email/senha errados
2. Esperado: "Email ou senha incorretos"

### Validacao
- [x] Mensagens de erro aparecem
- [x] Cores corretas (red)
- [x] Sem crash
- [x] App continua funcional

---

## TESTE 13: Fluxo Completo

### Cenário: Novo usuário

```
1. Registrar: novo@cafe.com / senha123
2. Fazer login
3. Ver tutorial → Clicar "Entendi!"
4. Adicionar café: "Café Especial" - Etiópia
5. Registrar extração: 20g de café, V60, 300ml água
6. Preencher análise sensorial: 8/8/8, nota 8.5
7. Compartilhar receita: "Café Especial" + V60 + 20g + 300ml + nota 8
8. Verificar recomendações: "Melhor receita para V60"
9. Logout
10. Login novamente
11. Verificar dados persistem
```

**Tempo esperado:** ~5 minutos

### Validacao
- [x] Sem erros durante fluxo
- [x] Dados salvos corretamente
- [x] UI responsiva
- [x] Spinners aparecem
- [x] Success messages funcionam

---

## TESTE 14: Cross-Browser

### Chrome
- [x] Testar

### Firefox
- [x] Testar

### Safari
- [x] Testar

### Edge
- [x] Testar

### Mobile Safari (iPhone)
- [x] Testar

---

## Resultado Esperado

Se todos testes passarem:
- ✓ App 9.6/10
- ✓ Production Ready
- ✓ Pronto para deploy

---

## Tempo de Testes

| Teste | Tempo |
|-------|-------|
| 1. Tutorial | 2 min |
| 2. Spinners | 3 min |
| 3. Botões Mobile | 5 min |
| 4. Análise Sensorial | 4 min |
| 5. Gráficos | 3 min |
| 6. Comunidade | 3 min |
| 7. Recomendações | 2 min |
| 8. Hover Effects | 3 min |
| 9. Responsividade | 5 min |
| 10. Dark Mode | 2 min |
| 11. Performance | 5 min |
| 12. Error Handling | 4 min |
| 13. Fluxo Completo | 5 min |
| 14. Cross-Browser | 5 min |
| **TOTAL** | **52 min** |

---

## Checklist Final

- [ ] Todos os 14 testes passaram
- [ ] Nenhum erro no console (DevTools)
- [ ] Nenhum erro nos logs (streamlit)
- [ ] Performance adequada
- [ ] Responsividade OK
- [ ] Dark mode funcionando
- [ ] Análise sensorial completa
- [ ] Gráficos renderizando
- [ ] Comunidade funcional
- [ ] Recomendações OK

## Status de Deployment

Se todos checkmarks: ✓ **READY TO DEPLOY**

---

Data: 2026-06-09
Versão: 2.0
Qualidade: Production
