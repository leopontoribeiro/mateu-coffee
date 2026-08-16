"""mc_data.py — dados estáticos do Mateu Coffee (métodos, moedores,
locais de compra, classificações de café e receitas-referência).

Extraído do monólito streamlit_app_final.py para modularização.
Apenas literais — sem Streamlit, DB ou lógica.
"""

METODOS = ["Espresso","V60","Pour Over","French Press","Aeropress",
           "Chemex","Moka Pot","Cold Brew","Sifão","Drip","Outro"]

_LOCAIS_COMPRA = ["Amazon", "Mercado Livre", "Shopee", "Guanabara",
                  "Mundial", "Megabox", "Outros"]

_MOEDORES = ["Starseeker e55Pro", "Acoplado Oster", "Comandante",
             "Hamilton Beach", "Outros"]

# ── Máquinas de espresso: pressão NOMINAL ≠ pressão NO BOLO DE CAFÉ ─────
# O número estampado na caixa ("15 bar", "20 bar") é a pressão MÁXIMA da
# bomba vibratória medida SEM CARGA (deadhead). Não é a pressão que chega
# ao puck. Entre a bomba e o café existem:
#   • OPV / válvula de alívio (limita o pico)
#   • perda de carga na tubulação, caldeira e tela de dispersão
#   • a própria resistência do bolo de café
# Resultado prático: uma máquina "15 bar" extrai por volta de 9 bar reais.
# Tratar 15 como pressão de extração gera diagnóstico falso de
# adstringência/canalização — foi exatamente o bug corrigido aqui.
#
#   nominal    bar estampado na especificação do fabricante
#   efetiva    bar estimado NO PUCK durante a extração
#   opv        True = tem válvula de alívio limitando o pico
#   nota       origem/confiança do dado
MAQUINAS_ESPRESSO = {
    "Oster Xpert Perfect Brew (BVSTEM7300)": {
        "nominal": 15.0, "efetiva": 9.0, "opv": True,
        "nota": "Bomba vibratória 15 bar (spec de catálogo, sem carga), "
                "portafiltro 58 mm. Pressão de extração real estimada ≈9 bar. "
                "VERIFICAR com manômetro/portafiltro de teste.",
    },
    "Doméstica 15 bar (genérica)": {
        "nominal": 15.0, "efetiva": 9.0, "opv": True,
        "nota": "Padrão da categoria: bomba ULKA/similar 15 bar nominal, "
                "OPV limitando a extração em torno de 9 bar.",
    },
    "Doméstica 20 bar (genérica)": {
        "nominal": 20.0, "efetiva": 9.5, "opv": True,
        "nota": "20 bar é marketing de bomba. A extração continua na faixa "
                "de 9–10 bar por causa do OPV.",
    },
    "Semi-profissional (E61 / 9 bar calibrada)": {
        "nominal": 9.0, "efetiva": 9.0, "opv": True,
        "nota": "Manômetro no grupo. Nominal e efetiva coincidem.",
    },
    "Alavanca / manual (Flair, Cafelat)": {
        "nominal": 12.0, "efetiva": 9.0, "opv": False,
        "nota": "Pressão controlada pelo braço do operador; 9 bar é o alvo "
                "típico, mas varia bastante entre extrações.",
    },
    "Outra / não sei": {
        "nominal": None, "efetiva": None, "opv": None,
        "nota": "Sem conversão aplicada — o valor digitado é usado como está.",
    },
}

# Faixa de pressão EFETIVA (no puck) considerada saudável para espresso.
PRESSAO_EFETIVA_IDEAL = (8.0, 10.0)


