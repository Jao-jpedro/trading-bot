# 📊 Atualização: Estratégia de Volume Ratio com Histerese

## Resumo das Alterações

Este documento descreve as mudanças implementadas para substituir a lógica de entrada baseada em RSI por uma estratégia avançada de **Volume Ratio (Buy/Sell)** combinada com **Histerese** e **Filtro de Tendência (EMAs 7 e 21)**.

---

## ✅ 1. Configuração Atualizada (TradingConfig)

### **Variáveis Removidas:**
- ~~`RSI_PERIOD`~~ - Período do RSI
- ~~`RSI_LONG_THRESHOLD`~~ - Threshold RSI para LONG
- ~~`RSI_SHORT_THRESHOLD`~~ - Threshold RSI para SHORT
- ~~`EMA_NEUTRAL_ZONE_PCT`~~ - Zona neutra da EMA 200
- ~~`MIN_VOLUME_RATIO`~~ - Validação de volume

### **Novas Variáveis Adicionadas:**
```python
# Indicadores - Volume Ratio + EMAs
EMA_FAST_PERIOD: int = 7         # EMA rápida (7 períodos)
EMA_SLOW_PERIOD: int = 21        # EMA lenta (21 períodos)

# Sinais de entrada - HISTERESE (Buy/Sell Volume Ratio)
RATIO_THRESHOLD_LONG: float = 1.10   # Ratio precisa subir a 1.10 para LONG
RATIO_THRESHOLD_SHORT: float = 0.90  # Ratio precisa cair a 0.90 para SHORT
```

---

## ✅ 2. Novo Motor de Cálculo de Volume Ratio

### **Função: `calculate_buy_sell_volumes(df: pd.DataFrame)`**

**Localização:** Linha ~1914  
**Objetivo:** Estimar a pressão de compra/venda de cada vela

**Lógica Implementada:**
1. **Avaliar variação de preço** (close vs close anterior)
2. **Atribuir volume proporcionalmente:**
   - Se preço subiu: maior % para "Compra" (60%-90%)
   - Se preço caiu: maior % para "Venda" (60%-90%)
   - A intensidade da variação define a proporção
3. **Calcular Ratio:** `buy_volume / sell_volume`
4. **Suavizar:** Média móvel de 3 períodos → `ratio_3`

**Campos adicionados ao DataFrame:**
- `buy_volume` - Volume estimado de compra
- `sell_volume` - Volume estimado de venda
- `ratio` - Ratio instantâneo (buy/sell)
- `ratio_3` - Ratio suavizado (média de 3 períodos)

---

## ✅ 3. Nova Lógica de Entrada (analyze_asset)

### **Função: `analyze_asset(symbol: str)`**

**Localização:** Linha ~1984  
**Estratégia Anterior:** RSI + EMA 200 + Volume  
**Nova Estratégia:** Volume Ratio + Histerese + EMAs 7/21

### **Fluxo de Análise:**

```
1. Buscar dados históricos (Binance via CCXT)
   ↓
2. Calcular Buy/Sell Volume Ratio para cada vela
   ↓
3. Obter ratio_3 atual e anterior
   ↓
4. Calcular EMA 7 e EMA 21
   ↓
5. Determinar Tendência:
   - EMA7 > EMA21 → ALTA (📈)
   - EMA7 < EMA21 → BAIXA (📉)
   - EMA7 = EMA21 → NEUTRA (➡️)
   ↓
6. Aplicar Histerese para Gatilhos:
   
   LONG: prev_ratio < 1.10 E curr_ratio >= 1.10 E ema_7 > ema_21
   SHORT: prev_ratio > 0.90 E curr_ratio <= 0.90 E ema_7 < ema_21
```

### **Campos Retornados (analysis):**

**Antes:**
- `rsi` - RSI atual
- `ema_200` - EMA 200
- `market_regime` - Regime de mercado
- `volume_ratio` - Volume atual/médio

**Agora:**
- `ratio_current` - Volume Ratio (buy/sell) atual
- `ratio_previous` - Volume Ratio anterior
- `ema_fast` - EMA 7
- `ema_slow` - EMA 21
- `trend` - Tendência ("ALTA", "BAIXA", "NEUTRA")
- `signal_reason` - Motivo do sinal ou bloqueio

---

## ✅ 4. Atualizações de Infraestrutura

### **4.1. Função `should_enter(analysis)`**

**Alterações:**
- Logs agora mostram **Volume Ratio** e **Tendência**
- Removido RSI e EMA 200

**Antes:**
```python
log(f"   RSI: {rsi:.1f}", "INFO")
log(f"   Regime: {market_regime}", "INFO")
log(f"   EMA 200: ${ema_200:.4f}", "INFO")
```

**Agora:**
```python
log(f"   📊 Volume Ratio: {ratio_current:.3f}", "INFO")
log(f"   📈 Tendência: {trend}", "INFO")
log(f"   EMA7: ${ema_fast:.4f} | EMA21: ${ema_slow:.4f}", "INFO")
```

---

### **4.2. Função `execute_entry(analysis)`**

