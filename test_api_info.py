#!/usr/bin/env python3
"""
Teste usando a API Info da Hyperliquid para verificar saldo da vault
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MASTER_ACCOUNT = "0x08183aa09eF03Cf8475D909F507606F5044cBdAB"
VAULT_ADDRESS = "0x5ff0f14d577106f9ede3d9568a423166be61ea9d"

print("=" * 80)
print("🔍 BUSCANDO SALDO DA VAULT VIA API INFO")
print("=" * 80)
print(f"🏦 Master Account: {MASTER_ACCOUNT}")
print(f"🏦 Vault Address: {VAULT_ADDRESS}")
print()

# Buscar user_state da Master Account
print("📊 1. Buscando user_state da Master Account...")
response1 = requests.post(
    "https://api.hyperliquid.xyz/info",
    json={
        "type": "clearinghouseState",
        "user": MASTER_ACCOUNT
    }
)

if response1.status_code == 200:
    data = response1.json()
    account_value = data.get("marginSummary", {}).get("accountValue", "0")
    print(f"✅ Master Account Value: ${account_value}")
else:
    print(f"❌ Erro: {response1.status_code}")

print()

# Buscar user_state da Vault
print("📊 2. Buscando user_state da Vault...")
response2 = requests.post(
    "https://api.hyperliquid.xyz/info",
    json={
        "type": "clearinghouseState",
        "user": VAULT_ADDRESS
    }
)

if response2.status_code == 200:
    data = response2.json()
    account_value = data.get("marginSummary", {}).get("accountValue", "0")
    total_margin = data.get("marginSummary", {}).get("totalMarginUsed", "0")
    withdrawable = data.get("withdrawable", "0")
    
    print(f"💰 Vault Account Value: ${account_value}")
    print(f"📊 Total Margin Used: ${total_margin}")
    print(f"✅ Withdrawable: ${withdrawable}")
    
    # Posições
    positions = data.get("assetPositions", [])
    if positions:
        print()
        print("📈 Posições abertas:")
        for pos in positions:
            position = pos.get("position", {})
            coin = position.get("coin")
            szi = position.get("szi")
            if float(szi) != 0:
                print(f"   {coin}: {szi}")
    else:
        print("ℹ️  Nenhuma posição aberta")
else:
    print(f"❌ Erro: {response2.status_code}")

print()
print("=" * 80)
