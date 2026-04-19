"""
Backtest Simples - Debug da nova estratégia
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from strategy_engine import StrategyEngine

def fetch_data(symbol: str = 'SOL/USDC:USDC', days: int = 30) -> pd.DataFrame:
    """Baixar dados históricos"""
    print(f"📊 Baixando {days} dias de dados...")
    
    exchange = ccxt.hyperliquid({'enableRateLimit': True})
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    all_data = []
    current_time = start_time
    
    while current_time < end_time:
        try:
            since = int(current_time.timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=1000)
            
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            last_timestamp = ohlcv[-1][0]
            current_time = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(hours=1)
            
        except Exception as e:
            print(f"Erro: {e}")
            break
    
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    print(f"✅ {len(df)} barras baixadas")
    return df


# Baixar dados
data = fetch_data('SOL/USDC:USDC', days=30)

# Criar estratégia
strategy = StrategyEngine(
    ema_period=50,  # Mais curta ainda
    rsi_period=14,
    atr_period=14,
    rsi_oversold=40,  # Menos extremo
    rsi_overbought=60,
    min_volatility_percentile=10,  # Muito permissivo
    max_volatility_percentile=90
)

print("\n🔍 Testando geração de sinais...\n")

signals_found = 0
for i in range(100, len(data), 50):  # A cada 50 barras
    historical_data = data.iloc[i-100:i+1].copy()
    
    try:
        signal = strategy.generate_signal(historical_data)
        
        if signal and signal.signal_type != 'NONE':
            signals_found += 1
            print(f"✅ Sinal encontrado na barra {i}:")
            print(f"   Tipo: {signal.signal_type}")
            print(f"   Confiança: {signal.confidence:.1f}%")
            print(f"   Razão: {signal.reason}")
            print(f"   Position Size: {signal.position_size_pct:.1f}%")
            if signal.levels:
                print(f"   Entry: ${signal.levels.entry_price:.2f}")
                print(f"   SL: ${signal.levels.stop_loss:.2f}")
                print(f"   TP1: ${signal.levels.take_profit_1:.2f}")
                print(f"   TP2: ${signal.levels.take_profit_2:.2f}")
            print()
    except Exception as e:
        print(f"❌ Erro ao gerar sinal na barra {i}: {e}")
        import traceback
        traceback.print_exc()
        break

print(f"\n📊 Total de sinais encontrados: {signals_found}/{int(len(data)/50)}")

if signals_found == 0:
    print("\n⚠️ NENHUM SINAL ENCONTRADO. Verificando condições de mercado...")
    
    # Pegar última janela
    recent_data = data.tail(200).copy()
    
    # Calcular indicadores manualmente
    recent_data['ema50'] = recent_data['close'].ewm(span=50, adjust=False).mean()
    recent_data['rsi'] = recent_data['close'].diff().apply(lambda x: max(x, 0)).rolling(14).mean() / \
                         recent_data['close'].diff().abs().rolling(14).mean() * 100
    
    # Calcular ATR
    high_low = recent_data['high'] - recent_data['low']
    high_close = abs(recent_data['high'] - recent_data['close'].shift())
    low_close = abs(recent_data['low'] - recent_data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    recent_data['atr'] = tr.rolling(14).mean()
    
    last = recent_data.iloc[-1]
    
    print(f"\n📈 Condições atuais (última barra):")
    print(f"   Preço: ${last['close']:.2f}")
    print(f"   EMA50: ${last['ema50']:.2f}")
    print(f"   RSI: {last['rsi']:.1f}")
    print(f"   ATR: ${last['atr']:.2f}")
    print(f"   Tendência: {'ALTA' if last['close'] > last['ema50'] else 'BAIXA'}")
    
    print(f"\n🎯 Condições para LONG:")
    print(f"   RSI < 40: {last['rsi'] < 40} (atual: {last['rsi']:.1f})")
    print(f"   Preço > EMA50: {last['close'] > last['ema50']}")
    
    print(f"\n🎯 Condições para SHORT:")
    print(f"   RSI > 60: {last['rsi'] > 60} (atual: {last['rsi']:.1f})")
    print(f"   Preço < EMA50: {last['close'] < last['ema50']}")