# ── Estilos de espresso ────────────────────────────────────────────────
# O espresso NÃO escala linearmente em ml. Ristretto, normale e lungo são
# RATIOS diferentes sobre a MESMA dose de pó — mudam yield, tempo e
# moagem. Escalar "36 ml → 54 ml" multiplicando a dose transformaria um
# normale em dois normales, não num lungo.
#
#   ratio       yield ÷ dose (1:X)
#   time        s alvo de extração
#   grind_delta ajuste de moagem relativo ao normale
#   ey_alvo     faixa de extraction yield esperada (%)
ESPRESSO_STYLES = {
    "Ristretto": {
        "ratio": 1.5, "time": 25, "grind_delta": "mais fina",
        "grind": "Fina — mais fina que o normale (compensa o yield curto)",
        "ey_alvo": (17.0, 20.0),
        "desc": "Concentrado e doce. Menos água pela mesma dose: corpo denso, "
                "acidez alta, final curto. Extrai menos sólidos — moa mais fino "
                "para não subextrair.",
    },
    "Normale": {
        "ratio": 2.0, "time": 28, "grind_delta": "referência",
        "grind": "Fina (textura de sal fino)",
        "ey_alvo": (18.0, 22.0),
        "desc": "Padrão moderno de campeonato. Equilíbrio entre corpo, doçura "
                "e acidez. É a referência de calibração do moedor.",
    },
    "Lungo": {
        "ratio": 3.0, "time": 35, "grind_delta": "mais grossa",
        "grind": "Fina-média — mais grossa que o normale (evita superextração)",
        "ey_alvo": (20.0, 23.0),
        "desc": "Mais água pela mesma dose: bebida mais longa e leve, porém "
                "com risco real de superextração (amargor/adstringência). "
                "Moa mais grosso para segurar o EY.",
    },
}

ESPRESSO_STYLE_DEFAULT = "Normale"

# Capacidade prática do cesto do portafiltro por dose de pó (g).
# Acima disso o puck encosta na tela de dispersão e canaliza.
CESTO_CAPACIDADE_G = {58: 22.0, 54: 20.0, 51: 16.0}
CESTO_PADRAO_MM = 58


# ── Retenção de água pelo pó (métodos filtrados/imersão) ───────────────
# O pó molhado retém água que NUNCA chega à jarra. Ignorar isso faz o app
# prometer um volume que não sai: 500 g de água com 30 g de pó rendem
# ~440 ml, não 500 ml.
#   g de água retida por g de café moído
RETENCAO_G_POR_G = {
    "V60": 2.0, "Pour Over": 2.0, "Chemex": 2.2, "Drip": 2.0, "Sifão": 1.8,
    "French Press": 2.1, "Aeropress": 1.8, "Cold Brew": 2.2, "Moka Pot": 1.5,
}
RETENCAO_PADRAO = 2.0

CLASSIFICACOES_CAFE = [
    "Especial (>80 pts)",
    "Gourmet",
    "Superior",
    "Tradicional",
    "Extraforte",
]

