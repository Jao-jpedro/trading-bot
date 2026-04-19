"""
═══════════════════════════════════════════════════════════════════════════════
INTEGRAÇÃO DA NOVA ESTRATÉGIA COM O CÓDIGO EXISTENTE
═══════════════════════════════════════════════════════════════════════════════

Este módulo mostra como integrar a nova estratégia otimizada
ao seu bot existente sem quebrar a estrutura atual.

Mudanças principais:
1. Substituir análise RSI simples por StrategyEngine
2. Adaptar execução de ordens para saídas parciais
3. Modificar StateManager para suportar múltiplos alvos
4. Atualizar Google Sheets com novos campos
"""

import pandas as pd
from typing import Dict, Optional
from strategy_engine import StrategyEngine, PositionManager, TradeSignal
import logging

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE ADAPTADORA - Liga estratégia nova ao código antigo
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedTradingStrategy:
    """
    Wrapper que adapta a nova estratégia ao seu código existente
    
    Mantém compatibilidade com:
    - ExchangeConnector
    - StateManager  
    - GoogleSheetsLogger
    
    Mas usa internamente a lógica otimizada
    """
    
    def __init__(
        self,
        leverage: float = 5.0,
        enable_partial_exits: bool = True,
        enable_trailing_stop: bool = True
    ):
        """
        Args:
            leverage: Alavancagem usada
            enable_partial_exits: Se True, executa saídas parciais (TP1/TP2)
            enable_trailing_stop: Se True, move stop para break-even após TP1
        """
        self.strategy = StrategyEngine(
            ema_period=200,
            rsi_period=14,
            atr_period=14,
            rsi_oversold=30,
            rsi_overbought=70,
            atr_sl_multiplier=1.5,
            atr_tp1_multiplier=2.0,
            atr_tp2_multiplier=4.0
        )
        
        self.position_manager = PositionManager(leverage=leverage)
        self.enable_partial_exits = enable_partial_exits
        self.enable_trailing_stop = enable_trailing_stop
        
        # Estado da posição atual (para controle de saídas parciais)
        self.active_position = None
        self.original_amount = 0  # Quantidade inicial da posição
    
    def analyze_entry(
        self,
        symbol: str,
        historical_data: pd.DataFrame,
        current_position: Optional[str] = None
    ) -> Dict:
        """
        Analisa se deve entrar em posição
        
        Substitui a lógica antiga de:
        - Apenas RSI
        - Sem filtro de tendência
        
        Args:
            symbol: Símbolo do ativo (ex: "SOL/USDC:USDC")
            historical_data: DataFrame com OHLCV
            current_position: Se já tem posição (LONG/SHORT/None)
        
        Returns:
            Dict compatível com código antigo:
            {
                'signal': 'LONG' | 'SHORT' | 'NONE',
                'confidence': float,
                'reason': str,
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,  # TP2 (final)
                'take_profit_1': float,  # TP1 (parcial)
                'position_size_pct': float,
                'rsi': float,  # Para compatibilidade com logs
                'ema200': float,  # Novo: referência de tendência
                'atr': float  # Novo: volatilidade
            }
        """
        
        # Gerar sinal usando nova estratégia
        signal = self.strategy.generate_signal(historical_data, current_position)
        
        # Analisar mercado para pegar valores dos indicadores
        market = self.strategy.analyze_market(historical_data)
        
        # Montar resposta no formato esperado pelo código antigo
        result = {
            'signal': signal.signal_type,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'rsi': market.rsi,
            'ema200': market.ema200,
            'atr': market.atr,
            'volatility_percentile': market.volatility_percentile,
            'position_size_pct': signal.position_size_pct
        }
        
        # Se tem níveis calculados, adicionar
        if signal.levels:
            result.update({
                'entry_price': signal.levels.entry_price,
                'stop_loss': signal.levels.stop_loss,
                'take_profit': signal.levels.take_profit_2,  # TP final
                'take_profit_1': signal.levels.take_profit_1,  # TP parcial
            })
        
        return result
    
    def monitor_position_exit(
        self,
        current_price: float,
        entry_data: Dict
    ) -> Dict:
        """
        Monitora posição ativa para executar saídas
        
        Novo comportamento:
        - Saída parcial em TP1 (50%)
        - Move stop para break-even após TP1
        - Saída total em TP2 ou SL
        
        Args:
            current_price: Preço atual do mercado
            entry_data: Dados da entrada (do analyze_entry ou do state)
        
        Returns:
            {
                'should_exit': bool,
                'exit_type': str,  # 'STOP_LOSS', 'TP1', 'TP2'
                'exit_percentage': float,  # 50 ou 100
                'current_roi': float,
                'new_stop_loss': Optional[float]  # Se trailing stop ativou
            }
        """
        
        # Reconstruir PositionLevels a partir dos dados salvos
        from strategy_engine import PositionLevels
        
        levels = PositionLevels(
            entry_price=entry_data['entry_price'],
            stop_loss=entry_data['stop_loss'],
            take_profit_1=entry_data.get('take_profit_1', entry_data['take_profit']),
            take_profit_2=entry_data.get('take_profit', entry_data['take_profit'])
        )
        
        signal_type = entry_data['signal']
        
        # Verificar condições de saída
        should_exit, exit_type, exit_pct = self.position_manager.check_exit_conditions(
            current_price=current_price,
            entry_price=levels.entry_price,
            levels=levels,
            signal_type=signal_type
        )
        
        # Calcular ROI atual
        roi = self.position_manager.calculate_roi(
            entry_price=levels.entry_price,
            exit_price=current_price,
            signal_type=signal_type
        )
        
        result = {
            'should_exit': should_exit,
            'exit_type': exit_type,
            'exit_percentage': exit_pct,
            'current_roi': roi,
            'new_stop_loss': None
        }
        
        # Se atingiu TP1 e trailing stop ativo, retornar novo SL
        if exit_type == "TP1" and self.enable_trailing_stop:
            result['new_stop_loss'] = levels.entry_price  # Break-even
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO DE INTEGRAÇÃO NO LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def example_main_loop_integration():
    """
    Exemplo de como modificar o loop principal do bot
    para usar a nova estratégia
    
    ANTES (código antigo):
    ```python
    rsi = calculate_rsi(data)
    if rsi < 20:
        signal = "LONG"
    elif rsi > 80:
        signal = "SHORT"
    ```
    
    DEPOIS (código novo):
    ```python
    analysis = strategy.analyze_entry(symbol, data, current_position)
    if analysis['signal'] != 'NONE' and analysis['confidence'] >= 60:
        # Executar entrada
    ```
    """
    
    # Criar estratégia otimizada
    strategy = EnhancedTradingStrategy(
        leverage=5.0,
        enable_partial_exits=True,
        enable_trailing_stop=True
    )
    
    # Simular loop principal
    symbols = ["SOL/USDC:USDC", "XRP/USDC:USDC"]
    
    for symbol in symbols:
        log.info(f"🔍 Analisando {symbol}...")
        
        # 1. BUSCAR DADOS HISTÓRICOS (mantém código antigo)
        # historical_data = exchange.fetch_historical_data(symbol, days=30)
        
        # Simulando dados
        import numpy as np
        historical_data = pd.DataFrame({
            'open': np.random.randn(300).cumsum() + 100,
            'high': np.random.randn(300).cumsum() + 101,
            'low': np.random.randn(300).cumsum() + 99,
            'close': np.random.randn(300).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 300)
        })
        
        # 2. VERIFICAR SE JÁ TEM POSIÇÃO (mantém código antigo)
        # current_position = state.get_active_position(symbol)
        current_position = None  # Simulação
        
        # 3. ANALISAR ENTRADA (NOVO - substitui análise RSI simples)
        analysis = strategy.analyze_entry(
            symbol=symbol,
            historical_data=historical_data,
            current_position=current_position
        )
        
        log.info(f"📊 {symbol}:")
        log.info(f"   Sinal: {analysis['signal']}")
        log.info(f"   Confiança: {analysis['confidence']:.1f}%")
        log.info(f"   RSI: {analysis['rsi']:.1f}")
        log.info(f"   EMA200: ${analysis['ema200']:.2f}")
        log.info(f"   ATR: ${analysis['atr']:.2f}")
        log.info(f"   Razão: {analysis['reason']}")
        
        # 4. DECIDIR SE ENTRA
        if analysis['signal'] != 'NONE' and analysis['confidence'] >= 60:
            log.info(f"🚨 SINAL DE ENTRADA {analysis['signal']}!")
            
            # EXECUTAR ORDEM (mantém código antigo de execução)
            """
            order_result = exchange.create_market_order(
                symbol=symbol,
                side='buy' if analysis['signal'] == 'LONG' else 'sell',
                amount_usd=balance * analysis['position_size_pct'] / 100,
                leverage=5.0
            )
            
            if order_result:
                # Salvar estado com NOVOS campos
                state.record_entry(
                    symbol=symbol,
                    signal=analysis['signal'],
                    entry_price=analysis['entry_price'],
                    stop_loss=analysis['stop_loss'],
                    take_profit=analysis['take_profit'],
                    take_profit_1=analysis['take_profit_1'],  # NOVO
                    amount=order_result['amount'],
                    rsi=analysis['rsi'],
                    ema200=analysis['ema200'],  # NOVO
                    atr=analysis['atr'],  # NOVO
                    confidence=analysis['confidence'],  # NOVO
                    trade_id=generate_trade_id()
                )
            """
        
        # 5. MONITORAR SAÍDAS (se tem posição)
        if current_position:
            current_price = historical_data['close'].iloc[-1]
            
            exit_check = strategy.monitor_position_exit(
                current_price=current_price,
                entry_data=current_position  # Dados salvos no state
            )
            
            if exit_check['should_exit']:
                log.info(f"{get_exit_emoji(exit_check['exit_type'])} {exit_check['exit_type']} atingido!")
                log.info(f"   ROI: {exit_check['current_roi']:+.2f}%")
                log.info(f"   Fechando {exit_check['exit_percentage']:.0f}% da posição")
                
                # EXECUTAR SAÍDA (parcial ou total)
                """
                # Calcular quanto fechar
                if exit_check['exit_percentage'] == 50:
                    # Saída PARCIAL (TP1)
                    amount_to_close = current_position['amount'] * 0.5
                else:
                    # Saída TOTAL (TP2 ou SL)
                    amount_to_close = current_position['remaining_amount']
                
                # Executar ordem de saída
                exit_order = exchange.create_market_order(
                    symbol=symbol,
                    side='sell' if current_position['signal'] == 'LONG' else 'buy',
                    amount_usd=amount_to_close * current_price,
                    leverage=5.0
                )
                
                if exit_order:
                    # Atualizar estado
                    if exit_check['exit_percentage'] == 50:
                        # TP1: manter posição parcial aberta
                        state.update_partial_exit(
                            trade_id=current_position['trade_id'],
                            exit_price=current_price,
                            exit_percentage=50,
                            roi=exit_check['current_roi'],
                            new_stop_loss=exit_check['new_stop_loss']
                        )
                    else:
                        # TP2 ou SL: fechar posição completa
                        state.close_position(
                            trade_id=current_position['trade_id'],
                            exit_price=current_price,
                            roi=exit_check['current_roi'],
                            exit_type=exit_check['exit_type']
                        )
                """


