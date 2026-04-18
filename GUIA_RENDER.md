# 🚀 GUIA DE DEPLOY NO RENDER

**Data:** 18/04/2026  
**Repositório:** https://github.com/Jao-jpedro/trading-bot

---

## 📋 VARIÁVEIS DE AMBIENTE NECESSÁRIAS

### 🔴 OBRIGATÓRIAS (sem elas o bot não funciona)

#### 1. **WALLET_ADDRESS**
```
Descrição: Endereço da sua carteira Hyperliquid
Formato: 0x... (42 caracteres)
Exemplo: 0x1234567890abcdef1234567890abcdef12345678
Onde obter: MetaMask ou sua carteira Ethereum
```

#### 2. **HYPERLIQUID_PRIVATE_KEY**
```
Descrição: Chave privada da carteira Hyperliquid
Formato: 0x... (66 caracteres) ou string hex sem 0x
Exemplo: 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
Onde obter: MetaMask → Account details → Export private key
⚠️ NUNCA compartilhe esta chave!
```

#### 3. **GOOGLE_CREDENTIALS_BASE64**
```
Descrição: Credenciais do Google Cloud em formato base64
Formato: String base64 longa
Como obter: Converter API.json para base64 (veja seção abaixo)
```

---

### 🟡 OPCIONAIS (mas recomendadas)

#### 4. **HYPERLIQUID_SUBACCOUNT** (Recomendado)
```
Descrição: Endereço da subconta/vault Hyperliquid
Formato: 0x... (42 caracteres)
Exemplo: 0xabcdef1234567890abcdef1234567890abcdef12
Quando usar: Se você usa vault/subconta na Hyperliquid
Benefício: Isolar fundos do bot
```

#### 5. **DISCORD_WEBHOOK_URL** (Recomendado)
```
Descrição: URL do webhook Discord para notificações
Formato: https://discord.com/api/webhooks/...
Exemplo: https://discord.com/api/webhooks/123456789/abcdefghijklmnop
Como obter: 
  1. Discord → Server Settings → Integrations → Webhooks
  2. Create Webhook → Copy URL
Benefício: Receber alertas de trades em tempo real
```

#### 6. **GOOGLE_SHEET_NAME** (Recomendado)
```
Descrição: Nome da planilha Google Sheets
Formato: String
Valor padrão: Base_logs
Exemplo: Base_logs
Quando mudar: Se você renomear a planilha no Google Sheets
```

---

### 🟢 OPCIONAIS (podem deixar em branco)

#### 7. **BINANCE_API_KEY** (Opcional)
```
Descrição: API Key da Binance
Formato: String alfanumérica
Exemplo: A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
Como obter: Binance → API Management → Create API
Uso: Buscar dados históricos (o bot funciona sem)
Nota: Dados históricos podem vir da Hyperliquid também
```

#### 8. **BINANCE_API_SECRET** (Opcional)
```
Descrição: API Secret da Binance
Formato: String alfanumérica
Exemplo: Q7W8E9R0T1Y2U3I4O5P6A7S8D9F0G1H2
Como obter: Mesma página da API Key
Uso: Acompanha BINANCE_API_KEY
```

---

## 🔐 CONVERTER API.json PARA BASE64

O Render não permite upload direto de arquivos. Você precisa converter o `API.json` para base64.

### Método 1: Terminal no Mac

```bash
# Navegar até o diretório
cd /Users/joaoreis/Documents/Trading

# Converter para base64 (tudo em uma linha)
base64 -i API.json | tr -d '\n' > api_base64.txt

# Ver o resultado
cat api_base64.txt

# Copiar para área de transferência
cat api_base64.txt | pbcopy
```

Depois cole o valor no Render como variável `GOOGLE_CREDENTIALS_BASE64`.

### Método 2: Python

```bash
python3 -c "import base64; print(base64.b64encode(open('API.json', 'rb').read()).decode())"
```

### Método 3: Online (NÃO RECOMENDADO)
⚠️ Nunca use sites online para converter credenciais! Risco de segurança.

---

## 🔧 MODIFICAR trading.py PARA LER BASE64

Você precisa modificar o código para ler credenciais do base64:

### Localizar esta seção no `trading.py`:

```python
# Linha ~182
def __init__(self, sheet_name: str = None):
    # ... código existente ...
    
    # MODIFICAR ESTA PARTE:
    credentials_file = "API.json"  # ❌ Isso não funciona no Render
```

### Substituir por:

```python
def __init__(self, sheet_name: str = None):
    # ... código existente ...
    
    # Ler credenciais do ambiente (base64) ou arquivo local
    import base64
    
    google_creds_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    
    if google_creds_base64:
        # Produção: ler de variável de ambiente
        log("📊 Carregando credenciais Google do ambiente (base64)", "INFO")
        creds_json = base64.b64decode(google_creds_base64)
        creds_dict = json.loads(creds_json)
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        self.gc = gspread.authorize(credentials)
        
    else:
        # Desenvolvimento: ler de arquivo local
        log("📊 Carregando credenciais Google do arquivo API.json", "INFO")
        credentials_file = "API.json"
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        self.gc = gspread.authorize(credentials)
```

---

## 🎯 PASSO A PASSO NO RENDER

### 1. Criar Conta no Render
```
1. Acesse: https://render.com
2. Sign up with GitHub
3. Autorize acesso aos seus repositórios
```

### 2. Criar Background Worker
```
1. Dashboard → New + → Background Worker
2. Conectar repositório: Jao-jpedro/trading-bot
3. Selecionar branch: main
```

