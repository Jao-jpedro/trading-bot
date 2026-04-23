#!/usr/bin/env python3

"""
Sistema de Trading com RSI - Long e Short
Estratégia: Baseada apenas em RSI
- LONG quando RSI < 20 (sobrevendido)
- SHORT quando RSI > 80 (sobrecomprado)
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# ===== IMPORTS ESSENCIAIS =====
import ccxt
import requests
import gspread
from google.oauth2.service_account import Credentials

# ===== CONFIGURAÇÃO DE TIMEZONE =====
UTC = timezone.utc

# ===== HYPERLIQUID API =====
_HL_INFO_URL = "https://api.hyperliquid.xyz/info"
_HTTP_TIMEOUT = 10
_SESSION = requests.Session()

# Sistema de rate limiting
_RATE_LIMIT_DELAY = 0.5  # 500ms entre requisições
_LAST_REQUEST_TIME = 0
_MAX_RETRIES = 3
_RETRY_BACKOFF = [2, 5, 10]  # Segundos de espera entre retries

def _http_post_json(url: str, payload: dict, timeout: int = _HTTP_TIMEOUT, retry_count: int = 0):
    """Helper para fazer requisições POST JSON com rate limiting e retry"""
    global _LAST_REQUEST_TIME
    
    # Rate limiting: esperar entre requisições
    current_time = time.time()
    time_since_last = current_time - _LAST_REQUEST_TIME
    if time_since_last < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - time_since_last)
    
    try:
        _LAST_REQUEST_TIME = time.time()
        r = _SESSION.post(url, json=payload, timeout=timeout)
        
        # Se receber 429 (rate limit), fazer retry com backoff exponencial
        if r.status_code == 429:
            if retry_count < _MAX_RETRIES:
                wait_time = _RETRY_BACKOFF[retry_count]
                print(f"[WARN] Rate limit atingido (429), aguardando {wait_time}s antes de retry {retry_count + 1}/{_MAX_RETRIES}...")
                time.sleep(wait_time)
                return _http_post_json(url, payload, timeout, retry_count + 1)
            else:
                print(f"[ERROR] Rate limit persistente após {_MAX_RETRIES} tentativas")
                return None
        
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if retry_count < _MAX_RETRIES and e.response and e.response.status_code >= 500:
            # Erro de servidor, tentar novamente
            wait_time = _RETRY_BACKOFF[retry_count]
            print(f"[WARN] Erro de servidor ({e.response.status_code}), aguardando {wait_time}s antes de retry...")
            time.sleep(wait_time)
            return _http_post_json(url, payload, timeout, retry_count + 1)
        print(f"[WARN] Requisição falhou: {e}")
        return None
    except Exception as e:
        print(f"[WARN] Requisição falhou: {e}")
        return None

def _hl_get_account_value(wallet: str) -> float:
    """Busca o saldo DISPONÍVEL de uma conta/vault específica via API Hyperliquid"""
    if not wallet:
        return 0.0
    data = _http_post_json(_HL_INFO_URL, {"type": "clearinghouseState", "user": wallet})
    try:
        if not data or "marginSummary" not in data:
            return 0.0
        
        margin_summary = data["marginSummary"]
        
        # Saldo disponível = accountValue - totalMarginUsed
        account_value = float(margin_summary.get("accountValue", 0))
        margin_used = float(margin_summary.get("totalMarginUsed", 0))
        
        available = account_value - margin_used
        
        return max(available, 0.0)  # Garantir que não seja negativo
    except Exception as e:
        print(f"[ERROR] Erro parseando saldo: {e}")
        return 0.0

def _hl_get_latest_fill(wallet: str, symbol: str = None):
    """Busca último preenchimento (fill) de ordem via API Hyperliquid"""
    if not wallet:
        return None
    data = _http_post_json(_HL_INFO_URL, {"type": "userFills", "user": wallet})
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    
    fills = data
    if symbol:
        fills = [f for f in fills if f.get('coin') == symbol.replace('/USDC:USDC', '')]
    
    if not fills:
        return None
    
    # Retornar fill mais recente
    return fills[0]

def _hl_get_user_state(wallet: str):
    """Busca estado completo do usuário incluindo posições abertas"""
    if not wallet:
        return None
    data = _http_post_json(_HL_INFO_URL, {"type": "clearinghouseState", "user": wallet})
    return data

def _hl_get_user_fills(wallet: str, limit: int = 100):
    """
    Busca histórico de trades (fills) do usuário via API Hyperliquid.
    Retorna lista de fills ordenados por timestamp (mais recente primeiro).
    """
    if not wallet:
        return []
    
    data = _http_post_json(_HL_INFO_URL, {
        "type": "userFills",
        "user": wallet
    })
    
    if not data or not isinstance(data, list):
        return []
    
    # Limitar quantidade de fills retornados
    return data[:limit]

# ===== LOGGING =====
_LOG_FILE = None

def setup_log_file():
    """Configura arquivo de log baseado na data/hora atual"""
    global _LOG_FILE
    if _LOG_FILE is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _LOG_FILE = f"trading_dca_{timestamp}.log"
        print(f"📝 Log será salvo em: {_LOG_FILE}")

def log(message: str, level: str = "INFO"):
    """Sistema de log simplificado"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    
    print(log_line, flush=True)
    
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
                f.flush()
        except Exception as e:
            print(f"[ERROR] Erro salvando log: {e}")

# ===== NOTIFICAÇÕES DISCORD =====
class DiscordNotifier:
    """Sistema de notificações Discord"""
    
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.enabled = bool(self.webhook_url)
        self.last_notification_time = 0
        self.cooldown_seconds = 30
    
    def send(self, title: str, message: str, color: int = 0x00ff00):
        """Envia notificação para Discord"""
        if not self.enabled:
            return False
        
        current_time = time.time()
        if current_time - self.last_notification_time < self.cooldown_seconds:
            return False
        
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(self.webhook_url, json={"embeds": [embed]}, timeout=10)
            
            if response.status_code == 204:
                self.last_notification_time = current_time
                return True
            return False
                
        except Exception as e:
            log(f"Erro no Discord: {e}", "ERROR")
            return False

discord = DiscordNotifier()

