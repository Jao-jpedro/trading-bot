# 📝 VARIÁVEIS DE AMBIENTE - RESUMO RÁPIDO

## 🔴 OBRIGATÓRIAS

```bash
WALLET_ADDRESS=0x1234...              # Sua carteira Hyperliquid
HYPERLIQUID_PRIVATE_KEY=0xabcd...     # Chave privada (⚠️ SEGREDO!)
GOOGLE_CREDENTIALS_BASE64=eyJ0eXB...  # API.json em base64
```

---

## 🟡 RECOMENDADAS

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # Notificações
GOOGLE_SHEET_NAME=Base_logs                                # Nome da planilha
HYPERLIQUID_SUBACCOUNT=0x5678...                          # Vault (se usar)
```

---

## 🟢 OPCIONAIS

```bash
BINANCE_API_KEY=A1B2C3...        # Dados históricos (opcional)
BINANCE_API_SECRET=Q7W8E9...     # Acompanha API Key
```

---

## 🔧 COMO CONVERTER API.json PARA BASE64

```bash
# No terminal do Mac:
cd /Users/joaoreis/Documents/Trading
base64 -i API.json | tr -d '\n' | pbcopy

# Agora está na área de transferência!
# Cole no Render como: GOOGLE_CREDENTIALS_BASE64
```

---

## 📋 TEMPLATE PRONTO

```bash
# Copie e preencha com seus valores:

WALLET_ADDRESS=
HYPERLIQUID_PRIVATE_KEY=
GOOGLE_CREDENTIALS_BASE64=
DISCORD_WEBHOOK_URL=
GOOGLE_SHEET_NAME=Base_logs
HYPERLIQUID_SUBACCOUNT=
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

---

## ⚠️ IMPORTANTE

**Antes de deployar no Render:**
1. ✅ Converter API.json para base64
2. ✅ Modificar trading.py para ler base64 (veja GUIA_RENDER.md)
3. ✅ Testar localmente primeiro
4. ✅ Fazer commit das mudanças
5. ✅ Depois configurar no Render

---

**Quer que eu modifique o trading.py agora para suportar base64?**
