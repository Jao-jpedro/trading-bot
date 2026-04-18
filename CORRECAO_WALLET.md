# 🔧 CORREÇÃO - Variáveis de Ambiente no Render

## ✅ Configuração CORRETA

Atualize as variáveis de ambiente no Render com os seguintes valores:

```
WALLET_ADDRESS=0x0effe318659DE1cD2B2564A4A75e43186Ac06337
HYPERLIQUID_PRIVATE_KEY=0x40a76704827d33be22ee9083bf2b0713e91a6372616c1468e9bd16430adbe645
HYPERLIQUID_SUBACCOUNT=0x5ff0f14d577106f9ede3d9568a423166be61ea9d
```

## 📝 Explicação:

- **WALLET_ADDRESS**: Endereço derivado da private key que **assina** as transações
  - Valor: `0x0effe318659DE1cD2B2564A4A75e43186Ac06337`
  
- **HYPERLIQUID_PRIVATE_KEY**: Chave privada usada para assinar
  - Valor: `0x40a76704827d33be22ee9083bf2b0713e91a6372616c1468e9bd16430adbe645`
  
- **HYPERLIQUID_SUBACCOUNT**: Vault onde as operações acontecem (não muda)
  - Valor: `0x5ff0f14d577106f9ede3d9568a423166be61ea9d`

## 🎯 Como funciona:

1. Bot usa `WALLET_ADDRESS` (0x0effe318...) para **assinar** as transações
2. CCXT usa `HYPERLIQUID_PRIVATE_KEY` para fazer a assinatura criptográfica
3. Operações são executadas na **vault** (0x5ff0f14d...)

## ⚠️ IMPORTANTE:

A carteira `0x08183aa09eF03Cf8475D909F507606F5044cBdAB` que estava configurada **NÃO** corresponde à private key que você tem. Por isso o erro "User or API Wallet does not exist" acontecia.

## 🚀 Próximos Passos:

1. Acesse o painel do Render
2. Vá em **Environment Variables**
3. Atualize apenas o `WALLET_ADDRESS` para: `0x0effe318659DE1cD2B2564A4A75e43186Ac06337`
4. Salve as alterações
5. O Render vai fazer redeploy automático
6. Bot deve funcionar corretamente agora! ✅
