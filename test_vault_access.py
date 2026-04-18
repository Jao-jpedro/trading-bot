#!/usr/bin/env python3
"""
Teste alternativo para verificar acesso à vault
Testa diferentes configurações de acesso
"""
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '0x0effe318659DE1cD2B2564A4A75e43186Ac06337')
PRIVATE_KEY = os.getenv('HYPERLIQUID_PRIVATE_KEY')
VAULT_ADDRESS = os.getenv('HYPERLIQUID_SUBACCOUNT', '0x5ff0f14d577106f9ede3d9568a423166be61ea9d')

print("=" * 80)
print("🧪 TESTE DE ACESSO À VAULT - MÚLTIPLAS CONFIGURAÇÕES")
print("=" * 80)
print(f"🔑 Carteira: {WALLET_ADDRESS}")
print(f"🏦 Vault: {VAULT_ADDRESS}")
print()

# Teste 1: Usando vaultAddress nas options
print("📋 TESTE 1: Usando vaultAddress nas options")
print("-" * 80)
try:
    exchange = ccxt.hyperliquid({
        'walletAddress': WALLET_ADDRESS,
        'privateKey': PRIVATE_KEY,
    })
    exchange.options['vaultAddress'] = VAULT_ADDRESS
    
    balance = exchange.fetch_balance()
    usdc = balance['total'].get('USDC', 0)
    print(f"✅ Resultado: ${usdc:.2f} USDC")
except Exception as e:
    print(f"❌ Erro: {e}")

print()

# Teste 2: Usando walletAddress como vault diretamente
print("📋 TESTE 2: Usando walletAddress como vault")
print("-" * 80)
try:
    exchange = ccxt.hyperliquid({
        'walletAddress': VAULT_ADDRESS,
        'privateKey': PRIVATE_KEY,
    })
    
    balance = exchange.fetch_balance()
    usdc = balance['total'].get('USDC', 0)
    print(f"✅ Resultado: ${usdc:.2f} USDC")
except Exception as e:
    print(f"❌ Erro: {e}")

print()

# Teste 3: Tentando fetch_balance com parâmetros específicos
print("📋 TESTE 3: fetch_balance com params={'type': 'vault'}")
print("-" * 80)
try:
    exchange = ccxt.hyperliquid({
        'walletAddress': WALLET_ADDRESS,
        'privateKey': PRIVATE_KEY,
    })
    exchange.options['vaultAddress'] = VAULT_ADDRESS
    
    balance = exchange.fetch_balance({'type': 'vault'})
    usdc = balance['total'].get('USDC', 0)
    print(f"✅ Resultado: ${usdc:.2f} USDC")
except Exception as e:
    print(f"❌ Erro: {e}")

print()

# Teste 4: Listar posições abertas
print("📋 TESTE 4: Verificando posições abertas na vault")
print("-" * 80)
try:
    exchange = ccxt.hyperliquid({
        'walletAddress': WALLET_ADDRESS,
        'privateKey': PRIVATE_KEY,
    })
    exchange.options['vaultAddress'] = VAULT_ADDRESS
    
    positions = exchange.fetch_positions()
    if positions:
        print(f"✅ Encontradas {len(positions)} posições:")
        for pos in positions:
            if float(pos.get('contracts', 0)) != 0:
                print(f"   {pos['symbol']}: {pos['contracts']} contratos")
    else:
        print("ℹ️  Nenhuma posição aberta")
except Exception as e:
    print(f"❌ Erro: {e}")

print()
print("=" * 80)
print("💡 PRÓXIMOS PASSOS:")
print("=" * 80)
print("1. Se todos os testes falharam, você precisa:")
print(f"   → Adicionar {WALLET_ADDRESS} como 'agent' na vault {VAULT_ADDRESS}")
print("   → Na Hyperliquid: Sub-Accounts → VWAP_PULLBACK → Add Agent")
print()
print("2. Se TESTE 2 funcionou, precisamos mudar o código para usar:")
print("   walletAddress = VAULT_ADDRESS (em vez de usar vaultAddress nas options)")
print()
print("=" * 80)
