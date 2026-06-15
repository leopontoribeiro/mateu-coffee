"""
Barista Expert - IA especializada em café usando Claude API
"""
import os
import json
import anthropic


# Carregar knowledge base
def load_knowledge_base():
    """Carrega o JSON de conhecimento sobre café."""
    try:
        with open("coffee_knowledge.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


KB = load_knowledge_base()
KB_TEXT = json.dumps(KB, indent=2, ensure_ascii=False)


def ask_barista_expert(pergunta: str) -> str:
    """
    Pergunta ao Barista Expert usando Claude API com knowledge base.

    Args:
        pergunta: Pergunta sobre café, extração, grãos, equipamentos, etc

    Returns:
        Resposta do barista expert baseada no knowledge base
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ Variável ANTHROPIC_API_KEY não configurada no Render"

    try:
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = f"""Você é um Barista Expert — especialista em café com 15+ anos de experiência.

Use a seguinte base de conhecimento para responder perguntas sobre:
- Equipamentos (Oster, Starseeker E55 Pro)
- Grãos e variedades (Arábica, Robusta, Bourbon Amarelo, Geisha, etc)
- Marcas (Orfeu, Coffee++, Três Corações)
- Química e extração (Maillard, TDS, pressão, temperatura)
- Métodos de extração (Espresso, V60, Prensa Francesa, etc)
- Defeitos e soluções (Underextraction, Overextraction, Channeling)
- Armazenamento, água, cupping

KNOWLEDGE BASE:
{KB_TEXT}

Instruções:
1. Sempre responda em português brasileiro
2. Seja prático e direto
3. Se a pergunta for sobre equipamentos/grãos que estão na KB, use as especificações exatas
4. Dê dicas actionáveis que o usuário possa executar imediatamente
5. Se não souber, admita e sugira experimentação
6. Inclua referências à knowledge base quando relevante (ex: "Conforme a documentação do E55 Pro...")

Responda de forma conversacional mas técnica, como um barista experiente explicando para outro café."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": pergunta
                }
            ]
        )

        return message.content[0].text

    except Exception as e:
        return f"❌ Erro ao conectar com Barista Expert: {str(e)}"


if __name__ == "__main__":
    # Teste
    resposta = ask_barista_expert("Como calibrar a moagem do Starseeker E55 Pro para espresso na Oster?")
    print(resposta)
