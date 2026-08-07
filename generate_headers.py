#!/usr/bin/env python3
"""
Gera cabeçalhos para copiar manualmente na planilha Base_logs
"""

def generate_headers():
    """Gera os 36 cabeçalhos formatados para copiar/colar"""
    
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
    
    print("=" * 80)
    print("📊 CABEÇALHOS PARA PLANILHA BASE_LOGS (36 COLUNAS)")
    print("=" * 80)
    print()
    print("📋 INSTRUÇÕES:")
    print("   1. Selecione e copie TODO o texto abaixo")
    print("   2. Abra sua planilha Base_logs no Google Sheets")
    print("   3. Clique na célula A1")
    print("   4. Cole (Ctrl+V ou Cmd+V)")
    print("   5. Os cabeçalhos serão distribuídos nas colunas A até AJ")
    print()
    print("=" * 80)
    print()
    
    # Formato separado por TAB (para colar no Sheets)
    headers_tab = '\t'.join(headers)
    print(headers_tab)
    
    print()
    print("=" * 80)
    print()
    
    # Mostrar estrutura
    print("📊 ESTRUTURA:")
    print()
    
    sections = [
        ("A-G", "Identificação", 7, headers[0:7]),
        ("H-L", "Contexto/Indicadores", 5, headers[7:12]),
        ("M-Q", "Execução", 5, headers[12:17]),
        ("R-X", "Gestão de Risco", 7, headers[17:24]),
        ("Y-AD", "Resultados", 6, headers[24:30]),
        ("AE-AJ", "Análise", 6, headers[30:36])
    ]
    
    for cols, name, count, section_headers in sections:
        print(f"   {cols} ({count} colunas) - {name}:")
        for i, h in enumerate(section_headers, 1):
            print(f"      {i}. {h}")
        print()
    
    print(f"✅ Total: {len(headers)} colunas")
    print()
    print("=" * 80)
    print()
    print("💡 DICA: Após colar, formate a linha 1:")
    print("   - Negrito")
    print("   - Centralizar texto")
    print("   - Cor de fundo cinza")
    print("   - Congelar linha (Ver → Congelar → 1 linha)")
    print()
    
    # Gerar também em formato CSV
    print("=" * 80)
    print("📄 FORMATO CSV (alternativo):")
    print("=" * 80)
    print()
    headers_csv = ','.join(headers)
    print(headers_csv)
    print()

if __name__ == "__main__":
    generate_headers()
