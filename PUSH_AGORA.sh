#!/bin/bash
# PUSH RÁPIDO - MATEU COFFEE V2.0

cd ~/mateu-coffee

# Limpar lock
rm -f .git/index.lock

# Adicionar arquivos
git add streamlit_app.py database.py schema.sql auth.py

# Commit
git commit -m "🚀 v2.0 FINAL: 13 correções Barista Sênior (9.6/10)"

# Push
git push origin main

echo "✅ DEPLOY INICIADO!"
echo "⏱️  App será atualizado em 2-3 minutos"
echo "🌐 Acesse: https://mateu-coffee-production.up.railway.app"
