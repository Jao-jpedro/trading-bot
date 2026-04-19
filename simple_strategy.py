"""
Estratégia Simplificada para Backtest
Apenas RSI puro com ATR stops
"""

from dataclasses import dataclass
from typing import Literal, Optional
import pandas as pd

@dataclass
class SimpleSignal:
    signal_type: Literal["LONG", "SHORT", "NONE"]
    confidence: float
    reason: str
    entry_price: float = 0
    stop_loss: float = 0
    take_profit_1: float = 0
    take_profit_2: float = 0
    position_size_pct: float = 25.0

class SimpleStrategy:
    """Estratégia RSI simples com stops ATR"""
    
    def __init__(
        self,
        rsi_period: int = 14,
        atr_period: int = 14,
        rsi_oversold: float = 35,
        rsi_overbought: float = 65,
        atr_sl_mult: float = 1.5,
        atr_tp1_mult: float = 2.0,
        atr_tp2_mult: float = 4.0
    ):
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_sl_mult = atr_sl_mult
        self.atr_tp1_mult = atr_tp1_mult
        self.atr_tp2_mult = atr_tp2_mult
    
    def _calculate_rsi(self, data: pd.DataFrame) -> float:
        """Calcular RSI"""
        closes = data['close']
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = -delta.where(delta < 0, 0).rolling(self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def _calculate_atr(self, data: pd.DataFrame) -> float:
        """Calcular ATR"""
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr.iloc[-1]
    
    def generate_signal(self, data: pd.DataFrame) -> SimpleSignal:
        """Gerar sinal baseado em RSI"""
        
        if len(data) < max(self.rsi_period, self.atr_period) + 1:
            return SimpleSignal("NONE", 0, "Dados insuficientes")
        
        price = data['close'].iloc[-1]
        rsi = self._calculate_rsi(data)
        atr = self._calculate_atr(data)
        
        # LONG: RSI oversold
        if rsi < self.rsi_oversold:
            confidence = ((self.rsi_oversold - rsi) / self.rsi_oversold) * 100
            confidence = min(confidence, 100)
            
            sl = price - (atr * self.atr_sl_mult)
            tp1 = price + (atr * self.atr_tp1_mult)
            tp2 = price + (atr * self.atr_tp2_mult)
            
            return SimpleSignal(
                signal_type="LONG",
                confidence=confidence,
                reason=f"RSI oversold: {rsi:.1f}",
                entry_price=price,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                position_size_pct=25.0
            )
        
        # SHORT: RSI overbought
        elif rsi > self.rsi_overbought:
            confidence = ((rsi - self.rsi_overbought) / (100 - self.rsi_overbought)) * 100
            confidence = min(confidence, 100)
            
            sl = price + (atr * self.atr_sl_mult)
            tp1 = price - (atr * self.atr_tp1_mult)
            tp2 = price - (atr * self.atr_tp2_mult)
            
            return SimpleSignal(
                signal_type="SHORT",
                confidence=confidence,
                reason=f"RSI overbought: {rsi:.1f}",
                entry_price=price,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                position_size_pct=25.0
            )
        
        return SimpleSignal("NONE", 0, f"RSI neutro: {rsi:.1f}")
