# 🚨 ERRO: "User or API Wallet does not exist"

**Erro:**
```
User or API Wallet 0x95cf910f947a5be26bc7c18f8b8048185126b4e9 does not exist
```

---

## 🔍 DIAGNÓSTICO

O bot está tentando operar, mas a **carteira API não existe na Hyperliquid**.

### Configuração atual:
```
WALLET_ADDRESS = 0x95cf910f947a5be26bc7c18f8b8048185126b4e9  ← API Wallet (NÃO EXISTE)
HYPERLIQUID_SUBACCOUNT = 0x5ff0f14d577166f9ede3d9568a423166be61ea9d  ← Vault
```

---

## ✅ SOLUÇÃO

Você tem **2 opções**:

### **OPÇÃO 1: Registrar a API Wallet na Hyperliquid** (Recomendado se você quer isolar)

1. Acesse https://app.hyperliquid.xyz
2. Conecte a carteira `0x95cf910f947a5be26bc7c18f8b8048185126b4e9`
3. Faça um depósito mínimo ($1) para "ativar" a conta
4. A vault já existe, então depois você pode transferir fundos

**Problema:** Essa carteira provavelmente não tem fundos e você não tem acesso a ela diretamente.

---

### **OPÇÃO 2: Usar sua carteira principal** (Mais Fácil)

Se você tem uma carteira que **já usa** na Hyperliquid com fundos:

1. **Encontre o endereço da sua carteira principal:**
   - Aquela que você usa no MetaMask
   - Que já tem fundos na Hyperliquid
   - Exemplo: `0xSUACARTEIRA...`

2. **Atualize o `.env` no Render:**

```bash
# Use SUA carteira principal (aquela com fundos)
WALLET_ADDRESS=0xSUACARTEIRA...  ← A que você usa normalmente
HYPERLIQUID_PRIVATE_KEY=0x...     ← A private key DESSA carteira

# Vault continua a mesma
HYPERLIQUID_SUBACCOUNT=0x5ff0f14d577166f9ede3d9568a423166be61ea9d
```

3. **Verificar se a vault tem fundos:**
   - Acesse https://app.hyperliquid.xyz
   - Conecte sua carteira principal
   - Vá em "Vault" ou "Subaccounts"
   - Confirme que `0x5ff0...ea9d` tem saldo ($13.73)

---

### **OPÇÃO 3: Operar direto na carteira (sem vault)** (Não Recomendado)

Se você não quer usar vault:

```bash
WALLET_ADDRESS=0xSUACARTEIRA...  ← Carteira com fundos
HYPERLIQUID_PRIVATE_KEY=0x...     ← Private key dessa carteira
# HYPERLIQUID_SUBACCOUNT=  ← REMOVER esta linha
```

⚠️ **Problema:** O código agora EXIGE vault. Precisaria modificar o código.

---

## 🎯 RECOMENDAÇÃO

**Use a OPÇÃO 2:**

1. Descubra qual é **SUA carteira principal** (a que você usa no MetaMask)
2. Configure `WALLET_ADDRESS` com o endereço dela
3. Configure `HYPERLIQUID_PRIVATE_KEY` com a private key dela
4. Mantenha `HYPERLIQUID_SUBACCOUNT` como está

**Como obter sua carteira e private key:**

### MetaMask:
```
1. Abrir MetaMask
2. Clicar no ícone da conta (topo direito)
3. "Account details"
4. Copiar endereço (WALLET_ADDRESS)
5. "Export Private Key" (HYPERLIQUID_PRIVATE_KEY)
```

---

## 🔧 Verificar Configuração

Após ajustar, rode localmente:

```bash
python trading.py
```

**Output esperado:**
```
🏦 Configurando operação na subconta (vault): 0x5ff0...
🔑 Carteira principal (assinatura): 0xSUACARTEIRA...  ← Deve ser SUA carteira
✅ Conexões estabelecidas
💰 Saldo disponível: $13.73  ← Deve mostrar saldo da vault
```

Se mostrar `$0.00`, a vault não tem fundos ou está configurada errada.

---

## 📝 Atualizar Render

Depois de testar localmente:

1. Acesse: https://dashboard.render.com
2. Seu serviço: trading-bot
3. Environment → Edit
4. Atualizar:
   - `WALLET_ADDRESS` = Sua carteira principal
   - `HYPERLIQUID_PRIVATE_KEY` = Private key da sua carteira
5. Save Changes
6. Render vai reiniciar automaticamente

---

## ⚠️ IMPORTANTE

**Nunca compartilhe:**
- ❌ Private key
- ❌ Credenciais Google (base64)
- ❌ Seeds de carteiras

**Sempre verifique:**
- ✅ Carteira existe na Hyperliquid
- ✅ Tem fundos (mínimo $10)
- ✅ Vault está ativa
- ✅ Private key corresponde ao endereço

---

**Qual opção você quer seguir? Precisa de ajuda para encontrar sua carteira principal?**
