# 🔧 Guia: Atualizar Planilha Base_logs com 36 Colunas

## 📋 Opções para Atualizar a Planilha

### ✅ **OPÇÃO 1: Atualização Manual (Mais Rápida)**

1. **Abra sua planilha Base_logs no Google Sheets**

2. **Selecione a linha 1 (cabeçalhos)**

3. **Cole os seguintes cabeçalhos na linha 1, coluna A:**

```
ID	Data	Hora	Timestamp	Cripto	Operação	Tipo	RSI	EMA_Trend	ATR	ATR_Percentil	Volume_Ratio	Preço_Entrada	Slippage_%	Tamanho_Posição_USD	Tamanho_Posição_Moedas	Leverage	Stop_Loss_Preço	Stop_Loss_%	Take_Profit_1_Preço	Take_Profit_1_%	Take_Profit_2_Preço	Take_Profit_2_%	Risk_Reward_Ratio	Preço_Saída	P&L_USD	P&L_%	Tempo_Trade_Min	MFE_%	MAE_%	Mercado_Tendência	Mercado_Volatilidade	Qualidade_Entrada	Motivo	Observações
```

4. **Formate os cabeçalhos:**
   - Selecione linha 1
   - Negrito (Ctrl+B / Cmd+B)
   - Centralizar texto
   - Adicionar cor de fundo cinza claro
   - Congelar linha 1 (Ver → Congelar → 1 linha)

---

### 🔧 **OPÇÃO 2: Script Automático (Requer Credenciais Google)**

#### **Passo 1: Configurar Credenciais Google Cloud**

Se você ainda não tem as credenciais:

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto (ou use existente)
3. Ative a API do Google Sheets
4. Crie uma conta de serviço (Service Account)
5. Baixe o arquivo JSON de credenciais
6. Renomeie para `google-credentials.json`
7. Coloque na pasta `/Users/joaoreis/Documents/Trading/`

**Consulte o arquivo `SETUP_GOOGLE_CLOUD.md` para instruções detalhadas**

#### **Passo 2: Compartilhar Planilha**

1. Abra o arquivo `google-credentials.json`
2. Copie o email da service account (ex: `bot@projeto.iam.gserviceaccount.com`)
3. Abra sua planilha Base_logs
4. Clique em "Compartilhar"
5. Adicione o email da service account com permissão de "Editor"

#### **Passo 3: Executar Script**

```bash
cd /Users/joaoreis/Documents/Trading
python update_sheets_headers.py
```

O script irá:
- ✅ Conectar à planilha Base_logs
- ✅ Verificar dados existentes
- ✅ Atualizar para 36 colunas
- ✅ Formatar cabeçalhos (negrito + fundo cinza)
- ✅ Congelar primeira linha

---

## 📊 Estrutura das 36 Colunas

### **1. IDENTIFICAÇÃO** (Colunas A-G: 7 campos)
- A: ID (identificador único do trade)
- B: Data (formato DD/MM/YYYY)
- C: Hora (formato HH:MM:SS)
- D: Timestamp (ISO 8601 completo)
- E: Cripto (SOL, XRP, etc)
- F: Operação (LONG ou SHORT)
- G: Tipo (Entrada ou Saída)

### **2. CONTEXTO/INDICADORES** (Colunas H-L: 5 campos)
- H: RSI (Relative Strength Index)
- I: EMA_Trend (Bullish, Bearish, Neutral)
- J: ATR (Average True Range em USD)
- K: ATR_Percentil (0-100, ranking de volatilidade)
- L: Volume_Ratio (volume atual / média)

### **3. EXECUÇÃO** (Colunas M-Q: 5 campos)
- M: Preço_Entrada (preço exato)
- N: Slippage_% (diferença esperado vs real)
- O: Tamanho_Posição_USD (em dólares)
- P: Tamanho_Posição_Moedas (quantidade)
- Q: Leverage (alavancagem usada)

