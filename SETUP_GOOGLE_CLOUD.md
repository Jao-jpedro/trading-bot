# 🔧 Configuração Google Cloud - Passo a Passo

## ⚠️ Erro Detectado

```
Google Drive API has not been used in project 475137082592 before or it is disabled
```

## ✅ Solução

Você precisa **ativar 2 APIs** no Google Cloud Console:

### **Passo 1: Ativar Google Drive API**

1. Acesse: https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=475137082592

2. Clique no botão **"ATIVAR"** (Enable)

3. Aguarde alguns segundos até a ativação

### **Passo 2: Ativar Google Sheets API**

1. Acesse: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=475137082592

2. Clique no botão **"ATIVAR"** (Enable)

3. Aguarde alguns segundos até a ativação

---

## 🔗 Links Rápidos

### Seu Projeto: `mudar-1572192250313`
ID do Projeto: `475137082592`

**Painel do Projeto:**
https://console.cloud.google.com/home/dashboard?project=mudar-1572192250313

**APIs & Services:**
https://console.cloud.google.com/apis/dashboard?project=mudar-1572192250313

**Service Account (bot-trader):**
https://console.cloud.google.com/iam-admin/serviceaccounts?project=mudar-1572192250313

**Email da Service Account:**
```
bot-trader@mudar-1572192250313.iam.gserviceaccount.com
```

---

## 📋 Checklist Completo

### ✅ Já Configurado
- [x] Projeto criado: `mudar-1572192250313`
- [x] Service Account criada: `bot-trader`
- [x] Credenciais JSON baixadas: `API.json`
- [x] Arquivo na pasta do projeto

### ⚠️ Falta Fazer
- [ ] Ativar **Google Drive API**
- [ ] Ativar **Google Sheets API**
- [ ] Criar planilha no Google Sheets
- [ ] Compartilhar planilha com: `bot-trader@mudar-1572192250313.iam.gserviceaccount.com`
- [ ] Dar permissão de **Editor** (não Viewer!)

---

## 🚀 Depois de Ativar as APIs

### Aguarde 2-3 minutos e teste novamente:

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Testar conexão
python test_sheets.py
```

### Se tudo funcionar, você verá:

```
✅ Credenciais carregadas com sucesso
✅ Planilha 'Trading Bot' encontrada
✅ Conectado à aba: Sheet1
✅ Cabeçalhos criados
✅ Linha de teste adicionada
🎉 Google Sheets funcionando perfeitamente!
```

---

## 🆘 Problemas Comuns

### 1. "Spreadsheet not found"
**Causa:** Planilha não compartilhada com a service account  
**Solução:** 
1. Abra a planilha no Google Sheets
2. Clique em "Compartilhar"
3. Adicione: `bot-trader@mudar-1572192250313.iam.gserviceaccount.com`
4. Permissão: **Editor**

### 2. "Permission denied"
**Causa:** Service account tem permissão errada  
**Solução:** Mudar de "Viewer" para "Editor"

### 3. "API not enabled"
**Causa:** APIs não foram ativadas  
**Solução:** Seguir Passo 1 e 2 acima

### 4. "Invalid credentials"
**Causa:** Arquivo API.json incorreto ou corrompido  
**Solução:** Baixar novamente do Google Cloud Console

---

## 📝 Notas Importantes

- As APIs são **gratuitas** para uso normal do bot
- Não há custo para ativar
- A ativação é instantânea mas pode levar 2-3 min para propagar
- Você só precisa fazer isso **uma vez**

---

## ✅ Próximos Passos Após Configuração

1. **Criar planilha** no Google Sheets
2. **Compartilhar** com service account
3. **Configurar nome** no `.env`:
   ```env
   GOOGLE_SHEET_NAME=Trading Bot
   ```
4. **Testar** com: `python test_sheets.py`
5. **Rodar bot**: `python trading.py`

---

**Data:** 18/04/2026  
**Status:** Aguardando ativação das APIs
