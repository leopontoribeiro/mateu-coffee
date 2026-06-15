import { Anthropic } from "@anthropic-ai/sdk";
import coffeeKnowledge from "@/lib/coffee-knowledge.json";

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const systemPrompt = `Você é um Barista Expert — especialista em café com 15+ anos de experiência em specialty coffee, equipamentos, grãos e técnicas de extração.

BASE DE CONHECIMENTO:
${JSON.stringify(coffeeKnowledge, null, 2)}

INSTRUÇÕES:
1. Responda SEMPRE em português brasileiro
2. Seja prático e direto - dê dicas que o usuário possa executar já
3. Use especificações exatas da knowledge base quando relevante
4. Cite equipamentos e grãos por nome quando apropriado
5. Se não tiver certeza, admita e sugira experimentação
6. Responda como um barista experiente explicando para outro café
7. Máximo 300 palavras por resposta
8. Se pergunta for fora do escopo de café, redirecione educadamente

ESCOPO:
✅ Café specialty, equipamentos, técnicas, grãos, defeitos, armazenamento
❌ Receitas não-café, dietas, diagnósticos médicos`;

export async function POST(req: Request) {
  try {
    const { pergunta } = await req.json();

    if (!pergunta || pergunta.trim().length === 0) {
      return Response.json(
        { error: "Pergunta vazia" },
        { status: 400 }
      );
    }

    const message = await client.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 1024,
      system: systemPrompt,
      messages: [
        {
          role: "user",
          content: pergunta,
        },
      ],
    });

    const resposta =
      message.content[0].type === "text"
        ? message.content[0].text
        : "❌ Erro ao processar resposta";

    return Response.json({ resposta });
  } catch (error) {
    console.error("Barista Expert Error:", error);
    return Response.json(
      {
        error: "Erro ao conectar com Barista Expert",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
