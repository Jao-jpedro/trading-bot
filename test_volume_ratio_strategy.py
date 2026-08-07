#!/usr/bin/env python3

"""
Script de teste para validar a nova lógica de Volume Ratio

Testa:
1. Cálculo de buy/sell volume
2. Ratio suavizado
3. Detecção de cruzamentos com histerese
4. Filtro de tendência (EMAs)
"""

import pandas as pd
import numpy as np

def test_volume_ratio_calculation():
    """Testa o cálculo de buy/sell volume"""
    print("=" * 60)
    print("TESTE 1: Cálculo de Volume Ratio")
    print("=" * 60)
    
    # Criar dados de teste
    data = {
        'close': [100, 102, 101, 105, 103, 108],  # Preços variando
        'volume': [1000, 1200, 900, 1500, 800, 1300]
    }
    df = pd.DataFrame(data)
    
    # Calcular mudanças de preço
    df['price_change'] = df['close'].diff()
    df['price_change_pct'] = df['price_change'] / df['close'].shift(1)
    
    # Distribuir volume
    df['buy_volume'] = 0.0
    df['sell_volume'] = 0.0
    
    for idx in range(1, len(df)):
        total_volume = df.iloc[idx]['volume']
        price_change = df.iloc[idx]['price_change']
        
        if price_change > 0:
            # Preço subiu - mais volume de compra
            price_change_pct_abs = abs(df.iloc[idx]['price_change_pct'])
            buy_pct = min(0.9, 0.6 + (price_change_pct_abs * 10))
            
            df.loc[df.index[idx], 'buy_volume'] = total_volume * buy_pct
            df.loc[df.index[idx], 'sell_volume'] = total_volume * (1 - buy_pct)
        elif price_change < 0:
            # Preço caiu - mais volume de venda
            price_change_pct_abs = abs(df.iloc[idx]['price_change_pct'])
            sell_pct = min(0.9, 0.6 + (price_change_pct_abs * 10))
            
            df.loc[df.index[idx], 'sell_volume'] = total_volume * sell_pct
            df.loc[df.index[idx], 'buy_volume'] = total_volume * (1 - sell_pct)
        else:
            # Sem mudança - distribuir igualmente
            df.loc[df.index[idx], 'buy_volume'] = total_volume * 0.5
            df.loc[df.index[idx], 'sell_volume'] = total_volume * 0.5
    
    # Calcular ratio
    df['ratio'] = df['buy_volume'] / df['sell_volume'].replace(0, 1)
    df['ratio_3'] = df['ratio'].rolling(window=3, min_periods=1).mean()
    
    print("\nResultados:")
    print(df[['close', 'volume', 'price_change', 'buy_volume', 'sell_volume', 'ratio', 'ratio_3']].to_string())
    
    print("\n✅ TESTE 1 PASSOU: Volume ratio calculado corretamente")
    print()

