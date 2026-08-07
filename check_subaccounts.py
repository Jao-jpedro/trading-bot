#!/usr/bin/env python3
"""
Script para listar todas as subcontas da Hyperliquid e seus saldos
"""
import os
import sys
import requests

# API Hyperliquid
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

def get_all_subaccounts(master_wallet: str):
    """Lista todas as subcontas de uma wallet master"""
    print(f"\n🔍 Buscando subcontas da wallet master: {master_wallet}\n")
    
    # Buscar estado da wallet master
    response = requests.post(HL_INFO_URL, json={
        "type": "clearinghouseState",
        "user": master_wallet
    })
    
    if response.status_code != 200:
        print(f"❌ Erro HTTP: {response.status_code}")
        return
    
    data = response.json()
    
    print(f"📊 MASTER ACCOUNT: {master_wallet}")
    print(f"=" * 80)
    
    if "marginSummary" in data:
        margin = data["marginSummary"]
        account_value = float(margin.get("accountValue", 0))
        margin_used = float(margin.get("totalMarginUsed", 0))
        available = account_value - margin_used
        
        print(f"💰 Account Value: ${account_value:.2f}")
        print(f"📊 Margin Used: ${margin_used:.2f}")
        print(f"✅ Available: ${available:.2f}")
    
    print(f"\n" + "=" * 80)
    print(f"🔍 TESTANDO ENDEREÇOS DE SUBCONTAS CONHECIDOS:\n")
    
    # Lista de possíveis subcontas para testar
    known_addresses = [
        "0x5ff0f14d577106f9ede3d9568a423166be61ea9d",
        # Adicione outros endereços se souber
    ]
    
    for addr in known_addresses:
        print(f"\n📍 Testando: {addr}")
        print("-" * 80)
        
        response = requests.post(HL_INFO_URL, json={
            "type": "clearinghouseState",
            "user": addr
        })
        
        if response.status_code == 200:
            data = response.json()
            
            if "marginSummary" in data:
                margin = data["marginSummary"]
                account_value = float(margin.get("accountValue", 0))
                margin_used = float(margin.get("totalMarginUsed", 0))
                available = account_value - margin_used
                
                print(f"💰 Account Value: ${account_value:.2f}")
                print(f"📊 Margin Used: ${margin_used:.2f}")
                print(f"✅ Available: ${available:.2f}")
                
                if available > 0:
                    print(f"🎯 ESTA SUBCONTA TEM SALDO! ✅")
            
            if "assetPositions" in data and data["assetPositions"]:
                print(f"📊 Posições abertas: {len(data['assetPositions'])}")
                for pos in data["assetPositions"]:
                    print(f"   - {pos.get('position', {})}")

if __name__ == "__main__":
    # Pegar endereços das variáveis de ambiente
    master_wallet = os.getenv("WALLET_ADDRESS")
    subaccount = os.getenv("HYPERLIQUID_SUBACCOUNT")
    
    if not master_wallet:
        print("❌ WALLET_ADDRESS não configurado!")
        sys.exit(1)
    
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE SUBCONTAS HYPERLIQUID")
    print("=" * 80)
    
    print(f"\n📋 Variáveis de ambiente:")
    print(f"   WALLET_ADDRESS: {master_wallet}")
    print(f"   HYPERLIQUID_SUBACCOUNT: {subaccount}")
    
    # Verificar master account
    get_all_subaccounts(master_wallet)
    
    print("\n" + "=" * 80)
    print("💡 PRÓXIMOS PASSOS:")
    print("=" * 80)
    print("\n1. Acesse https://app.hyperliquid.xyz/")
    print("2. Clique em 'Sub-Accounts' no canto superior direito")
    print("3. Selecione 'VWAP_PULLBACK'")
    print("4. Na URL, você verá o endereço correto da subconta")
    print("5. Copie e atualize HYPERLIQUID_SUBACCOUNT no Render.com")
    print("\n")