# ===== INTEGRAÇÃO GOOGLE SHEETS =====
class GoogleSheetsLogger:
    """Sistema de registro de operações no Google Sheets"""
    
    def __init__(self, credentials_file: str = "API.json", sheet_name: str = None):
        self.credentials_file = credentials_file
        self.sheet_name = sheet_name or os.getenv("GOOGLE_SHEET_NAME", "Base_logs")
        self.enabled = False
        self.worksheet = None
        
        # Tentar conectar ao Google Sheets
        self._connect()
    
    def _connect(self):
        """Conecta ao Google Sheets usando as credenciais"""
        try:
            # Configurar credenciais - Prioridade: base64 > arquivo local
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Tentar ler de variável de ambiente (base64) - PRODUÇÃO
            google_creds_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
            
            if google_creds_base64:
                # Produção: ler credenciais do ambiente (base64)
                log("📊 Carregando credenciais Google do ambiente (base64)", "INFO")
                import base64
                
                try:
                    creds_json = base64.b64decode(google_creds_base64)
                    creds_dict = json.loads(creds_json)
                    
                    creds = Credentials.from_service_account_info(
                        creds_dict,
                        scopes=scopes
                    )
                except Exception as e:
                    log(f"❌ Erro decodificando GOOGLE_CREDENTIALS_BASE64: {e}", "ERROR")
                    return
                    
            elif os.path.exists(self.credentials_file):
                # Desenvolvimento: ler credenciais de arquivo local
                log(f"📊 Carregando credenciais Google do arquivo {self.credentials_file}", "INFO")
                
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=scopes
                )
            else:
                # Nenhuma credencial disponível
                log(f"⚠️ Credenciais Google não encontradas (nem base64 nem arquivo {self.credentials_file})", "WARN")
                return
            
            # Conectar ao Google Sheets
            client = gspread.authorize(creds)
            
            # Abrir ou criar planilha
            try:
                spreadsheet = client.open(self.sheet_name)
                log(f"✅ Conectado à planilha existente: {self.sheet_name}", "INFO")
            except gspread.SpreadsheetNotFound:
                spreadsheet = client.create(self.sheet_name)
                log(f"✅ Planilha criada: {self.sheet_name}", "INFO")
            
            # Usar primeira aba ou criar
            try:
                self.worksheet = spreadsheet.sheet1
            except:
                self.worksheet = spreadsheet.add_worksheet(title="Trades", rows=1000, cols=6)
            
            # Verificar se cabeçalho existe
            headers = self.worksheet.row_values(1)
            if not headers or headers[0] != "ID":
                # Criar cabeçalho COMPLETO para análise quantitativa
                self.worksheet.update('A1:AJ1', [[
                    # Identificação
                    'ID', 'Data', 'Hora', 'Timestamp', 'Cripto', 'Operação', 'Tipo',
                    
                    # Contexto de Entrada - Indicadores
                    'RSI', 'EMA_Trend', 'ATR', 'ATR_Percentil', 'Volume_Ratio',
                    
                    # Execução - Preços e Posição
                    'Preço_Entrada', 'Slippage_%', 'Tamanho_Posição_USD', 'Tamanho_Posição_Moedas', 'Leverage',
                    
                    # Gestão de Risco - Stops e Targets
                    'Stop_Loss_Preço', 'Stop_Loss_%', 'Take_Profit_1_Preço', 'Take_Profit_1_%',
                    'Take_Profit_2_Preço', 'Take_Profit_2_%', 'Risk_Reward_Ratio',
                    
                    # Resultados - Saída e P&L
                    'Preço_Saída', 'P&L_USD', 'P&L_%', 'Tempo_Trade_Min', 'MFE_%', 'MAE_%',
                    
                    # Análise - Classificação e Qualidade
                    'Mercado_Tendência', 'Mercado_Volatilidade', 'Qualidade_Entrada', 'Motivo', 'Observações'
                ]])
                log("✅ Cabeçalhos COMPLETOS criados (36 colunas para análise quantitativa)", "INFO")
            
            self.enabled = True
            log(f"✅ Google Sheets configurado com sucesso", "INFO")
            
        except Exception as e:
            log(f"❌ Erro conectando ao Google Sheets: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self.enabled = False
    
    def log_trade(self, trade_data: dict):
        """
        Registra uma operação COMPLETA na planilha com todos os dados para análise quantitativa
        
        Args:
            trade_data: Dicionário com TODOS os campos do trade:
                # Identificação
                - trade_id: ID único do trade
                - timestamp: datetime completo
                - crypto: Moeda (SOL, XRP, etc)
                - operation: LONG ou SHORT
                - trade_type: Entrada ou Saída
                
                # Contexto de Entrada
                - rsi: Valor RSI
                - ema_trend: "Bullish", "Bearish", "Neutral"
                - atr: Average True Range
                - atr_percentile: Percentil ATR (0-100) para classificar volatilidade
                - volume_ratio: Volume atual / Volume médio
                
                # Execução
                - entry_price: Preço de entrada
                - slippage_pct: Slippage % (diferença entre preço esperado e real)
                - position_size_usd: Tamanho em USD
                - position_size_coins: Tamanho em moedas
                - leverage: Alavancagem usada
                
                # Gestão de Risco
                - stop_loss_price: Preço do stop loss
                - stop_loss_pct: % de distância do stop
                - tp1_price: Take profit 1 (parcial)
                - tp1_pct: % TP1
                - tp2_price: Take profit 2 (total)
                - tp2_pct: % TP2
                - risk_reward: Ratio R:R
                
                # Resultados (para trades fechados)
                - exit_price: Preço de saída
                - pnl_usd: Lucro/Prejuízo em USD
                - pnl_pct: Lucro/Prejuízo %
                - time_in_trade_min: Tempo no trade (minutos)
                - mfe_pct: Maximum Favorable Excursion %
                - mae_pct: Maximum Adverse Excursion %
                
                # Análise
                - market_trend: "Strong Uptrend", "Uptrend", "Range", "Downtrend", "Strong Downtrend"
                - market_volatility: "Muito Alta", "Alta", "Normal", "Baixa"
                - entry_quality: "Excelente", "Boa", "Regular", "Ruim"
                - reason: Motivo da operação
                - notes: Observações adicionais
        """
        if not self.enabled:
            return
            log("⚠️ Google Sheets não habilitado, registro ignorado", "DEBUG")
            return False
        
        try:
            # Extrair dados do dicionário com valores padrão
            trade_id = trade_data.get('trade_id', '')
            timestamp = trade_data.get('timestamp', datetime.now())
            crypto = trade_data.get('crypto', 'SOL')
            operation = trade_data.get('operation', 'LONG')
            trade_type = trade_data.get('trade_type', 'Entrada')
            
            # Formatar data/hora
            data = timestamp.strftime("%d/%m/%Y")
            hora = timestamp.strftime("%H:%M:%S")
            timestamp_str = timestamp.isoformat()
            
            # Contexto de Entrada - Indicadores
            rsi = trade_data.get('rsi')
            rsi_str = f"{rsi:.2f}" if rsi is not None else "-"
            ema_trend = trade_data.get('ema_trend', '-')
            atr = trade_data.get('atr')
            atr_str = f"{atr:.4f}" if atr is not None and atr > 0 else "-"
            atr_percentile = trade_data.get('atr_percentile')
            atr_pct_str = f"{atr_percentile:.1f}" if atr_percentile is not None else "-"
            volume_ratio = trade_data.get('volume_ratio')
            vol_ratio_str = f"{volume_ratio:.2f}" if volume_ratio is not None else "-"
            
            # Execução - Preços e Posição
            entry_price = trade_data.get('entry_price', 0)
            entry_str = f"{entry_price:.4f}" if entry_price > 0 else "-"
            slippage = trade_data.get('slippage_pct')
            slippage_str = f"{slippage:.3f}" if slippage is not None else "-"
            pos_size_usd = trade_data.get('position_size_usd')
            pos_usd_str = f"{pos_size_usd:.2f}" if pos_size_usd is not None else "-"
            pos_size_coins = trade_data.get('position_size_coins')
            pos_coins_str = f"{pos_size_coins:.4f}" if pos_size_coins is not None else "-"
            leverage = trade_data.get('leverage', 1)
            leverage_str = f"{leverage}x"
            
            # Gestão de Risco - Stops e Targets
            sl_price = trade_data.get('stop_loss_price')
            sl_price_str = f"{sl_price:.4f}" if sl_price is not None else "-"
            sl_pct = trade_data.get('stop_loss_pct')
            sl_pct_str = f"{sl_pct:.2f}" if sl_pct is not None else "-"
            tp1_price = trade_data.get('tp1_price')
            tp1_price_str = f"{tp1_price:.4f}" if tp1_price is not None else "-"
            tp1_pct = trade_data.get('tp1_pct')
            tp1_pct_str = f"{tp1_pct:.2f}" if tp1_pct is not None else "-"
            tp2_price = trade_data.get('tp2_price')
            tp2_price_str = f"{tp2_price:.4f}" if tp2_price is not None else "-"
            tp2_pct = trade_data.get('tp2_pct')
            tp2_pct_str = f"{tp2_pct:.2f}" if tp2_pct is not None else "-"
            rr_ratio = trade_data.get('risk_reward')
            rr_str = f"{rr_ratio:.2f}" if rr_ratio is not None else "-"
            
            # Resultados - Saída e P&L
            exit_price = trade_data.get('exit_price')
            exit_str = f"{exit_price:.4f}" if exit_price is not None else "-"
            pnl_usd = trade_data.get('pnl_usd')
            pnl_usd_str = f"{pnl_usd:.2f}" if pnl_usd is not None else "-"
            pnl_pct = trade_data.get('pnl_pct')
            pnl_pct_str = f"{pnl_pct:.2f}" if pnl_pct is not None else "-"
            time_in_trade = trade_data.get('time_in_trade_min')
            time_str = f"{time_in_trade:.0f}" if time_in_trade is not None else "-"
            mfe = trade_data.get('mfe_pct')
            mfe_str = f"{mfe:.2f}" if mfe is not None else "-"
            mae = trade_data.get('mae_pct')
            mae_str = f"{mae:.2f}" if mae is not None else "-"
            
            # Análise - Classificação e Qualidade
            market_trend = trade_data.get('market_trend', '-')
            market_volatility = trade_data.get('market_volatility', '-')
            entry_quality = trade_data.get('entry_quality', '-')
            reason = trade_data.get('reason', '')
            notes = trade_data.get('notes', '')
            
            # Montar linha completa (36 colunas)
            row = [
                # Identificação
                trade_id, data, hora, timestamp_str, crypto, operation, trade_type,
                
                # Contexto de Entrada - Indicadores
                rsi_str, ema_trend, atr_str, atr_pct_str, vol_ratio_str,
                
                # Execução - Preços e Posição
                entry_str, slippage_str, pos_usd_str, pos_coins_str, leverage_str,
                
                # Gestão de Risco - Stops e Targets
                sl_price_str, sl_pct_str, tp1_price_str, tp1_pct_str,
                tp2_price_str, tp2_pct_str, rr_str,
                
                # Resultados - Saída e P&L
                exit_str, pnl_usd_str, pnl_pct_str, time_str, mfe_str, mae_str,
                
                # Análise - Classificação e Qualidade
                market_trend, market_volatility, entry_quality, reason, notes
            ]
            
            # Adicionar linha na planilha
            self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            
            log(f"📊 Trade registrado: {trade_id} | {crypto} {operation} {trade_type} @ ${entry_str} | RSI: {rsi_str} | ATR: {atr_str}", "INFO")
            return True
            
        except Exception as e:
            log(f"❌ Erro registrando no Google Sheets: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return False
            return False

# Instância global do Google Sheets Logger
sheets_logger = GoogleSheetsLogger()

# ===== CONFIGURAÇÃO =====
@dataclass
class TradingConfig:
    """Configuração da estratégia"""
    
    # Assets a operar (lista de símbolos)
    SYMBOLS: List[str] = None
    LEVERAGE: int = 5
    
    # Dados históricos
    HISTORICAL_DAYS: int = 30       # Últimos 30 dias para RSI
    TIMEFRAME: str = "1h"           # Gráfico de 1 hora
    
    # Indicadores
    RSI_PERIOD: int = 14             # Período do RSI
    
    # Sinais de entrada
    RSI_LONG_THRESHOLD: float = 20   # RSI < 20 para LONG (sobrevendido)
    RSI_SHORT_THRESHOLD: float = 80  # RSI > 80 para SHORT (sobrecomprado)
    
    # Estratégia de entrada
    ENTRY_CAPITAL_PCT: float = 25.0   # Usa 25% do capital por entrada (conservador)
    ENTRY_COOLDOWN_HOURS: int = 48    # Cooldown de 48h entre entradas no mesmo asset
    
    # Estratégia de SAÍDA - OTIMIZADA
    ATR_PERIOD: int = 14                 # Período para calcular ATR
    ATR_SL_MULTIPLIER: float = 1.5       # Stop Loss = 1.5x ATR (adaptativo)
    
    # TAKE PROFITS FIXOS (conforme especificação)
    TAKE_PROFIT_1_PCT: float = 10.0      # TP1: 10% fixo (vende 50% da posição)
    TAKE_PROFIT_2_PCT: float = 20.0      # TP2: 20% fixo (vende 100% - toda a posição)
    
    # Fallback apenas para stop loss
    STOP_LOSS_PRICE_PCT: float = 2.0     # Fallback: 2% no preço se ATR falhar
    
    # Gestão de saída parcial
    TP1_SELL_PCT: float = 50.0           # Vende 50% no TP1
    MOVE_SL_TO_BREAKEVEN: bool = True    # Move SL para breakeven após TP1
    
    # Gestão de capital
    MIN_ORDER_USD: float = 10.0  # Mínimo $10 para ordem Hyperliquid
    
    def __post_init__(self):
        if self.SYMBOLS is None:
            self.SYMBOLS = ["SOL/USDC:USDC", "XRP/USDC:USDC"]

# ===== GERENCIADOR DE ESTADO =====
class StateManager:
    """Gerencia o estado da estratégia (últimas operações, cooldowns, etc)"""
    
    def __init__(self, state_file: str = "dca_state.json", exchange=None):
        self.state_file = state_file
        self.state = self.load_state()
        self.exchange = exchange
        
        # Auto-reconstruir estado se necessário
        if exchange and self.needs_reconstruction():
            log("⚠️ Detectado estado inconsistente - iniciando reconstrução...", "WARN")
            self.reconstruct_from_hyperliquid(exchange)
    
    def needs_reconstruction(self) -> bool:
        """Verifica se precisa reconstruir estado a partir da API"""
        try:
            if not self.exchange:
                return False
            
            # Buscar posições de todos os símbolos configurados
            from dataclasses import fields
            cfg_fields = {f.name: f.default for f in fields(TradingConfig)}
            symbols = cfg_fields.get('SYMBOLS', ["SOL/USDC:USDC"])
            
            for symbol in symbols:
                position = self.exchange.get_position(symbol)
                
                # Se tem posição aberta mas sem entries no estado, precisa reconstruir
                if position and abs(float(position.get("contracts", 0))) > 0:
                    has_entries = len(self.state.get("position_entries", [])) > 0
                    if not has_entries:
                        coin = symbol.split('/')[0]
                        log(f"🔍 Posição {coin} detectada ({abs(float(position.get('contracts', 0))):.4f}) mas estado vazio - RECONSTRUIR", "WARN")
                        return True
            
            return False
            
        except Exception as e:
            log(f"❌ Erro verificando necessidade de reconstrução: {e}", "ERROR")
            import traceback
            log(f"   {traceback.format_exc()}", "DEBUG")
            return False
    
    def load_state(self) -> dict:
        """Carrega estado do arquivo JSON"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log(f"Erro carregando estado: {e}", "WARN")
        
        # Estado inicial
        return {
            "last_buy_timestamp": None,
            "last_buy_step": None,  # Último degrau de compra executado
            "last_sell_timestamp": None,
            "last_sell_step": None,  # Último degrau de venda executado
            "position_entries": [],  # Lista de entradas com preço e quantidade
        }
    
    def reconstruct_from_hyperliquid(self, exchange):
        """
        Reconstrói o estado a partir do histórico de trades da Hyperliquid.
        Chamado quando detecta posição aberta mas estado vazio.
        """
        try:
            log("🔍 Reconstruindo estado do histórico Hyperliquid...", "INFO")
            
            # Buscar fills recentes da Hyperliquid
            vault_address = os.getenv("HYPERLIQUID_SUBACCOUNT")
            if not vault_address:
                log("❌ HYPERLIQUID_SUBACCOUNT não configurado", "ERROR")
                return False
            
            # Chamar a função helper global
            fills = _hl_get_user_fills(vault_address, limit=100)
            
            if not fills:
                log("❌ Nenhum fill encontrado no histórico", "WARN")
                return False
            
            log(f"📊 Encontrados {len(fills)} fills no histórico", "INFO")
            
            # Reconstruir position_entries a partir dos fills de compra (Open Long)
            entries = []
            last_buy_time = None
            last_buy_step = None
            last_sell_time = None
            last_sell_step = None
            
            # Processar do mais antigo para o mais recente
            for fill in reversed(fills):
                try:
                    coin = fill.get("coin", "")
                    direction = fill.get("dir", "")
                    px = float(fill.get("px", 0))
                    sz = float(fill.get("sz", 0))
                    time_ms = int(fill.get("time", 0))
                    
                    # Filtrar apenas SOL
                    if coin != "SOL":
                        continue
                    
                    # Converter timestamp
                    timestamp = datetime.fromtimestamp(time_ms / 1000.0)
                    
                    # Detectar COMPRAS: "Open Long" ou "Close Short"
                    if "Open Long" in direction:
                        # É uma compra (abrir long)
                        entries.append({
                            "price": px,
                            "amount": sz,
                            "timestamp": timestamp.isoformat(),
                            "operation": "LONG"
                        })
                        last_buy_time = timestamp
                        log(f"   🟢 LONG aberto: {sz:.4f} SOL @ ${px:.4f} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                    
                    # Detectar VENDAS A DESCOBERTO: "Open Short"
                    elif "Open Short" in direction:
                        # É uma venda a descoberto (abrir short)
                        entries.append({
                            "price": px,
                            "amount": sz,
                            "timestamp": timestamp.isoformat(),
                            "operation": "SHORT"
                        })
                        last_buy_time = timestamp
                        log(f"   🔴 SHORT aberto: {sz:.4f} SOL @ ${px:.4f} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                    
                    # Detectar FECHAMENTO: "Close Long" ou "Close Short"
                    elif "Close" in direction:
                        # É um fechamento de posição
                        last_sell_time = timestamp
                        
                        # Remover proporcionalmente dos entries (FIFO - first in, first out)
                        remaining_to_close = sz
                        i = 0
                        while i < len(entries) and remaining_to_close > 0:
                            if entries[i]["amount"] <= remaining_to_close:
                                # Remove entrada completamente
                                remaining_to_close -= entries[i]["amount"]
                                entries.pop(i)
                            else:
                                # Remove parcialmente
                                entries[i]["amount"] -= remaining_to_close
                                remaining_to_close = 0
                                i += 1
                        
                        log(f"   ⚪ Fechamento: {sz:.4f} SOL @ ${px:.4f} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                        
                except Exception as e:
                    log(f"Erro processando fill: {e}", "DEBUG")
                    continue
            
            # Atualizar estado
            if entries:
                self.state["position_entries"] = entries
                avg_price = sum(e["price"] * e["amount"] for e in entries) / sum(e["amount"] for e in entries)
                total_amount = sum(e["amount"] for e in entries)
                log(f"✅ Reconstruído: {len(entries)} entradas, {total_amount:.4f} SOL @ preço médio ${avg_price:.4f}", "INFO")
            
            if last_buy_time:
                self.state["last_buy_timestamp"] = last_buy_time.isoformat()
                # Tentar inferir o degrau de compra baseado no % abaixo do máximo
                if last_buy_step is not None:
                    self.state["last_buy_step"] = last_buy_step
                log(f"✅ Última compra: {last_buy_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                
            if last_sell_time:
                self.state["last_sell_timestamp"] = last_sell_time.isoformat()
                # Tentar inferir o degrau de venda baseado no ganho obtido
                if last_sell_step is not None:
                    self.state["last_sell_step"] = last_sell_step
                log(f"✅ Última venda: {last_sell_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
            
            self.save_state()
            
            # NOVO: Reconstruir alvos (stop loss e take profit) se necessário
            self.reconstruct_targets_if_needed()
            
            return True
            
        except Exception as e:
            log(f"❌ Erro reconstruindo estado: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return False
    
    def reconstruct_targets_if_needed(self):
        """
        Reconstrói os alvos de saída (stop loss e take profit) quando:
        - Há posição aberta
        - Mas não há targets salvos (active_targets vazio)
        
        Isso acontece quando o bot reinicia após uma entrada.
        """
        try:
            # Verificar se já tem targets configurados
            if self.state.get("active_targets"):
                log("✅ Alvos de saída já configurados", "DEBUG")
                return
            
            # Verificar se há entradas de posição
            entries = self.state.get("position_entries", [])
            if not entries:
                log("ℹ️  Sem posição aberta, não há alvos para reconstruir", "DEBUG")
                return
            
            # Pegar dados da última entrada
            last_entry = entries[-1]
            entry_price = last_entry.get("price")
            amount = sum(e.get("amount", 0) for e in entries)
            operation = last_entry.get("operation", "LONG")
            atr = last_entry.get("atr")
            trade_id = last_entry.get("trade_id")
            
            if not entry_price or not amount:
                log("⚠️ Dados de entrada incompletos, não é possível reconstruir alvos", "WARN")
                return
            
            log("🔧 Reconstruindo alvos de saída...", "INFO")
            log(f"   📊 Preço de entrada: ${entry_price:.4f}", "INFO")
            log(f"   🪙 Quantidade: {amount:.4f}", "INFO")
            log(f"   📈 Operação: {operation}", "INFO")
            
            # Calcular Stop Loss usando ATR se disponível, senão usar fixo
            if atr and atr > 0:
                log(f"   📊 ATR salvo: ${atr:.4f}", "INFO")
                
                # Importar configuração
                from dataclasses import fields
                cfg_fields = {f.name: f.default for f in fields(TradingConfig)}
                atr_sl_mult = cfg_fields.get('ATR_SL_MULTIPLIER', 1.5)
                
                if operation == "LONG":
                    stop_loss_price = entry_price - (atr * atr_sl_mult)
                else:  # SHORT
                    stop_loss_price = entry_price + (atr * atr_sl_mult)
                
                log(f"   ✅ Usando Stop Loss dinâmico (ATR SL: {atr_sl_mult}x)", "INFO")
            else:
                log(f"   ⚠️ ATR não disponível, usando Stop Loss fixo (2%)", "WARN")
                
                if operation == "LONG":
                    stop_loss_price = entry_price * 0.98  # -2%
                else:  # SHORT
                    stop_loss_price = entry_price * 1.02  # +2%
            
            # Calcular Take Profits FIXOS (10% e 20%)
            if operation == "LONG":
                take_profit_1_price = entry_price * 1.10  # +10%
                take_profit_2_price = entry_price * 1.20  # +20%
            else:  # SHORT
                take_profit_1_price = entry_price * 0.90  # -10%
                take_profit_2_price = entry_price * 0.80  # -20%
            
            log(f"   ✅ Usando Take Profits FIXOS (TP1: 10%, TP2: 20%)", "INFO")
            
            # Determinar símbolo (assumir SOL se não especificado)
            symbol = "SOL/USDC:USDC"  # Default
            coin = "SOL"
            
            # Salvar targets reconstruídos com os novos campos
            self.state["active_targets"] = {
                "symbol": symbol,
                "coin": coin,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_2_price,  # Compatibilidade
                "take_profit_1_price": take_profit_1_price,
                "take_profit_2_price": take_profit_2_price,
                "amount": amount,
                "amount_remaining": amount,  # NOVO: quantidade restante
                "signal": operation,
                "entry_rsi": last_entry.get("rsi"),
                "entry_atr": atr,
                "trade_id": trade_id or f"{coin}_RECONSTRUCTED",
                "entry_time": last_entry.get("timestamp", datetime.now().isoformat()),
                "tp1_hit": False,  # NOVO: controle de TP1
                "breakeven_set": False,  # NOVO: controle de breakeven
                "reconstructed": True  # Flag para indicar que foi reconstruído
            }
            
            self.save_state()
            
            log(f"✅ ALVOS RECONSTRUÍDOS:", "INFO")
            log(f"   🔴 Stop Loss: ${stop_loss_price:.4f}", "INFO")
            log(f"   🟡 Take Profit 1 (50% @ 10%): ${take_profit_1_price:.4f}", "INFO")
            log(f"   🟢 Take Profit 2 (100% @ 20%): ${take_profit_2_price:.4f}", "INFO")
            log(f"   💡 Monitoramento ativo a partir de agora", "INFO")
            
        except Exception as e:
            log(f"❌ Erro reconstruindo targets: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
    
    def save_state(self):
        """Salva estado no arquivo JSON"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            log(f"Erro salvando estado: {e}", "ERROR")
    
    def can_buy(self, cooldown_hours: int) -> bool:
        """Verifica se pode comprar (respeita cooldown em horas)"""
        if self.state["last_buy_timestamp"] is None:
            return True
        
        last_timestamp = datetime.fromisoformat(self.state["last_buy_timestamp"])
        time_diff = datetime.now() - last_timestamp
        
        # Calcular diferença em horas
        hours_passed = time_diff.total_seconds() / 3600
        
        cooldown_passed = hours_passed >= cooldown_hours
        if not cooldown_passed:
            log(f"⏳ Cooldown de compra: {hours_passed:.1f}/{cooldown_hours}h", "DEBUG")
        return cooldown_passed
    
    def record_buy(self, price: float, amount: float, crypto: str = "SOL", operation: str = "LONG", 
                   rsi: float = None, atr: float = None, stop_loss: float = None, 
                   take_profit_1: float = None, take_profit_2: float = None,
                   ema_trend: str = None, atr_percentile: float = None, volume_ratio: float = None):
        """
        Registra uma compra com DADOS COMPLETOS para análise quantitativa
        
        Args:
            price: Preço de entrada
            amount: Quantidade de moedas
            crypto: Criptomoeda (SOL, XRP, etc)
            operation: LONG ou SHORT
            rsi: Valor RSI
            atr: Average True Range
            stop_loss: Preço do stop loss
            take_profit_1: Preço do take profit parcial
            take_profit_2: Preço do take profit total
            ema_trend: Tendência EMA ("Bullish", "Bearish", "Neutral")
            atr_percentile: Percentil do ATR (0-100)
            volume_ratio: Ratio volume atual/médio
        """
        now = datetime.now()
        
        # Gerar ID único para o trade: CRYPTO_TIMESTAMP
        # Exemplo: SOL_20260418_143025
        trade_id = f"{crypto}_{now.strftime('%Y%m%d_%H%M%S')}"
        
        self.state["last_buy_timestamp"] = now.isoformat()
        self.state["position_entries"].append({
            "timestamp": now.isoformat(),
            "price": price,
            "amount": amount,
            "rsi": rsi,
            "atr": atr,
            "operation": operation,
            "trade_id": trade_id,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2
        })
        self.save_state()
        
        log(f"💾 COMPRA REGISTRADA NO ESTADO:", "INFO")
        log(f"   🆔 Trade ID: {trade_id}", "INFO")
        log(f"   📅 Data/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        log(f"   💰 Preço: ${price:.4f}", "INFO")
        log(f"   🪙 Quantidade: {amount:.4f} {crypto}", "INFO")
        log(f"   📊 RSI: {rsi:.2f}" if rsi else "", "INFO")
        log(f"   📊 ATR: ${atr:.4f}" if atr and atr > 0 else "", "INFO")
        log(f"   🛑 Stop Loss: ${stop_loss:.4f}" if stop_loss else "", "INFO")
        log(f"   🎯 TP1: ${take_profit_1:.4f}" if take_profit_1 else "", "INFO")
        log(f"   🎯 TP2: ${take_profit_2:.4f}" if take_profit_2 else "", "INFO")
        log(f"   ⏰ Próxima compra: após {(now + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M')}", "INFO")
        
        # Calcular métricas
        position_size_usd = price * amount
        
        # Calcular % de stop loss e take profits
        if operation == "LONG":
            sl_pct = ((price - stop_loss) / price * 100) if stop_loss else None
            tp1_pct = ((take_profit_1 - price) / price * 100) if take_profit_1 else None
            tp2_pct = ((take_profit_2 - price) / price * 100) if take_profit_2 else None
        else:  # SHORT
            sl_pct = ((stop_loss - price) / price * 100) if stop_loss else None
            tp1_pct = ((price - take_profit_1) / price * 100) if take_profit_1 else None
            tp2_pct = ((price - take_profit_2) / price * 100) if take_profit_2 else None
        
        # Calcular Risk:Reward ratio
        risk_reward = (tp1_pct / sl_pct) if (sl_pct and tp1_pct and sl_pct > 0) else None
        
        # Classificar tendência de mercado
        market_trend = ema_trend if ema_trend else "-"
        
        # Classificar volatilidade
        if atr_percentile is not None:
            if atr_percentile >= 80:
                market_volatility = "Muito Alta"
            elif atr_percentile >= 60:
                market_volatility = "Alta"
            elif atr_percentile >= 40:
                market_volatility = "Normal"
            else:
                market_volatility = "Baixa"
        else:
            market_volatility = "-"
        
        # Avaliar qualidade da entrada
        entry_quality = self._evaluate_entry_quality(rsi, atr_percentile, volume_ratio, operation)
        
        # Determinar motivo
        if operation == "LONG":
            reason = f"RSI sobrevendido ({rsi:.2f} < 20)" if rsi else "Entrada LONG"
        else:
            reason = f"RSI sobrecomprado ({rsi:.2f} > 80)" if rsi else "Entrada SHORT"
        
        # Preparar dados completos para Google Sheets
        trade_data = {
            # Identificação
            'trade_id': trade_id,
            'timestamp': now,
            'crypto': crypto,
            'operation': operation,
            'trade_type': 'Entrada',
            
            # Contexto de Entrada - Indicadores
            'rsi': rsi,
            'ema_trend': market_trend,
            'atr': atr,
            'atr_percentile': atr_percentile,
            'volume_ratio': volume_ratio,
            
            # Execução - Preços e Posição
            'entry_price': price,
            'slippage_pct': None,  # Será calculado em produção comparando preço esperado vs real
            'position_size_usd': position_size_usd,
            'position_size_coins': amount,
            'leverage': 1,  # Sem alavancagem por padrão
            
            # Gestão de Risco - Stops e Targets
            'stop_loss_price': stop_loss,
            'stop_loss_pct': sl_pct,
            'tp1_price': take_profit_1,
            'tp1_pct': tp1_pct,
            'tp2_price': take_profit_2,
            'tp2_pct': tp2_pct,
            'risk_reward': risk_reward,
            
            # Resultados - Saída e P&L (vazios na entrada)
            'exit_price': None,
            'pnl_usd': None,
            'pnl_pct': None,
            'time_in_trade_min': None,
            'mfe_pct': None,
            'mae_pct': None,
            
            # Análise - Classificação e Qualidade
            'market_trend': market_trend,
            'market_volatility': market_volatility,
            'entry_quality': entry_quality,
            'reason': reason,
            'notes': ''
        }
        
        # Registrar no Google Sheets
        sheets_logger.log_trade(trade_data)
        
        return trade_id  # Retornar ID para usar depois
    
    def _evaluate_entry_quality(self, rsi: float, atr_percentile: float, volume_ratio: float, operation: str) -> str:
        """Avalia a qualidade da entrada baseado em múltiplos fatores"""
        score = 0
        
        # RSI adequado para operação (peso 3)
        if rsi is not None:
            if operation == "LONG" and rsi < 25:
                score += 3
            elif operation == "LONG" and rsi < 30:
                score += 2
            elif operation == "SHORT" and rsi > 75:
                score += 3
            elif operation == "SHORT" and rsi > 70:
                score += 2
        
        # Volatilidade favorável (peso 2)
        if atr_percentile is not None:
            if 40 <= atr_percentile <= 70:  # Volatilidade normal/alta mas não extrema
                score += 2
            elif atr_percentile < 40:  # Muito baixa
                score += 1
        
        # Volume acima da média (peso 2)
        if volume_ratio is not None:
            if volume_ratio > 1.5:
                score += 2
            elif volume_ratio > 1.0:
                score += 1
        
        # Classificar (máximo 7 pontos)
        if score >= 6:
            return "Excelente"
        elif score >= 4:
            return "Boa"
        elif score >= 2:
            return "Regular"
        else:
            return "Ruim"
    
    def record_sell(self, price: float, amount: float, crypto: str = "SOL", operation: str = "LONG", 
                   rsi: float = None, reason: str = "", trade_id: str = "",
                   entry_price: float = None, entry_time: datetime = None):
        """
        Registra uma venda com cálculo completo de resultados
        
        Args:
            price: Preço de saída
            amount: Quantidade vendida
            crypto: Criptomoeda
            operation: LONG ou SHORT
            rsi: RSI na saída
            reason: Motivo da saída (Stop Loss, Take Profit, etc)
            trade_id: ID do trade (para vincular com entrada)
            entry_price: Preço de entrada (para calcular P&L)
            entry_time: Timestamp da entrada (para calcular tempo no trade)
        """
        now = datetime.now()
        self.state["last_sell_timestamp"] = now.isoformat()
        self.save_state()
        
        # Calcular resultados
        if entry_price:
            if operation == "LONG":
                pnl_pct = ((price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_pct = ((entry_price - price) / entry_price) * 100
            
            pnl_usd = (price - entry_price) * amount if operation == "LONG" else (entry_price - price) * amount
        else:
            pnl_pct = None
            pnl_usd = None
        
        # Calcular tempo no trade
        if entry_time:
            time_in_trade_min = (now - entry_time).total_seconds() / 60
        else:
            time_in_trade_min = None
        
        log(f"💾 VENDA REGISTRADA NO ESTADO:", "INFO")
        log(f"   🆔 Trade ID: {trade_id}", "INFO")
        log(f"   📅 Data/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        log(f"   💰 Preço: ${price:.4f}", "INFO")
        log(f"   🪙 Quantidade: {amount:.4f} {crypto}", "INFO")
        log(f"   📊 RSI: {rsi:.2f}" if rsi else "", "INFO")
        log(f"   🎯 Motivo: {reason}", "INFO")
        if pnl_pct is not None:
            log(f"   💵 P&L: ${pnl_usd:.2f} ({pnl_pct:+.2f}%)", "INFO")
        if time_in_trade_min is not None:
            log(f"   ⏱️  Tempo: {time_in_trade_min:.0f} min", "INFO")
        
        # Preparar dados completos para Google Sheets
        trade_data = {
            # Identificação
            'trade_id': trade_id,
            'timestamp': now,
            'crypto': crypto,
            'operation': operation,
            'trade_type': 'Saída',
            
            # Contexto (na saída)
            'rsi': rsi,
            'ema_trend': '-',
            'atr': None,
            'atr_percentile': None,
            'volume_ratio': None,
            
            # Execução
            'entry_price': entry_price,
            'slippage_pct': None,
            'position_size_usd': price * amount,
            'position_size_coins': amount,
            'leverage': 1,
            
            # Gestão de Risco (copiar da entrada)
            'stop_loss_price': None,
            'stop_loss_pct': None,
            'tp1_price': None,
            'tp1_pct': None,
            'tp2_price': None,
            'tp2_pct': None,
            'risk_reward': None,
            
            # Resultados
            'exit_price': price,
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct,
            'time_in_trade_min': time_in_trade_min,
            'mfe_pct': None,  # TODO: calcular em monitoramento contínuo
            'mae_pct': None,  # TODO: calcular em monitoramento contínuo
            
            # Análise
            'market_trend': '-',
            'market_volatility': '-',
            'entry_quality': '-',
            'reason': reason,
            'notes': ''
        }
        
        # Registrar no Google Sheets
        sheets_logger.log_trade(trade_data)
    
    def get_position_entry(self, index: int = -1) -> dict:
        """Retorna dados da entrada de posição (útil para vendas)"""
        entries = self.state.get("position_entries", [])
        if entries and len(entries) > abs(index):
            return entries[index]
        return None
    
    def get_average_entry_price(self) -> float:
        """
        Calcula preço médio de entrada baseado nas entradas registradas.
        Se não houver entries mas houver posição, tenta buscar da API como fallback.
        """
        entries = self.state["position_entries"]
        if not entries:
            # Fallback: tentar buscar da posição atual se exchange está disponível
            if self.exchange:
                try:
                    position = self.exchange.get_position()
                    if position and position.get("size", 0) > 0:
                        entry_price = position.get("entryPrice", 0)
                        if entry_price > 0:
                            log(f"⚠️ Usando entry_price da posição como fallback: ${entry_price:.4f}", "WARN")
                            return float(entry_price)
                except Exception as e:
                    log(f"Erro buscando entry_price da posição: {e}", "DEBUG")
            
            return 0.0
        
        total_value = sum(e["price"] * e["amount"] for e in entries)
        total_amount = sum(e["amount"] for e in entries)
        
        return total_value / total_amount if total_amount > 0 else 0.0
    
    def show_state_summary(self):
        """Mostra resumo do estado atual"""
        log("", "INFO")
        log("📋 ESTADO ATUAL DO SISTEMA:", "INFO")
        
        # Última compra
        if self.state["last_buy_timestamp"]:
            last_buy = datetime.fromisoformat(self.state["last_buy_timestamp"])
            hours_since_buy = (datetime.now() - last_buy).total_seconds() / 3600
            log(f"   🟢 Última compra: {last_buy.strftime('%Y-%m-%d %H:%M:%S')} ({hours_since_buy:.1f}h atrás)", "INFO")
        else:
            log(f"   🟢 Última compra: Nenhuma", "INFO")
        
        # Entradas registradas
        entries = self.state["position_entries"]
        if entries:
            log(f"   📊 Total de entradas: {len(entries)}", "INFO")
            for i, entry in enumerate(entries, 1):
                entry_time = datetime.fromisoformat(entry["timestamp"])
                log(f"      {i}. {entry_time.strftime('%Y-%m-%d %H:%M')} | ${entry['price']:.4f} | {entry['amount']:.4f} SOL", "INFO")
        else:
            log(f"   📊 Total de entradas: 0", "INFO")
        
        log("", "INFO")

# ===== CONEXÃO COM EXCHANGES =====
class ExchangeConnector:
    """Gerencia conexão com Hyperliquid (dados + execução)"""
    
    def __init__(self, cfg: TradingConfig):
        self.cfg = cfg
        
        # Cache para dados históricos (evitar rate limit)
        self._cache = {}
        self._cache_duration = 3600  # 1 hora em segundos
        
        # Binance OPCIONAL (apenas se keys estiverem configuradas)
        binance_key = os.getenv('BINANCE_API_KEY', '')
        binance_secret = os.getenv('BINANCE_API_SECRET', '')
        
        if binance_key and binance_secret:
            try:
                self.binance = ccxt.binance({
                    'apiKey': binance_key,
                    'secret': binance_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
                log("✅ Binance conectada (backup para dados)", "INFO")
            except Exception as e:
                log(f"⚠️ Binance não disponível: {e}", "WARN")
                self.binance = None
        else:
            log("ℹ️  Binance não configurada (usando apenas Hyperliquid)", "INFO")
            self.binance = None
        
        # Hyperliquid para execução
        wallet_address = os.getenv("WALLET_ADDRESS", "")
        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")  # Usar APENAS esta variável
        vault_address = os.getenv("HYPERLIQUID_SUBACCOUNT", "")  # Subconta
        
        if not wallet_address or not private_key:
            raise ValueError("WALLET_ADDRESS e HYPERLIQUID_PRIVATE_KEY devem estar configurados")
        
        if not vault_address:
            raise ValueError("HYPERLIQUID_SUBACCOUNT (vault/subconta) deve estar configurada")
        
        log(f"🏦 Configurando operação na subconta (vault): {vault_address}", "INFO")
        log(f"🔑 Carteira principal (assinatura): {wallet_address}", "INFO")
        log(f"🔐 Private key configurada: {private_key[:10]}...{private_key[-4:]}", "DEBUG")
        
        self.hyperliquid = ccxt.hyperliquid({
            'walletAddress': wallet_address,
            'privateKey': private_key,
            'enableRateLimit': True,
        })
        
        # SEMPRE usar subconta (obrigatório)
        self.hyperliquid.options['vaultAddress'] = vault_address
        
        # Wallet address é SEMPRE a vault (subconta)
        self.wallet_address = vault_address
        
        log("✅ Conexões estabelecidas: Hyperliquid (dados + execução)", "INFO")
    
    def fetch_historical_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Busca dados históricos com cache (evita rate limit)"""
        try:
            coin = symbol.split('/')[0]
            cache_key = f"{symbol}_{days}"
            
            # Verificar cache primeiro
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                age = time.time() - cached_time
                
                if age < self._cache_duration:
                    log(f"📊 Usando dados em cache de {coin} ({age/60:.1f} min atrás)", "DEBUG")
                    return cached_data
            
            # Cache expirado ou não existe - buscar novos dados
            timeframe = self.cfg.TIMEFRAME
            limit = days * 24 + 50
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            log(f"📊 Buscando dados históricos de {coin} na Hyperliquid...", "DEBUG")
            
            # Adicionar delay ANTES da requisição para evitar rate limit
            log(f"⏳ Aguardando 2s antes de buscar dados (evitar rate limit)...", "DEBUG")
            time.sleep(2.0)  # 2 segundos entre requisições
            
            # Buscar da Hyperliquid
            ohlcv = self.hyperliquid.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            if not ohlcv or len(ohlcv) == 0:
                log(f"⚠️ Nenhum dado histórico retornado para {coin}", "WARN")
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Salvar no cache
            self._cache[cache_key] = (df, time.time())
            
            log(f"📊 Dados históricos {coin} ({timeframe}): {len(df)} candles, {df['timestamp'].min()} até {df['timestamp'].max()}", "INFO")
            
            return df
            
        except Exception as e:
            log(f"❌ Erro buscando dados históricos {symbol}: {e}", "ERROR")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """Busca preço atual de um símbolo com cache"""
        try:
            coin = symbol.split('/')[0]
            cache_key = f"price_{symbol}"
            
            # Verificar cache (válido por 30 segundos para preços)
            if cache_key in self._cache:
                cached_price, cached_time = self._cache[cache_key]
                age = time.time() - cached_time
                
                if age < 30:  # Cache de 30 segundos para preços
                    log(f"💰 Preço {coin} em cache: ${cached_price:.4f} ({age:.1f}s atrás)", "DEBUG")
                    return cached_price
            
            # Adicionar delay antes de buscar preço
            time.sleep(0.5)  # 500ms entre requisições
            
            # Buscar direto da Hyperliquid
            ticker = self.hyperliquid.fetch_ticker(symbol)
            price = ticker['last']
            
            # Salvar no cache
            self._cache[cache_key] = (price, time.time())
            
            log(f"💰 Preço atual {coin}: ${price:.4f}", "DEBUG")
            return price
        except Exception as e:
            log(f"❌ Erro buscando preço {symbol}: {e}", "ERROR")
            
            # Tentar usar preço do cache mesmo expirado
            cache_key = f"price_{symbol}"
            if cache_key in self._cache:
                cached_price, cached_time = self._cache[cache_key]
                age = time.time() - cached_time
                log(f"⚠️ Usando preço em cache expirado ({age/60:.1f} min): ${cached_price:.4f}", "WARN")
                return cached_price
            
            return 0.0
    
    def get_balance(self) -> float:
        """Retorna saldo disponível na conta Hyperliquid"""
        try:
            balance = _hl_get_account_value(self.wallet_address) if self.wallet_address else 0.0
            log(f"💵 Saldo disponível: ${balance:.2f}", "DEBUG")
            return balance
        except Exception as e:
            log(f"❌ Erro buscando saldo: {e}", "ERROR")
            return 0.0
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Retorna posição aberta (se houver) via API direta Hyperliquid"""
        try:
            # Usar API direta para obter estado do usuário
            user_state = _hl_get_user_state(self.wallet_address)
            
            if not user_state or "assetPositions" not in user_state:
                log(f"⚠️ Nenhuma posição encontrada na resposta da API para {symbol}", "DEBUG")
                return None
            
            asset_positions = user_state["assetPositions"]
            
            # Procurar posição do asset específico
            coin_name = symbol.replace('/USDC:USDC', '')  # "SOL" ou "XRP"
            
            for pos in asset_positions:
                position_coin = pos.get("position", {}).get("coin", "")
                size = float(pos.get("position", {}).get("szi", 0))
                
                if position_coin == coin_name and abs(size) > 0:
                    # Converter para formato compatível
                    entry_px = float(pos.get("position", {}).get("entryPx", 0))
                    
                    log(f"✅ Posição encontrada: {size} {coin_name} @ ${entry_px:.4f}", "DEBUG")
                    
                    return {
                        "symbol": symbol,
                        "contracts": size,
                        "entryPrice": entry_px,
                        "side": "long" if size > 0 else "short",
                        "unrealizedPnl": float(pos.get("position", {}).get("unrealizedPnl", 0)),
                        "marginUsed": float(pos.get("position", {}).get("marginUsed", 0)),
                    }
            
            log(f"⚠️ Nenhuma posição de {coin_name} encontrada", "DEBUG")
            return None
            
        except Exception as e:
            log(f"❌ Erro buscando posição {symbol}: {e}", "ERROR")
            return None
    
    def create_market_order(self, symbol: str, side: str, amount_usd: float, leverage: int) -> bool:
        """Cria ordem market na Hyperliquid com logs detalhados"""
        try:
            coin = symbol.split('/')[0]
            
            log(f"", "INFO")
            log(f"🔨 INICIANDO CREATE_MARKET_ORDER", "INFO")
            log(f"   Symbol: {symbol}", "INFO")
            log(f"   Side: {side}", "INFO")
            log(f"   Amount USD: ${amount_usd:.2f}", "INFO")
            log(f"   Leverage: {leverage}x", "INFO")
            
            # Configurar leverage primeiro
            log(f"🔧 Configurando leverage {leverage}x para {symbol}", "INFO")
            try:
                self.hyperliquid.set_leverage(leverage, symbol, {"marginMode": "isolated"})
                log(f"✅ Leverage configurado com sucesso", "DEBUG")
            except Exception as e:
                log(f"⚠️ Erro ao configurar leverage (pode já estar configurado): {e}", "WARN")
            
            # Buscar preço atual
            log(f"📊 Buscando preço atual de {coin}...", "DEBUG")
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                log("❌ Preço inválido, não é possível criar ordem", "ERROR")
                return False
            log(f"✅ Preço atual: ${current_price:.4f}", "DEBUG")
            
            # Calcular quantidade de coins com alavancagem
            # Fórmula: amount = (USD_a_gastar * leverage) / preço
            notional = amount_usd * leverage
            amount = notional / current_price
            
            log(f"🧮 CÁLCULO DE QUANTIDADE:", "INFO")
            log(f"   Notional: ${notional:.2f}", "INFO")
            log(f"   Amount calculado: {amount:.6f} {coin}", "INFO")
            
            # Arredondar quantidade conforme precisão do mercado
            amount_before = amount
            amount = float(self.hyperliquid.amount_to_precision(symbol, amount))
            log(f"   Amount arredondado: {amount:.6f} {coin} (antes: {amount_before:.6f})", "INFO")
            
            # Verificar valor mínimo
            notional_value = amount * current_price
            log(f"   Valor nocional final: ${notional_value:.2f}", "INFO")
            
            if notional_value < self.cfg.MIN_ORDER_USD:
                log(f"❌ Valor nocional muito baixo: ${notional_value:.2f} < ${self.cfg.MIN_ORDER_USD}", "ERROR")
                return False
            
            log(f"📤 CRIANDO ORDEM MARKET:", "INFO")
            log(f"   {side.upper()} {amount:.4f} {coin}", "INFO")
            log(f"   💰 USD investidos: ${amount_usd:.2f}", "INFO")
            log(f"   📊 Leverage: {leverage}x", "INFO")
            log(f"   💵 Valor nocional: ${notional:.2f}", "INFO")
            log(f"   📈 Preço: ${current_price:.4f}", "INFO")
            
            # Criar ordem market (Hyperliquid exige price para calcular slippage)
            log(f"🚀 Enviando ordem para Hyperliquid...", "INFO")
            order = self.hyperliquid.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                price=current_price,  # Necessário para Hyperliquid calcular slippage
                params={}
            )
            
            log(f"✅ ORDEM CRIADA COM SUCESSO!", "INFO")
            log(f"   Order ID: {order.get('id', 'N/A')}", "INFO")
            log(f"   Status: {order.get('status', 'N/A')}", "INFO")
            log(f"   Info completa: {order}", "DEBUG")
            return True
            
        except Exception as e:
            log(f"❌ ERRO CRÍTICO AO CRIAR ORDEM!", "ERROR")
            log(f"   Exception: {type(e).__name__}", "ERROR")
            log(f"   Message: {str(e)}", "ERROR")
            import traceback
            log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    def close_position_partial(self, percentage: float) -> bool:
        """Fecha parcialmente a posição (percentage = 0-100)"""
        try:
            pos = self.get_position()
            if not pos:
                log("⚠️ Nenhuma posição aberta para fechar", "WARN")
                return False
            
            current_amount = abs(float(pos.get('contracts', 0)))
            amount_to_close = current_amount * (percentage / 100.0)
            
            # Arredondar
            amount_to_close = float(self.hyperliquid.amount_to_precision(self.cfg.SYMBOL, amount_to_close))
            
            # Verificar mínimo
            current_price = self.get_current_price()
            notional = amount_to_close * current_price
            
            if notional < self.cfg.MIN_ORDER_USD:
                log(f"⚠️ Ordem muito pequena (${notional:.2f} < ${self.cfg.MIN_ORDER_USD}), pulando", "WARN")
                return False
            
            log(f"📤 Fechando {percentage:.0f}% da posição ({amount_to_close:.4f} SOL)", "INFO")
            
            # Fechar posição (ordem market com reduceOnly - Hyperliquid exige price)
            order = self.hyperliquid.create_order(
                symbol=self.cfg.SYMBOL,
                type='market',
                side='sell',  # Sempre sell para fechar LONG
                amount=amount_to_close,
                price=current_price,  # Necessário para Hyperliquid calcular slippage
                params={'reduceOnly': True}
            )
            
            log(f"✅ Posição fechada parcialmente: {order}", "INFO")
            return True
            
        except Exception as e:
            log(f"❌ Erro fechando posição: {e}", "ERROR")
            return False

# ===== ESTRATÉGIA =====
class TradingStrategy:
    """Estratégia com EMA 200 para determinar tendência"""
    
    def __init__(self, cfg: TradingConfig):
        self.cfg = cfg
        self.exchange = ExchangeConnector(cfg)
        # StateManager precisa do exchange para reconstruir estado
        self.state = StateManager(exchange=self.exchange)
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula o RSI (Relative Strength Index) do DataFrame"""
        try:
            if len(df) < period + 1:
                log("⚠️ Dados insuficientes para calcular RSI", "WARN")
                return 50.0  # Valor neutro como fallback
            
            # Calcular variações de preço
            delta = df['close'].diff()
            
            # Separar ganhos e perdas
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # Calcular médias móveis exponenciais
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # Calcular RS (Relative Strength)
            rs = avg_gain / avg_loss
            
            # Calcular RSI
            rsi = 100 - (100 / (1 + rs))
            
            # Retornar último valor
            rsi_value = rsi.iloc[-1]
            
            # Tratar casos especiais (NaN, inf)
            if pd.isna(rsi_value) or np.isinf(rsi_value):
                return 50.0
            
            return float(rsi_value)
            
        except Exception as e:
            log(f"⚠️ Erro calculando RSI: {e}", "WARN")
            return 50.0  # Valor neutro como fallback
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula o ATR (Average True Range) do DataFrame"""
        try:
            if len(df) < period + 1:
                log("⚠️ Dados insuficientes para calcular ATR", "WARN")
                return 0.0
            
            # Calcular True Range
            high = df['high']
            low = df['low']
            close_prev = df['close'].shift(1)
            
            tr1 = high - low
            tr2 = abs(high - close_prev)
            tr3 = abs(low - close_prev)
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calcular ATR (média móvel do True Range)
            atr = tr.rolling(window=period).mean()
            
            # Retornar último valor
            atr_value = atr.iloc[-1]
            
            # Tratar casos especiais
            if pd.isna(atr_value) or np.isinf(atr_value):
                return 0.0
            
            return float(atr_value)
            
        except Exception as e:
            log(f"⚠️ Erro calculando ATR: {e}", "WARN")
            return 0.0
    
    def calculate_ema(self, df: pd.DataFrame, period: int = 200) -> float:
        """Calcula a EMA (Exponential Moving Average) do DataFrame"""
        try:
            if len(df) < period:
                log(f"⚠️ Dados insuficientes para calcular EMA {period}", "WARN")
                return 0.0
            
            # Calcular EMA
            ema = df['close'].ewm(span=period, adjust=False).mean()
            
            # Retornar último valor
            ema_value = ema.iloc[-1]
            
            # Tratar casos especiais (NaN, inf)
            if pd.isna(ema_value) or np.isinf(ema_value):
                return 0.0
            
            return float(ema_value)
            
        except Exception as e:
            log(f"⚠️ Erro calculando EMA: {e}", "WARN")
            return 0.0
    
    def analyze_asset(self, symbol: str) -> Dict[str, Any]:
        """Analisa um asset específico e determina se deve entrar LONG ou SHORT"""
        # Buscar dados históricos
        df = self.exchange.fetch_historical_data(symbol, self.cfg.HISTORICAL_DAYS)
        
        if df.empty:
            log(f"❌ Sem dados históricos para {symbol}", "ERROR")
            return {}
        
        # Calcular indicadores
        rsi = self.calculate_rsi(df, period=self.cfg.RSI_PERIOD)
        
        # Preço atual
        current_price = self.exchange.get_current_price(symbol)
        
        if current_price <= 0:
            log(f"❌ Preço inválido para {symbol}", "ERROR")
            return {}
        
        # Posição atual neste asset
        position = self.exchange.get_position(symbol)
        
        # Determinar sinal de entrada baseado apenas no RSI
        signal = None
        if rsi < self.cfg.RSI_LONG_THRESHOLD:
            signal = "LONG"  # RSI sobrevendido
        elif rsi > self.cfg.RSI_SHORT_THRESHOLD:
            signal = "SHORT"  # RSI sobrecomprado
        
        coin = symbol.split('/')[0]
        
        analysis = {
            "symbol": symbol,
            "coin": coin,
            "current_price": current_price,
            "rsi": rsi,
            "signal": signal,
            "position": position,
            "has_position": position is not None,
            "data": df,  # Adicionar DataFrame para cálculo de ATR
        }
        
        # Log da análise
        log(f"", "INFO")
        log(f"📊 {coin}: Preço=${current_price:.4f} | RSI={rsi:.1f} | Sinal: {signal if signal else 'NENHUM'}", "INFO")
        
        # Se tem posição, calcular % de ganho
        if position:
            entry_price = float(position.get('entryPrice', 0))
            position_size = float(position.get('contracts', 0))
            side = position.get('side', '')
            
            unrealized_pnl = float(position.get('unrealizedPnl', 0))
            margin_used = float(position.get('marginUsed', 0))
            
            # % de ganho baseado no PNL real
            if margin_used > 0:
                pct_gain_real = (unrealized_pnl / margin_used) * 100
            else:
                # Fallback
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                if side == "short":
                    price_change_pct = -price_change_pct
                pct_gain_real = price_change_pct * self.cfg.LEVERAGE
            
            analysis["entry_price"] = entry_price
            analysis["pct_gain"] = pct_gain_real
            analysis["position_size"] = position_size
            analysis["unrealized_pnl"] = unrealized_pnl
            
            log(f"   � Posição: {side.upper()} {abs(position_size):.4f} {coin} @ ${entry_price:.4f}", "INFO")
            log(f"   {'📈' if pct_gain_real >= 0 else '📉'} PNL: {pct_gain_real:+.2f}% | ${unrealized_pnl:+.2f}", "INFO")
        
        return analysis
    
    def should_enter(self, analysis: Dict) -> bool:
        """Verifica se deve entrar na posição"""
        # Se já tem posição aberta neste asset, não faz nada
        if analysis.get("has_position"):
            log(f"⏭️  {analysis['coin']}: Já tem posição aberta, ignorando", "DEBUG")
            return False
        
        # Se não tem sinal de entrada, não faz nada
        if not analysis.get("signal"):
            log(f"⏭️  {analysis['coin']}: Sem sinal de entrada", "DEBUG")
            return False
        
        # Verificar cooldown
        symbol = analysis["symbol"]
        if not self.state.can_buy(self.cfg.ENTRY_COOLDOWN_HOURS):
            return False
        
        signal = analysis["signal"]
        rsi = analysis["rsi"]
        
        log(f"🚨 SINAL DE ENTRADA {signal}: {analysis['coin']}", "INFO")
        log(f"   RSI: {rsi:.1f}", "INFO")
        return True
    
    def execute_entry(self, analysis: Dict) -> bool:
        """Executa entrada (LONG ou SHORT)"""
        balance = self.exchange.get_balance()
        current_price = analysis["current_price"]
        signal = analysis["signal"]
        symbol = analysis["symbol"]
        coin = analysis["coin"]
        rsi = analysis["rsi"]
        data = analysis.get("data")  # DataFrame com dados históricos para ATR
        
        # Calcular quanto investir
        amount_usd = balance * (self.cfg.ENTRY_CAPITAL_PCT / 100.0)
        
        # Com leverage: valor nocional
        notional_value = amount_usd * self.cfg.LEVERAGE
        amount_coins = notional_value / current_price
        
        # Verificar mínimo
        if notional_value < self.cfg.MIN_ORDER_USD:
            log(f"⚠️ Valor nocional muito baixo: ${notional_value:.2f} < ${self.cfg.MIN_ORDER_USD}", "WARN")
            return False
        
        side = "buy" if signal == "LONG" else "sell"
        
        log(f"🎯 ENTRANDO {signal}: {self.cfg.ENTRY_CAPITAL_PCT}% do capital em {coin}", "INFO")
        log(f"   💰 Capital disponível: ${balance:.2f}", "INFO")
        log(f"   📊 Investindo: ${amount_usd:.2f}", "INFO")
        log(f"   🔧 Leverage {self.cfg.LEVERAGE}x → Valor nocional: ${notional_value:.2f}", "INFO")
        log(f"   🪙 Quantidade: {amount_coins:.4f} {coin} @ ${current_price:.4f}", "INFO")
        log(f"   📈 RSI: {rsi:.2f}", "INFO")
        
        # Calcular ATR ANTES da entrada (para passar ao record_buy)
        atr = 0.0
        atr_percentile = None
        if data is not None and not data.empty:
            atr = self.calculate_atr(data, period=self.cfg.ATR_PERIOD)
            if atr > 0:
                log(f"   📊 ATR: ${atr:.4f} (será usado para stops dinâmicos)", "INFO")
                
                # Calcular percentil do ATR (volatilidade relativa)
                atr_series = data['high'] - data['low']
                atr_series = atr_series.rolling(window=self.cfg.ATR_PERIOD).mean()
                if len(atr_series) > 0:
                    atr_rank = (atr_series < atr).sum()
                    atr_percentile = (atr_rank / len(atr_series)) * 100
        
        # Calcular volume ratio
        volume_ratio = None
        if data is not None and not data.empty and 'volume' in data.columns:
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume
        
        # Detectar tendência EMA
        ema_trend = "Neutral"
        if data is not None and not data.empty:
            try:
                ema_200 = data['close'].ewm(span=200, adjust=False).mean().iloc[-1]
                if current_price > ema_200 * 1.02:
                    ema_trend = "Bullish"
                elif current_price < ema_200 * 0.98:
                    ema_trend = "Bearish"
            except:
                pass
        
        # Executar ordem MARKET
        success = self.exchange.create_market_order(symbol, side, amount_usd, self.cfg.LEVERAGE)
        
        if success:
            # Calcular stops ANTES de registrar (para incluir no registro)
            stop_loss_price = None
            take_profit_1_price = None
            take_profit_2_price = None
            
            # Stop Loss: usar ATR se disponível, senão fixo
            if atr > 0:
                log(f"📊 ATR calculado: ${atr:.4f} (stop loss dinâmico)", "INFO")
                
                if signal == "LONG":
                    stop_loss_price = current_price - (atr * self.cfg.ATR_SL_MULTIPLIER)
                else:
                    stop_loss_price = current_price + (atr * self.cfg.ATR_SL_MULTIPLIER)
                
                sl_distance = abs(stop_loss_price - current_price) / current_price * 100
                stop_loss_roi = sl_distance * self.cfg.LEVERAGE
                
                log(f"✅ Stop Loss dinâmico (ATR 1.5x): ${stop_loss_price:.4f} (-{stop_loss_roi:.1f}%)", "INFO")
            else:
                log(f"⚠️ ATR inválido, usando stop loss fixo (2%)", "WARN")
                
                if signal == "LONG":
                    stop_loss_price = current_price * (1 - self.cfg.STOP_LOSS_PRICE_PCT / 100.0)
                else:
                    stop_loss_price = current_price * (1 + self.cfg.STOP_LOSS_PRICE_PCT / 100.0)
                
                stop_loss_roi = self.cfg.STOP_LOSS_PRICE_PCT * self.cfg.LEVERAGE
            
            # Take Profits: SEMPRE FIXOS em 10% e 20%
            if signal == "LONG":
                take_profit_1_price = current_price * (1 + self.cfg.TAKE_PROFIT_1_PCT / 100.0)  # +10%
                take_profit_2_price = current_price * (1 + self.cfg.TAKE_PROFIT_2_PCT / 100.0)  # +20%
            else:  # SHORT
                take_profit_1_price = current_price * (1 - self.cfg.TAKE_PROFIT_1_PCT / 100.0)  # -10%
                take_profit_2_price = current_price * (1 - self.cfg.TAKE_PROFIT_2_PCT / 100.0)  # -20%
            
            take_profit_1_roi = self.cfg.TAKE_PROFIT_1_PCT * self.cfg.LEVERAGE
            take_profit_2_roi = self.cfg.TAKE_PROFIT_2_PCT * self.cfg.LEVERAGE
            
            log(f"✅ Take Profits FIXOS: TP1=10% (50% posição), TP2=20% (50% posição)", "INFO")
            
            # Registrar entrada com TODOS os dados
            trade_id = self.state.record_buy(
                price=current_price,
                amount=amount_coins,
                crypto=coin,
                operation=signal,
                rsi=rsi,
                atr=atr,
                stop_loss=stop_loss_price,
                take_profit_1=take_profit_1_price,
                take_profit_2=take_profit_2_price,
                ema_trend=ema_trend,
                atr_percentile=atr_percentile,
                volume_ratio=volume_ratio
            )
            
            log(f"", "INFO")
            log(f"🎯 ALVOS DEFINIDOS (monitoramento automático):", "INFO")
            log(f"   🔴 Stop Loss: ${stop_loss_price:.4f} (-{stop_loss_roi:.0f}% ROI)", "INFO")
            log(f"   � Take Profit 1: ${take_profit_1_price:.4f} (+{take_profit_1_roi:.0f}% ROI) - 50% posição", "INFO")
            log(f"   �🟢 Take Profit 2: ${take_profit_2_price:.4f} (+{take_profit_2_roi:.0f}% ROI) - 50% posição", "INFO")
            
            # Salvar alvos no estado para monitoramento (incluindo controle de TP1)
            self.state.state["active_targets"] = {
                "symbol": symbol,
                "coin": coin,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_2_price,  # Manter compatibilidade
                "take_profit_1_price": take_profit_1_price,
                "take_profit_2_price": take_profit_2_price,
                "amount": amount_coins,
                "amount_remaining": amount_coins,  # NOVO: rastrear quantidade restante
                "signal": signal,
                "entry_rsi": rsi,
                "entry_atr": atr,
                "trade_id": trade_id,
                "entry_time": datetime.now().isoformat(),
                "tp1_hit": False,  # NOVO: controle se TP1 já foi atingido
                "breakeven_set": False  # NOVO: controle se SL foi movido para breakeven
            }
            self.state.save_state()
            
            # Notificar Discord
            discord.send(
                f"{'🟢' if signal == 'LONG' else '🔴'} ENTRADA {signal} - {coin}",
                f"**Preço:** ${current_price:.4f}\n"
                f"**RSI:** {rsi:.2f}\n"
                f"**ATR:** ${atr:.4f} ({atr_percentile:.0f}º percentil)" if atr > 0 and atr_percentile else f"**RSI:** {rsi:.2f}\n" +
                f"**Capital usado:** ${amount_usd:.2f} ({self.cfg.ENTRY_CAPITAL_PCT}% do saldo)\n"
                f"**Leverage:** {self.cfg.LEVERAGE}x\n"
                f"**Valor nocional:** ${notional_value:.2f}\n"
                f"**Quantidade:** {amount_coins:.4f} {coin}\n\n"
                f"**Alvos automáticos:**\n"
                f"🔴 Stop Loss: ${stop_loss_price:.4f} ({-stop_loss_roi:+.0f}% ROI)\n"
                f"� TP1 (50%): ${take_profit_1_price:.4f} ({take_profit_1_roi:+.0f}% ROI)\n"
                f"🟢 TP2 (50%): ${take_profit_2_price:.4f} ({take_profit_2_roi:+.0f}% ROI)",
                0x00ff00 if signal == "LONG" else 0xff0000
            )
        
        return success
    
    def monitor_and_execute_exits(self):
        """
        Monitora posições ativas e executa saídas quando atingem Stop Loss ou Take Profit.
        Sistema controlado pelo bot (não pela exchange).
        Com suporte a TP1 parcial (50%), TP2 total, e breakeven após TP1.
        """
        # Verificar se há posição ativa
        active = self.state.state.get("active_targets")
        if not active:
            log("ℹ️  Nenhum active_targets encontrado - nada para monitorar", "DEBUG")
            log(f"   Estado atual: {list(self.state.state.keys())}", "DEBUG")
            
            # Tentar reconstruir se houver posição aberta
            if self.state.needs_reconstruction():
                log("🔧 Detectada posição sem targets - reconstruindo...", "WARN")
                self.state.reconstruct_from_hyperliquid(self.exchange)
            return
        
        symbol = active.get("symbol")
        coin = active.get("coin")
        entry_price = active.get("entry_price")
        stop_loss_price = active.get("stop_loss_price")
        take_profit_1_price = active.get("take_profit_1_price")  # TP1: 10%
        take_profit_2_price = active.get("take_profit_2_price")  # TP2: 20%
        amount_remaining = active.get("amount_remaining")  # Quantidade restante
        signal = active.get("signal")
        entry_rsi = active.get("entry_rsi")
        trade_id = active.get("trade_id")
        tp1_hit = active.get("tp1_hit", False)  # Controle de TP1
        breakeven_set = active.get("breakeven_set", False)  # Controle de breakeven
        
        if not all([symbol, coin, entry_price, stop_loss_price, take_profit_1_price, 
                    take_profit_2_price, amount_remaining, signal, trade_id]):
            log("⚠️ Dados incompletos em active_targets, ignorando monitoramento", "WARN")
            return
        
        try:
            # Buscar preço atual usando método com cache
            current_price = self.exchange.get_current_price(symbol)
            if current_price == 0.0:
                log(f"⚠️ Preço inválido para {symbol}, pulando monitoramento", "WARN")
                return
            
            # Calcular ROI atual
            if signal == "LONG":
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                price_change_pct = ((entry_price - current_price) / entry_price) * 100
            
            roi_current = price_change_pct * self.cfg.LEVERAGE
            
            # LOGS DETALHADOS PARA DEBUG
            log(f"", "INFO")
            log(f"🔍 DEBUG MONITORAMENTO - {coin} ({signal})", "INFO")
            log(f"   💰 Preço Atual: ${current_price:.4f}", "INFO")
            log(f"   📈 Preço Entrada: ${entry_price:.4f}", "INFO")
            log(f"   🎯 TP1 (10%): ${take_profit_1_price:.4f} {'✅ ATINGIDO' if (signal == 'LONG' and current_price >= take_profit_1_price) or (signal == 'SHORT' and current_price <= take_profit_1_price) else '❌ NÃO'}", "INFO")
            log(f"   🎯 TP2 (20%): ${take_profit_2_price:.4f} {'✅ ATINGIDO' if (signal == 'LONG' and current_price >= take_profit_2_price) or (signal == 'SHORT' and current_price <= take_profit_2_price) else '❌ NÃO'}", "INFO")
            log(f"   🛑 Stop Loss: ${stop_loss_price:.4f} {'🔴 ATINGIDO' if (signal == 'LONG' and current_price <= stop_loss_price) or (signal == 'SHORT' and current_price >= stop_loss_price) else '✅ SEGURO'}", "INFO")
            log(f"   📊 Variação: {price_change_pct:+.2f}% | ROI: {roi_current:+.2f}%", "INFO")
            log(f"   🔢 Quantidade Restante: {amount_remaining:.4f} {coin}", "INFO")
            log(f"   🏁 TP1 Executado: {'Sim' if tp1_hit else 'Não'}", "INFO")
            log(f"   🔒 Breakeven Ativo: {'Sim' if breakeven_set else 'Não'}", "INFO")
            
            # ============================================================
            # LÓGICA DE TP1 (10% - vende 50% da posição)
            # ============================================================
            if not tp1_hit:
                hit_tp1 = False
                if signal == "LONG":
                    if current_price >= take_profit_1_price:
                        hit_tp1 = True
                        log(f"🎯 CONDIÇÃO TP1 ATINGIDA! Preço ${current_price:.4f} >= TP1 ${take_profit_1_price:.4f}", "INFO")
                else:  # SHORT
                    if current_price <= take_profit_1_price:
                        hit_tp1 = True
                        log(f"🎯 CONDIÇÃO TP1 ATINGIDA! Preço ${current_price:.4f} <= TP1 ${take_profit_1_price:.4f}", "INFO")
                
                if hit_tp1:
                    log(f"🎯 TP1 (10%) atingido para {coin}!", "INFO")
                    log(f"   📊 Preço entrada: ${entry_price:.4f}", "INFO")
                    log(f"   💰 Preço TP1: ${current_price:.4f}", "INFO")
                    log(f"   📊 ROI: {roi_current:+.2f}%", "INFO")
                    
                    # Vender 50% da posição
                    amount_to_sell = amount_remaining * 0.5
                    exit_side = "sell" if signal == "LONG" else "buy"
                    amount_usd = amount_to_sell * current_price
                    
                    log(f"📤 EXECUTANDO VENDA TP1:", "INFO")
                    log(f"   Lado: {exit_side.upper()}", "INFO")
                    log(f"   Quantidade: {amount_to_sell:.4f} {coin}", "INFO")
                    log(f"   Valor USD: ${amount_usd:.2f}", "INFO")
                    log(f"   Leverage: {self.cfg.LEVERAGE}x", "INFO")
                    
                    success = self.exchange.create_market_order(
                        symbol,
                        exit_side,
                        amount_usd,
                        self.cfg.LEVERAGE
                    )
                    
                    if success:
                        log(f"✅ ORDEM TP1 EXECUTADA COM SUCESSO!", "INFO")
                        
                        # Registrar venda parcial no Google Sheets
                        self.state.record_sell(
                            current_price,
                            amount_to_sell,
                            coin,
                            signal,
                            rsi=None,
                            reason="Take Profit 1 (50%)",
                            trade_id=trade_id
                        )
                        
                        # Notificar Discord
                        discord.send(
                            f"🎯 TP1 EXECUTADO - {coin}",
                            f"**Preço de entrada:** ${entry_price:.4f}\n"
                            f"**Preço TP1:** ${current_price:.4f}\n"
                            f"**Quantidade vendida:** {amount_to_sell:.4f} {coin} (50%)\n"
                            f"**Quantidade restante:** {amount_remaining - amount_to_sell:.4f} {coin}\n"
                            f"**Operação:** {signal}\n"
                            f"**ROI:** {roi_current:+.2f}%\n"
                            f"**Trade ID:** {trade_id}",
                            0x00ff00
                        )
                        
                        # Atualizar estado: marcar TP1 como executado
                        self.state.state["active_targets"]["tp1_hit"] = True
                        self.state.state["active_targets"]["amount_remaining"] = amount_remaining - amount_to_sell
                        
                        # MOVER STOP LOSS PARA BREAKEVEN
                        if self.cfg.MOVE_SL_TO_BREAKEVEN:
                            old_sl = stop_loss_price
                            self.state.state["active_targets"]["stop_loss_price"] = entry_price
                            self.state.state["active_targets"]["breakeven_set"] = True
                            self.state.save_state()
                            
                            log(f"🔒 Stop Loss movido para BREAKEVEN: ${old_sl:.4f} → ${entry_price:.4f}", "INFO")
                            discord.send(
                                f"🔒 STOP LOSS MOVIDO PARA BREAKEVEN - {coin}",
                                f"**Stop Loss anterior:** ${old_sl:.4f}\n"
                                f"**Novo Stop Loss (breakeven):** ${entry_price:.4f}\n"
                                f"**Trade ID:** {trade_id}",
                                0xffff00
                            )
                        else:
                            self.state.save_state()
                        
                        log(f"✅ TP1 executado! 50% vendido, SL movido para breakeven", "INFO")
                        return  # Sair para evitar checar TP2/SL no mesmo ciclo
                    else:
                        log(f"❌ ERRO AO EXECUTAR ORDEM TP1! Verifique create_market_order", "ERROR")
                        return
                else:
                    log(f"⏳ TP1 ainda não atingido (aguardando ${take_profit_1_price:.4f})", "DEBUG")
            else:
                log(f"✅ TP1 já foi executado anteriormente", "DEBUG")
            
            # ============================================================
            # LÓGICA DE TP2 (20% - vende 100% da posição total)
            # ============================================================
            hit_tp2 = False
            if signal == "LONG":
                if current_price >= take_profit_2_price:
                    hit_tp2 = True
                    log(f"🎯 CONDIÇÃO TP2 ATINGIDA! Preço ${current_price:.4f} >= TP2 ${take_profit_2_price:.4f}", "INFO")
            else:  # SHORT
                if current_price <= take_profit_2_price:
                    hit_tp2 = True
                    log(f"🎯 CONDIÇÃO TP2 ATINGIDA! Preço ${current_price:.4f} <= TP2 ${take_profit_2_price:.4f}", "INFO")
            
            # ============================================================
            # LÓGICA DE STOP LOSS (agora pode ser breakeven)
            # ============================================================
            hit_stop_loss = False
            if signal == "LONG":
                if current_price <= stop_loss_price:
                    hit_stop_loss = True
                    log(f"🛑 CONDIÇÃO STOP LOSS ATINGIDA! Preço ${current_price:.4f} <= SL ${stop_loss_price:.4f}", "INFO")
            else:  # SHORT
                if current_price >= stop_loss_price:
                    hit_stop_loss = True
                    log(f"🛑 CONDIÇÃO STOP LOSS ATINGIDA! Preço ${current_price:.4f} >= SL ${stop_loss_price:.4f}", "INFO")
            
            # Executar saída total (TP2 ou SL)
            if hit_stop_loss or hit_tp2:
                exit_type = "Stop Loss" if hit_stop_loss else "Take Profit 2"
                emoji = "🔴" if hit_stop_loss else "🟢"
                
                # Se SL e breakeven_set=True, foi saída no breakeven (sem perda nem ganho)
                if hit_stop_loss and breakeven_set:
                    exit_type = "Breakeven (Stop Loss)"
                    emoji = "🟡"
                    log(f"🟡 SAÍDA NO BREAKEVEN DETECTADA!", "INFO")
                
                log(f"{emoji} {exit_type} atingido para {coin}!", "INFO")
                log(f"   📊 Preço entrada: ${entry_price:.4f}", "INFO")
                log(f"   💰 Preço saída: ${current_price:.4f}", "INFO")
                log(f"   📊 ROI: {roi_current:+.2f}%", "INFO")
                
                # Vender a quantidade restante (100% no caso do TP2)
                exit_side = "sell" if signal == "LONG" else "buy"
                amount_usd = amount_remaining * current_price
                
                log(f"📤 EXECUTANDO VENDA {exit_type.upper()}:", "INFO")
                log(f"   Lado: {exit_side.upper()}", "INFO")
                log(f"   Quantidade: {amount_remaining:.4f} {coin}", "INFO")
                log(f"   Valor USD: ${amount_usd:.2f}", "INFO")
                log(f"   Leverage: {self.cfg.LEVERAGE}x", "INFO")
                
                success = self.exchange.create_market_order(
                    symbol,
                    exit_side,
                    amount_usd,
                    self.cfg.LEVERAGE
                )
                
                if success:
                    log(f"✅ ORDEM {exit_type.upper()} EXECUTADA COM SUCESSO!", "INFO")
                    
                    # Registrar venda final no Google Sheets
                    reason = exit_type
                    self.state.record_sell(
                        current_price,
                        amount_remaining,
                        coin,
                        signal,
                        rsi=None,
                        reason=reason,
                        trade_id=trade_id
                    )
                    
                    # Notificar Discord
                    discord.send(
                        f"{emoji} {exit_type.upper()} EXECUTADO - {coin}",
                        f"**Preço de entrada:** ${entry_price:.4f}\n"
                        f"**Preço de saída:** ${current_price:.4f}\n"
                        f"**Quantidade vendida:** {amount_remaining:.4f} {coin}\n"
                        f"**Operação:** {signal}\n"
                        f"**ROI:** {roi_current:+.2f}%\n"
                        f"**Trade ID:** {trade_id}",
                        0xff0000 if hit_stop_loss else 0x00ff00
                    )
                    
                    # Limpar estado (trade finalizado)
                    self.state.state["active_targets"] = {}
                    self.state.state["position_entries"] = []
                    self.state.save_state()
                    
                    log(f"✅ Posição {coin} fechada completamente!", "INFO")
                else:
                    log(f"❌ Erro ao executar ordem de saída para {coin}", "ERROR")
            else:
                # Log de monitoramento
                log(f"👀 Monitorando {coin}: ${current_price:.4f} | ROI {roi_current:+.2f}% | "
                    f"SL ${stop_loss_price:.4f} | TP1 ${take_profit_1_price:.4f} | TP2 ${take_profit_2_price:.4f} | "
                    f"TP1_hit={tp1_hit} | Restante={amount_remaining:.4f}", "DEBUG")

                
        except Exception as e:
            log(f"❌ Erro monitorando saídas: {e}", "ERROR")
    
    def cancel_all_orders(self, symbol: str):
        """Cancela todas as ordens abertas de um símbolo"""
        try:
            orders = self.exchange.hyperliquid.fetch_open_orders(symbol)
            if orders:
                coin = symbol.split('/')[0]
                log(f"🗑️  Cancelando {len(orders)} ordens de {coin}...", "INFO")
                for order in orders:
                    self.exchange.hyperliquid.cancel_order(order['id'], symbol)
                    log(f"   ✅ Ordem {order['id']} cancelada", "DEBUG")
            else:
                log(f"   ℹ️  Nenhuma ordem aberta para {symbol}", "DEBUG")
        except Exception as e:
            log(f"❌ Erro cancelando ordens de {symbol}: {e}", "ERROR")
    
    def run_cycle(self):
        """Executa um ciclo da estratégia para todos os assets"""
        log("=" * 80, "INFO")
        log("🔄 INICIANDO CICLO", "INFO")
        log("=" * 80, "INFO")
        
        # NOVO SISTEMA: Monitorar posições ativas e executar saídas
        self.monitor_and_execute_exits()
        
        # Mostrar estado atual
        self.state.show_state_summary()
        
        # Mostrar saldo disponível
        balance = self.exchange.get_balance()
        log(f"💰 Saldo disponível: ${balance:.2f}", "INFO")
        
        try:
            # Analisar cada asset
            for symbol in self.cfg.SYMBOLS:
                coin = symbol.split('/')[0]
                log(f"", "INFO")
                log(f"🔍 Analisando {coin}...", "INFO")
                
                analysis = self.analyze_asset(symbol)
                
                if not analysis:
                    log(f"⚠️ Análise falhou para {coin}, pulando", "WARN")
                    continue
                
                # Verificar sinal de entrada
                if self.should_enter(analysis):
                    # Cancelar todas as ordens abertas antes de entrar
                    self.cancel_all_orders(symbol)
                    # Executar entrada (LONG ou SHORT)
                    self.execute_entry(analysis)
            
            log("", "INFO")
            log("✅ Ciclo concluído", "INFO")
            
        except Exception as e:
            log(f"❌ Erro no ciclo: {e}", "ERROR")
            import traceback
            traceback.print_exc()

# ===== MAIN =====
def main():
    """Função principal"""
    setup_log_file()
    
    log("=" * 80, "INFO")
    log("🚀 INICIANDO SISTEMA DE TRADING - EMA 200 + RSI", "INFO")
    log("=" * 80, "INFO")
    
    # Carregar variáveis de ambiente
    try:
        from dotenv import load_dotenv
        # Tentar carregar .env.dca primeiro, senão .env padrão
        if os.path.exists('.env.dca'):
            load_dotenv('.env.dca')
            log("✅ Carregado .env.dca", "INFO")
        else:
            load_dotenv()
            log("✅ Carregado .env", "INFO")
    except ImportError:
        log("⚠️ python-dotenv não instalado, usando variáveis de ambiente do sistema", "WARN")
    
    # Configuração
    cfg = TradingConfig()
    
    log(f"⚙️  Configuração:", "INFO")
    log(f"   Assets: {', '.join([s.split('/')[0] for s in cfg.SYMBOLS])} ({cfg.LEVERAGE}x leverage)", "INFO")
    log(f"   Timeframe: {cfg.TIMEFRAME}", "INFO")
    log(f"   RSI: {cfg.RSI_PERIOD} períodos", "INFO")
    log(f"   Entrada LONG: RSI < {cfg.RSI_LONG_THRESHOLD} (sobrevendido)", "INFO")
    log(f"   Entrada SHORT: RSI > {cfg.RSI_SHORT_THRESHOLD} (sobrecomprado)", "INFO")
    log(f"   Capital por entrada: {cfg.ENTRY_CAPITAL_PCT}%", "INFO")
    log(f"   Cooldown entrada: {cfg.ENTRY_COOLDOWN_HOURS}h (2 dias)", "INFO")
    log(f"   Stop Loss: ATR dinâmico (1.5x) ou {cfg.STOP_LOSS_PRICE_PCT:.1f}% fixo", "INFO")
    log(f"   Take Profit 1: {cfg.TAKE_PROFIT_1_PCT:.1f}% (vende {cfg.TP1_SELL_PCT:.0f}%)", "INFO")
    log(f"   Take Profit 2: {cfg.TAKE_PROFIT_2_PCT:.1f}% (vende 100%)", "INFO")
    log(f"   Breakeven após TP1: {'Sim' if cfg.MOVE_SL_TO_BREAKEVEN else 'Não'}", "INFO")
    
    # Criar estratégia
    strategy = TradingStrategy(cfg)
    
    # Loop principal
    log("🔁 Entrando no loop principal (Ctrl+C para parar)", "INFO")
    
    # Intervalo de verificação: 5 minutos (reduzido de 3 para evitar rate limit)
    check_interval = 300  # 5 minutos em segundos
    
    log(f"⏰ Intervalo entre ciclos: {check_interval/60:.0f} minutos", "INFO")
    log(f"ℹ️  Aumentado para 5 min para evitar rate limiting da API", "INFO")
    
    try:
        while True:
            strategy.run_cycle()
            
            log(f"⏰ Próximo ciclo em {check_interval/60:.0f} minutos...", "INFO")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        log("🛑 Sistema interrompido pelo usuário", "INFO")
    except Exception as e:
        log(f"❌ Erro fatal: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    
    log("👋 Sistema encerrado", "INFO")

if __name__ == "__main__":
    main()