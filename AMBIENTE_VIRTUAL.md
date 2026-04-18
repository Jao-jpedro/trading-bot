# 🐍 Ambiente Virtual Python - Guia Rápido

## ✅ Ambiente Virtual Criado com Sucesso!

**Localização:** `/Users/joaoreis/Documents/Trading/.venv`  
**Python Version:** 3.9.6  
**Status:** ✅ Ativado e Configurado

---

## 📦 Pacotes Instalados

| Pacote | Versão | Uso |
|--------|--------|-----|
| ccxt | 4.5.49 | Conexão com exchanges (Binance, Hyperliquid) |
| pandas | 2.3.3 | Manipulação de dados históricos |
| numpy | 2.0.2 | Cálculos matemáticos (RSI, médias) |
| gspread | 6.2.1 | Integração Google Sheets |
| google-auth | 2.49.2 | Autenticação Google APIs |
| requests | 2.32.5 | Requisições HTTP |
| python-dotenv | 1.2.1 | Carregar variáveis .env |

**Total de pacotes:** 42 (incluindo dependências)

---

## 🚀 Como Usar

### Ativar o Ambiente Virtual

**Opção 1: Script automático**
```bash
source activate.sh
```

**Opção 2: Manual**
```bash
source .venv/bin/activate
```

### Desativar
```bash
deactivate
```

### Verificar Status
```bash
# Ver qual Python está sendo usado
which python

# Ver pacotes instalados
pip list

# Ver informações do ambiente
python --version
```

---

## 🛠️ Comandos Úteis

### Executar Scripts

```bash
# Ativar ambiente primeiro
source .venv/bin/activate

# Testar Google Sheets
python test_sheets.py

# Rodar bot de trading
python trading.py
```

### Gerenciar Pacotes

```bash
# Instalar novo pacote
pip install nome_do_pacote

# Atualizar pacote
pip install --upgrade nome_do_pacote

# Remover pacote
pip uninstall nome_do_pacote

# Listar pacotes desatualizados
pip list --outdated

# Exportar dependências
pip freeze > requirements.txt
```

---

## 📁 Estrutura do Projeto

```
Trading/
├── .venv/                      ← Ambiente virtual (não commitar)
├── API.json                    ← Credenciais Google (não commitar)
├── trading.py                  ← Bot principal
├── test_sheets.py              ← Teste Google Sheets
├── requirements.txt            ← Dependências
├── activate.sh                 ← Script de ativação
├── .env                        ← Variáveis de ambiente (criar)
├── .env.example                ← Template de .env
├── .gitignore                  ← Arquivos ignorados pelo Git
├── README.md                   ← Documentação principal
├── IMPLEMENTACAO.md            ← Resumo de mudanças
└── SETUP_GOOGLE_CLOUD.md       ← Guia Google Cloud
```

---

## ⚠️ Avisos Importantes

### 1. Python 3.9 End of Life
```
FutureWarning: You are using a Python version 3.9 past its end of life
```

**Solução (opcional):** Atualizar para Python 3.10+
```bash
# Verificar versão do Python instalada
python3 --version

# Se tiver Python 3.10+, recriar ambiente
rm -rf .venv
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. OpenSSL Warning
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```

**Solução:** Atualizar macOS ou instalar OpenSSL via Homebrew
```bash
brew install openssl
```

**Nota:** Esses avisos **não impedem** o funcionamento do bot!

---

## 🎯 Status Atual

### ✅ Funcionando
- [x] Ambiente virtual criado
- [x] Todas as dependências instaladas
- [x] Arquivo API.json detectado
- [x] Credenciais Google carregadas

### ⚠️ Pendente
- [ ] Ativar Google Drive API
- [ ] Ativar Google Sheets API
- [ ] Criar/compartilhar planilha
- [ ] Configurar arquivo .env

Ver: `SETUP_GOOGLE_CLOUD.md` para próximos passos

---

## 🔄 Workflow Diário

```bash
# 1. Entrar na pasta
cd /Users/joaoreis/Documents/Trading

# 2. Ativar ambiente
source .venv/bin/activate

# 3. Rodar bot
python trading.py

# 4. Quando terminar
deactivate
```

---

## 🐛 Troubleshooting

### "command not found: python"
**Solução:** Use `python3` ou ative o ambiente virtual

### "No module named 'ccxt'"
**Solução:** Ativar ambiente virtual primeiro
```bash
source .venv/bin/activate
```

### "Permission denied"
**Solução:** Dar permissão de execução
```bash
chmod +x activate.sh
```

### Reinstalar tudo do zero
```bash
# Remover ambiente
rm -rf .venv

# Recriar
python3 -m venv .venv

# Ativar
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 📊 Próximos Passos

1. ✅ ~~Criar ambiente virtual~~ **CONCLUÍDO**
2. ✅ ~~Instalar dependências~~ **CONCLUÍDO**
3. ⚠️ Ativar APIs no Google Cloud (ver `SETUP_GOOGLE_CLOUD.md`)
4. ⚠️ Criar planilha e compartilhar
5. ⚠️ Configurar arquivo `.env`
6. ⚠️ Testar com `python test_sheets.py`
7. ⚠️ Rodar bot com `python trading.py`

---

**Criado em:** 18/04/2026  
**Última atualização:** 18/04/2026  
**Status:** ✅ Operacional
