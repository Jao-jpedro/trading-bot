# 🏦 CONFIGURAÇÃO: Bot Opera APENAS na Subconta (Vault)

**Data:** 18/04/2026  
**Status:** ✅ Configurado

---

## 🎯 Mudança Implementada

**ANTES:**
- Bot podia operar na carteira principal OU na subconta
- HYPERLIQUID_SUBACCOUNT era opcional

**DEPOIS:**
- Bot SEMPRE opera na subconta (vault)
- HYPERLIQUID_SUBACCOUNT é **OBRIGATÓRIA**
- Carteira principal só assina transações

---

## 🔑 Variáveis de Ambiente Necessárias

```bash
# Carteira principal (só para assinatura)
WALLET_ADDRESS=0x1234...

# Chave privada da carteira principal
HYPERLIQUID_PRIVATE_KEY=0xabcd...

# ⚠️ OBRIGATÓRIA: Subconta/Vault onde o bot opera
HYPERLIQUID_SUBACCOUNT=0x5678...
```

---

## 📊 Como Funciona

```
┌─────────────────────────────────────┐
│  WALLET_ADDRESS                     │  ← Carteira principal
│  (0x1234...)                        │     (apenas assina)
│                                     │
│  + HYPERLIQUID_PRIVATE_KEY          │
└─────────────┬───────────────────────┘
              │
              │ Assina transações
              ▼
┌─────────────────────────────────────┐
│  HYPERLIQUID_SUBACCOUNT (VAULT)     │  ← Bot opera aqui!
│  (0x5678...)                        │
│                                     │
│  • Saldo: $13.73                    │
│  • Trades executados aqui           │
│  • Isolado da carteira principal    │
└─────────────────────────────────────┘
```

---

## ✅ Benefícios

### 1. **Segurança**
- Fundos isolados na vault
- Carteira principal não exposta
- Limita risco em caso de problema

### 2. **Organização**
- Bot opera em conta separada
- Fácil auditar performance
- Não mistura com trades manuais

### 3. **Controle**
- Pode depositar/sacar da vault
- Desabilitar vault sem afetar carteira principal
- Múltiplos bots em vaults diferentes

---

## 🔧 Código Modificado

### ExchangeConnector.__init__() (linha ~647)

```python
# ANTES:
if vault_address:
    self.hyperliquid.options['vaultAddress'] = vault_address
    log(f"🏦 Usando subconta (vault): {vault_address}", "INFO")

self.wallet_address = vault_address if vault_address else wallet_address

# DEPOIS:
if not vault_address:
    raise ValueError("HYPERLIQUID_SUBACCOUNT (vault/subconta) deve estar configurada")

log(f"🏦 Configurando operação na subconta (vault): {vault_address}", "INFO")
log(f"🔑 Carteira principal (assinatura): {wallet_address}", "INFO")

# SEMPRE usar subconta (obrigatório)
self.hyperliquid.options['vaultAddress'] = vault_address

# Wallet address é SEMPRE a vault (subconta)
self.wallet_address = vault_address
```

---

## 🚀 Como Usar

### 1. Criar Vault na Hyperliquid

```
1. Acesse: https://app.hyperliquid.xyz
2. Conecte sua carteira (WALLET_ADDRESS)
3. Vá em "Vault" ou "Subaccounts"
4. Crie nova vault
5. Deposite fundos na vault
6. Copie endereço da vault
```

### 2. Configurar .env

```bash
WALLET_ADDRESS=0x95cf910f947a5be26bc7c18f8b8048185126b4e9
HYPERLIQUID_PRIVATE_KEY=0x...
HYPERLIQUID_SUBACCOUNT=0x5ff0f14d577166f9ede3d9568a423166be61ea9d
```

### 3. Rodar Bot

```bash
python trading.py
```

**Output esperado:**
```
🏦 Configurando operação na subconta (vault): 0x5ff0f14d577166f9ede3d9568a423166be61ea9d
🔑 Carteira principal (assinatura): 0x95cf910f947a5be26bc7c18f8b8048185126b4e9
✅ Conexões estabelecidas: Binance (dados) + Hyperliquid (execução)
💰 Saldo disponível: $13.73
```

---

## ⚠️ Erros Comuns

### Erro 1: "HYPERLIQUID_SUBACCOUNT deve estar configurada"

**Causa:** Variável não definida no .env

**Solução:**
```bash
# Adicione no .env:
HYPERLIQUID_SUBACCOUNT=0x5ff0f14d577166f9ede3d9568a423166be61ea9d
```

### Erro 2: "Vault does not exist"

**Causa:** Endereço da vault incorreto ou vault não criada

**Solução:**
1. Verifique endereço no Hyperliquid
2. Confirme que vault está ativa
3. Deposite fundos mínimos na vault

### Erro 3: "Insufficient funds"

**Causa:** Saldo na vault muito baixo

**Solução:**
1. Depositar mais fundos na vault
2. Ou reduzir `ENTRY_CAPITAL_PCT` no código

---

## 📋 Checklist

Antes de rodar o bot:

- [ ] Vault criada na Hyperliquid
- [ ] Fundos depositados na vault (mínimo $10)
- [ ] WALLET_ADDRESS configurada (carteira principal)
- [ ] HYPERLIQUID_PRIVATE_KEY configurada
- [ ] HYPERLIQUID_SUBACCOUNT configurada (vault)
- [ ] Testado com pequena quantia primeiro

---

## 🎯 Próximos Passos

1. **Testar localmente** com a vault configurada
2. **Verificar saldo** está sendo lido da vault
3. **Executar trade teste** com capital mínimo
4. **Validar Google Sheets** registra corretamente
5. **Deploy no Render** quando validado

---

**Status:** ✅ Pronto para usar com vault obrigatória
