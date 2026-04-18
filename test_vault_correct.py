#!/usr/bin/env python3
"""
Teste com configuração correta de vault no CCXT Hyperliquid
Baseado na documentação oficial do CCXT
"""
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '0x0effe318659DE1cD2B2564A4A75e43186Ac06337')
PRIVATE_KEY = os.getenv('HYPERLIQUID_PRIVATE_KEY')
VAULT_ADDRESS = os.getenv('HYPERLIQUID_SUBACCOUNT', '0x5ff0f14d577106f9ede3d9568a423166be61ea9d')

print("=" * 80)
print("🧪 TESTE COM CONFIGURAÇÃO CORRETA DE VAULT")
print("=" * 80)
print(f"🔑 Agent (assina): {WALLET_ADDRESS}")
print(f"🏦 Vault (opera): {VAULT_ADDRESS}")
print()

# Teste com configuração correta segundo documentação CCXT
print("📋 Configurando exchange com vault...")
print("-" * 80)

try:
    # Criar exchange com a carteira que assina
    exchange = ccxt.hyperliquid({
        'walletAddress': WALLET_ADDRESS,
        'privateKey': PRIVATE_KEY,
        'options': {
            'vaultAddress': VAULT_ADDRESS,  # Vault onde opera
        }
    })
    
    print("✅ Exchange configurada")
    print(f"   walletAddress: {exchange.walletAddress}")
    print(f"   vaultAddress: {exchange.options.get('vaultAddress', 'N/A')}")
    print()
    
    # Teste 1: Buscar saldo
    print("📊 1. Buscando saldo da vault...")
    balance = exchange.fetch_balance()
    
    print("💰 Saldo USDC:")
    usdc_total = balance['total'].get('USDC', 0)
    usdc_free = balance['free'].get('USDC', 0)
    usdc_used = balance['used'].get('USDC', 0)
    
    print(f"   Total: ${usdc_total:.2f}")
    print(f"   Livre: ${usdc_free:.2f}")
    print(f"   Usado: ${usdc_used:.2f}")
    print()
    
    # Teste 2: Buscar posições
    print("📊 2. Buscando posições abertas...")
    positions = exchange.fetch_positions()
    
    if positions and len(positions) > 0:
        print(f"✅ Encontradas {len(positions)} posições:")
        for pos in positions:
            contracts = float(pos.get('contracts', 0))
            if contracts != 0:
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                print(f"   {symbol}: {side} {contracts} contratos")
    else:
        print("ℹ️  Nenhuma posição aberta")
    print()
    
    # Teste 3: Buscar ticker de SOL
    print("📊 3. Buscando preço SOL...")
    ticker = exchange.fetch_ticker('SOL/USDC:USDC')
    print(f"✅ SOL: ${ticker['last']:.4f}")
    print()
    
    print("=" * 80)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    print()
    print("Stack trace completo:")
    traceback.print_exc()
    print()
    print("=" * 80)
    print("💡 POSSÍVEIS CAUSAS:")
    print("=" * 80)
    print("1. A vault não está vinculada à carteira agent")
    print("2. A private key não tem permissão para acessar a vault")
    print("3. Formato incorreto do vaultAddress")
    print("=" * 80)