### 3. Configurar Build
```
Name: trading-bot
Environment: Python 3
Region: Oregon (US West) - menor latência
Branch: main
Build Command: pip install -r requirements.txt
Start Command: python trading.py
```

### 4. Adicionar Variáveis de Ambiente

**No painel do Render:**
```
Environment → Add Environment Variable

Adicionar UMA POR UMA:

1. WALLET_ADDRESS = 0x...
2. HYPERLIQUID_PRIVATE_KEY = 0x...
3. GOOGLE_CREDENTIALS_BASE64 = eyJ0eXBlIjoi... (muito longo)
4. DISCORD_WEBHOOK_URL = https://discord.com/api/webhooks/...
5. GOOGLE_SHEET_NAME = Base_logs
6. HYPERLIQUID_SUBACCOUNT = 0x... (se usar vault)
```

### 5. Deploy
```
1. Click "Create Background Worker"
2. Aguardar build (2-5 minutos)
3. Verificar logs
```

---

## 📊 VALIDAR DEPLOYMENT

### Verificar Logs no Render:

**Logs esperados:**
```
🚀 INICIANDO SISTEMA DE TRADING - EMA 200 + RSI
✅ Carregado .env
✅ Conexões estabelecidas: Binance (dados) + Hyperliquid (execução)
📊 Carregando credenciais Google do ambiente (base64)
✅ Google Sheets conectado: Base_logs
💰 Saldo disponível: $1,234.56
🔄 INICIANDO CICLO
```

**Se der erro:**
```
❌ WALLET_ADDRESS e HYPERLIQUID_PRIVATE_KEY devem estar configurados
→ Verificar variáveis de ambiente

❌ Error loading credentials from environment
→ Verificar GOOGLE_CREDENTIALS_BASE64

❌ Spreadsheet not found
→ Verificar permissões do service account
→ Compartilhar planilha com: bot-trader@mudar-1572192250313.iam.gserviceaccount.com
```

---

## ✅ CHECKLIST DE CONFIGURAÇÃO

Antes de fazer deploy:

- [ ] Converter API.json para base64
- [ ] Modificar trading.py para ler base64
- [ ] Testar localmente com variável de ambiente
- [ ] Criar conta no Render
- [ ] Conectar repositório GitHub
- [ ] Configurar todas as variáveis obrigatórias
- [ ] Adicionar variáveis opcionais (Discord, etc)
- [ ] Fazer commit e push das mudanças
- [ ] Criar Background Worker
- [ ] Verificar logs de build
- [ ] Confirmar bot está rodando
- [ ] Verificar primeiro trade no Google Sheets
- [ ] Validar notificações Discord

---

## 🔧 TEMPLATE DE VARIÁVEIS

Copie e preencha:

```bash
# ===== OBRIGATÓRIAS =====
WALLET_ADDRESS=
HYPERLIQUID_PRIVATE_KEY=
GOOGLE_CREDENTIALS_BASE64=

# ===== RECOMENDADAS =====
DISCORD_WEBHOOK_URL=
GOOGLE_SHEET_NAME=Base_logs
HYPERLIQUID_SUBACCOUNT=

# ===== OPCIONAIS =====
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

---

## 💰 CUSTOS DO RENDER

### Free Tier (Gratuito)
```
✅ 750 horas/mês
✅ Suficiente para 1 bot rodando 24/7
✅ Reinicia após 15 min de inatividade
❌ Não recomendado para trading real
```

### Paid Tier ($7/mês)
```
✅ Sempre online
✅ Sem reinicializações
✅ 512 MB RAM
✅ Recomendado para produção
```

---

## 🚨 SEGURANÇA

### ⚠️ NUNCA faça:
- ❌ Commitar chaves privadas no GitHub
- ❌ Compartilhar HYPERLIQUID_PRIVATE_KEY
- ❌ Usar sites online para converter credenciais
- ❌ Expor variáveis em logs públicos

### ✅ SEMPRE faça:
- ✅ Use variáveis de ambiente
- ✅ Mantenha .gitignore atualizado
- ✅ Teste com pequenas quantias primeiro
- ✅ Configure limites de perda
- ✅ Monitor logs regularmente

---

## 🆘 TROUBLESHOOTING

### Problema: "Module not found"
```
Solução: Verificar requirements.txt contém todas as dependências
pip freeze > requirements.txt
```

### Problema: "Google Sheets API not enabled"
```
Solução: No Google Cloud Console
1. APIs & Services → Enable APIs
2. Buscar "Google Sheets API"
3. Enable
```

### Problema: "Permission denied on spreadsheet"
```
Solução: Compartilhar planilha
1. Abrir Base_logs no Google Sheets
2. Share → Add: bot-trader@mudar-1572192250313.iam.gserviceaccount.com
3. Role: Editor
```

### Problema: "Insufficient funds"
```
Solução: Depositar mais fundos na Hyperliquid
ou reduzir ENTRY_CAPITAL_PCT no código
```

### Problema: Bot para após algumas horas
```
Solução: Upgrade para Paid tier no Render
Free tier hiberna após inatividade
```

---

## 📞 SUPORTE

**Render Docs:** https://render.com/docs  
**Render Status:** https://status.render.com  
**Hyperliquid Docs:** https://hyperliquid.gitbook.io

---

## 🎉 PRÓXIMOS PASSOS

Após configurar variáveis:

1. **Modificar trading.py** (adicionar suporte a base64)
2. **Testar localmente** com variáveis de ambiente
3. **Commit e push** das mudanças
4. **Deploy no Render**
5. **Monitorar logs**
6. **Validar primeiro trade**

---

**Quer que eu ajude a modificar o `trading.py` para suportar base64?**
