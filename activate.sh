#!/bin/bash
# Script para ativar o ambiente virtual

echo "🐍 Ativando ambiente virtual Python..."
source .venv/bin/activate

echo "✅ Ambiente virtual ativado!"
echo ""
echo "📦 Pacotes instalados:"
pip list | grep -E "(ccxt|pandas|numpy|gspread|google-auth|requests|python-dotenv)"
echo ""
echo "💡 Para desativar, use: deactivate"
echo "💡 Para rodar o bot: python trading.py"
echo "💡 Para testar Google Sheets: python test_sheets.py"
