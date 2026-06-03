#!/bin/bash

# Script para fazer PUSH dos arquivos para GitHub
# Execute isto no TERMINAL do seu computador (não na VM)

echo "🚀 Iniciando Push para GitHub..."
echo ""

# Navegar para o repositório
cd ~/mateu-coffee-v1_1 || cd /path/to/mateu-coffee-v1_1

# Verificar status
echo "📋 Status atual:"
git status

echo ""
echo "⏳ Aguarde autenticação GitHub..."
echo ""

# Fazer o push
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PUSH CONCLUÍDO COM SUCESSO!"
    echo ""
    echo "Seu repositório foi atualizado em:"
    echo "https://github.com/leopontoribeiro/mateu-coffee"
    echo ""
    echo "🎉 Próximo passo: Deploy no Railway"
else
    echo ""
    echo "❌ Erro ao fazer push. Verifique suas credenciais do GitHub."
fi