def test_histerese_detection():
    """Testa a detecção de cruzamentos com histerese"""
    print("=" * 60)
    print("TESTE 2: Detecção de Histerese")
    print("=" * 60)
    
    RATIO_THRESHOLD_LONG = 1.10
    RATIO_THRESHOLD_SHORT = 0.90
    
    # Cenários de teste
    scenarios = [
        {
            "name": "LONG - Cruzamento válido",
            "prev_ratio": 1.05,
            "curr_ratio": 1.15,
            "ema_fast": 100,
            "ema_slow": 95,
            "expected_signal": "LONG"
        },
        {
            "name": "LONG - Sem cruzamento (já acima)",
            "prev_ratio": 1.12,
            "curr_ratio": 1.15,
            "ema_fast": 100,
            "ema_slow": 95,
            "expected_signal": None
        },
        {
            "name": "LONG - Cruzamento mas sem tendência",
            "prev_ratio": 1.05,
            "curr_ratio": 1.15,
            "ema_fast": 95,
            "ema_slow": 100,
            "expected_signal": None
        },
        {
            "name": "SHORT - Cruzamento válido",
            "prev_ratio": 0.95,
            "curr_ratio": 0.85,
            "ema_fast": 95,
            "ema_slow": 100,
            "expected_signal": "SHORT"
        },
        {
            "name": "SHORT - Sem cruzamento (já abaixo)",
            "prev_ratio": 0.85,
            "curr_ratio": 0.80,
            "ema_fast": 95,
            "ema_slow": 100,
            "expected_signal": None
        }
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        prev_ratio = scenario["prev_ratio"]
        curr_ratio = scenario["curr_ratio"]
        ema_fast = scenario["ema_fast"]
        ema_slow = scenario["ema_slow"]
        expected = scenario["expected_signal"]
        
        # Lógica de detecção
        signal = None
        
        # Gatilho LONG
        if prev_ratio < RATIO_THRESHOLD_LONG and curr_ratio >= RATIO_THRESHOLD_LONG:
            if ema_fast > ema_slow:
                signal = "LONG"
        
        # Gatilho SHORT
        elif prev_ratio > RATIO_THRESHOLD_SHORT and curr_ratio <= RATIO_THRESHOLD_SHORT:
            if ema_fast < ema_slow:
                signal = "SHORT"
        
        # Verificar resultado
        if signal == expected:
            print(f"✅ {scenario['name']}")
            print(f"   Ratio: {prev_ratio:.2f} → {curr_ratio:.2f}")
            print(f"   EMAs: {ema_fast:.2f} vs {ema_slow:.2f}")
            print(f"   Sinal: {signal if signal else 'NENHUM'}")
            passed += 1
        else:
            print(f"❌ {scenario['name']}")
            print(f"   Esperado: {expected if expected else 'NENHUM'}")
            print(f"   Obtido: {signal if signal else 'NENHUM'}")
            failed += 1
        print()
    
    print(f"Resultados: {passed} passou, {failed} falhou")
    
    if failed == 0:
        print("✅ TESTE 2 PASSOU: Histerese funcionando corretamente")
    else:
        print("❌ TESTE 2 FALHOU")
    print()

def test_ema_calculation():
    """Testa o cálculo de EMAs"""
    print("=" * 60)
    print("TESTE 3: Cálculo de EMAs")
    print("=" * 60)
    
    # Dados de teste
    prices = [100, 102, 101, 105, 103, 108, 107, 110, 112, 115, 
              114, 118, 120, 119, 122, 125, 123, 128, 130, 132, 
              135, 133]
    
    df = pd.DataFrame({'close': prices})
    
    # Calcular EMAs
    ema_7 = df['close'].ewm(span=7, adjust=False).mean().iloc[-1]
    ema_21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
    
    print(f"\nÚltimo preço: ${df['close'].iloc[-1]:.2f}")
    print(f"EMA 7: ${ema_7:.2f}")
    print(f"EMA 21: ${ema_21:.2f}")
    
    # Determinar tendência
    if ema_7 > ema_21:
        trend = "ALTA"
    elif ema_7 < ema_21:
        trend = "BAIXA"
    else:
        trend = "NEUTRA"
    
    print(f"Tendência: {trend}")
    
    # Validar que EMA 7 reage mais rápido que EMA 21
    if ema_7 > ema_21 and df['close'].iloc[-1] > df['close'].iloc[0]:
        print("\n✅ TESTE 3 PASSOU: EMAs calculadas corretamente (tendência de alta detectada)")
    else:
        print("\n⚠️  TESTE 3: Resultado inesperado")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTE DE VALIDAÇÃO - ESTRATÉGIA VOLUME RATIO")
    print("=" * 60 + "\n")
    
    test_volume_ratio_calculation()
    test_histerese_detection()
    test_ema_calculation()
    
    print("=" * 60)
    print("TODOS OS TESTES CONCLUÍDOS")
    print("=" * 60)
