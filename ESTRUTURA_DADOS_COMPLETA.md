# 📊 Estrutura Completa de Dados - Trading Quantitativo

## 🎯 Objetivo

Sistema completo de coleta de dados para cada trade, permitindo análise quantitativa profunda e melhoria contínua da estratégia.

---

## 📋 Estrutura do Google Sheets (36 Colunas)

### 1️⃣ **IDENTIFICAÇÃO** (4 colunas)
| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| **ID** | Identificador único do trade | `SOL_20260419_143025` |
| **Data** | Data da operação | `19/04/2026` |
| **Hora** | Hora da operação | `14:30:25` |
| **Timestamp** | ISO timestamp completo | `2026-04-19T14:30:25` |
| **Cripto** | Moeda negociada | `SOL`, `XRP` |
| **Operação** | Direção | `LONG`, `SHORT` |
| **Tipo** | Entrada ou Saída | `Entrada`, `Saída` |

### 2️⃣ **CONTEXTO DE ENTRADA - Indicadores** (5 colunas)
| Coluna | Descrição | Uso Analítico |
|--------|-----------|---------------|
| **RSI** | Relative Strength Index | Identificar sobrecompra/sobrevenda (< 20 = forte sobrevenda) |
| **EMA_Trend** | Tendência EMA 200 | Classificar contexto: `Bullish`, `Bearish`, `Neutral` |
| **ATR** | Average True Range ($) | Medir volatilidade absoluta do momento |
| **ATR_Percentil** | Percentil do ATR (0-100) | Classificar volatilidade relativa (>80 = muito alta) |
| **Volume_Ratio** | Volume atual / Volume médio 20 | Confirmar força do movimento (>1.5 = forte) |

**📈 Análise Possível:**
- Identificar qual RSI gera melhores entradas (ex: < 15 vs < 25)
- Determinar se entradas em tendência bullish/bearish performam diferente
- Avaliar se alta volatilidade (ATR alto) gera mais lucro ou risco
- Verificar se volume alto confirma entradas de qualidade

### 3️⃣ **EXECUÇÃO - Preços e Posição** (5 colunas)
| Coluna | Descrição | Uso Analítico |
|--------|-----------|---------------|
| **Preço_Entrada** | Preço exato de entrada | Base para calcular P&L |
| **Slippage_%** | Diferença % entre esperado e real | Medir qualidade de execução |
| **Tamanho_Posição_USD** | Tamanho em dólares | Analisar gestão de capital |
| **Tamanho_Posição_Moedas** | Quantidade de moedas | Rastrear quantidade física |
| **Leverage** | Alavancagem usada | Correlacionar risco vs retorno |

**📈 Análise Possível:**
- Calcular slippage médio por moeda e horário
- Otimizar tamanho de posição (25% é ideal?)
- Avaliar impacto da alavancagem no P&L e drawdown

### 4️⃣ **GESTÃO DE RISCO - Stops e Targets** (7 colunas)
| Coluna | Descrição | Uso Analítico |
|--------|-----------|---------------|
| **Stop_Loss_Preço** | Preço do stop loss | Definir níveis de proteção |
| **Stop_Loss_%** | % de distância do stop | Comparar stop fixo vs ATR |
| **Take_Profit_1_Preço** | Preço do TP parcial (60%) | Saída parcial |
| **Take_Profit_1_%** | % do TP1 | Avaliar eficiência de TP parcial |
| **Take_Profit_2_Preço** | Preço do TP total | Saída completa |
| **Take_Profit_2_%** | % do TP2 | Medir ambição do target |
| **Risk_Reward_Ratio** | Ratio R:R (TP/SL) | Otimizar para > 1.5:1 |

**📈 Análise Possível:**
- Determinar R:R ideal (1.5:1, 2:1, 3:1?)
- Avaliar taxa de acerto em diferentes níveis de stop
- Comparar stops fixos (2%) vs ATR (1.5x volatilidade)
- Verificar se TP parcial melhora resultados

### 5️⃣ **RESULTADOS - Saída e P&L** (6 colunas)
| Coluna | Descrição | Uso Analítico |
|--------|-----------|---------------|
| **Preço_Saída** | Preço exato de saída | Calcular P&L real |
| **P&L_USD** | Lucro/Prejuízo em dólares | Resultado absoluto |
| **P&L_%** | Lucro/Prejuízo percentual | Resultado relativo |
| **Tempo_Trade_Min** | Duração do trade (minutos) | Otimizar timing |
| **MFE_%** | Maximum Favorable Excursion | Quanto poderia ter ganho (melhor ponto) |
| **MAE_%** | Maximum Adverse Excursion | Quanto chegou a perder (pior ponto) |

