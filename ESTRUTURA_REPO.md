# 📦 Estrutura do Repositório

## ✅ Arquivos Incluídos no GitHub

### Código Principal
- `trading.py` - Bot de trading principal
- `test_sheets.py` - Script de teste Google Sheets

### Configuração
- `requirements.txt` - Dependências Python
- `.env.example` - Template de variáveis de ambiente
- `.gitignore` - Proteção de arquivos sensíveis
- `activate.sh` - Script de ativação do ambiente virtual

### Documentação
- `README.md` - Documentação principal
- `AMBIENTE_VIRTUAL.md` - Guia do ambiente Python
- `SETUP_GOOGLE_CLOUD.md` - Configuração Google Cloud
- `IMPLEMENTACAO.md` - Resumo de implementações
- `MUDANCAS_SISTEMA.md` - Mudanças no sistema de vendas
- `SISTEMA_ID.md` - Sistema de IDs para vincular trades
- `TESTE_SUCESSO.md` - Resultados dos testes

---

## ❌ Arquivos NÃO Incluídos (Protegidos)

### Credenciais (Nunca commitar!)
- ❌ `API.json` - Credenciais Google Cloud
- ❌ `.env` - Variáveis de ambiente reais
- ❌ `.env.dca` - Configurações específicas

### Dados Operacionais
- ❌ `dca_state.json` - Estado do bot
- ❌ `*.log` - Logs de execução
- ❌ Arquivos de backup

### Ambiente Python
- ❌ `.venv/` - Ambiente virtual
- ❌ `__pycache__/` - Cache Python
- ❌ `*.pyc` - Arquivos compilados

---

## 🚀 Como Usar Este Repositório

1. **Clone o repositório:**
   ```bash
   git clone <seu-repo>
   cd trading-bot
   ```

2. **Configure o ambiente:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure credenciais:**
   ```bash
   cp .env.example .env
   # Edite .env com suas chaves
   # Adicione seu API.json do Google Cloud
   ```

4. **Execute:**
   ```bash
   python test_sheets.py  # Testar Google Sheets
   python trading.py      # Rodar bot
   ```

---

## 🔒 Segurança

**NUNCA commite:**
- Chaves de API
- Senhas
- Arquivos .env com dados reais
- API.json do Google Cloud
- Logs com informações sensíveis

**Sempre use:**
- `.env.example` como template
- `.gitignore` configurado corretamente
- Variáveis de ambiente no Render/servidor

---

**Última atualização:** 18/04/2026
