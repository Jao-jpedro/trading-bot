#!/usr/bin/env python3
"""
Teste: Verificar se sua private key corresponde à carteira mãe
"""

from eth_account import Account

print("=" * 80)
print("🔐 TESTE DE CORRESPONDÊNCIA")
print("=" * 80)
print()

# Sua carteira mãe (do MetaMask)
carteira_mae = "0x08183aa09eF03Cf8475D909F507606F5044cBdAB"

# Private key que você configurou
private_key = "0x8e4dd7dcd6ec715a4f44bc81e835407e8cd7a9335e21c8c74fcfe545e3e9d49d"

# Derivar endereço da private key
account = Account.from_key(private_key)
endereco_derivado = account.address

print(f"📝 Carteira mãe esperada:")
print(f"   {carteira_mae}")
print()
print(f"🔐 Endereço derivado da private key configurada:")
print(f"   {endereco_derivado}")
print()

if endereco_derivado.lower() == carteira_mae.lower():
    print("✅ CORRETO! Private key corresponde à carteira mãe")
    print()
    print("🎉 Configuração está correta!")
    print("   Pode usar no Render sem modificações")
else:
    print("❌ INCORRETO! Private key NÃO corresponde à carteira mãe")
    print()
    print("🔧 PROBLEMA:")
    print("   A private key configurada é de outro endereço")
    print(f"   Ela pertence a: {endereco_derivado}")
    print()
    print("✅ SOLUÇÃO:")
    print("   1. Abra MetaMask")
    print(f"   2. Selecione a carteira: {carteira_mae}")
    print("   3. Account Details → Export Private Key")
    print("   4. Use ESSA private key no Render")

print()
print("=" * 80)
print("💡 LEMBRE-SE:")
print("   WALLET_ADDRESS = Carteira mãe (assina transações)")
print("   HYPERLIQUID_PRIVATE_KEY = Private key DA CARTEIRA MÃE")
print("   HYPERLIQUID_SUBACCOUNT = Vault (onde bot opera)")
print("=" * 80)
