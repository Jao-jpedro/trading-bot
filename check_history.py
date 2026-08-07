#!/usr/bin/env python3
import requests
import json
from datetime import datetime

addresses = {
    'SUBACCOUNT': '0x5ff0f14d577106f9ede3d9568a423166be61ea9d',
    'Master': '0x0effe318659DE1cD2B2564A4A75e43186Ac06337',
}

print("\n" + "="*80)
print("🔍 VERIFICANDO HISTÓRICO DE TRADES")
print("="*80)

for name, addr in addresses.items():
    print(f"\n📍 {name}: {addr}")
    print("-"*80)
    
    # Buscar fills (trades executados)
    response = requests.post('https://api.hyperliquid.xyz/info', json={
        'type': 'userFills',
        'user': addr
    })
    
    if response.status_code == 200:
        fills = response.json()
        
        if fills and len(fills) > 0:
            print(f"✅ Encontrados {len(fills)} trades")
            print(f"\n📊 Últimos 5 trades:")
            
            for i, fill in enumerate(fills[:5]):
                # Converter timestamp
                ts = fill.get('time', 0)
                dt = datetime.fromtimestamp(ts / 1000) if ts else None
                
                coin = fill.get('coin', '?')
                side = fill.get('side', '?')
                px = fill.get('px', '?')
                sz = fill.get('sz', '?')
                
                print(f"\n   {i+1}. {coin} {side}")
                print(f"      Preço: ${px}")
                print(f"      Size: {sz}")
                print(f"      Data: {dt.strftime('%Y-%m-%d %H:%M:%S') if dt else '?'}")
        else:
            print("⚠️ Nenhum trade encontrado")
    else:
        print(f"❌ Erro: {response.status_code}")
    
    # Buscar estado atual
    response = requests.post('https://api.hyperliquid.xyz/info', json={
        'type': 'clearinghouseState',
        'user': addr
    })
    
    if response.status_code == 200:
        data = response.json()
        margin = data.get('marginSummary', {})
        account_value = float(margin.get('accountValue', 0))
        
        print(f"\n💰 Saldo atual: ${account_value:.2f}")
        
        # Verificar posições abertas
        positions = data.get('assetPositions', [])
        if positions:
            print(f"📊 Posições abertas: {len(positions)}")
            for pos in positions:
                position_data = pos.get('position', {})
                coin = position_data.get('coin', '?')
                szi = position_data.get('szi', '?')
                entry_px = position_data.get('entryPx', '?')
                
                print(f"   - {coin}: {szi} @ ${entry_px}")

print("\n" + "="*80)
print("💡 DIAGNÓSTICO:")
print("="*80)
print("\nSe houver trades recentes, o bot ESTAVA funcionando!")
print("Se o saldo está $0.00 agora, pode ser que:")
print("  1. Todas as ordens foram executadas e fechadas")
print("  2. Stop loss foi atingido")
print("  3. Fundos foram transferidos para outra conta")
print("\n")
