# 🚀 GUIA DE DEPLOY - Render.com

## Pré-requisitos ✓

✅ Código integrado com ATR  
✅ Backtest validado (+105% em 180 dias)  
✅ Dashboard HTML criado  
✅ Git configurado  
✅ Conta no Render.com  

---

## Passo 1: Commit de Todas as Mudanças

```bash
cd /Users/joaoreis/Documents/Trading

# Ver status
git status

# Adicionar todos os arquivos
git add -A

# Commit com mensagem descritiva
git commit -m "feat: estratégia otimizada ATR completa - backtest +105%, dashboard, stops dinâmicos"

# Push para GitHub
git push origin main
```

---

## Passo 2: Configurar Variáveis de Ambiente no Render

### Acessar Render Dashboard:
1. Ir para: https://dashboard.render.com/
2. Selecionar seu serviço `trading-bot`
3. Ir em **Environment** → **Environment Variables**

### Variáveis OBRIGATÓRIAS:

```bash
# Carteiras Hyperliquid
WALLET_ADDRESS=0x08183aa09eF03Cf8475D909F507606F5044cBdAB
HYPERLIQUID_PRIVATE_KEY=0x40a76704827d33be22ee9083bf2b0713e91a6372616c1468e9bd16430adbe645
HYPERLIQUID_SUBACCOUNT=0x5ff0f14d577166f9ede3d9568a423166be61ea9d

# Google Sheets (Base64 do arquivo API.json)
GOOGLE_CREDENTIALS_BASE64=<seu_base64_aqui>
GOOGLE_SHEET_NAME=Base_logs

# Discord (opcional)
DISCORD_WEBHOOK_URL=<seu_webhook_aqui>
```

### Como gerar GOOGLE_CREDENTIALS_BASE64:

```bash
# No Mac/Linux:
base64 -i mudar-1572192250313-373774f3e702.json | tr -d '\n'

# Copiar output e colar no Render
```

---

## Passo 3: Deploy Manual no Render

### Opção A: Deploy Automático (Push GitHub)
- Render detecta o push e faz deploy automaticamente
- Aguardar 2-5 minutos

### Opção B: Deploy Manual
1. No Render Dashboard
2. Selecionar `trading-bot`
3. Clicar em **Manual Deploy**
4. Selecionar branch `main`
5. Clicar em **Deploy latest commit**

---

## Passo 4: Monitorar Logs

### Ver logs em tempo real:
1. No Render Dashboard
2. Ir em **Logs**
3. Procurar por:

```
✅ Google Sheets configurado com sucesso
✅ Conexões estabelecidas: Hyperliquid (dados + execução)
💵 Saldo disponível: $13.73
📊 ATR calculado: $X.XX (stops dinâmicos)
✅ Usando stops ATR (1.5x SL, 2.5x TP)
```

### Logs de Erro Comuns:

| Erro | Causa | Solução |
|------|-------|---------|
| `WALLET_ADDRESS não encontrado` | Variável não configurada | Adicionar no Render Environment |
| `Erro conectando Google Sheets` | Base64 inválido | Regenerar base64 do JSON |
| `Nenhum dado histórico` | Rate limit Hyperliquid | Aguardar 2-3 minutos |

---

## Passo 5: Validar Primeira Operação

### O que monitorar:

1. **Detecção de Sinal**
   ```
   📊 SOL: Preço=$85.00 | RSI=18.5 | Sinal: LONG
   📊 ATR calculado: $0.70 (stops dinâmicos)
   ```

2. **Entrada Executada**
   ```
   🎯 ENTRANDO LONG: 25% do capital em SOL
   💰 Capital disponível: $13.73
   📊 Investindo: $3.43
   🪙 Quantidade: 0.202 SOL @ $85.00
   ```

3. **Stops Calculados com ATR**
   ```
   ✅ Usando stops ATR (1.5x SL, 2.5x TP)
   🎯 ALVOS DEFINIDOS:
      🔴 Stop Loss: $83.95 (-6.15% ROI)
      🟢 Take Profit: $86.75 (+10.30% ROI)
   ```