**📈 Análise Possível:**
- **Win Rate:** % de trades lucrativos
- **Expectativa:** (Win% × Win Avg) - (Loss% × Loss Avg)
- **Profit Factor:** Total ganhos / Total perdas
- **Drawdown:** Maior queda acumulada
- **MFE/MAE:** Avaliar se stops e TPs estão bem posicionados
  - Se MAE >> Stop Loss → Stop muito apertado
  - Se MFE >> Take Profit → TP muito conservador

### 6️⃣ **ANÁLISE - Classificação e Qualidade** (5 colunas)
| Coluna | Descrição | Valores Possíveis |
|--------|-----------|-------------------|
| **Mercado_Tendência** | Classificação da tendência | `Strong Uptrend`, `Uptrend`, `Range`, `Downtrend`, `Strong Downtrend` |
| **Mercado_Volatilidade** | Nível de volatilidade | `Muito Alta`, `Alta`, `Normal`, `Baixa` |
| **Qualidade_Entrada** | Score de qualidade | `Excelente`, `Boa`, `Regular`, `Ruim` |
| **Motivo** | Razão da operação | `RSI sobrevendido (18.5 < 20)`, `Stop Loss`, `Take Profit 1` |
| **Observações** | Notas adicionais | Eventos especiais, notícias, etc |

**📈 Análise Possível:**
- Identificar qual contexto gera mais lucro (uptrend vs range vs downtrend)
- Avaliar performance em diferentes níveis de volatilidade
- Correlacionar qualidade de entrada com resultado final
- Filtrar entradas: focar apenas em "Excelente" e "Boa"?

---

## 🔢 Métricas Calculadas (Dashboard)

### Métricas de Performance
```python
# Win Rate
win_rate = (trades_vencedores / total_trades) * 100

# Average Win / Average Loss
avg_win = soma_lucros / num_lucros
avg_loss = soma_perdas / num_perdas

# Expectativa (Expectation)
expectation = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

# Profit Factor
profit_factor = total_lucros / abs(total_perdas)

# Sharpe Ratio
sharpe = (retorno_medio - taxa_livre_risco) / desvio_padrao_retornos

# Maximum Drawdown
max_dd = max(pico_capital - capital_atual) / pico_capital * 100
```

### Métricas de Timing
```python
# Tempo médio em trade vencedor vs perdedor
avg_time_win = media(tempo_trades_vencedores)
avg_time_loss = media(tempo_trades_perdedores)

# Melhor horário para operar
profit_by_hour = group_by(hora).sum(pnl)
```

### Métricas de Risco
```python
# R:R Médio Realizado
realized_rr = avg_win / avg_loss

# Stop Loss Hit Rate
sl_hit_rate = (trades_stopped / total_trades) * 100

# Take Profit Hit Rate
tp_hit_rate = (trades_tp / total_trades) * 100
```

---

## 📊 Exemplos de Análises Avançadas

### 1. **Otimização de RSI**
```sql
SELECT 
    CASE 
        WHEN RSI < 15 THEN '< 15'
        WHEN RSI < 20 THEN '15-20'
        WHEN RSI < 25 THEN '20-25'
        ELSE '25+'
    END AS rsi_range,
    COUNT(*) as num_trades,
    AVG(P&L_%) as avg_return,
    SUM(CASE WHEN P&L_% > 0 THEN 1 ELSE 0 END) / COUNT(*) as win_rate
FROM trades
WHERE Tipo = 'Saída'
GROUP BY rsi_range
```

### 2. **Performance por Volatilidade**
```sql
SELECT 
    Mercado_Volatilidade,
    AVG(P&L_USD) as avg_profit,
    AVG(Tempo_Trade_Min) as avg_duration,
    MAX(MAE_%) as max_adverse,
    MAX(MFE_%) as max_favorable
FROM trades
WHERE Tipo = 'Saída'
GROUP BY Mercado_Volatilidade
```

### 3. **Eficiência de Stops**
```sql
SELECT 
    CASE 
        WHEN Stop_Loss_% < 1.5 THEN 'Tight (< 1.5%)'
        WHEN Stop_Loss_% < 2.5 THEN 'Normal (1.5-2.5%)'
        ELSE 'Wide (> 2.5%)'
    END AS stop_range,
    COUNT(*) as num_trades,
    SUM(CASE WHEN Motivo = 'Stop Loss' THEN 1 ELSE 0 END) / COUNT(*) as stop_hit_rate,
    AVG(P&L_%) as avg_return
FROM trades
WHERE Tipo = 'Saída'
GROUP BY stop_range
```

### 4. **Qualidade de Entrada vs Resultado**
```sql
SELECT 
    Qualidade_Entrada,
    COUNT(*) as num_trades,
    AVG(P&L_%) as avg_return,
    SUM(CASE WHEN P&L_% > 0 THEN 1 ELSE 0 END) / COUNT(*) as win_rate,
    AVG(Risk_Reward_Ratio) as avg_rr
FROM trades
WHERE Tipo = 'Saída'
GROUP BY Qualidade_Entrada
ORDER BY avg_return DESC
```

