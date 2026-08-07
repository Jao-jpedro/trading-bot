#!/usr/bin/env python3
"""Teste de validação do cálculo de amount_usd para TP1/TP2/SL"""

# Cenário de exemplo
entry_price = 72.3340
amount_coins = 0.2935  # SOL comprados
leverage = 5
capital_investido = 21.09  # USD investidos (exemplo)

# Após TP1 atingido
current_price_tp1 = 78.7315
amount_remaining = amount_coins  # ainda não vendeu nada

print("=" * 70)
print("TESTE DE CÁLCULO - TP1 (50% da posição)")
print("=" * 70)
print(f"Entrada: {amount_coins:.4f} SOL @ ${entry_price:.4f}")
print(f"Capital investido: ${capital_investido:.2f}")
print(f"Leverage: {leverage}x")
print(f"Valor notional da posição: ${amount_coins * entry_price:.2f}")
print()

# TP1: Vender 50% da posição
amount_to_sell_tp1 = amount_remaining * 0.5
print(f"TP1 - Preço atual: ${current_price_tp1:.4f}")
print(f"TP1 - Quantidade a vender: {amount_to_sell_tp1:.4f} SOL (50%)")
print()

# Cálculo ERRADO (antigo)
amount_usd_wrong = amount_to_sell_tp1 * current_price_tp1
print(f"❌ CÁLCULO ERRADO (antigo):")
print(f"   amount_usd = {amount_to_sell_tp1:.4f} * {current_price_tp1:.4f} = ${amount_usd_wrong:.2f}")
print(f"   create_market_order vai multiplicar por {leverage}x:")
print(f"   notional = ${amount_usd_wrong:.2f} * {leverage} = ${amount_usd_wrong * leverage:.2f}")
print(f"   quantidade = ${amount_usd_wrong * leverage:.2f} / ${current_price_tp1:.4f} = {(amount_usd_wrong * leverage) / current_price_tp1:.4f} SOL")
print(f"   ⚠️ Vai tentar vender {(amount_usd_wrong * leverage) / current_price_tp1:.4f} SOL (mais que os {amount_to_sell_tp1:.4f} desejados!)")
print()

# Cálculo CORRETO (novo)
amount_usd_correct = (amount_to_sell_tp1 * current_price_tp1) / leverage
print(f"✅ CÁLCULO CORRETO (novo):")
print(f"   amount_usd = ({amount_to_sell_tp1:.4f} * {current_price_tp1:.4f}) / {leverage} = ${amount_usd_correct:.2f}")
print(f"   create_market_order vai multiplicar por {leverage}x:")
print(f"   notional = ${amount_usd_correct:.2f} * {leverage} = ${amount_usd_correct * leverage:.2f}")
print(f"   quantidade = ${amount_usd_correct * leverage:.2f} / ${current_price_tp1:.4f} = {(amount_usd_correct * leverage) / current_price_tp1:.4f} SOL")
print(f"   ✅ Vai vender exatamente {(amount_usd_correct * leverage) / current_price_tp1:.4f} SOL (correto!)")
print()

print("=" * 70)
print("CONCLUSÃO:")
print("=" * 70)
print(f"✅ Com o cálculo correto, TP1 vende 50% ({amount_to_sell_tp1:.4f} SOL)")
print(f"✅ Restam 50% ({amount_remaining - amount_to_sell_tp1:.4f} SOL) para TP2")
print(f"❌ Com o cálculo errado, TP1 venderia {(amount_usd_wrong * leverage) / current_price_tp1:.4f} SOL")
print(f"   (isso seria {((amount_usd_wrong * leverage) / current_price_tp1) / amount_coins * 100:.0f}% da posição!)")
