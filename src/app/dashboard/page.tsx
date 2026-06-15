"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { BaristaExpert } from "@/components/BaristaExpert";

interface Coffee {
  id: string;
  nome: string;
  avaliacao: number;
  origem: string;
  preco: number;
}

interface Promotion {
  id: string;
  titulo: string;
  descricao: string;
  desconto: number;
}

// Dados mock - substituir pela sua API depois
const bestCoffee: Coffee = {
  id: "1",
  nome: "Orfeu Bourbon Amarelo",
  avaliacao: 9.5,
  origem: "Sul de Minas",
  preco: 89.9,
};

const dailyPromotions: Promotion[] = [
  {
    id: "1",
    titulo: "Blend Clássico",
    descricao: "20% OFF",
    desconto: 20,
  },
  {
    id: "2",
    titulo: "Kit Espresso",
    descricao: "Café + Xícara",
    desconto: 15,
  },
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">
            Dashboard ☕
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Bem-vindo ao seu diário premium de cafés especiais
          </p>
        </div>

        {/* Melhor Café + Promoções (uma linha, 2 colunas iguais) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Café com melhor avaliação */}
          <Card className="p-6 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-950 dark:to-amber-950 border border-orange-200 dark:border-orange-800">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-orange-900 dark:text-orange-100 mb-1">
                  ⭐ Melhor Café
                </h3>
                <p className="text-sm text-orange-700 dark:text-orange-300">
                  Maior avaliação do mês
                </p>
              </div>
              <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
                {bestCoffee.avaliacao}
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                  {bestCoffee.nome}
                </p>
                <p className="text-sm text-orange-700 dark:text-orange-300">
                  {bestCoffee.origem}
                </p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-orange-200 dark:border-orange-700">
                <span className="text-sm font-medium text-orange-700 dark:text-orange-300">
                  Preço
                </span>
                <span className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  R$ {bestCoffee.preco}
                </span>
              </div>

              <button className="w-full mt-4 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg transition">
                Comprar Agora
              </button>
            </div>
          </Card>

          {/* Melhores Promoções do Dia */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white px-2">
              🎯 Promoções do Dia
            </h3>

            {dailyPromotions.map((promo) => (
              <Card
                key={promo.id}
                className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-orange-400 dark:hover:border-orange-600 transition cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-bold text-slate-900 dark:text-white">
                      {promo.titulo}
                    </p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {promo.descricao}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                      -{promo.desconto}%
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Barista Expert (2/3 da largura) */}
        <div className="lg:col-span-2">
          <div className="h-96">
            <BaristaExpert />
          </div>
        </div>

        {/* Outras seções que você possa ter */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-white dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              📊 Estatísticas
            </h3>
            <div className="space-y-2 text-sm">
              <p className="text-slate-600 dark:text-slate-400">
                Total de Cafés: <span className="font-bold">12</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Extrações este mês: <span className="font-bold">24</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Nota média: <span className="font-bold text-orange-600">8.5</span>
              </p>
            </div>
          </Card>

          <Card className="p-6 bg-white dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              🔥 Tendência
            </h3>
            <div className="space-y-2 text-sm">
              <p className="text-slate-600 dark:text-slate-400">
                Método favorito: <span className="font-bold">Espresso</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Grão mais usado: <span className="font-bold">Arábica</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Melhor hora: <span className="font-bold">Manhã (08h)</span>
              </p>
            </div>
          </Card>

          <Card className="p-6 bg-white dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              ⏰ Próximo
            </h3>
            <div className="space-y-2 text-sm">
              <p className="text-slate-600 dark:text-slate-400">
                Próxima entrega: <span className="font-bold">3 dias</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Café a chegar: <span className="font-bold">Geisha</span>
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                Status: <span className="font-bold text-blue-600">Em trânsito</span>
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
