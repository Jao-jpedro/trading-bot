#!/usr/bin/env python3
"""Teste da nova função de saldo (Spot + Perps)"""

import os
import sys
import requests

# Configurar env vars
os.environ['WALLET_ADDRESS'] = '0x08183aa09eF03Cf8475D909F507606F5044cBdAB'
os.environ['HYPERLIQUID_SUBACCOUNT'] = '0x5ff0f14d577166f9ede3d9568a423166be61ea9d'
os.environ['HYPERLIQUID_PRIVATE_KEY'] = 'dummy_key_for_test'

# Importar função do trading.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trading import _hl_get_account_value

print("🧪 TESTANDO NOVA FUNÇÃO _hl_get_account_value()")
print("=" * 70)

wallet = os.environ['HYPERLIQUID_SUBACCOUNT']
print(f"📍 Wallet testada: {wallet[:10]}...{wallet[-10:]}")
print()

saldo = _hl_get_account_value(wallet)

print("=" * 70)
print(f"🎯 RESULTADO FINAL: ${saldo:.2f}")
print(f"✅ ESPERADO: ~$4.98 (saldo livre em spot)")
print()

if abs(saldo - 4.98) < 0.10:
    print("✅✅✅ TESTE PASSOU! Saldo correto detectado!")
else:
    print(f"❌ TESTE FALHOU! Esperado ~$4.98, obteve ${saldo:.2f}")
