#!/usr/bin/env python3
"""Simula o tratamento do erro 'Reduce only order would increase position'"""
import os
from trading import _HL_INFO_URL, _http_post_json, log

# Simular mensagem de erro
err_msg = 'hyperliquid {"status":"ok","response":{"type":"order","data":{"statuses":[{"error":"Reduce only order would increase position. asset=5"}]}}}'

print('=== Simulação de erro reduceOnly ===')
print(err_msg)

# Chamar comportamento de sincronização: tentar buscar estado real (vai usar API) e imprimir resultado
wallet = os.getenv('HYPERLIQUID_SUBACCOUNT', '0x5ff0f14d577166f9ede3d9568a423166be61ea9d')

print('\nBuscando estado atual da conta (via API Hyperliquid)...')
state = _http_post_json(_HL_INFO_URL, {"type": "clearinghouseState", "user": wallet})
print('Estado retornado:')
print(state)

# Verificar se coin existe nas assetPositions
coin = 'SOL'
found = False
if state and isinstance(state, dict):
    for pos in state.get('assetPositions', []):
        p = pos.get('position', {})
        if p.get('coin') == coin:
            found = True
            break

print(f'Posição {coin} encontrada no exchange? {found}')

if not found:
    print('Simulação completa: a rotina deve marcar posição como fechada e retornar sucesso.')
else:
    print('Simulação: posição ainda existe no exchange.')