# Perfil de referência por método de preparo. Cada extração tem dose, ratio,
# tempo, temperatura e moagem próprios — e só o espresso usa pressão (bar).
# 'pressure': None marca métodos filtrados/imersão → o campo de bar é
# DESATIVADO na interface (não se aplica). 'yield' é calculado (dose*ratio).
#   dose      g de pó (base: 1 dose de espresso / 1 preparo de coado)
#   ratio     água ÷ pó
#   time      s alvo de extração (referência p/ o timer)
#   temp      °C da água
#   pressure  bar (None = método não usa pressão)
#   grind     moagem sugerida
#   (o rótulo do campo de saída é derivado na UI: espresso = bebida na
#    xícara; coados = água a despejar, com o líquido na jarra à parte)
#   dose_max/water_max  limites dos campos numéricos
METHOD_PROFILES = {
    # Espresso: os valores abaixo são a BASE POR DOSE (1 shot, estilo
    # Normale). O ratio/tempo/moagem finais vêm de ESPRESSO_STYLES e o
    # total é multiplicado pelo nº de doses. Não escale espresso em ml.
    "Espresso":     {"dose": 18.0, "ratio": 2.0,  "time": 28,  "temp": 92.0, "pressure": 9.0,
                     "grind": "Fina (textura de sal fino)", "dose_max": 30.0, "water_max": 80.0},
    "V60":          {"dose": 15.0, "ratio": 16.7, "time": 210, "temp": 94.0, "pressure": None,
                     "grind": "Média-fina (mais grossa que espresso)", "dose_max": 40.0, "water_max": 700.0},
    "Pour Over":    {"dose": 18.0, "ratio": 16.0, "time": 180, "temp": 93.0, "pressure": None,
                     "grind": "Média", "dose_max": 40.0, "water_max": 700.0},
    "French Press": {"dose": 30.0, "ratio": 16.0, "time": 240, "temp": 96.0, "pressure": None,
                     "grind": "Grossa (imersão longa)", "dose_max": 60.0, "water_max": 1000.0},
    "Aeropress":    {"dose": 15.0, "ratio": 15.0, "time": 150, "temp": 85.0, "pressure": None,
                     "grind": "Média (textura de areia)", "dose_max": 30.0, "water_max": 300.0},
    "Chemex":       {"dose": 33.0, "ratio": 15.0, "time": 270, "temp": 94.0, "pressure": None,
                     "grind": "Média-grossa", "dose_max": 60.0, "water_max": 1000.0},
    "Moka Pot":     {"dose": 18.0, "ratio": 10.0, "time": 300, "temp": 100.0, "pressure": None,
                     "grind": "Média-fina (sem compactar)", "dose_max": 40.0, "water_max": 500.0},
    "Cold Brew":    {"dose": 100.0, "ratio": 10.0, "time": 240, "temp": 22.0, "pressure": None,
                     "grind": "Grossa (pimenta-do-reino grossa)", "dose_max": 200.0, "water_max": 2000.0},
    "Sifão":        {"dose": 20.0, "ratio": 15.0, "time": 150, "temp": 92.0, "pressure": None,
                     "grind": "Média", "dose_max": 40.0, "water_max": 600.0},
    "Drip":         {"dose": 20.0, "ratio": 16.0, "time": 300, "temp": 94.0, "pressure": None,
                     "grind": "Média", "dose_max": 60.0, "water_max": 1500.0},
    "Outro":        {"dose": 18.0, "ratio": 2.0,  "time": 30,  "temp": 92.0, "pressure": None,
                     "grind": "—", "dose_max": 60.0, "water_max": 2000.0},
}

