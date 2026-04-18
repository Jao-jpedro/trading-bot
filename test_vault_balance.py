#!/usr/bin/env python3
"""
Teste para verificar saldo na vault da Hyperliquid
"""
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '0x0effe318659DE1cD2B2564A4A75e43186Ac06337')
PRIVATE_KEY = os.getenv('HYPERLIQUID_PRIVATE_KEY')
VAULT_ADDRESS = os.getenv('HYPERLIQUID_SUBACCOUNT', '0x5ff0f14d577106f9ede3d9568a423166be61ea9d')

print("=" * 80)
print("🔍 TESTANDO SALDO NA VAULT")
print("=" * 80)
print(f"🔑 Carteira (assinatura): {WALLET_ADDRESS}")
print(f"🏦 Vault (operações): {VAULT_ADDRESS}")
print()

try:
    # Conectar à Hyperliquid
    exchange = ccxt.hyperliquid({
        'walletAddress': WALLET_ADDRESS,
        'privateKey': PRIVATE_KEY,
    })
    
    # Configurar vault como subaccount
    exchange.options['vaultAddress'] = VAULT_ADDRESS
    
    print("✅ Conectado à Hyperliquid")
    print()
    
    # Buscar saldo
    print("📊 Buscando saldo da vault...")
    balance = exchange.fetch_balance()
    
    print()
    print("=" * 80)
    print("💰 RESULTADO:")
    print("=" * 80)
    
    # Saldo total
    if 'USDC' in balance['total']:
        total = balance['total']['USDC']
        free = balance['free'].get('USDC', 0)
        used = balance['used'].get('USDC', 0)
        
        print(f"💵 USDC Total: ${total:.2f}")
        print(f"✅ USDC Livre: ${free:.2f}")
        print(f"🔒 USDC Usado: ${used:.2f}")
    else:
        print("⚠️ Nenhum saldo USDC encontrado")
    
    print()
    print("📋 Todos os ativos:")
    for currency, amount in balance['total'].items():
        if amount > 0:
            print(f"   {currency}: {amount}")
    
    print()
    print("=" * 80)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
