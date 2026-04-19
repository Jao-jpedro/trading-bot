"""
Debug: testar strategy_engine diretamente
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from strategy_engine import StrategyEngine, calculate_ema, calculate_rsi, calculate_atr

# Baixar dados
print("📊 Baixando dados...")
exchange = ccxt.hyperliquid({'enableRateLimit': True})
ohlcv = exchange.fetch_ohlcv('SOL/USDC:USDC', timeframe='1h', limit=500)
data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')

print(f"✅ {len(data)} barras baixadas\n")

# Criar estratégia com parâmetros permissivos
strategy = StrategyEngine(
    ema_period=50,
    rsi_period=14,
    atr_period=14,
    rsi_oversold=40,  # Mais permissivo
    rsi_overbought=60,
    min_volatility_percentile=10,
    max_volatility_percentile=90
)

print("🔧 Parâmetros da estratégia:")
print(f"   EMA Period: {strategy.ema_period}")
print(f"   RSI Oversold: {strategy.rsi_oversold}")
print(f"   RSI Overbought: {strategy.rsi_overbought}")
print(f"   Vol Min/Max: {strategy.min_volatility_percentile}/{strategy.max_volatility_percentile}\n")

# Analisar mercado atual
print("📈 Analisando mercado atual...")
market = strategy.analyze_market(data)

print(f"   Preço: ${market.price:.2f}")
print(f"   EMA{strategy.ema_period}: ${market.ema200:.2f}")
print(f"   RSI: {market.rsi:.2f}")
print(f"   ATR: ${market.atr:.4f}")
print(f"   Vol Percentile: {market.volatility_percentile:.1f}%\n")

print("✅ Condições de mercado:")
print(f"   In Uptrend: {market.in_uptrend} (preço > EMA)")
print(f"   In Downtrend: {market.in_downtrend} (preço < EMA)")
print(f"   Is Oversold: {market.is_oversold} (RSI < {market.rsi_oversold_threshold})")
print(f"   Is Overbought: {market.is_overbought} (RSI > {market.rsi_overbought_threshold})")
print(f"   Good Volatility: {market.has_good_volatility} ({market.min_vol_percentile}-{market.max_vol_percentile}%)\n")

# Tentar gerar sinal
print("🎯 Tentando gerar sinal...")
signal = strategy.generate_signal(data)

print(f"\n📊 RESULTADO:")
print(f"   Signal Type: {signal.signal_type}")
print(f"   Confidence: {signal.confidence:.1f}%")
print(f"   Reason: {signal.reason}")

if signal.signal_type != 'NONE':
    print(f"   Position Size: {signal.position_size_pct:.1f}%")
    if signal.levels:
        print(f"   Entry: ${signal.levels.entry_price:.2f}")
        print(f"   SL: ${signal.levels.stop_loss:.2f}")
        print(f"   TP1: ${signal.levels.take_profit_1:.2f}")
        print(f"   TP2: ${signal.levels.take_profit_2:.2f}")
else:
    print("\n❌ Nenhum sinal gerado!")
    print("\n🔍 Para gerar LONG, precisa:")
    print(f"   ✓ Preço > EMA50: {market.in_uptrend}")
    print(f"   ✓ RSI < {strategy.rsi_oversold}: {market.is_oversold}")
    print(f"   ✓ Vol {strategy.min_volatility_percentile}-{strategy.max_volatility_percentile}%: {market.has_good_volatility}")
    
    print("\n🔍 Para gerar SHORT, precisa:")
    print(f"   ✓ Preço < EMA50: {market.in_downtrend}")
    print(f"   ✓ RSI > {strategy.rsi_overbought}: {market.is_overbought}")
    print(f"   ✓ Vol {strategy.min_volatility_percentile}-{strategy.max_volatility_percentile}%: {market.has_good_volatility}")

# Testar em várias barras históricas
print("\n\n🔍 Testando últimas 100 barras...")
signals_count = 0

for i in range(len(data)-100, len(data)):
    test_data = data.iloc[:i+1]
    test_signal = strategy.generate_signal(test_data)
    
    if test_signal.signal_type != 'NONE':
        signals_count += 1
        print(f"\n✅ Sinal {test_signal.signal_type} na barra {i}:")
        print(f"   Confiança: {test_signal.confidence:.1f}%")
        print(f"   Razão: {test_signal.reason}")

print(f"\n📊 Total de sinais nas últimas 100 barras: {signals_count}")
