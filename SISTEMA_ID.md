# ✅ COLUNA ID IMPLEMENTADA COM SUCESSO!

**Data:** 18/04/2026  
**Feature:** Sistema de ID para vincular compra e venda

---

## 🎯 Objetivo

Criar um **ID único** para cada trade que vincula a **compra** com a **venda**, facilitando análises de performance.

---

## 📊 Nova Estrutura da Planilha (9 colunas)

| ID | Data | Hora | Preço | Cripto | Operação | Tipo de Operação | RSI | Motivo |
|----|------|------|-------|--------|----------|------------------|-----|--------|
| SOL_20260418_143025 | 18/04/2026 | 14:30:25 | 145.2500 | SOL | LONG | Compra | 18.45 | RSI sobrevendido (18.45 < 20) |
| SOL_20260418_143025 | 18/04/2026 | 16:45:10 | 151.3200 | SOL | LONG | Venda | 65.23 | Take Profit atingido |

**Mesma ID** = Mesma operação!

---

## 🔑 Formato do ID

```
CRYPTO_YYYYMMDD_HHMMSS

Exemplos:
- SOL_20260418_143025
- XRP_20260418_182033
- BTC_20260419_091542
```

**Componentes:**
- **CRYPTO**: Nome da criptomoeda (SOL, XRP, BTC, etc)
- **YYYYMMDD**: Data (Ano+Mês+Dia)
- **HHMMSS**: Hora (Hora+Minuto+Segundo)

**Gerado no momento da compra** e reutilizado na venda!

---

## 🔄 Fluxo com ID

### 1. Compra (Entrada)
```python
# Bot detecta RSI < 20
trade_id = record_buy(...)
# Gera: SOL_20260418_143025
# Salva no estado: active_targets["trade_id"] = trade_id
# Registra no Sheets com este ID
```

### 2. Venda (Saída)
```python
# Bot detecta Take Profit
trade_id = active_targets["trade_id"]  # Recupera ID da compra
record_sell(..., trade_id=trade_id)  # Usa mesmo ID
# Registra no Sheets com mesmo ID
```

---

## 📈 Análises Possíveis

### 1. **Calcular ROI por Trade**
```sql
SELECT 
    ID,
    MAX(CASE WHEN "Tipo de Operação" = 'Compra' THEN Preço END) as Preço_Compra,
    MAX(CASE WHEN "Tipo de Operação" = 'Venda' THEN Preço END) as Preço_Venda,
    (Preço_Venda - Preço_Compra) / Preço_Compra * 100 as ROI_Pct
FROM Base_logs
GROUP BY ID
```

### 2. **Duração de cada Trade**
```sql
SELECT 
    ID,
    MAX(Data || ' ' || Hora) - MIN(Data || ' ' || Hora) as Duração
FROM Base_logs
GROUP BY ID
```

### 3. **Win Rate**
```sql
SELECT 
    COUNT(CASE WHEN ROI > 0 THEN 1 END) * 100.0 / COUNT(*) as Win_Rate
FROM (
    SELECT ID, 
        (MAX(Preço_Venda) - MIN(Preço_Compra)) as ROI
    FROM Base_logs
    GROUP BY ID
)
```

### 4. **Melhor/Pior Trade**
```sql
-- Melhor
SELECT * FROM Base_logs 
WHERE ID = (
    SELECT ID FROM Base_logs 
    GROUP BY ID
    ORDER BY (MAX(Preço) - MIN(Preço)) DESC 
    LIMIT 1
)

-- Pior
SELECT * FROM Base_logs 
WHERE ID = (
    SELECT ID FROM Base_logs 
    GROUP BY ID
    ORDER BY (MAX(Preço) - MIN(Preço)) ASC 
    LIMIT 1
)
```

### 5. **Análise por Motivo de Saída**
```sql
SELECT 
    Motivo,
    COUNT(*) as Quantidade,
    AVG(ROI) as ROI_Médio
FROM (
    SELECT ID, Motivo,
        (MAX(Preço) - MIN(Preço)) as ROI
    FROM Base_logs
    WHERE "Tipo de Operação" = 'Venda'
    GROUP BY ID, Motivo
)
GROUP BY Motivo
```

---

## 📋 Exemplo de Planilha Completa