**Alterações:**
- Extrair `ratio_current`, `ema_fast`, `ema_slow`, `trend` do analysis
- Calcular `ema_trend` baseado em EMA7 vs EMA21
- Usar `ratio_current` como `volume_ratio`

**Google Sheets & Discord:**
- Campo `rsi` agora contém o **Volume Ratio** (mantido por compatibilidade)
- Campo `market_regime` agora contém a **Tendência** (ALTA/BAIXA/NEUTRA)
- Logs e notificações mostram:
  - "Volume Ratio: X.XXX"
  - "Tendência: ALTA (EMA7=XX.XX vs EMA21=XX.XX)"

**Notificação Discord - Antes:**
```
**RSI:** 18.50
**Regime:** TENDÊNCIA ALTA
**EMA 200:** $195.25
```

**Notificação Discord - Agora:**
```
**Volume Ratio:** 1.125
**Tendência:** ALTA (EMA7=$197.45 vs EMA21=$193.80)
```

---

### **4.3. Função `record_buy(...)`**

**Alterações:**
- Parâmetro `rsi` agora recebe **Volume Ratio** (nome mantido por compatibilidade)
- Parâmetro `market_regime` agora recebe **Tendência**
- Logs atualizados:
  - ~~"RSI: XX.XX"~~ → "Volume Ratio: X.XXX"

---

## 📋 Regras Estritas Preservadas

✅ **Infraestrutura 100% Intacta:**
- ✅ `fetch_historical_data` - Continua usando Binance via CCXT
- ✅ `_http_post_json` - Rate limiting e Exponential Backoff preservados
- ✅ `get_current_price` - Cache de 5 minutos mantido
- ✅ `create_market_order` - Execução na Hyperliquid sem alterações
- ✅ `monitor_and_execute_exits` - Stop Loss (ATR), TP1 (15%), TP2 (40%) preservados
- ✅ `StateManager` - Reconstrução de estado mantida
- ✅ `GoogleSheetsLogger` - Logging completo preservado
- ✅ `DiscordNotifier` - Notificações preservadas
- ✅ Gestão de risco (alavancagem 5x, cooldown 48h) mantida

---

## 🎯 Comportamento Esperado

### **Exemplo de Entrada LONG:**

```
📊 SOL: Preço=$197.45
   📈 Tendência: ALTA | EMA7=$197.45 | EMA21=$193.80
   📊 Volume Ratio (suavizado): 1.125 (anterior: 1.085)
   🎯 Thresholds: LONG=1.10 | SHORT=0.90
   ✅ SINAL: LONG - Ratio cruzou 1.10 para cima E tendência de alta (EMA 7 > EMA 21)
```

### **Exemplo de Entrada SHORT:**

```
📊 XRP: Preço=$0.5420
   📉 Tendência: BAIXA | EMA7=$0.5410 | EMA21=$0.5450
   📊 Volume Ratio (suavizado): 0.875 (anterior: 0.915)
   🎯 Thresholds: LONG=1.10 | SHORT=0.90
   ✅ SINAL: SHORT - Ratio cruzou 0.90 para baixo E tendência de baixa (EMA 7 < EMA 21)
```

### **Exemplo de Bloqueio (Histerese):**

```
📊 SOL: Preço=$197.45
   📈 Tendência: NEUTRA | EMA7=$195.20 | EMA21=$195.25
   📊 Volume Ratio (suavizado): 1.125 (anterior: 1.085)
   🎯 Thresholds: LONG=1.10 | SHORT=0.90
   🚫 Ratio cruzou 1.10 MAS sem tendência de alta (bloqueado)
```

---

## 📈 Vantagens da Nova Estratégia

1. ⚡ **Mais Entradas:** Ratio 1.10/0.90 é menos extremo que RSI 20/80
2. 🎯 **Maior Precisão:** Histerese evita entradas em ruído
3. 📊 **Melhor Contexto:** EMAs 7/21 capturam tendência de curto prazo
4. 🔄 **Flexibilidade:** Thresholds ajustáveis (1.10/0.90 podem ser otimizados)
5. 🧠 **Lógica Robusta:** Análise de fluxo de volume > indicadores de momentum

---

## 🚀 Próximos Passos

1. **Testar localmente:** `python3 trading.py`
2. **Monitorar logs:** Verificar detecção de sinais
3. **Ajustar thresholds:** Se necessário, otimizar 1.10/0.90
4. **Backtesting:** Comparar performance vs RSI antigo
5. **Deploy:** Push para GitHub → Render.com

---

## 📝 Notas Técnicas

- **Compatibilidade:** Campo `rsi` nos logs/sheets agora contém Volume Ratio
- **Performance:** Cálculo de volume ratio é O(n) - negligível
- **Cache:** Dados históricos da Binance continuam cacheados por 5min
- **Rate Limiting:** 2s entre requisições, 2 retries, backoff [5s, 15s]

---

**Data de Implementação:** 2026-08-07  
**Versão:** 2.0.0 - Volume Ratio Strategy  
**Autor:** Trading Bot Team
