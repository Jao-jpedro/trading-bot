# 🤖 Trading Bot - RSI Strategy com Google Sheets

Bot de trading automatizado para criptomoedas que opera LONG/SHORT baseado em RSI, com registro completo de operações no Google Sheets para análise de performance.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production-success)

## 📊 Funcionalidades

- ✅ Trading automatizado baseado em RSI
- ✅ Suporte a múltiplos assets (SOL, XRP)
- ✅ Alavancagem configurável (padrão 5x)
- ✅ Stop Loss e Take Profit automáticos
- ✅ **Registro automático de trades no Google Sheets**
- ✅ Notificações Discord
- ✅ Sistema de logs detalhado
- ✅ Reconstrução automática de estado

## 📋 Estrutura da Planilha Google Sheets

O bot registra automaticamente cada operação com as seguintes colunas:

| Data | Hora | Preço | Cripto | Operação | Tipo de Operação |
|------|------|-------|--------|----------|------------------|
| 18/04/2026 | 14:30:25 | 145.2500 | SOL | LONG | Compra |
| 18/04/2026 | 16:45:10 | 151.3200 | SOL | LONG | Venda |

- **Data**: Data da operação (DD/MM/YYYY)
- **Hora**: Hora da operação (HH:MM:SS)
- **Preço**: Preço de execução
- **Cripto**: Ativo negociado (SOL, XRP, etc)
- **Operação**: Tipo de posição (LONG ou SHORT)
- **Tipo de Operação**: Compra ou Venda

## 🔧 Configuração do Google Sheets

### 1. Criar Projeto no Google Cloud

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative as APIs necessárias:
   - Google Sheets API
   - Google Drive API

### 2. Criar Service Account

1. Vá em "IAM & Admin" > "Service Accounts"
2. Clique em "Create Service Account"
3. Dê um nome (ex: "bot-trader")
4. Clique em "Create and Continue"
5. Em "Grant this service account access to project", selecione "Editor"
6. Clique em "Continue" e depois "Done"

### 3. Gerar Credenciais JSON

1. Clique na service account criada
2. Vá em "Keys" > "Add Key" > "Create new key"
3. Selecione "JSON" e clique em "Create"
4. O arquivo JSON será baixado automaticamente
5. **Renomeie o arquivo para `API.json`** e coloque na pasta do projeto

### 4. Compartilhar Planilha

1. Crie uma planilha no Google Sheets (ou use existente)
2. Abra o arquivo `API.json` e copie o email da service account:
   ```json
   "client_email": "bot-trader@seu-projeto.iam.gserviceaccount.com"
   ```
3. Compartilhe a planilha com este email (permissão de **Editor**)
4. Configure o nome da planilha no `.env`:
   ```
   GOOGLE_SHEET_NAME=Trading Bot
   ```

## 🚀 Instalação e Uso

### Instalação Local

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 3. Colocar arquivo API.json na pasta do projeto

# 4. Executar o bot
python trading.py
```

### Deploy no Render

1. Crie um novo **Background Worker** no Render
2. Conecte seu repositório GitHub
3. Configure as variáveis de ambiente no painel do Render
4. **Importante**: Faça upload do arquivo `API.json` via Render Dashboard:
   - Vá em "Environment" > "Secret Files"
   - Adicione o arquivo `API.json`

## 📝 Variáveis de Ambiente

```env
# Hyperliquid (obrigatório)
WALLET_ADDRESS=sua_carteira
HYPERLIQUID_PRIVATE_KEY=sua_chave_privada
HYPERLIQUID_SUBACCOUNT=sua_subconta

# Binance (opcional - para dados históricos)
BINANCE_API_KEY=sua_api_key
BINANCE_API_SECRET=sua_api_secret

# Discord (opcional)
DISCORD_WEBHOOK_URL=seu_webhook

# Google Sheets (opcional)
GOOGLE_SHEET_NAME=Trading Bot
```

## 🔍 Monitoramento

O bot registra **automaticamente** no Google Sheets:

- ✅ Todas as **compras** (entradas LONG/SHORT)
- ✅ Todas as **vendas** (Stop Loss ou Take Profit)
- ✅ Data, hora e preço exatos
- ✅ Tipo de operação e cripto

## 🎯 Estratégia

- **Entrada LONG**: RSI < 20 (sobrevendido)
- **Entrada SHORT**: RSI > 80 (sobrecomprado)
- **Stop Loss**: 2% movimento = -10% ROI
- **Take Profit**: 4% movimento = +20% ROI
- **Cooldown**: 48h entre entradas

## 📊 Logs

Os logs são salvos em arquivos com timestamp:
```
trading_dca_20260418_143025.log
```

## ⚠️ Importante

- Mantenha o arquivo `API.json` **seguro** (não commitá-lo no Git)
- Verifique se a planilha está compartilhada com a service account
- O bot precisa rodar continuamente para monitorar ordens executadas

## 🛠️ Troubleshooting

### Erro: "Spreadsheet not found"
- Verifique se compartilhou a planilha com o email da service account
- Confirme o nome da planilha no `.env`

### Erro: "Permission denied"
- A service account precisa ter permissão de **Editor** na planilha
- Verifique as APIs ativadas no Google Cloud Console

### Registros não aparecem
- Verifique os logs do bot: `📊 Registro Google Sheets: ...`
- Confirme que o arquivo `API.json` está correto
- Teste a conexão verificando os logs iniciais: `✅ Google Sheets configurado com sucesso`

## 📞 Suporte

Para dúvidas sobre a integração do Google Sheets, verifique:
- [Documentação gspread](https://docs.gspread.org/)
- [Google Sheets API](https://developers.google.com/sheets/api)