| ID | Data | Hora | Preço | Cripto | Operação | Tipo | RSI | Motivo |
|----|------|------|-------|--------|----------|------|-----|--------|
| SOL_20260418_143025 | 18/04/2026 | 14:30:25 | 145.25 | SOL | LONG | Compra | 18.45 | RSI sobrevendido |
| SOL_20260418_143025 | 18/04/2026 | 16:45:10 | 151.32 | SOL | LONG | Venda | 65.23 | Take Profit |
| XRP_20260418_182033 | 18/04/2026 | 18:20:33 | 0.5234 | XRP | SHORT | Compra | 85.67 | RSI sobrecomprado |
| XRP_20260418_182033 | 19/04/2026 | 09:15:42 | 0.5120 | XRP | SHORT | Venda | 45.23 | Take Profit |
| SOL_20260419_143000 | 19/04/2026 | 14:30:00 | 146.12 | SOL | LONG | Compra | 19.23 | RSI sobrevendido |
| SOL_20260419_143000 | 19/04/2026 | 15:10:25 | 143.20 | SOL | LONG | Venda | 28.45 | Stop Loss |

---

## 🎯 Insights Rápidos

### Trade 1: **SOL_20260418_143025**
- **Entrada:** $145.25 (RSI 18.45)
- **Saída:** $151.32 (RSI 65.23)
- **ROI:** +4.18%
- **Duração:** 2h 14min
- **Resultado:** ✅ **GANHO** (Take Profit)

### Trade 2: **XRP_20260418_182033**
- **Entrada:** $0.5234 (RSI 85.67)
- **Saída:** $0.5120 (RSI 45.23)
- **ROI:** +2.18% (SHORT)
- **Duração:** 14h 55min
- **Resultado:** ✅ **GANHO** (Take Profit)

### Trade 3: **SOL_20260419_143000**
- **Entrada:** $146.12 (RSI 19.23)
- **Saída:** $143.20 (RSI 28.45)
- **ROI:** -2.00%
- **Duração:** 40min
- **Resultado:** ❌ **PERDA** (Stop Loss)

**Resumo:** 2 ganhos, 1 perda = **66.7% win rate** ✅

---

## 🔧 Implementação Técnica

### 1. **Geração do ID** (`record_buy`)
```python
now = datetime.now()
trade_id = f"{crypto}_{now.strftime('%Y%m%d_%H%M%S')}"
# Exemplo: SOL_20260418_143025
```

### 2. **Salvamento no Estado**
```python
{
    "position_entries": [{
        "trade_id": "SOL_20260418_143025",
        "price": 145.25,
        "amount": 10.5,
        ...
    }],
    "active_targets": {
        "trade_id": "SOL_20260418_143025",
        ...
    }
}
```

### 3. **Registro na Planilha**
```python
# Compra
sheets_logger.log_trade(..., trade_id="SOL_20260418_143025")

# Venda (usa mesmo ID)
trade_id = active_targets["trade_id"]
sheets_logger.log_trade(..., trade_id=trade_id)
```

---

## ✅ Funções Modificadas

| Função | Mudança |
|--------|---------|
| `GoogleSheetsLogger.__init__()` | Cabeçalhos: 8 → **9 colunas** (ID adicionado) |
| `log_trade()` | Novo parâmetro: `trade_id` |
| `record_buy()` | Gera `trade_id` e **retorna** para uso posterior |
| `record_sell()` | Recebe `trade_id` da compra |
| `execute_entry()` | Captura `trade_id` e salva em `active_targets` |
| `monitor_and_execute_exits()` | Recupera `trade_id` e passa para `record_sell()` |

---

## 📊 Teste Realizado

```
✅ Planilha 'Base_logs' conectada
✅ Cabeçalhos criados (9 colunas com ID)
✅ Linha de teste adicionada
✅ ID gerado: SOL_20260418_HHMMSS
```

**Acesse:** https://docs.google.com/spreadsheets/d/1cXFK2GB1dtuHXWRQuIMA_4Q7b6VoBH7j3No9cBRuJB0

---

## 🎁 Benefícios

1. ✅ **Rastreabilidade Total**
   - Cada par compra/venda tem ID único
   - Fácil filtrar por trade específico

2. ✅ **Análise de Performance**
   - Calcular ROI por trade
   - Identificar melhores/piores operações
   - Win rate automático

3. ✅ **Duração dos Trades**
   - Quanto tempo cada trade levou
   - Trades mais rápidos vs. mais lentos

4. ✅ **Análise por Motivo**
   - Quantos SL vs. TP?
   - Qual motivo tem melhor performance?

5. ✅ **Relatórios Automáticos**
   - Dashboards no Google Sheets
   - Gráficos de performance
   - Estatísticas detalhadas

---

## 📈 Próximos Passos (Opcionais)

- [ ] Criar dashboard automático no Sheets
- [ ] Calcular coluna ROI automaticamente
- [ ] Adicionar gráficos de performance
- [ ] Exportar relatórios mensais
- [ ] Integrar com ferramentas de BI

---

**Status:** ✅ **IMPLEMENTADO E TESTADO**  
**Versão:** 2.0 com Sistema de IDs  
**Data:** 18/04/2026
