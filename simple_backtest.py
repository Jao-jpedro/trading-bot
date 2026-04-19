"""
Backtest Rápido - Estratégia Simples RSI + ATR
Compara: RSI fixo (2%/4%) vs RSI + ATR dinâmico + Saídas Parciais
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from simple_strategy import SimpleStrategy
import json

def fetch_data(symbol='SOL/USDC:USDC', days=180):
    """Baixar dados"""
    print(f"📊 Baixando {days} dias de {symbol}...")
    
    exchange = ccxt.hyperliquid({'enableRateLimit': True})
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    all_data = []
    current_time = start_time
    
    while current_time < end_time:
        since = int(current_time.timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=1000)
        
        if not ohlcv:
            break
        
        all_data.extend(ohlcv)
        current_time = datetime.fromtimestamp(ohlcv[-1][0] / 1000) + timedelta(hours=1)
    
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    print(f"✅ {len(df)} barras\n")
    return df

def run_backtest(data, strategy, use_partial_exits=False, name="Strategy"):
    """Backtest com ou sem saídas parciais"""
    
    capital = 1000
    leverage = 5
    trades = []
    position = None
    
    print(f"🔄 Rodando {name}...")
    
    for i in range(100, len(data)):
        current_bar = data.iloc[i]
        price = current_bar['close']
        
        # Gerenciar posição
        if position:
            if position['side'] == 'LONG':
                # Check SL
                if price <= position['sl']:
                    pnl = (price - position['entry']) * position['size']
                    trades.append({'pnl': pnl, 'reason': 'SL'})
                    capital += pnl
                    position = None
                # Check TP1
                elif not position.get('tp1_hit') and price >= position['tp1']:
                    if use_partial_exits:
                        # Saída parcial 50%
                        partial_size = position['size'] * 0.5
                        pnl = (price - position['entry']) * partial_size
                        trades.append({'pnl': pnl, 'reason': 'TP1 (50%)'})
                        capital += pnl
                        position['size'] *= 0.5
                        position['sl'] = position['entry']  # Break-even
                        position['tp1_hit'] = True
                    else:
                        # Fecha tudo
                        pnl = (price - position['entry']) * position['size']
                        trades.append({'pnl': pnl, 'reason': 'TP'})
                        capital += pnl
                        position = None
                # Check TP2
                elif position.get('tp1_hit') and price >= position['tp2']:
                    pnl = (price - position['entry']) * position['size']
                    trades.append({'pnl': pnl, 'reason': 'TP2 (50%)'})
                    capital += pnl
                    position = None
            
            else:  # SHORT
                if price >= position['sl']:
                    pnl = (position['entry'] - price) * position['size']
                    trades.append({'pnl': pnl, 'reason': 'SL'})
                    capital += pnl
                    position = None
                elif not position.get('tp1_hit') and price <= position['tp1']:
                    if use_partial_exits:
                        partial_size = position['size'] * 0.5
                        pnl = (position['entry'] - price) * partial_size
                        trades.append({'pnl': pnl, 'reason': 'TP1 (50%)'})
                        capital += pnl
                        position['size'] *= 0.5
                        position['sl'] = position['entry']
                        position['tp1_hit'] = True
                    else:
                        pnl = (position['entry'] - price) * position['size']
                        trades.append({'pnl': pnl, 'reason': 'TP'})
                        capital += pnl
                        position = None
                elif position.get('tp1_hit') and price <= position['tp2']:
                    pnl = (position['entry'] - price) * position['size']
                    trades.append({'pnl': pnl, 'reason': 'TP2 (50%)'})
                    capital += pnl
                    position = None
        
        # Buscar novos sinais
        if not position:
            historical = data.iloc[max(0, i-100):i+1]
            signal = strategy.generate_signal(historical)
            
            if signal.signal_type in ['LONG', 'SHORT']:
                position_value = capital * 0.25 * leverage
                size = position_value / price
                
                position = {
                    'entry': signal.entry_price,
                    'side': signal.signal_type,
                    'size': size,
                    'sl': signal.stop_loss,
                    'tp1': signal.take_profit_1,
                    'tp2': signal.take_profit_2,
                    'tp1_hit': False
                }
    
    # Fechar posição aberta
    if position:
        price = data.iloc[-1]['close']
        if position['side'] == 'LONG':
            pnl = (price - position['entry']) * position['size']
        else:
            pnl = (position['entry'] - price) * position['size']
        trades.append({'pnl': pnl, 'reason': 'END'})
        capital += pnl
    
    # Métricas
    if trades:
        trades_df = pd.DataFrame(trades)
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]
        
        return {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
            'total_pnl': trades_df['pnl'].sum(),
            'total_return': ((capital - 1000) / 1000) * 100,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0,
            'final_capital': capital
        }
    
    return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0, 'total_return': 0, 
            'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0, 'final_capital': 1000,
            'winning_trades': 0, 'losing_trades': 0}

# Download data
data = fetch_data('SOL/USDC:USDC', days=180)

# Estratégia 1: RSI puro (35/65) sem saídas parciais
print("="*80)
strategy1 = SimpleStrategy(
    rsi_oversold=35,
    rsi_overbought=65,
    atr_sl_mult=1.5,
    atr_tp1_mult=2.5,  # TP único
    atr_tp2_mult=2.5
)
results1 = run_backtest(data.copy(), strategy1, use_partial_exits=False, name="RSI + ATR (sem parciais)")

# Estratégia 2: RSI puro (35/65) COM saídas parciais
print("="*80)
strategy2 = SimpleStrategy(
    rsi_oversold=35,
    rsi_overbought=65,
    atr_sl_mult=1.5,
    atr_tp1_mult=2.0,  # TP1
    atr_tp2_mult=4.0   # TP2
)
results2 = run_backtest(data.copy(), strategy2, use_partial_exits=True, name="RSI + ATR (COM parciais 50/50)")

# Comparar
print("\n" + "="*80)
print("📊 COMPARAÇÃO DE RESULTADOS")
print("="*80)

metrics = [
    ('Total Trades', 'total_trades', ''),
    ('Winning Trades', 'winning_trades', ''),
    ('Win Rate', 'win_rate', '%'),
    ('Profit Factor', 'profit_factor', 'x'),
    ('Retorno Total', 'total_return', '%'),
    ('PnL Total', 'total_pnl', '$'),
    ('Avg Win', 'avg_win', '$'),
    ('Avg Loss', 'avg_loss', '$'),
]

print(f"\n{'Métrica':<20} {'Sem Parciais':<18} {'Com Parciais':<18} {'Diferença'}")
print("-"*80)

for label, key, unit in metrics:
    val1 = results1.get(key, 0)
    val2 = results2.get(key, 0)
    
    if key in ['total_trades', 'winning_trades', 'losing_trades']:
        str1 = f"{int(val1)}{unit}"
        str2 = f"{int(val2)}{unit}"
    else:
        str1 = f"{val1:.2f}{unit}"
        str2 = f"{val2:.2f}{unit}"
    
    if val1 != 0:
        diff_pct = ((val2 - val1) / abs(val1)) * 100
        if diff_pct > 0:
            diff_str = f"🟢 +{diff_pct:.1f}%"
        elif diff_pct < 0:
            diff_str = f"🔴 {diff_pct:.1f}%"
        else:
            diff_str = "⚪ 0%"
    else:
        diff_str = "-"
    
    print(f"{label:<20} {str1:<18} {str2:<18} {diff_str}")

print("="*80)

if results2['total_return'] > results1['total_return']:
    diff = results2['total_return'] - results1['total_return']
    print(f"\n✅ Saídas parciais SUPERIORES: +{diff:.2f}% de retorno extra")
else:
    diff = results1['total_return'] - results2['total_return']
    print(f"\n⚠️ Saídas únicas SUPERIORES: +{diff:.2f}% de retorno extra")

print(f"\n💰 Capital Inicial: $1000.00")
print(f"💰 Capital Final (Sem Parciais): ${results1['final_capital']:.2f}")
print(f"💰 Capital Final (Com Parciais): ${results2['final_capital']:.2f}")

# Salvar
results = {
    'date': datetime.now().isoformat(),
    'period': f"{data['timestamp'].min()} to {data['timestamp'].max()}",
    'without_partial_exits': results1,
    'with_partial_exits': results2
}

with open('simple_backtest_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print("\n💾 Resultados salvos em: simple_backtest_results.json")
print("✅ BACKTEST CONCLUÍDO!\n")
