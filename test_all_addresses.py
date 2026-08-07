#!/usr/bin/env python3
import requests
import json

# Testar todos os endereços
addresses = {
    'Antigo SUBACCOUNT': '0x5ff0f14d577106f9ede3d9568a423166be61ea9d',
    'Novo CORRETO': '0x5ff0f14d577166f9ede3d9568a423166be61ea9d',
    'Master Account': '0x0effe318659DE1cD2B2564A4A75e43186Ac06337',
}

print("\n" + "="*80)
print("🔍 TESTANDO TODOS OS ENDEREÇOS")
print("="*80)

for name, addr in addresses.items():
    print(f"\n📍 {name}: {addr}")
    print("-"*80)
    
    response = requests.post('https://api.hyperliquid.xyz/info', json={
        'type': 'clearinghouseState',
        'user': addr
    })
    
    if response.status_code == 200:
        data = response.json()
        
        # Mostrar saldo
        if 'marginSummary' in data:
            margin = data['marginSummary']
            account_value = float(margin.get('accountValue', 0))
            margin_used = float(margin.get('totalMarginUsed', 0))
            available = account_value - margin_used
            
            print(f"💰 Account Value: ${account_value:.2f}")
            print(f"📊 Margin Used: ${margin_used:.2f}")
            print(f"✅ Available: ${available:.2f}")
            
            if available > 0:
                print(f"\n🎯 ENCONTRADO! ESTE ENDEREÇO TEM ${available:.2f}! ✅✅✅")
                print(f"\nAtualizar no Render.com:")
                print(f"HYPERLIQUID_SUBACCOUNT={addr}")
        
        # Mostrar resposta completa
        print(f"\n📋 Resposta completa:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Erro HTTP: {response.status_code}")

print("\n" + "="*80)
