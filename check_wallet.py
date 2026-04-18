#!/usr/bin/env python3
"""
Script para verificar qual endereço corresponde à private key configurada
"""

import os
from eth_account import Account

# Carregar .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Ler private key
private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")

if not private_key:
    print("❌ HYPERLIQUID_PRIVATE_KEY não encontrada nas variáveis de ambiente")
    print("\nConfigure no .env ou export HYPERLIQUID_PRIVATE_KEY=0x...")
    exit(1)

# Garantir que tem prefixo 0x
if not private_key.startswith("0x"):
    private_key = "0x" + private_key

try:
    # Derivar endereço da private key
    account = Account.from_key(private_key)
    derived_address = account.address
    
    print("=" * 80)
    print("🔐 VERIFICAÇÃO DE CARTEIRA")
    print("=" * 80)
    print()
    print(f"📋 Private Key (primeiros 10 chars): {private_key[:10]}...")
    print(f"📋 Private Key (últimos 4 chars): ...{private_key[-4:]}")
    print()
    print(f"✅ Endereço derivado da private key:")
    print(f"   {derived_address}")
    print()
    
    # Comparar com WALLET_ADDRESS configurada
    configured_wallet = os.getenv("WALLET_ADDRESS", "")
    
    if configured_wallet:
        print(f"📝 WALLET_ADDRESS configurada:")
        print(f"   {configured_wallet}")
        print()
        
        if derived_address.lower() == configured_wallet.lower():
            print("✅ CORRETO! WALLET_ADDRESS corresponde à private key")
        else:
            print("❌ ERRO! WALLET_ADDRESS NÃO corresponde à private key")
            print()
            print("🔧 SOLUÇÃO:")
            print(f"   Configure WALLET_ADDRESS={derived_address}")
    else:
        print("⚠️  WALLET_ADDRESS não está configurada")
        print()
        print("🔧 SOLUÇÃO:")
        print(f"   Configure WALLET_ADDRESS={derived_address}")
    
    print()
    print("=" * 80)
    print("💡 DICA:")
    print("   WALLET_ADDRESS deve ser o endereço que ASSINA as transações")
    print("   Esse endereço é derivado automaticamente da HYPERLIQUID_PRIVATE_KEY")
    print("   HYPERLIQUID_SUBACCOUNT é a VAULT onde o bot opera (pode ser diferente)")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Erro ao processar private key: {e}")
    print()
    print("Certifique-se que HYPERLIQUID_PRIVATE_KEY é válida")
