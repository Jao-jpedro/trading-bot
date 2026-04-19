"""
Backtest da Estratégia Otimizada
Compara performance: Estratégia Antiga (RSI puro) vs Nova (EMA+RSI+ATR)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from strategy_engine import StrategyEngine, PositionManager
from typing import Dict, List, Tuple
import json

class Backtest:
    def __init__(self, initial_capital: float = 1000, leverage: int = 5):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.capital = initial_capital
        self.equity_curve = []
        self.trades = []
        self.positions = []
        
    def run_old_strategy(self, data: pd.DataFrame) -> Dict:
        """
        Estratégia antiga: RSI puro com SL/TP fixos
        """
        print("🔄 Rodando backtest da ESTRATÉGIA ANTIGA...")
        
        self.capital = self.initial_capital
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
        # Calcular RSI
        data['rsi'] = self._calculate_rsi(data['close'], period=14)
        
        position = None
        
        for i in range(100, len(data)):
            current_bar = data.iloc[i]
            current_price = current_bar['close']
            rsi = current_bar['rsi']
            
            # Registrar equity
            if position:
                unrealized_pnl = self._calculate_pnl(
                    position['entry_price'],
                    current_price,
                    position['size'],
                    position['side']
                )
                current_equity = self.capital + unrealized_pnl
            else:
                current_equity = self.capital
            
            self.equity_curve.append({
                'timestamp': current_bar['timestamp'],
                'equity': current_equity
            })
            
            # Gerenciar posição aberta
            if position:
                pnl_pct = self._calculate_pnl_pct(
                    position['entry_price'],
                    current_price,
                    position['side']
                )
                
                # Check SL/TP fixos
                if position['side'] == 'LONG':
                    if current_price <= position['stop_loss']:
                        # Stop Loss hit
                        self._close_position(position, current_price, current_bar['timestamp'], 'SL')
                        position = None
                    elif current_price >= position['take_profit']:
                        # Take Profit hit
                        self._close_position(position, current_price, current_bar['timestamp'], 'TP')
                        position = None
                else:  # SHORT
                    if current_price >= position['stop_loss']:
                        self._close_position(position, current_price, current_bar['timestamp'], 'SL')
                        position = None
                    elif current_price <= position['take_profit']:
                        self._close_position(position, current_price, current_bar['timestamp'], 'TP')
                        position = None
            
            # Buscar novas entradas (se não tiver posição)
            if not position and i < len(data) - 1:
                signal = None
                
                if rsi < 20:
                    signal = 'LONG'
                elif rsi > 80:
                    signal = 'SHORT'
                
                if signal:
                    # Calcular SL/TP fixos (2% e 4%)
                    if signal == 'LONG':
                        stop_loss = current_price * 0.98  # -2%
                        take_profit = current_price * 1.04  # +4%
                    else:
                        stop_loss = current_price * 1.02
                        take_profit = current_price * 0.96
                    
                    # Position size: 30% do capital
                    position_size = (self.capital * 0.30) * self.leverage / current_price
                    
                    position = {
                        'entry_price': current_price,
                        'entry_time': current_bar['timestamp'],
                        'side': signal,
                        'size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'capital_used': self.capital * 0.30
                    }
        
        # Fechar posição aberta no final
        if position:
            self._close_position(position, data.iloc[-1]['close'], data.iloc[-1]['timestamp'], 'END')
        
        return self._calculate_metrics()
    
    def run_new_strategy(self, data: pd.DataFrame) -> Dict:
        """
        Estratégia nova: EMA200 + RSI + ATR com saídas parciais
        """
        print("🔄 Rodando backtest da ESTRATÉGIA NOVA...")
        
        self.capital = self.initial_capital
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
        # Inicializar estratégia com parâmetros mais permissivos
        strategy = StrategyEngine(
            ema_period=50,  # EMA mais curta = mais sinais
            rsi_period=14,
            atr_period=14,
            rsi_oversold=35,  # Valores menos extremos
            rsi_overbought=65,
            atr_sl_multiplier=1.5,
            atr_tp1_multiplier=2.0,
            atr_tp2_multiplier=4.0,
            min_volatility_percentile=10,  # Muito permissivo
            max_volatility_percentile=90
        )
        
        # Calcular indicadores
        data['ema50'] = data['close'].ewm(span=50, adjust=False).mean()
        data['rsi'] = self._calculate_rsi(data['close'], period=14)
        data['atr'] = self._calculate_atr(data, period=14)
        
        position = None
        signals_found = 0
        signals_with_confidence = 0
        
        for i in range(50, len(data)):
            current_bar = data.iloc[i]
            current_price = current_bar['close']
            
            # Registrar equity
            if position:
                unrealized_pnl = self._calculate_pnl(
                    position['entry_price'],
                    current_price,
                    position['size'],
                    position['side']
                )
                current_equity = self.capital + unrealized_pnl
            else:
                current_equity = self.capital
            
            self.equity_curve.append({
                'timestamp': current_bar['timestamp'],
                'equity': current_equity
            })
            
            # Gerenciar posição aberta (lógica simplificada de saídas parciais)
            if position:
                should_exit = False
                exit_pct = 100
                exit_reason = None
                
                if position['side'] == 'LONG':
                    # LONG: SL abaixo, TPs acima
                    if current_price <= position['current_sl']:
                        should_exit = True
                        exit_pct = 100
                        exit_reason = 'SL'
                    elif not position.get('tp1_hit') and current_price >= position['tp1']:
                        should_exit = True
                        exit_pct = 50
                        exit_reason = 'TP1'
                    elif position.get('tp1_hit') and current_price >= position['tp2']:
                        should_exit = True
                        exit_pct = 100  # Fecha 50% restante (mas position['size'] já é 50%)
                        exit_reason = 'TP2'
                else:  # SHORT
                    if current_price >= position['current_sl']:
                        should_exit = True
                        exit_pct = 100
                        exit_reason = 'SL'
                    elif not position.get('tp1_hit') and current_price <= position['tp1']:
                        should_exit = True
                        exit_pct = 50
                        exit_reason = 'TP1'
                    elif position.get('tp1_hit') and current_price <= position['tp2']:
                        should_exit = True
                        exit_pct = 100
                        exit_reason = 'TP2'
                
                if should_exit:
                    if exit_pct == 100 and not position.get('tp1_hit'):
                        # Fechar tudo (SL ou sem ter atingido TP1)
                        self._close_position(
                            position, 
                            current_price, 
                            current_bar['timestamp'], 
                            exit_reason
                        )
                        position = None
                    elif exit_pct == 50:
                        # Saída parcial (TP1)
                        partial_size = position['size'] * 0.5
                        remaining_size = position['size'] * 0.5
                        
                        # Registrar trade parcial
                        pnl = self._calculate_pnl(
                            position['entry_price'],
                            current_price,
                            partial_size,
                            position['side']
                        )
                        
                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current_bar['timestamp'],
                            'side': position['side'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_price,
                            'size': partial_size,
                            'pnl': pnl,
                            'pnl_pct': (pnl / (position['capital_used'] * 0.5)) * 100,
                            'exit_reason': f"{exit_reason} (50%)"
                        })
                        
                        self.capital += pnl
                        
                        # Atualizar posição
                        position['size'] = remaining_size
                        position['capital_used'] = position['capital_used'] * 0.5
                        position['current_sl'] = position['entry_price']  # Move para break-even
                        position['tp1_hit'] = True
                    else:
                        # Fechar resto (TP2 após TP1)
                        self._close_position(
                            position, 
                            current_price, 
                            current_bar['timestamp'], 
                            exit_reason
                        )
                        position = None
            
            # Buscar novas entradas (se não tiver posição)
            if not position and i < len(data) - 1:
                # Preparar dados históricos
                historical_data = data.iloc[max(0, i-100):i+1].copy()
                
                # Gerar sinal
                signal = strategy.generate_signal(historical_data)
                
                # Contar sinais
                if signal and signal.signal_type != 'NONE':
                    signals_found += 1
                    if signal.confidence >= 50:
                        signals_with_confidence += 1
                
                # Debug: logar sinais encontrados
                if signal and signal.signal_type != 'NONE':
                    if i % 200 == 0 or signals_with_confidence < 5:  # Primeiros sinais
                        print(f"  Sinal {signal.signal_type} na barra {i}, confiança: {signal.confidence:.1f}%")
                
                # Aceitar sinais com confiança >= 50% (ao invés de 60% padrão)
                if signal and signal.signal_type in ['LONG', 'SHORT'] and signal.confidence >= 50:
                    # Calcular níveis de entrada
                    levels = strategy.calculate_position_levels(
                        entry_price=current_price,
                        signal_type=signal.signal_type,
                        atr=current_bar['atr']
                    )
                    
                    # Position size baseado em confiança
                    base_size = 20 + (signal.confidence / 100 * 10)  # 20-30%
                    position_size = (self.capital * (base_size/100)) * self.leverage / current_price
                    
                    position = {
                        'id': f"trade_{i}",
                        'entry_price': current_price,
                        'entry_time': current_bar['timestamp'],
                        'side': signal.signal_type,
                        'size': position_size,
                        'stop_loss': levels.stop_loss,
                        'current_sl': levels.stop_loss,
                        'tp1': levels.take_profit_1,
                        'tp2': levels.take_profit_2,
                        'capital_used': self.capital * (base_size/100),
                        'confidence': signal.confidence,
                        'tp1_hit': False
                    }
        
        # Fechar posição aberta no final
        if position:
            self._close_position(position, data.iloc[-1]['close'], data.iloc[-1]['timestamp'], 'END')
        
        print(f"\n  📊 Sinais gerados: {signals_found}")
        print(f"  ✅ Sinais com confiança >= 50%: {signals_with_confidence}")
        
        return self._calculate_metrics()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcular ATR"""
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def _calculate_pnl(self, entry_price: float, exit_price: float, size: float, side: str) -> float:
        """Calcular PnL em USD"""
        if side == 'LONG':
            pnl = (exit_price - entry_price) * size
        else:
            pnl = (entry_price - exit_price) * size
        return pnl
    
    def _calculate_pnl_pct(self, entry_price: float, current_price: float, side: str) -> float:
        """Calcular PnL em %"""
        if side == 'LONG':
            return ((current_price - entry_price) / entry_price) * 100
        else:
            return ((entry_price - current_price) / entry_price) * 100
    
    def _close_position(self, position: Dict, exit_price: float, exit_time, reason: str):
        """Fechar posição e registrar trade"""
        pnl = self._calculate_pnl(
            position['entry_price'],
            exit_price,
            position['size'],
            position['side']
        )
        
        self.trades.append({
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'pnl_pct': (pnl / position['capital_used']) * 100,
            'exit_reason': reason
        })
        
        self.capital += pnl
    
    def _calculate_metrics(self) -> Dict:
        """Calcular métricas de performance"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'total_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        # Separar wins e losses
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]
        
        # Métricas básicas
        total_trades = len(trades_df)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        
        total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
        total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')
        
        total_pnl = trades_df['pnl'].sum()
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        avg_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Max Drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # Sharpe Ratio (simplified)
        returns = trades_df['pnl_pct']
        sharpe_ratio = (returns.mean() / returns.std()) if returns.std() > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_rr': avg_rr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': self.capital
        }


def fetch_historical_data(symbol: str = 'SOL/USDC:USDC', days: int = 90) -> pd.DataFrame:
    """
    Buscar dados históricos da Hyperliquid
    """
    print(f"📊 Baixando dados históricos de {symbol} ({days} dias)...")
    
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    # Calcular timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Buscar dados (1h timeframe)
    all_data = []
    current_time = start_time
    
    while current_time < end_time:
        try:
            since = int(current_time.timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=1000)
            
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            
            # Próxima janela
            last_timestamp = ohlcv[-1][0]
            current_time = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(hours=1)
            
            print(f"  Baixados até: {current_time.strftime('%Y-%m-%d %H:%M')}")
            
        except Exception as e:
            print(f"  ⚠️ Erro ao baixar dados: {e}")
            break
    
    # Converter para DataFrame
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Remover duplicatas
    df = df.drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    print(f"✅ {len(df)} barras de 1h baixadas ({df['timestamp'].min()} até {df['timestamp'].max()})")
    
    return df


def print_comparison(old_metrics: Dict, new_metrics: Dict):
    """
    Imprimir comparação visual entre estratégias
    """
    print("\n" + "="*80)
    print("📊 COMPARAÇÃO DE PERFORMANCE: ANTIGA vs NOVA")
    print("="*80)
    
    metrics = [
        ('Total de Trades', 'total_trades', '', False),
        ('Win Rate', 'win_rate', '%', False),
        ('Profit Factor', 'profit_factor', 'x', False),
        ('Retorno Total', 'total_return', '%', False),
        ('PnL Total', 'total_pnl', '$', False),
        ('Avg Win', 'avg_win', '$', False),
        ('Avg Loss', 'avg_loss', '$', True),
        ('R:R Médio', 'avg_rr', ':1', False),
        ('Max Drawdown', 'max_drawdown', '%', True),
        ('Sharpe Ratio', 'sharpe_ratio', '', False),
    ]
    
    print(f"\n{'Métrica':<20} {'Antiga':<15} {'Nova':<15} {'Melhoria':<15}")
    print("-"*80)
    
    for label, key, unit, inverse in metrics:
        old_val = old_metrics.get(key, 0)
        new_val = new_metrics.get(key, 0)
        
        # Calcular melhoria
        if old_val != 0:
            if inverse:
                improvement = ((old_val - new_val) / abs(old_val)) * 100
            else:
                improvement = ((new_val - old_val) / abs(old_val)) * 100
        else:
            improvement = 0
        
        # Formatar valores
        if 'pnl' in key.lower() or 'win' in key.lower() or 'loss' in key.lower():
            old_str = f"{old_val:.2f}{unit}"
            new_str = f"{new_val:.2f}{unit}"
        elif key == 'total_trades' or key == 'winning_trades' or key == 'losing_trades':
            old_str = f"{int(old_val)}{unit}"
            new_str = f"{int(new_val)}{unit}"
        else:
            old_str = f"{old_val:.2f}{unit}"
            new_str = f"{new_val:.2f}{unit}"
        
        # Emoji de melhoria
        if improvement > 5:
            emoji = "🟢"
            improvement_str = f"+{improvement:.1f}%"
        elif improvement < -5:
            emoji = "🔴"
            improvement_str = f"{improvement:.1f}%"
        else:
            emoji = "⚪"
            improvement_str = f"{improvement:.1f}%"
        
        print(f"{label:<20} {old_str:<15} {new_str:<15} {emoji} {improvement_str}")
    
    print("="*80)
    
    # Resumo final
    print("\n📌 RESUMO:")
    
    if new_metrics['total_return'] > old_metrics['total_return']:
        diff = new_metrics['total_return'] - old_metrics['total_return']
        print(f"✅ Nova estratégia SUPERIOR: +{diff:.2f}% de retorno extra")
    else:
        diff = old_metrics['total_return'] - new_metrics['total_return']
        print(f"⚠️ Estratégia antiga SUPERIOR: +{diff:.2f}% de retorno extra")
    
    print(f"\n💰 Capital Inicial: ${old_metrics.get('final_capital', 1000) - old_metrics.get('total_pnl', 0):.2f}")
    print(f"💰 Capital Final (Antiga): ${old_metrics.get('final_capital', 0):.2f}")
    print(f"💰 Capital Final (Nova): ${new_metrics.get('final_capital', 0):.2f}")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("🚀 INICIANDO BACKTEST COMPARATIVO")
    print("="*80)
    
    # 1. Baixar dados históricos (6 meses para mais variação)
    data = fetch_historical_data(symbol='SOL/USDC:USDC', days=180)
    
    # 2. Rodar estratégia antiga
    print("\n" + "="*80)
    backtest_old = Backtest(initial_capital=1000, leverage=5)
    old_metrics = backtest_old.run_old_strategy(data.copy())
    
    # 3. Rodar estratégia nova
    print("\n" + "="*80)
    backtest_new = Backtest(initial_capital=1000, leverage=5)
    new_metrics = backtest_new.run_new_strategy(data.copy())
    
    # 4. Comparar resultados
    print_comparison(old_metrics, new_metrics)
    
    # 5. Salvar resultados
    results = {
        'backtest_date': datetime.now().isoformat(),
        'period': f"{data['timestamp'].min()} to {data['timestamp'].max()}",
        'symbol': 'SOL/USDC:USDC',
        'initial_capital': 1000,
        'leverage': 5,
        'old_strategy': old_metrics,
        'new_strategy': new_metrics,
        'old_trades': backtest_old.trades,
        'new_trades': backtest_new.trades
    }
    
    with open('backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("💾 Resultados salvos em: backtest_results.json")
    print("\n✅ BACKTEST CONCLUÍDO!")
