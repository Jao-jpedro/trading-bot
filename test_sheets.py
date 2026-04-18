#!/usr/bin/env python3
"""
Script de teste para verificar conexão com Google Sheets
"""

import os
import sys

def test_imports():
    """Testa se todas as bibliotecas estão instaladas"""
    print("🔍 Verificando bibliotecas...")
    
    missing = []
    
    try:
        import ccxt
        print("✅ ccxt")
    except ImportError:
        missing.append("ccxt")
        print("❌ ccxt")
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError:
        missing.append("pandas")
        print("❌ pandas")
    
    try:
        import numpy
        print("✅ numpy")
    except ImportError:
        missing.append("numpy")
        print("❌ numpy")
    
    try:
        import gspread
        print("✅ gspread")
    except ImportError:
        missing.append("gspread")
        print("❌ gspread")
    
    try:
        from google.oauth2.service_account import Credentials
        print("✅ google-auth")
    except ImportError:
        missing.append("google-auth")
        print("❌ google-auth")
    
    if missing:
        print(f"\n⚠️  Bibliotecas faltando: {', '.join(missing)}")
        print(f"💡 Instale com: pip install {' '.join(missing)}")
        return False
    
    print("\n✅ Todas as bibliotecas instaladas!")
    return True

def test_google_sheets():
    """Testa conexão com Google Sheets"""
    print("\n🔍 Verificando Google Sheets...")
    
    # Verificar arquivo API.json
    if not os.path.exists("API.json"):
        print("❌ Arquivo API.json não encontrado")
        print("💡 Certifique-se de que o arquivo API.json está na pasta do projeto")
        return False
    
    print("✅ Arquivo API.json encontrado")
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Configurar credenciais
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file("API.json", scopes=scopes)
        client = gspread.authorize(creds)
        
        print("✅ Credenciais carregadas com sucesso")
        
        # Tentar abrir planilha existente
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Base_logs")
        
        try:
            spreadsheet = client.open(sheet_name)
            print(f"✅ Planilha '{sheet_name}' encontrada")
            worksheet = spreadsheet.sheet1
            print(f"✅ Conectado à aba: {worksheet.title}")
        except gspread.SpreadsheetNotFound:
            print(f"⚠️  Planilha '{sheet_name}' não encontrada")
            print(f"💡 Criando planilha de teste...")
            spreadsheet = client.create(sheet_name)
            worksheet = spreadsheet.sheet1
            print(f"✅ Planilha de teste criada: {sheet_name}")
            print(f"💡 Compartilhe com você mesmo para visualizar")
        
        # Testar escrita
        print("\n🔍 Testando escrita na planilha...")
        
        # Criar cabeçalhos
        headers = ['ID', 'Data', 'Hora', 'Preço', 'Cripto', 'Operação', 'Tipo de Operação', 'RSI', 'Motivo']
        worksheet.update('A1:I1', [headers])
        print("✅ Cabeçalhos criados")
        
        # Adicionar linha de teste
        from datetime import datetime
        now = datetime.now()
        test_id = f"SOL_{now.strftime('%Y%m%d_%H%M%S')}"
        test_row = [
            test_id,
            now.strftime("%d/%m/%Y"),
            now.strftime("%H:%M:%S"),
            "145.2500",
            "SOL",
            "LONG",
            "Compra (TESTE)",
            "18.45",
            "RSI sobrevendido (TESTE)"
        ]
        worksheet.append_row(test_row)
        print("✅ Linha de teste adicionada")
        
        print(f"\n🎉 Google Sheets funcionando perfeitamente!")
        print(f"📊 Acesse: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🧪 TESTE DE INTEGRAÇÃO GOOGLE SHEETS")
    print("=" * 60)
    print()
    
    # Teste 1: Bibliotecas
    if not test_imports():
        print("\n❌ Instale as bibliotecas primeiro:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Teste 2: Google Sheets
    if not test_google_sheets():
        print("\n❌ Erro na conexão com Google Sheets")
        print("\n📋 Checklist:")
        print("  1. Arquivo API.json na pasta do projeto")
        print("  2. APIs ativadas no Google Cloud (Sheets + Drive)")
        print("  3. Planilha compartilhada com a service account")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)

if __name__ == "__main__":
    main()