def get_exit_emoji(exit_type: str) -> str:
    """Helper para emojis de saída"""
    emojis = {
        "STOP_LOSS": "🔴",
        "TP1": "🟡",
        "TP2": "🟢",
        "TRAILING_STOP": "🔵"
    }
    return emojis.get(exit_type, "⚪")


# ═══════════════════════════════════════════════════════════════════════════════
# MODIFICAÇÕES NECESSÁRIAS NO SEU CÓDIGO ATUAL
# ═══════════════════════════════════════════════════════════════════════════════

"""
CHECKLIST DE MUDANÇAS NO trading.py:

1. ✅ Importar nova estratégia:
   from strategy_engine import StrategyEngine, PositionManager
   from strategy_integration import EnhancedTradingStrategy

2. ✅ Substituir análise RSI simples:
   ANTES:
   if rsi < 20:
       signal = "LONG"
   
   DEPOIS:
   strategy = EnhancedTradingStrategy()
   analysis = strategy.analyze_entry(symbol, data)
   if analysis['signal'] != 'NONE':
       signal = analysis['signal']

3. ✅ Adicionar novos campos ao StateManager:
   - take_profit_1 (TP parcial)
   - ema200 (referência de tendência)
   - atr (volatilidade)
   - confidence (confiança do sinal)
   - remaining_amount (quanto ainda está aberto após TP1)

4. ✅ Modificar monitor_and_execute_exits():
   ANTES: Apenas verifica SL e TP fixos
   DEPOIS: Usa position_manager.check_exit_conditions()
           para saídas parciais e trailing stop

5. ✅ Atualizar Google Sheets:
   Adicionar colunas:
   - Confidence (%)
   - EMA200
   - ATR
   - Exit % (50 ou 100)
   - Exit Type (TP1, TP2, SL)

6. ✅ Modificar lógica de cooldown:
   ANTES: 48h fixo
   DEPOIS: Adaptar baseado em volatilidade
           (alta vol = cooldown maior)
"""


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("=" * 80)
    print("DEMONSTRAÇÃO DE INTEGRAÇÃO")
    print("=" * 80)
    
    example_main_loop_integration()