---

## 🔄 Como os Dados São Coletados

### **Na Entrada (execute_entry)**
```python
trade_data = {
    # Identificação
    'trade_id': f"{crypto}_{timestamp}",
    'timestamp': datetime.now(),
    'crypto': 'SOL',
    'operation': 'LONG',
    'trade_type': 'Entrada',
    
    # Contexto calculado automaticamente
    'rsi': 18.5,  # do análise técnica
    'ema_trend': 'Bullish',  # preço > EMA 200
    'atr': 2.35,  # calculado do histórico
    'atr_percentile': 65.0,  # ATR ranking
    'volume_ratio': 1.8,  # volume atual / médio
    
    # Execução
    'entry_price': 142.50,
    'position_size_usd': 500.00,
    'position_size_coins': 3.5088,
    'leverage': 1,
    
    # Gestão de Risco (calculado com ATR)
    'stop_loss_price': 138.97,  # entry - (atr * 1.5)
    'stop_loss_pct': 2.48,
    'tp1_price': 146.03,  # entry + (atr * 2.5 * 0.6)
    'tp1_pct': 2.48,
    'tp2_price': 148.38,  # entry + (atr * 2.5)
    'tp2_pct': 4.12,
    'risk_reward': 1.66,  # TP1 / SL
    
    # Análise
    'market_trend': 'Bullish',
    'market_volatility': 'Normal',
    'entry_quality': 'Excelente',  # RSI < 20 + volume alto
    'reason': 'RSI sobrevendido (18.5 < 20)',
    'notes': ''
}

sheets_logger.log_trade(trade_data)
```

### **Na Saída (record_sell)**
```python
trade_data = {
    # Mesmo trade_id da entrada
    'trade_id': entry_trade_id,
    'trade_type': 'Saída',
    
    # Resultados calculados
    'exit_price': 146.20,
    'pnl_usd': +12.98,
    'pnl_pct': +2.60,
    'time_in_trade_min': 145,
    'mfe_pct': +3.20,  # melhor ponto alcançado
    'mae_pct': -0.80,  # pior ponto alcançado
    
    'reason': 'Take Profit 1',
    'notes': 'Saída parcial (50% da posição)'
}

sheets_logger.log_trade(trade_data)
```

---

## 🎯 Algoritmo de Classificação de Qualidade

```python
def evaluate_entry_quality(rsi, atr_percentile, volume_ratio, operation):
    score = 0
    
    # RSI adequado (peso 3)
    if operation == "LONG":
        if rsi < 25: score += 3
        elif rsi < 30: score += 2
    else:  # SHORT
        if rsi > 75: score += 3
        elif rsi > 70: score += 2
    
    # Volatilidade favorável (peso 2)
    if 40 <= atr_percentile <= 70:  # Normal/Alta
        score += 2
    elif atr_percentile < 40:  # Baixa
        score += 1
    
    # Volume acima da média (peso 2)
    if volume_ratio > 1.5: score += 2
    elif volume_ratio > 1.0: score += 1
    
    # Classificar (máximo 7 pontos)
    if score >= 6: return "Excelente"
    elif score >= 4: return "Boa"
    elif score >= 2: return "Regular"
    else: return "Ruim"
```

---

## 🚀 Próximos Passos de Otimização

### Fase 1: Coleta (✅ IMPLEMENTADO)
- [x] Estrutura de 36 colunas
- [x] Cálculo automático de métricas
- [x] Classificação de qualidade
- [x] MFE/MAE tracking

### Fase 2: Análise (📅 Próximo)
- [ ] Dashboard Google Sheets com fórmulas
- [ ] Gráficos de performance por métrica
- [ ] Relatórios semanais/mensais automatizados
- [ ] Alertas de degradação de performance

### Fase 3: Otimização (🔮 Futuro)
- [ ] Backtesting com parâmetros otimizados
- [ ] Machine Learning para prever qualidade
- [ ] Auto-ajuste de parâmetros (RSI threshold, ATR multiplier)
- [ ] A/B testing de estratégias

---

## 📚 Referências

- **MFE/MAE Analysis:** Tomasini & Jaekle - "Trading Systems"
- **Expectancy Formula:** Van Tharp - "Trade Your Way to Financial Freedom"
- **Profit Factor:** Jack Schwager - "Market Wizards"
- **Sharpe Ratio:** William Sharpe - "Mutual Fund Performance"

---

**✨ Com esta estrutura, você tem:**
- 📊 Dados completos de cada trade
- 🔍 Capacidade de análise profunda
- 🎯 Métricas quantitativas objetivas
- 🚀 Base para otimização contínua
- 📈 Evolução data-driven da estratégia

**Resultado esperado:** Estratégia cada vez mais refinada através de análise quantitativa rigorosa! 🎯
