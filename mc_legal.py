"""mc_legal.py — Termos de Uso e Política de Privacidade.

Textos em markdown, sem dependência de Streamlit para poderem ser lidos e
revisados fora do app.

ATENÇÃO — antes de abrir o cadastro ao público, substitua os marcadores
`[PREENCHER: ...]`. Eles são dados jurídicos do controlador que só o titular
do negócio tem; deixá-los como estão torna os documentos inválidos na prática.
"""
from __future__ import annotations

VIGENCIA = "1 de agosto de 2026"
CONTROLADOR = "[PREENCHER: nome completo ou razão social do controlador]"
DOC_CONTROLADOR = "[PREENCHER: CPF ou CNPJ]"
CONTATO = "[PREENCHER: e-mail de contato para titulares de dados]"

TERMOS = f"""
## Termos de Uso

**Vigência:** {VIGENCIA}

### 1. O que é o Mateu Coffee
O Mateu Coffee é um aplicativo para registrar cafés, extrações e avaliações
sensoriais. É oferecido por {CONTROLADOR} ({DOC_CONTROLADOR}).

### 2. Sua conta
Você é responsável pela senha e pelo que acontece na sua conta. Se desconfiar
de acesso indevido, troque a senha imediatamente — isso encerra as sessões
abertas em outros dispositivos.

### 3. Seu conteúdo é seu
Os cafés, extrações, notas e fotos que você registra continuam sendo seus.
Você nos autoriza apenas a armazenar e processar esse conteúdo para operar o
aplicativo — nada além disso. Não vendemos, licenciamos nem publicamos seu
conteúdo.

### 4. Uso aceitável
Não use o aplicativo para enviar conteúdo ilegal, de terceiros sem
autorização, ou para tentar obter acesso a dados de outras contas.

### 5. Assistente de IA
O "Barista Expert" usa um modelo de linguagem de terceiros e pode errar. As
sugestões são orientativas — confira antes de aplicar, especialmente em
equipamentos sob pressão. Há um limite diário de uso por conta.

### 6. Disponibilidade
O aplicativo é oferecido "como está", sem garantia de disponibilidade
ininterrupta. Fazemos backups automáticos, mas mantenha sua própria cópia do
que for importante — a exportação está na aba Backup.

### 7. Encerramento
Você pode excluir sua conta a qualquer momento pela aba Backup. A exclusão
apaga seus dados de forma definitiva.

### 8. Mudanças nestes termos
Podemos atualizar estes termos. Mudanças relevantes serão anunciadas no
próprio aplicativo antes de passarem a valer.

### 9. Foro
Aplica-se a legislação brasileira.
"""

PRIVACIDADE = f"""
## Política de Privacidade

**Vigência:** {VIGENCIA}
**Controlador:** {CONTROLADOR} ({DOC_CONTROLADOR})
**Contato do titular:** {CONTATO}

### 1. Quais dados tratamos

**Que você fornece**
- E-mail e senha (a senha é guardada apenas como hash bcrypt — ninguém,
  nem nós, consegue lê-la).
- Cafés, extrações, cápsulas, notas sensoriais e avaliações.
- Fotos de embalagens de café e de xícaras.
- Perguntas feitas ao assistente de IA.

**Coletados automaticamente**
- Endereço IP e horário nas tentativas de login, para conter ataques de força
  bruta.
- Um cookie de sessão (`mc_remember`), se você marcar "manter-me conectado".
  Ele guarda um identificador aleatório, não sua senha.

**Se você entrar com o Google:** recebemos seu e-mail e identificador da
conta Google. Não acessamos contatos, agenda ou arquivos.

### 2. Por que tratamos (base legal — LGPD art. 7º)
- **Execução de contrato (inciso V):** operar sua conta e guardar seu acervo.
- **Legítimo interesse (inciso IX):** segurança, prevenção a fraude e limites
  de uso abusivo.

Não usamos seus dados para publicidade e não fazemos perfilamento.

### 3. Com quem compartilhamos
Apenas com a infraestrutura necessária para o aplicativo funcionar:
- **Render** — hospedagem do aplicativo.
- **Neon** — banco de dados (PostgreSQL).
- **Google (Gemini)** — recebe o texto das perguntas que você faz ao Barista
  Expert. Não envie dados pessoais nesse campo.
- **Google OAuth** — apenas se você optar por entrar com o Google.
- **Resend** — envio dos e-mails de recuperação de senha.

Parte desses serviços processa dados fora do Brasil. Não vendemos dados a
ninguém.

### 4. Por quanto tempo guardamos
Enquanto sua conta existir. Tentativas de login e pedidos de redefinição de
senha são apagados após 7 dias. Backups automáticos são mantidos até os 5 mais
recentes. Ao excluir a conta, tudo é removido.

### 5. Seus direitos (LGPD art. 18)
Você pode, a qualquer momento e por conta própria, na aba **Backup**:
- **Acessar e portar** seus dados — exportação em ZIP com CSVs e fotos.
- **Eliminar** sua conta e todos os dados.

Para correção, informação sobre compartilhamento, revogação de consentimento
ou qualquer dúvida, escreva para {CONTATO}. Respondemos em até 15 dias.

### 6. Segurança
Conexão sempre por HTTPS, senha guardada como hash bcrypt, token de sessão
guardado como hash, isolamento por conta em todas as consultas e limite de
tentativas de login. Nenhum sistema é totalmente imune — se ocorrer um
incidente relevante, avisaremos os titulares afetados e a ANPD.

### 7. Crianças
O aplicativo não é destinado a menores de 18 anos.

### 8. Mudanças
Atualizações desta política serão anunciadas no aplicativo.
"""


def pendencias() -> list[str]:
    """Marcadores ainda não preenchidos — usado pelo teste e pelo aviso na UI."""
    faltando = []
    for nome, valor in (("controlador", CONTROLADOR),
                        ("documento", DOC_CONTROLADOR),
                        ("contato", CONTATO)):
        if "PREENCHER" in valor:
            faltando.append(nome)
    return faltando
