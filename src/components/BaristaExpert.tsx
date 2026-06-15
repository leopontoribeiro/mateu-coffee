"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Loader, Send, Sparkles } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function BaristaExpert() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pergunta.trim() || loading) return;

    const userMessage = pergunta;
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setPergunta("");
    setLoading(true);

    try {
      const res = await fetch("/api/barista", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta: userMessage }),
      });

      if (!res.ok) throw new Error("Erro na resposta");

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.resposta || "❌ Erro ao conectar com Barista Expert",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Erro ao conectar com Barista Expert. Tente novamente.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full h-full flex flex-col bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-950 dark:to-amber-950 border border-orange-200 dark:border-orange-800">
      {/* Header */}
      <div className="p-6 border-b border-orange-200 dark:border-orange-800">
        <div className="flex items-center gap-3 mb-2">
          <Sparkles className="w-6 h-6 text-orange-600 dark:text-orange-400" />
          <h3 className="text-xl font-bold text-orange-900 dark:text-orange-100">
            Barista Expert
          </h3>
        </div>
        <p className="text-sm text-orange-700 dark:text-orange-300">
          IA especializada em café • Equipamentos • Grãos • Técnicas • Defeitos
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div>
              <Sparkles className="w-12 h-12 text-orange-400 mx-auto mb-4 opacity-50" />
              <p className="text-orange-700 dark:text-orange-300">
                Faça uma pergunta sobre café...
              </p>
              <p className="text-xs text-orange-600 dark:text-orange-400 mt-2">
                Ex: Como calibrar a moagem para espresso?
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                  msg.role === "user"
                    ? "bg-orange-600 text-white rounded-br-none"
                    : "bg-white dark:bg-orange-900 text-gray-800 dark:text-orange-50 rounded-bl-none border border-orange-200 dark:border-orange-700"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-orange-900 px-4 py-3 rounded-lg rounded-bl-none border border-orange-200 dark:border-orange-700">
              <Loader className="w-5 h-5 text-orange-600 dark:text-orange-400 animate-spin" />
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleAsk}
        className="p-6 border-t border-orange-200 dark:border-orange-800"
      >
        <div className="flex gap-2">
          <Input
            placeholder="Pergunta ao Barista Expert..."
            value={pergunta}
            onChange={(e) => setPergunta(e.target.value)}
            disabled={loading}
            className="dark:bg-orange-900 dark:border-orange-700 dark:text-white"
          />
          <Button
            type="submit"
            disabled={loading || !pergunta.trim()}
            className="bg-orange-600 hover:bg-orange-700 text-white px-4"
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </form>
    </Card>
  );
}
