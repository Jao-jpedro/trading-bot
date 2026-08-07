#!/usr/bin/env python3
"""
Script para atualizar cabeçalhos da planilha Base_logs
Adiciona as 36 colunas do sistema de dados quantitativos
"""

import gspread
from google.oauth2.service_account import Credentials
import os

def update_base_logs_headers():
    """Atualiza os cabeçalhos da planilha Base_logs"""
    
    print("🔧 ATUALIZANDO PLANILHA BASE_LOGS")
    print("=" * 60)
    
    # Configuração - usar API.json
    credentials_file = "API.json"
    
    if not os.path.exists(credentials_file):
        print(f"❌ Arquivo de credenciais não encontrado: {credentials_file}")
        print(f"\n💡 SOLUÇÃO:")
        print(f"   Certifique-se de que o arquivo API.json está na pasta")
        print(f"   Caminho esperado: /Users/joaoreis/Documents/Trading/API.json")
        return False
    
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Base_logs")
    
    print(f"✅ Credenciais encontradas: {credentials_file}")
    print(f"✅ Nome da planilha: {sheet_name}")
    
    # Conectar ao Google Sheets
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes
        )
        
        client = gspread.authorize(creds)
        print(f"✅ Conectado ao Google Sheets")
        
    except Exception as e:
        print(f"❌ Erro conectando ao Google Sheets: {e}")
        return False
    
    # Abrir planilha
    try:
        spreadsheet = client.open(sheet_name)
        print(f"✅ Planilha aberta: {sheet_name}")
        
        worksheet = spreadsheet.sheet1
        print(f"✅ Aba encontrada: {worksheet.title}")
        
    except gspread.SpreadsheetNotFound:
        print(f"❌ Planilha '{sheet_name}' não encontrada")
        print(f"   Certifique-se de que a planilha existe e está compartilhada")
        return False
    
    # Verificar dados existentes
    try:
        existing_data = worksheet.get_all_values()
        num_rows = len(existing_data)
        
        if num_rows > 0:
            print(f"⚠️  ATENÇÃO: Planilha contém {num_rows} linhas de dados")
            print(f"   Primeira linha atual: {existing_data[0][:5]}...")
            
            response = input("\n❓ Deseja substituir os cabeçalhos? (s/n): ")
            if response.lower() != 's':
                print("❌ Operação cancelada pelo usuário")
                return False
        
    except Exception as e:
        print(f"⚠️  Erro verificando dados existentes: {e}")
    
    # Criar cabeçalhos completos (36 colunas)
    headers = [
        # Identificação (7 colunas)
        'ID', 'Data', 'Hora', 'Timestamp', 'Cripto', 'Operação', 'Tipo',
        
        # Contexto de Entrada - Indicadores (5 colunas)
        'RSI', 'EMA_Trend', 'ATR', 'ATR_Percentil', 'Volume_Ratio',
        
        # Execução - Preços e Posição (5 colunas)
        'Preço_Entrada', 'Slippage_%', 'Tamanho_Posição_USD', 'Tamanho_Posição_Moedas', 'Leverage',
        
        # Gestão de Risco - Stops e Targets (7 colunas)
        'Stop_Loss_Preço', 'Stop_Loss_%', 'Take_Profit_1_Preço', 'Take_Profit_1_%',
        'Take_Profit_2_Preço', 'Take_Profit_2_%', 'Risk_Reward_Ratio',
        
        # Resultados - Saída e P&L (6 colunas)
        'Preço_Saída', 'P&L_USD', 'P&L_%', 'Tempo_Trade_Min', 'MFE_%', 'MAE_%',
        
        # Análise - Classificação e Qualidade (6 colunas)
        'Mercado_Tendência', 'Mercado_Volatilidade', 'Qualidade_Entrada', 'Motivo', 'Observações'
    ]
    
    print(f"\n📊 ESTRUTURA DOS CABEÇALHOS:")
    print(f"   Total de colunas: {len(headers)}")
    print(f"   Intervalo: A1:AJ1")
    
    # Atualizar cabeçalhos
    try:
        worksheet.update('A1:AJ1', [headers], value_input_option='USER_ENTERED')
        print(f"✅ Cabeçalhos atualizados com sucesso!")
        
        # Formatar cabeçalho (negrito)
        try:
            worksheet.format('A1:AJ1', {
                'textFormat': {'bold': True},
                'horizontalAlignment': 'CENTER',
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            print(f"✅ Formatação aplicada (negrito + fundo cinza)")
        except Exception as e:
            print(f"⚠️  Formatação não aplicada: {e}")
        
        # Congelar primeira linha
        try:
            worksheet.freeze(rows=1)
            print(f"✅ Primeira linha congelada")
        except Exception as e:
            print(f"⚠️  Congelamento não aplicado: {e}")
        
    except Exception as e:
        print(f"❌ Erro atualizando cabeçalhos: {e}")
        return False
    
    # Resumo final
    print(f"\n" + "=" * 60)
    print(f"✅ PLANILHA ATUALIZADA COM SUCESSO!")
    print(f"=" * 60)
    print(f"\n📋 ESTRUTURA IMPLEMENTADA:")
    print(f"   1️⃣  Identificação (A-G): 7 colunas")
    print(f"   2️⃣  Contexto/Indicadores (H-L): 5 colunas")
    print(f"   3️⃣  Execução (M-Q): 5 colunas")
    print(f"   4️⃣  Gestão de Risco (R-X): 7 colunas")
    print(f"   5️⃣  Resultados (Y-AD): 6 colunas")
    print(f"   6️⃣  Análise (AE-AJ): 6 colunas")
    print(f"\n📊 Total: 36 colunas de dados quantitativos")
    print(f"\n🔗 Acesse: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")
    
    return True

if __name__ == "__main__":
    try:
        success = update_base_logs_headers()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
