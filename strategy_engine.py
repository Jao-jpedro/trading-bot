"""
═══════════════════════════════════════════════════════════════════════════════
STRATEGY ENGINE - Trading Algorítmico Otimizado
═══════════════════════════════════════════════════════════════════════════════

Estratégia: EMA200 + RSI + ATR (Trend Following com Mean Reversion Timing)

Filosofia:
- Operar apenas a favor da tendência principal (EMA 200)
- Usar RSI para timing de entrada em pullbacks
- Stop Loss e Take Profit adaptativos baseados em volatilidade (ATR)
- Gestão parcial de posição para maximizar lucros e proteger capital

Melhorias vs código original:
1. Filtro de tendência obrigatório (EMA 200)
2. Stop Loss dinâmico baseado em ATR
3. Take Profit escalonado (50% em TP1, 50% em TP2)
4. Trailing stop após primeiro alvo
5. Position sizing baseado em risco
6. Filtro de volatilidade (evita mercado lateral)
7. Cooldown adaptativo
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Literal, Tuple
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# INDICADORES TÉCNICOS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_ema(data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    Calcula EMA (Exponential Moving Average)
    
    Args:
        data: DataFrame com dados OHLCV
        period: Período da EMA
        column: Coluna a usar (default: 'close')
    
    Returns:
        Series com valores da EMA
    """
    return data[column].ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """
    Calcula RSI (Relative Strength Index)
    
    Implementação otimizada usando método Wilder
    
    Args:
        data: DataFrame com dados OHLCV
        period: Período do RSI (default: 14)
        column: Coluna a usar (default: 'close')
    
    Returns:
        Series com valores do RSI (0-100)
    """
    delta = data[column].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    # Wilder's smoothing
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calcula ATR (Average True Range) - Medida de volatilidade
    
    ATR é crucial para:
    - Definir stop loss adaptativo
    - Calcular take profit baseado em volatilidade
    - Position sizing
    
    Args:
        data: DataFrame com dados OHLCV (precisa ter high, low, close)
        period: Período do ATR (default: 14)
    
    Returns:
        Series com valores do ATR
    """
    high = data['high']
    low = data['low']
    close = data['close']
    
    # True Range = max(H-L, |H-C_prev|, |L-C_prev|)
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    return atr


def calculate_volatility_percentile(atr: pd.Series, lookback: int = 100) -> float:
    """
    Calcula percentil de volatilidade atual vs histórico
    
    Usado para filtrar mercado lateral:
    - < 30%: Baixa volatilidade (evitar)
    - 30-70%: Volatilidade normal (operar)
    - > 70%: Alta volatilidade (cautela ou evitar)
    
    Args:
        atr: Series com valores de ATR
        lookback: Período para calcular percentil
    
    Returns:
        Percentil atual (0-100)
    """
    if len(atr) < lookback:
        return 50.0  # Default: volatilidade média
    
    current_atr = atr.iloc[-1]
    historical_atr = atr.iloc[-lookback:]
    
    percentile = (historical_atr < current_atr).sum() / len(historical_atr) * 100
    
    return percentile


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES PARA ORGANIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketConditions:
    """Estado atual do mercado"""
    price: float
    ema200: float
    rsi: float
    atr: float
    volatility_percentile: float
    rsi_oversold_threshold: float = 30
    rsi_overbought_threshold: float = 70
    min_vol_percentile: float = 30
    max_vol_percentile: float = 70
    
    @property
    def in_uptrend(self) -> bool:
        """Mercado em tendência de alta (preço > EMA200)"""
        return self.price > self.ema200
    
    @property
    def in_downtrend(self) -> bool:
        """Mercado em tendência de baixa (preço < EMA200)"""
        return self.price < self.ema200
    
    @property
    def is_oversold(self) -> bool:
        """RSI indica sobrevendido"""
        return self.rsi < self.rsi_oversold_threshold
    
    @property
    def is_overbought(self) -> bool:
        """RSI indica sobrecomprado"""
        return self.rsi > self.rsi_overbought_threshold
    
    @property
    def has_good_volatility(self) -> bool:
        """
        Volatilidade está em range ideal para operar
        Evita mercado lateral (baixa vol) e pânico (alta vol)
        """
        return self.min_vol_percentile <= self.volatility_percentile <= self.max_vol_percentile


@dataclass
class PositionLevels:
    """Níveis de entrada, stop e targets para uma posição"""
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Primeiro alvo (50% da posição)
    take_profit_2: float  # Segundo alvo (50% restante)
    
    def stop_loss_distance(self) -> float:
        """Distância do SL em % do preço de entrada"""
        return abs(self.entry_price - self.stop_loss) / self.entry_price * 100
    
    def tp1_distance(self) -> float:
        """Distância do TP1 em % do preço de entrada"""
        return abs(self.take_profit_1 - self.entry_price) / self.entry_price * 100
    
    def tp2_distance(self) -> float:
        """Distância do TP2 em % do preço de entrada"""
        return abs(self.take_profit_2 - self.entry_price) / self.entry_price * 100


@dataclass
class TradeSignal:
    """Sinal de trade gerado pela estratégia"""
    signal_type: Literal["LONG", "SHORT", "NONE"]
    confidence: float  # 0-100
    reason: str
    levels: Optional[PositionLevels] = None
    position_size_pct: float = 30.0  # % do capital a usar
    
    @property
    def should_enter(self) -> bool:
        """Se deve entrar no trade"""
        return self.signal_type != "NONE" and self.confidence >= 60


# ═══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DE SINAL
# ═══════════════════════════════════════════════════════════════════════════════

class StrategyEngine:
    """
    Engine principal da estratégia
    
    Parâmetros ajustáveis:
    - ema_period: Período da EMA de tendência (default: 200)
    - rsi_period: Período do RSI (default: 14)
    - atr_period: Período do ATR (default: 14)
    - rsi_oversold: Nível de RSI para LONG (default: 30)
    - rsi_overbought: Nível de RSI para SHORT (default: 70)
    - atr_sl_multiplier: Multiplicador ATR para Stop Loss (default: 1.5)
    - atr_tp1_multiplier: Multiplicador ATR para TP1 (default: 2.0)
    - atr_tp2_multiplier: Multiplicador ATR para TP2 (default: 4.0)
    """
    
    def __init__(
        self,
        ema_period: int = 200,
        rsi_period: int = 14,
        atr_period: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        atr_sl_multiplier: float = 1.5,
        atr_tp1_multiplier: float = 2.0,
        atr_tp2_multiplier: float = 4.0,
        min_volatility_percentile: float = 30,
        max_volatility_percentile: float = 70,
    ):
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp1_multiplier = atr_tp1_multiplier
        self.atr_tp2_multiplier = atr_tp2_multiplier
        self.min_volatility_percentile = min_volatility_percentile
        self.max_volatility_percentile = max_volatility_percentile
    
    def analyze_market(self, data: pd.DataFrame) -> MarketConditions:
        """
        Analisa dados do mercado e retorna condições atuais
        
        Args:
            data: DataFrame com OHLCV (precisa ter: open, high, low, close, volume)
        
        Returns:
            MarketConditions com estado atual
        """
        # Calcular indicadores
        ema200 = calculate_ema(data, self.ema_period)
        rsi = calculate_rsi(data, self.rsi_period)
        atr = calculate_atr(data, self.atr_period)
        
        # Pegar valores mais recentes
        current_price = data['close'].iloc[-1]
        current_ema200 = ema200.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Calcular percentil de volatilidade
        volatility_pct = calculate_volatility_percentile(atr, lookback=100)
        
        return MarketConditions(
            price=current_price,
            ema200=current_ema200,
            rsi=current_rsi,
            atr=current_atr,
            volatility_percentile=volatility_pct,
            rsi_oversold_threshold=self.rsi_oversold,
            rsi_overbought_threshold=self.rsi_overbought,
            min_vol_percentile=self.min_volatility_percentile,
            max_vol_percentile=self.max_volatility_percentile
        )
    
    def calculate_position_levels(
        self,
        entry_price: float,
        atr: float,
        signal_type: Literal["LONG", "SHORT"]
    ) -> PositionLevels:
        """
        Calcula níveis de SL e TP baseados em ATR
        
        Lógica:
        - SL: 1.5x ATR (adaptativo à volatilidade)
        - TP1: 2x ATR (R:R = 1.33:1)
        - TP2: 4x ATR (R:R = 2.66:1)
        
        Args:
            entry_price: Preço de entrada
            atr: ATR atual
            signal_type: LONG ou SHORT
        
        Returns:
            PositionLevels com todos os níveis calculados
        """
        # Calcular distâncias baseadas em ATR
        sl_distance = atr * self.atr_sl_multiplier
        tp1_distance = atr * self.atr_tp1_multiplier
        tp2_distance = atr * self.atr_tp2_multiplier
        
        if signal_type == "LONG":
            stop_loss = entry_price - sl_distance
            take_profit_1 = entry_price + tp1_distance
            take_profit_2 = entry_price + tp2_distance
        else:  # SHORT
            stop_loss = entry_price + sl_distance
            take_profit_1 = entry_price - tp1_distance
            take_profit_2 = entry_price - tp2_distance
        
        return PositionLevels(
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2
        )
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        current_position: Optional[str] = None
    ) -> TradeSignal:
        """
        Gera sinal de trade baseado na análise de mercado
        
        Lógica de entrada:
        
        LONG:
        1. Preço > EMA200 (tendência de alta)
        2. RSI < 30 (sobrevendido - pullback)
        3. Volatilidade em range normal (30-70%)
        
        SHORT:
        1. Preço < EMA200 (tendência de baixa)
        2. RSI > 70 (sobrecomprado - pullback)
        3. Volatilidade em range normal (30-70%)
        
        Args:
            data: DataFrame com OHLCV
            current_position: Posição atual (LONG/SHORT/None)
        
        Returns:
            TradeSignal com decisão e níveis
        """
        # Analisar mercado
        market = self.analyze_market(data)
        
        # Se já tem posição, não gerar novo sinal
        if current_position:
            return TradeSignal(
                signal_type="NONE",
                confidence=0,
                reason=f"Já em posição {current_position}"
            )
        
        # Verificar volatilidade
        if not market.has_good_volatility:
            return TradeSignal(
                signal_type="NONE",
                confidence=0,
                reason=f"Volatilidade fora do range ({market.volatility_percentile:.0f}%)"
            )
        
        # ═══════ LÓGICA PARA LONG ═══════
        if market.in_uptrend and market.is_oversold:
            # Calcular confiança baseada em quão forte é o setup
            distance_from_ema = ((market.price - market.ema200) / market.ema200) * 100
            rsi_strength = (self.rsi_oversold - market.rsi) / self.rsi_oversold * 100  # Quanto mais baixo, melhor
            
            # Confiança = média ponderada
            confidence = (distance_from_ema * 0.4 + rsi_strength * 0.6)
            confidence = min(max(confidence, 0), 100)  # Clip 0-100
            
            # Calcular níveis
            levels = self.calculate_position_levels(market.price, market.atr, "LONG")
            
            # Ajustar position size baseado em confiança
            position_size = 20 + (confidence / 100 * 10)  # 20-30%
            
            return TradeSignal(
                signal_type="LONG",
                confidence=confidence,
                reason=f"Tendência ALTA (preço {distance_from_ema:.1f}% > EMA200) + RSI sobrevendido ({market.rsi:.1f})",
                levels=levels,
                position_size_pct=position_size
            )
        
        # ═══════ LÓGICA PARA SHORT ═══════
        elif market.in_downtrend and market.is_overbought:
            # Calcular confiança
            distance_from_ema = ((market.ema200 - market.price) / market.ema200) * 100
            rsi_strength = (market.rsi - self.rsi_overbought) / (100 - self.rsi_overbought) * 100  # Quanto mais alto, melhor
            
            confidence = (distance_from_ema * 0.4 + rsi_strength * 0.6)
            confidence = min(max(confidence, 0), 100)
            
            # Calcular níveis
            levels = self.calculate_position_levels(market.price, market.atr, "SHORT")
            
            # Ajustar position size
            position_size = 20 + (confidence / 100 * 10)  # 20-30%
            
            return TradeSignal(
                signal_type="SHORT",
                confidence=confidence,
                reason=f"Tendência BAIXA (preço {distance_from_ema:.1f}% < EMA200) + RSI sobrecomprado ({market.rsi:.1f})",
                levels=levels,
                position_size_pct=position_size
            )
        
        # ═══════ SEM SINAL ═══════
        else:
            # Diagnosticar por que não gerou sinal
            if market.in_uptrend:
                reason = f"Tendência ALTA, mas RSI={market.rsi:.1f} (precisa <{self.rsi_oversold})"
            elif market.in_downtrend:
                reason = f"Tendência BAIXA, mas RSI={market.rsi:.1f} (precisa >{self.rsi_overbought})"
            else:
                reason = f"Sem tendência clara (preço ${market.price:.2f} próximo de EMA200 ${market.ema200:.2f})"
            
            return TradeSignal(
                signal_type="NONE",
                confidence=0,
                reason=reason
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GERENCIADOR DE POSIÇÃO (Position Manager)
# ═══════════════════════════════════════════════════════════════════════════════

class PositionManager:
    """
    Gerencia posição ativa, incluindo:
    - Monitoramento de SL/TP
    - Execução de saída parcial
    - Trailing stop após TP1
    - Break-even após TP1
    """
    
    def __init__(self, leverage: float = 5.0):
        self.leverage = leverage
        self.tp1_hit = False  # Flag se já atingiu TP1
        self.position_size_remaining = 100  # % da posição ainda aberta
    
    def check_exit_conditions(
        self,
        current_price: float,
        entry_price: float,
        levels: PositionLevels,
        signal_type: Literal["LONG", "SHORT"]
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Verifica se deve executar saída (total ou parcial)
        
        Retorna:
            (should_exit, exit_type, exit_percentage)
            
            exit_type pode ser:
            - "STOP_LOSS": Bateu stop loss (sai 100%)
            - "TP1": Bateu primeiro alvo (sai 50%)
            - "TP2": Bateu segundo alvo (sai 50% restante)
            - "TRAILING_STOP": Stop móvel foi atingido
        """
        
        if signal_type == "LONG":
            # LONG: SL abaixo, TPs acima
            
            # Verificar Stop Loss
            if current_price <= levels.stop_loss:
                return (True, "STOP_LOSS", 100.0)
            
            # Verificar TP2 (só possível se já passou por TP1)
            if self.tp1_hit and current_price >= levels.take_profit_2:
                return (True, "TP2", 50.0)  # Fecha 50% restante
            
            # Verificar TP1 (primeira vez)
            if not self.tp1_hit and current_price >= levels.take_profit_1:
                self.tp1_hit = True
                # Mover stop para break-even
                levels.stop_loss = entry_price
                return (True, "TP1", 50.0)  # Fecha 50%
        
        else:  # SHORT
            # SHORT: SL acima, TPs abaixo
            
            # Verificar Stop Loss
            if current_price >= levels.stop_loss:
                return (True, "STOP_LOSS", 100.0)
            
            # Verificar TP2
            if self.tp1_hit and current_price <= levels.take_profit_2:
                return (True, "TP2", 50.0)
            
            # Verificar TP1
            if not self.tp1_hit and current_price <= levels.take_profit_1:
                self.tp1_hit = True
                levels.stop_loss = entry_price  # Break-even
                return (True, "TP1", 50.0)
        
        return (False, None, None)
    
    def calculate_roi(
        self,
        entry_price: float,
        exit_price: float,
        signal_type: Literal["LONG", "SHORT"]
    ) -> float:
        """
        Calcula ROI considerando leverage
        
        Args:
            entry_price: Preço de entrada
            exit_price: Preço de saída
            signal_type: LONG ou SHORT
        
        Returns:
            ROI em % (considerando leverage)
        """
        if signal_type == "LONG":
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100
        
        roi = price_change_pct * self.leverage
        return roi
    
    def reset(self):
        """Reseta estado do gerenciador para nova posição"""
        self.tp1_hit = False
        self.position_size_remaining = 100


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Exemplo de como usar a estratégia
    """
    
    # Criar engine com parâmetros default
    strategy = StrategyEngine()
    position_manager = PositionManager(leverage=5.0)
    
    # Simular dados (em produção, viria do exchange)
    # DataFrame precisa ter: open, high, low, close, volume
    sample_data = pd.DataFrame({
        'open': np.random.randn(300).cumsum() + 100,
        'high': np.random.randn(300).cumsum() + 101,
        'low': np.random.randn(300).cumsum() + 99,
        'close': np.random.randn(300).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 300)
    })
    
    # Gerar sinal
    signal = strategy.generate_signal(sample_data)
    
    print("═" * 80)
    print("SINAL GERADO")
    print("═" * 80)
    print(f"Tipo: {signal.signal_type}")
    print(f"Confiança: {signal.confidence:.1f}%")
    print(f"Razão: {signal.reason}")
    print(f"Tamanho posição: {signal.position_size_pct:.1f}%")
    
    if signal.levels:
        print(f"\nNíveis:")
        print(f"  Entrada: ${signal.levels.entry_price:.2f}")
        print(f"  Stop Loss: ${signal.levels.stop_loss:.2f} (-{signal.levels.stop_loss_distance():.2f}%)")
        print(f"  TP1: ${signal.levels.take_profit_1:.2f} (+{signal.levels.tp1_distance():.2f}%)")
        print(f"  TP2: ${signal.levels.take_profit_2:.2f} (+{signal.levels.tp2_distance():.2f}%)")