RECIPES = [
    {
        "id": "espresso",
        "nome": "Espresso Italiano",
        "metodo": "Espresso",
        "categoria": "Pressão",
        "icon": "⚡",
        "dificuldade": "Intermediário",
        "tempo": "25–35 s conforme o estilo",
        "rendimento": "1 dose · 27 a 54 g conforme o estilo",
        "ratio": "1:1,5 (ristretto) · 1:2 (normale) · 1:3 (lungo)",
        "moagem": "Fina — textura de sal de mesa (ajuste conforme o estilo)",
        "descricao": "Base de quase todas as bebidas de café. Os três estilos são "
                     "RATIOS diferentes sobre a mesma dose de 18 g — não volumes "
                     "diferentes da mesma bebida. Para mais café, faça mais doses, "
                     "não passe mais água pelo mesmo pó.",
        "equipamentos": [
            "Máquina de espresso (≈9 bar EFETIVOS no puck — o 'bar' da caixa "
            "é o pico da bomba sem carga)",
            "Moedor com discos planos ou cônicos",
            "Tamper 58 mm nivelador",
            "Balança 0,1 g",
            "Cronômetro",
        ],
        "ingredientes": [
            "18 g de café especialidade torra média/escura, moído na hora",
            "Água da máquina a 93 °C",
        ],
        "passos": [
            "Pré-aqueça a máquina por ao menos 20 min.",
            "Moa 18 g de café com moagem fina (textura de sal de mesa).",
            "Distribua o pó uniformemente no porta-filtro (WDT com agulha ajuda).",
            "Tampe firme e nivelado (≈15 kg de pressão).",
            "Limpe o resíduo da borda do porta-filtro.",
            "Encaixe e dispare imediatamente. Inicie o cronômetro.",
            "Escolha o alvo pelo ESTILO, sempre com os mesmos 18 g de pó: "
            "ristretto 27 g em ≈25 s · normale 36 g em ≈28 s · lungo 54 g em ≈35 s.",
            "Ajuste a moagem ao estilo: ristretto pede moagem mais FINA (o yield "
            "curto extrai menos); lungo pede moagem mais GROSSA (mais água pelo "
            "mesmo pó superextrai).",
            "Fora do tempo alvo → corrija pela moagem, não pela água: "
            "rápido demais = moa mais fino; lento demais = moa mais grosso.",
            "Precisa de mais café? Repita a extração com um puck novo. "
            "Passar mais água pelo mesmo pó não faz um lungo — faz um café aguado "
            "e superextraído.",
        ],
        "fonte": "Padrão WBC moderno (ristretto 1:1,5 · normale 1:2 · lungo 1:3)",
    },
    {
        "id": "v60",
        "nome": "V60 — The Ultimate Technique",
        "metodo": "Pour Over",
        "categoria": "Filtrado",
        "icon": "💧",
        "dificuldade": "Intermediário",
        "tempo": "≈4 min",
        "rendimento": "1 xícara · 250 ml",
        "ratio": "1 : 16,7",
        "moagem": "Média-fina (um pouco mais fina que sal grosso)",
        "descricao": "Receita do James Hoffmann — o tutorial mais assistido sobre V60. "
                     "Resulta em uma xícara doce, limpa e equilibrada.",
        "equipamentos": [
            "Hario V60 02 (cerâmica ou plástico)",
            "Papel filtro V60 02",
            "Chaleira de bico fino (gooseneck)",
            "Balança 0,1 g com cronômetro",
            "Recipiente / chávena",
        ],
        "ingredientes": [
            "15 g de café especialidade torra clara/média, moído na hora",
            "250 g de água a 95 °C (filtrada)",
        ],
        "passos": [
            "Esquente a água até 95 °C.",
            "Coloque o filtro no V60 e enxágue com água quente para tirar o "
            "gosto de papel e aquecer o coador. Descarte a água.",
            "Adicione 15 g de café moído médio-fino. Faça um pequeno furo no centro.",
            "T = 0 s: Despeje 50 g de água em movimento circular do centro para fora.",
            "Logo após, gire suavemente o V60 (Rao Swirl) para nivelar a cama.",
            "T = 0:45: Comece o pour principal. Vá até 100 g em 10 s.",
            "T = 1:15: Despeje até 200 g em 10 s, com movimento circular.",
            "T = 1:45: Despeje até 250 g em 10 s. Gire suavemente.",
            "T ≈ 3:30: drawdown completo. Bata levemente para nivelar a cama final.",
            "Gire para servir. Beba imediatamente.",
        ],
        "fonte": "James Hoffmann — Ultimate V60 Technique",
    },
    {
        "id": "aeropress",
        "nome": "AeroPress Invertido — Estilo Campeonato",
        "metodo": "Aeropress",
        "categoria": "Imersão",
        "icon": "🚀",
        "dificuldade": "Iniciante",
        "tempo": "≈2 min",
        "rendimento": "1 xícara · 130 ml",
        "ratio": "1 : 7 + diluição",
        "moagem": "Média (textura de areia)",
        "descricao": "Receita do estilo campeonato mundial de AeroPress: extração "
                     "concentrada, depois diluída. Saída suave e brilhante.",
        "equipamentos": [
            "AeroPress + filtro de papel",
            "Moedor",
            "Balança e cronômetro",
            "Chaleira",
        ],
        "ingredientes": [
            "18 g de café moído na hora (moagem média)",
            "100 g de água a 85 °C para extração",
            "30 g de água quente para diluição",
        ],
        "passos": [
            "Posição invertida: coloque o êmbolo na marca 4 do cilindro.",
            "Adicione 18 g de café. Dê uma chacoalhada leve para nivelar.",
            "T = 0:00: Despeje 50 g de água em ≈6 s, molhando todo o pó.",
            "T = 0:30: Despeje mais 50 g (total 100 g). Tampe com filtro encharcado.",
            "T = 1:00: Gire suavemente para misturar e bata na bancada para soltar bolhas.",
            "T = 1:35: Vire o AeroPress sobre o decanter. Comece a pressionar lentamente.",
            "Pressão constante por 30-40 s. Pare quando ouvir o chiado.",
            "Saída: ≈76 g concentrados. Dilua com 30 g de água quente.",
            "Mexa para integrar e sirva.",
        ],
        "fonte": "Padrão World AeroPress Championship",
    },
    {
        "id": "chemex",
        "nome": "Chemex — Café limpo e cristalino",
        "metodo": "Chemex",
        "categoria": "Filtrado",
        "icon": "🧪",
        "dificuldade": "Intermediário",
        "tempo": "≈5 min",
        "rendimento": "2 xícaras · 500 ml",
        "ratio": "1 : 15",
        "moagem": "Média-grossa (textura de areia grossa)",
        "descricao": "Filtro Chemex é mais espesso que o V60 — retém mais óleos e "
                     "dá uma xícara excepcionalmente limpa, com acidez bem definida.",
        "equipamentos": [
            "Chemex 6 cups",
            "Filtro Chemex pré-dobrado (bonded)",
            "Chaleira gooseneck",
            "Balança e cronômetro",
        ],
        "ingredientes": [
            "33 g de café especialidade torra clara/média",
            "500 g de água a 94 °C",
        ],
        "passos": [
            "Abra o filtro com a parte tripla apoiada no bico de vazão.",
            "Enxágue bem com água quente (importante por causa da espessura).",
            "Descarte a água sem mexer no filtro.",
            "Adicione 33 g de café moído médio-grosso.",
            "T = 0: Despeje 70 g (bloom) em espiral. Espere 45 s.",
            "T = 0:45: Vá até 250 g em 30 s, em pours circulares lentos.",
            "T = 1:30: Vá até 400 g em 30 s.",
            "T = 2:15: Vá até 500 g.",
            "Drawdown total entre 4:00 e 5:00. Remova o filtro com cuidado.",
            "Sirva quente — sem balançar a Chemex (a sedimentação dá clareza).",
        ],
        "fonte": "Chemex Coffee Maker — método clássico",
    },
    {
        "id": "french-press",
        "nome": "French Press — Ultimate Recipe",
        "metodo": "French Press",
        "categoria": "Imersão",
        "icon": "🫖",
        "dificuldade": "Iniciante",
        "tempo": "≈9 min",
        "rendimento": "2 xícaras · 500 ml",
        "ratio": "1 : 16,6",
        "moagem": "Média (não grossa, ao contrário do que se diz)",
        "descricao": "Receita do James Hoffmann que mudou paradigma: moagem média, "
                     "espera longa, sem mexer com colher. Resultado limpíssimo.",
        "equipamentos": [
            "French press 1L",
            "Moedor",
            "Balança e cronômetro",
            "Colher grande (não plástica)",
        ],
        "ingredientes": [
            "30 g de café moído na hora (moagem média)",
            "500 g de água a 96 °C",
        ],
        "passos": [
            "Pré-aqueça a French press com água quente. Descarte.",
            "Adicione 30 g de café moído médio.",
            "T = 0: Despeje 500 g de água quente sobre o pó, de uma vez.",
            "T = 4:00: Quebre a crosta de pó na superfície mexendo 3-4 vezes "
            "com a colher. Vão soltar gases.",
            "Retire a espuma e o pó da superfície com a colher (≈30 s).",
            "Deixe descansar de 5 a 8 minutos sem mexer (sedimentação).",
            "Coloque o êmbolo apenas apoiado na superfície — NÃO pressione.",
            "Sirva delicadamente, deixando os últimos 10% no fundo.",
        ],
        "fonte": "James Hoffmann — Ultimate French Press Technique",
    },
    {
        "id": "moka",
        "nome": "Moka Pot — Cafeteira Italiana",
        "metodo": "Moka Pot",
        "categoria": "Pressão",
        "icon": "♨️",
        "dificuldade": "Iniciante",
        "tempo": "≈6 min",
        "rendimento": "Conforme o tamanho da Moka (3, 6, 9 xícaras)",
        "ratio": "Padrão da Moka — preenchimento do funil",
        "moagem": "Média-fina (mais grossa que espresso)",
        "descricao": "Clássico italiano. Café encorpado e intenso, próximo de um "
                     "espresso simples. Truque do Hoffmann: água quente desde o início.",
        "equipamentos": [
            "Moka Pot Bialetti (3, 6 ou 9 xícaras)",
            "Moedor",
            "Chaleira",
            "Fogão",
        ],
        "ingredientes": [
            "Café moído médio-fino o suficiente para preencher o funil sem compactar",
            "Água quente até a válvula de segurança (sem cobri-la)",
        ],
        "passos": [
            "Ferva água em uma chaleira separadamente.",
            "Encha a base da Moka com água quente até logo abaixo da válvula.",
            "Coloque o funil. Preencha com café moído sem compactar — apenas "
            "nivele com o dedo. NÃO use tamper.",
            "Rosqueie a parte de cima com cuidado (atenção: a base está quente).",
            "Leve ao fogão em fogo baixo-médio. Tampa aberta.",
            "Quando o café começar a sair amarelado, fique perto.",
            "Assim que vier um som de chiado e a vazão ficar clara/branca, "
            "remova IMEDIATAMENTE do fogo.",
            "Pare a extração colocando a base sob água fria corrente por 5 s.",
            "Sirva imediatamente — Moka muda muito ao esfriar.",
        ],
        "fonte": "James Hoffmann — How to Make Stovetop Espresso",
    },
    {
        "id": "cold-brew",
        "nome": "Cold Brew — Infusão a Frio",
        "metodo": "Cold Brew",
        "categoria": "Imersão",
        "icon": "🧊",
        "dificuldade": "Iniciante",
        "tempo": "12 a 16 h (geladeira)",
        "rendimento": "1 L de concentrado",
        "ratio": "1 : 8 (concentrado) ou 1 : 12 (pronto)",
        "moagem": "Grossa (textura de pimenta-do-reino grossa)",
        "descricao": "Extração a frio. Doce, baixa acidez, muito refrescante. "
                     "O concentrado guarda na geladeira por até 2 semanas.",
        "equipamentos": [
            "Jarra grande ou frasco de vidro 1,5 L",
            "Coador de papel ou pano (Chemex serve)",
            "Geladeira",
        ],
        "ingredientes": [
            "120 g de café moído grosso (1 : 8 = concentrado) "
            "ou 80 g (1 : 12 = bebida pronta)",
            "1 L de água fria filtrada",
        ],
        "passos": [
            "Pese 120 g de café e moa grosso.",
            "Coloque o café no frasco. Adicione 1 L de água fria.",
            "Mexa bem com uma colher para garantir que todo o pó está molhado.",
            "Tampe e leve à geladeira por 12 a 16 horas.",
            "Coe primeiro em uma peneira fina para tirar o pó grosso.",
            "Filtre o líquido em papel filtro (Chemex/V60) — pode levar 20 min.",
            "Guarde o concentrado em garrafa fechada na geladeira.",
            "Para beber: dilua 1 : 1 com água ou leite, com gelo.",
            "Validade: até 2 semanas na geladeira.",
        ],
        "fonte": "Stumptown Roasters — guia clássico de Cold Brew",
    },
    {
        "id": "cappuccino",
        "nome": "Cappuccino Italiano Clássico",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "☁️",
        "dificuldade": "Avançado",
        "tempo": "≈3 min total",
        "rendimento": "150-180 ml",
        "ratio": "1/3 espresso · 1/3 leite · 1/3 espuma firme",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "O clássico italiano: terços iguais de espresso, leite vaporizado "
                     "e espuma firme e seca. Servido em xícara pequena (180 ml).",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite (350 ml) inox",
            "Termômetro (opcional) ou mão como referência",
            "Xícara de cappuccino 180 ml pré-aquecida",
        ],
        "ingredientes": [
            "1 dose de espresso (18 g → 36 g)",
            "120 ml de leite integral gelado",
        ],
        "passos": [
            "Pré-aqueça a xícara com água quente.",
            "Extraia 1 dose de espresso direto na xícara aquecida (vide receita Espresso).",
            "Encha a jarra com 120 ml de leite gelado.",
            "Posicione o bico do vaporizador 1 cm abaixo da superfície do leite.",
            "Abra o vapor: incorpore ar por 3-4 s (som de 'tch tch') para criar espuma.",
            "Afunde o bico no fundo (sem encostar) e crie um vórtice para integrar.",
            "Pare a 60-65 °C (jarra fica quente demais para segurar).",
            "Bata a jarra na bancada e gire para alinhar leite e espuma.",
            "Despeje delicadamente sobre o espresso. Leve a espuma com a colher por cima.",
            "Sirva imediatamente. Polvilhe cacau ou canela (opcional).",
        ],
        "fonte": "Padrão Italiano (180 ml, 1/3 + 1/3 + 1/3)",
    },
    {
        "id": "latte",
        "nome": "Caffè Latte",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "🥛",
        "dificuldade": "Intermediário",
        "tempo": "≈3 min",
        "rendimento": "250-300 ml",
        "ratio": "1 espresso : 3 leite vaporizado",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "Mais leite que o cappuccino, com microfoam suave em vez de "
                     "espuma firme. Textura aveludada e doce.",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite 500 ml",
            "Xícara grande ou copo 300 ml",
        ],
        "ingredientes": [
            "1 dose de espresso (18 g → 36 g)",
            "200 ml de leite integral gelado",
        ],
        "passos": [
            "Extraia 1 dose de espresso na xícara/copo (vide receita Espresso).",
            "Encha a jarra com 200 ml de leite integral gelado.",
            "Posicione o vaporizador na superfície e abra. Incorpore ar SÓ por 1-2 s "
            "(menos que cappuccino — queremos microfoam, não espuma firme).",
            "Afunde o bico 1 cm e crie um vórtice. Aqueça até 60-65 °C.",
            "Bata a jarra para estourar bolhas grossas. Gire para integrar.",
            "Despeje em fluxo contínuo sobre o espresso, alto e fino no início.",
            "Aproxime a jarra da superfície para começar a desenhar latte art.",
            "Sirva imediatamente.",
        ],
        "fonte": "Padrão SCA — Microfoam latte",
    },
    {
        "id": "flat-white",
        "nome": "Flat White Australiano",
        "metodo": "Espresso",
        "categoria": "Com Leite",
        "icon": "⚪",
        "dificuldade": "Avançado",
        "tempo": "≈3 min",
        "rendimento": "160-180 ml",
        "ratio": "2 espresso : 3 leite microfoam",
        "moagem": "Fina (mesma do espresso)",
        "descricao": "Estilo australiano/neozelandês: espresso duplo (ristretto) com "
                     "microfoam fininha. Café mais presente que no latte. Sem espuma alta.",
        "equipamentos": [
            "Máquina de espresso com vaporizador",
            "Jarra de leite 350 ml",
            "Xícara 160 ml pré-aquecida",
        ],
        "ingredientes": [
            "1 dose dupla ristretto (20 g → 30-35 g)",
            "120 ml de leite integral gelado",
        ],
        "passos": [
            "Pré-aqueça a xícara.",
            "Extraia 1 dose dupla ristretto (20 g de pó → 30-35 g na xícara em 25-30 s).",
            "Encha a jarra com 120 ml de leite gelado.",
            "Vaporize com MUITO POUCO ar (1 s só) — buscamos textura de tinta acetinada.",
            "Aqueça até 55-60 °C. Microfoam quase invisível.",
            "Bata a jarra. Gire muito até virar uma 'tinta' homogênea.",
            "Despeje em fluxo único e contínuo, baixo na superfície.",
            "Termine com um corte fino — sem 'topo' de espuma.",
            "Diferença para o latte: menos volume, menos espuma, mais café.",
        ],
        "fonte": "Padrão australiano/neozelandês moderno",
    },
]