### **4. GESTÃO DE RISCO** (Colunas R-X: 7 campos)
- R: Stop_Loss_Preço
- S: Stop_Loss_%
- T: Take_Profit_1_Preço (parcial 50%)
- U: Take_Profit_1_%
- V: Take_Profit_2_Preço (total 50%)
- W: Take_Profit_2_%
- X: Risk_Reward_Ratio

### **5. RESULTADOS** (Colunas Y-AD: 6 campos)
- Y: Preço_Saída
- Z: P&L_USD (lucro/prejuízo em dólares)
- AA: P&L_% (lucro/prejuízo percentual)
- AB: Tempo_Trade_Min (duração em minutos)
- AC: MFE_% (Maximum Favorable Excursion)
- AD: MAE_% (Maximum Adverse Excursion)

### **6. ANÁLISE** (Colunas AE-AJ: 6 campos)
- AE: Mercado_Tendência (Strong Uptrend, Uptrend, Range, Downtrend, Strong Downtrend)
- AF: Mercado_Volatilidade (Muito Alta, Alta, Normal, Baixa)
- AG: Qualidade_Entrada (Excelente, Boa, Regular, Ruim)
- AH: Motivo (razão da operação)
- AJ: Observações (notas adicionais)

---

## 🔍 Verificação Após Atualização

Depois de atualizar, verifique se:

1. ✅ A linha 1 contém os 36 cabeçalhos
2. ✅ Os cabeçalhos estão formatados (negrito, centralizado)
3. ✅ A linha 1 está congelada
4. ✅ As colunas vão até AJ (coluna 36)
5. ✅ Os dados antigos (se houver) estão preservados nas linhas 2+

---

## 🚀 Próximo Passo

Após atualizar a planilha, o bot automaticamente usará a nova estrutura:

```bash
# Testar conexão com planilha atualizada
export WALLET_ADDRESS="seu_endereço"
export HYPERLIQUID_PRIVATE_KEY="sua_chave"
export HYPERLIQUID_SUBACCOUNT="seu_vault"
python trading.py
```

Quando o bot executar um trade, ele preencherá automaticamente todas as 36 colunas com os dados quantitativos!

---

## 💡 Dicas

### **Backup dos Dados Antigos**
Se sua planilha já tem dados:
1. Duplique a aba antes de atualizar
2. Ou exporte como CSV backup

### **Fórmulas Úteis**
Após começar a coletar dados, você pode criar fórmulas:

```excel
// Win Rate
=COUNTIFS(G:G,"Saída",AA:AA,">0")/COUNTIF(G:G,"Saída")*100

// Profit Factor
=SUMIF(AA:AA,">0",AA:AA)/ABS(SUMIF(AA:AA,"<0",AA:AA))

// Tempo Médio em Vencedores
=AVERAGEIF(AA:AA,">0",AB:AB)
```

### **Tabelas Dinâmicas**
Crie tabelas dinâmicas para analisar:
- Performance por faixa de RSI
- Performance por volatilidade
- Performance por qualidade de entrada
- Win rate por hora do dia

---

## ❓ Problemas Comuns

### **"Permissão negada"**
- Verifique se compartilhou a planilha com a service account
- Verifique se deu permissão de "Editor"

### **"Planilha não encontrada"**
- Verifique se o nome está correto (Base_logs)
- Verifique se a variável GOOGLE_SHEET_NAME está configurada

### **"Credenciais inválidas"**
- Baixe novamente o JSON do Google Cloud
- Verifique se o arquivo não está corrompido
- Verifique se as APIs estão ativadas

---

## 📚 Mais Informações

- **Estrutura completa:** `ESTRUTURA_DADOS_COMPLETA.md`
- **Setup Google Cloud:** `SETUP_GOOGLE_CLOUD.md`
- **Implementação técnica:** `IMPLEMENTACAO_COMPLETA.md`

---

✅ **Planilha pronta para receber dados quantitativos completos!**