4. **Google Sheets Atualizado**
   - Verificar planilha `Base_logs`
   - Deve ter: ID, Data, Hora, Preço, Cripto, Operação, Tipo, RSI, **ATR**, Motivo
   - Exemplo: `SOL_20260419_143025 | 19/04/2026 | 14:30:25 | 85.0000 | SOL | LONG | Compra | 18.50 | 0.7000 | RSI sobrevendido`

---

## Passo 6: Testar Dashboard

### Abrir dashboard localmente:

```bash
cd /Users/joaoreis/Documents/Trading

# Servir com Python
python3 -m http.server 8000

# Abrir no navegador:
# http://localhost:8000/dashboard.html
```

### O dashboard deve mostrar:
- ✅ Retorno Total: +105.00%
- ✅ Win Rate: 45.45%
- ✅ Total Trades: 220
- ✅ Gráfico de equity curve
- ✅ Últimos 10 trades

---

## Passo 7: Monitoramento Contínuo

### Checklist Diário:

- [ ] Verificar logs no Render (sem erros)
- [ ] Conferir Google Sheets (trades registrados corretamente)
- [ ] Validar ATR sendo usado (não fallback para stops fixos)
- [ ] Monitorar saldo (não deve zerar inesperadamente)
- [ ] Verificar win rate (deve manter ~45-50%)

### Alertas de Atenção:

🚨 **Saldo zerado** → Parar bot, revisar trades  
🚨 **Win rate < 30%** → Mercado pode estar mudando, avaliar pause  
🚨 **Muitos stops fixos** → ATR não está calculando, verificar dados  
🚨 **Erro Google Sheets** → Credenciais expiraram, renovar  

---

## Rollback (Se Necessário)

Se algo der errado, reverter para versão anterior:

```bash
# Ver commits
git log --oneline

# Reverter para commit anterior
git revert HEAD

# Ou voltar para commit específico
git reset --hard <commit_hash>

# Push forçado (cuidado!)
git push -f origin main
```

---

## Parâmetros Recomendados para $13.73

```python
# No código (já configurado):
ENTRY_CAPITAL_PCT = 25.0      # Usar 25% por trade
ATR_SL_MULTIPLIER = 1.5       # SL = 1.5x ATR
ATR_TP_MULTIPLIER = 2.5       # TP = 2.5x ATR
LEVERAGE = 5                  # 5x leverage
RSI_LONG_THRESHOLD = 20       # RSI < 20 para LONG
RSI_SHORT_THRESHOLD = 80      # RSI > 80 para SHORT
ENTRY_COOLDOWN_HOURS = 48     # 48h entre trades
```

### Expectativas Realistas:

- **Capital:** $13.73
- **Por trade:** ~$3.43 (25%)
- **Exposição:** ~$17.15 (5x leverage)
- **Trades/mês:** ~4-6 trades
- **Meta 6 meses:** +30-50% ($18-21)
- **Risco máximo/trade:** -6% ROI ($0.20 perda)

---

## Suporte e Troubleshooting

### Logs úteis:

```bash
# Ver últimas 100 linhas
# (No Render Dashboard → Logs)

# Procurar por erros
grep "ERROR" logs.txt

# Procurar entradas
grep "ENTRANDO" logs.txt

# Procurar saídas
grep "SAÍDA" logs.txt
```

### Contacts de Emergência:

- **Render Support:** https://render.com/docs
- **Hyperliquid Docs:** https://hyperliquid.gitbook.io/
- **Google Sheets API:** https://developers.google.com/sheets

---

## ✅ Checklist Final Pré-Deploy

- [ ] Código testado localmente
- [ ] Todas as mudanças commitadas
- [ ] Push para GitHub realizado
- [ ] Variáveis de ambiente configuradas no Render
- [ ] GOOGLE_CREDENTIALS_BASE64 válido
- [ ] HYPERLIQUID_SUBACCOUNT correto (577166, não 106!)
- [ ] Dashboard funcional
- [ ] Backtest validado (+105%)
- [ ] Primeira operação planejada
- [ ] Google Sheets pronto para receber trades

---

**Última atualização:** 19/04/2026  
**Status:** Pronto para deploy em produção ✅
