#!/usr/bin/env python3
"""
Descobrir o endereço da API Wallet (agent) que precisa ser aprovado
"""
from eth_account import Account

API_PRIVATE_KEY = "0x40a76704827d33be22ee9083bf2b0713e91a6372616c1468e9bd16430adbe645"

account = Account.from_key(API_PRIVATE_KEY)

print("=" * 80)
print("🔑 ENDEREÇO DA API WALLET (AGENT)")
print("=" * 80)
print()
print(f"API Wallet Address: {account.address}")
print()
print("=" * 80)
print("📋 PRÓXIMO PASSO:")
print("=" * 80)
print()
print("1. Faça login na Hyperliquid com a Master Account:")
print("   0x08183aa09eF03Cf8475D909F507606F5044cBdAB")
print()
print("2. Vá em Settings → API Wallets (ou Sub-Accounts → API)")
print()
print(f"3. Aprove/Adicione este endereço como API Wallet:")
print(f"   {account.address}")
print()
print("4. Conceda permissões para operar na vault:")
print("   0x5ff0f14d577106f9ede3d9568a423166be61ea9d")
print()
print("=" * 80)
