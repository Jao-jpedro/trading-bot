#!/usr/bin/env python3
"""Teste standalone de saldo (sem importar trading.py)"""

import requests

WALLET = '0x5ff0f14d577166f9ede3d9568a423166be61ea9d'
API_URL = 'https://api.hyperliquid.xyz/info'

def get_balance(wallet):
    """Busca saldo em SPOT + PERPS"""
    
    # 1. PERPS
    perp_data = requests.post(
        API_URL,
        json={'type': 'clearinghouseState', 'user': wallet},
        headers={'Content-Type': 'application/json'},
        timeout=10
    ).json()
    
    perp_available = float(perp_data.get('withdrawable', 0))
    
    ms = perp_data.get('marginSummary', {})
    perp_av = float(ms.get('accountValue', 0))
    perp_mu = float(ms.get('totalMarginUsed', 0))
    
    print(f"📊 [PERPS] Withdrawable: ${perp_available:.2f}, AccountValue: ${perp_av:.2f}, MarginUsed: ${perp_mu:.2f}")
    
    # 2. SPOT
    spot_data = requests.post(
        API_URL,
        json={'type': 'spotClearinghouseState', 'user': wallet},
        headers={'Content-Type': 'application/json'},
        timeout=10
    ).json()
    
    spot_available = 0
    balances = spot_data.get('balances', [])
    
    for balance in balances:
        if balance.get('coin') == 'USDC':
            total = float(balance.get('total', 0))
            hold = float(balance.get('hold', 0))
            spot_available = total - hold
            print(f"💵 [SPOT] Total: ${total:.2f}, Hold: ${hold:.2f}, Livre: ${spot_available:.2f}")
            break
    
    # 3. TOTAL
    total = perp_available + spot_available
    print(f"✅ [TOTAL] ${total:.2f} (Perps: ${perp_available:.2f} + Spot: ${spot_available:.2f})")
    
    return total

print("🧪 TESTE DE SALDO (SPOT + PERPS)")
print("=" * 70)
print(f"📍 Wallet: {WALLET[:10]}...{WALLET[-10:]}")
print()

saldo = get_balance(WALLET)

print("=" * 70)
print(f"🎯 RESULTADO FINAL: ${saldo:.2f}")
print(f"✅ ESPERADO: ~$4.98")
print()

if abs(saldo - 4.98) < 0.10:
    print("✅✅✅ SUCESSO! Saldo correto detectado!")
    print("🎉 O bot agora consegue ver os $16.80 totais!")
    print("   - $11.82 bloqueados na posição (Hold)")
    print("   - $ 4.98 livres para novas entradas")
else:
    print(f"❌ Valor inesperado: ${saldo:.2f}")
