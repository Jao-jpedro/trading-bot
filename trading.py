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

def _http_post_json(url: str, payload: dict, timeout: int = _HTTP_TIMEOUT):
    """Helper para fazer requisições POST JSON"""
    try:
        r = _SESSION.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
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
                # Criar cabeçalho com ID e colunas de indicadores
                self.worksheet.update('A1:I1', [[
                    'ID', 'Data', 'Hora', 'Preço', 'Cripto', 'Operação', 'Tipo de Operação', 'RSI', 'Motivo'
                ]])
                log("✅ Cabeçalhos criados na planilha", "INFO")
            
            self.enabled = True
            log(f"✅ Google Sheets configurado com sucesso", "INFO")
            
        except Exception as e:
            log(f"❌ Erro conectando ao Google Sheets: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            self.enabled = False
    
    def log_trade(self, price: float, crypto: str, operation: str, trade_type: str, rsi: float = None, reason: str = "", trade_id: str = ""):
        """
        Registra uma operação na planilha
        
        Args:
            price: Preço da operação
            crypto: Nome da criptomoeda (ex: SOL, XRP)
            operation: Tipo de operação (LONG ou SHORT)
            trade_type: Tipo de trade (Compra ou Venda)
            rsi: Valor do RSI no momento da operação
            reason: Motivo da operação (ex: "RSI < 20", "Stop Loss", "Take Profit")
            trade_id: ID único para vincular compra e venda
        """
        if not self.enabled:
            log("⚠️ Google Sheets não habilitado, registro ignorado", "DEBUG")
            return False
        
        try:
            # Obter data e hora atual
            now = datetime.now()
            data = now.strftime("%d/%m/%Y")
            hora = now.strftime("%H:%M:%S")
            
            # Preparar linha de dados com ID na primeira coluna
            rsi_str = f"{rsi:.2f}" if rsi is not None else "-"
            row = [trade_id, data, hora, f"{price:.4f}", crypto, operation, trade_type, rsi_str, reason]
            
            # Adicionar linha na planilha
            self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            
            log(f"📊 Registro Google Sheets: ID={trade_id} | {data} {hora} | {crypto} | {operation} | {trade_type} @ ${price:.4f} | RSI: {rsi_str} | {reason}", "INFO")
            return True
            
        except Exception as e:
            log(f"❌ Erro registrando no Google Sheets: {e}", "ERROR")
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
    ENTRY_CAPITAL_PCT: float = 30.0   # Usa 30% do capital por entrada
    ENTRY_COOLDOWN_HOURS: int = 48    # Cooldown de 48h entre entradas no mesmo asset
    
    # Estratégia de SAÍDA (Stop Loss e Take Profit)
    # Com leverage 5x:
    #   - 2% de movimento no preço = 10% ROI
    #   - 4% de movimento no preço = 20% ROI
    STOP_LOSS_PRICE_PCT: float = 2.0    # 2% no preço = 10% ROI (ambos lados)
    TAKE_PROFIT_PRICE_PCT: float = 4.0  # 4% no preço = 20% ROI (ambos lados)
    
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
            
            # Buscar posição atual
            position = self.exchange.get_position()
            
            # Se tem posição aberta mas sem entries no estado, precisa reconstruir
            if position and abs(float(position.get("contracts", 0))) > 0:
                has_entries = len(self.state.get("position_entries", [])) > 0
                if not has_entries:
                    log(f"🔍 Posição detectada ({abs(float(position.get('contracts', 0))):.4f} {position.get('symbol', 'SOL')}) mas estado vazio", "WARN")
                    return True
            
            return False
            
        except Exception as e:
            log(f"Erro verificando necessidade de reconstrução: {e}", "DEBUG")
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
                    
                    # Detectar COMPRAS: "Open Long" ou "Open Short" (que seria fechar uma short anterior)
                    if "Open Long" in direction or direction == "Open Long":
                        # É uma compra
                        entries.append({
                            "price": px,
                            "amount": sz,
                            "timestamp": timestamp.isoformat()
                        })
                        last_buy_time = timestamp
                        log(f"   🟢 Compra: {sz:.4f} SOL @ ${px:.4f} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                    
                    # Detectar VENDAS: "Close Long" (fechar posição long) ou "Open Short" (vender a descoberto)
                    elif "Close Long" in direction or direction == "Close Long":
                        # É uma venda (fechando long)
                        last_sell_time = timestamp
                        
                        # Remover proporcionalmente dos entries (FIFO - first in, first out)
                        remaining_to_sell = sz
                        i = 0
                        while i < len(entries) and remaining_to_sell > 0:
                            if entries[i]["amount"] <= remaining_to_sell:
                                # Remove entrada completamente
                                remaining_to_sell -= entries[i]["amount"]
                                entries.pop(i)
                            else:
                                # Remove parcialmente
                                entries[i]["amount"] -= remaining_to_sell
                                remaining_to_sell = 0
                                i += 1
                        
                        log(f"   🔴 Venda: {sz:.4f} SOL @ ${px:.4f} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                        
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
            return True
            
        except Exception as e:
            log(f"❌ Erro reconstruindo estado: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
            return False
    
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
    
    def record_buy(self, price: float, amount: float, crypto: str = "SOL", operation: str = "LONG", rsi: float = None):
        """Registra uma compra"""
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
            "operation": operation,
            "trade_id": trade_id  # Salvar ID para usar na venda
        })
        self.save_state()
        
        log(f"💾 COMPRA REGISTRADA NO ESTADO:", "INFO")
        log(f"   🆔 Trade ID: {trade_id}", "INFO")
        log(f"   📅 Data/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        log(f"   💰 Preço: ${price:.4f}", "INFO")
        log(f"   🪙 Quantidade: {amount:.4f} {crypto}", "INFO")
        log(f"   📊 RSI: {rsi:.2f}" if rsi else "", "INFO")
        log(f"   ⏰ Próxima compra: após {(now + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M')}", "INFO")
        
        # Determinar motivo
        if operation == "LONG":
            reason = f"RSI sobrevendido ({rsi:.2f} < 20)" if rsi else "Entrada LONG"
        else:
            reason = f"RSI sobrecomprado ({rsi:.2f} > 80)" if rsi else "Entrada SHORT"
        
        # Registrar no Google Sheets com trade_id
        sheets_logger.log_trade(
            price=price,
            crypto=crypto,
            operation=operation,
            trade_type="Compra",
            rsi=rsi,
            reason=reason,
            trade_id=trade_id
        )
        
        return trade_id  # Retornar ID para usar depois
    
    def record_sell(self, price: float, amount: float, crypto: str = "SOL", operation: str = "LONG", rsi: float = None, reason: str = "", trade_id: str = ""):
        """Registra uma venda"""
        now = datetime.now()
        self.state["last_sell_timestamp"] = now.isoformat()
        self.save_state()
        
        log(f"💾 VENDA REGISTRADA NO ESTADO:", "INFO")
        log(f"   🆔 Trade ID: {trade_id}", "INFO")
        log(f"   📅 Data/Hora: {now.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        log(f"   💰 Preço: ${price:.4f}", "INFO")
        log(f"   🪙 Quantidade: {amount:.4f} {crypto}", "INFO")
        log(f"   📊 RSI: {rsi:.2f}" if rsi else "", "INFO")
        log(f"   🎯 Motivo: {reason}", "INFO")
        
        # Registrar no Google Sheets com mesmo trade_id da compra
        sheets_logger.log_trade(
            price=price,
            crypto=crypto,
            operation=operation,
            trade_type="Venda",
            rsi=rsi,
            reason=reason,
            trade_id=trade_id
        )
    
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
        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY") or os.getenv("PRIVATE_KEY", "")
        vault_address = os.getenv("HYPERLIQUID_SUBACCOUNT") or os.getenv("VAULT_ADDRESS", "")  # Subconta
        
        if not wallet_address or not private_key:
            raise ValueError("WALLET_ADDRESS e HYPERLIQUID_PRIVATE_KEY devem estar configurados")
        
        if not vault_address:
            raise ValueError("HYPERLIQUID_SUBACCOUNT (vault/subconta) deve estar configurada")
        
        log(f"🏦 Configurando operação na subconta (vault): {vault_address}", "INFO")
        log(f"🔑 Carteira principal (assinatura): {wallet_address}", "INFO")
        
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
            
            # Adicionar delay para evitar rate limit
            time.sleep(0.5)  # 500ms entre requisições
            
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
        """Busca preço atual de um símbolo"""
        try:
            coin = symbol.split('/')[0]
            
            # Buscar direto da Hyperliquid
            ticker = self.hyperliquid.fetch_ticker(symbol)
            price = ticker['last']
            log(f"💰 Preço atual {coin}: ${price:.4f}", "DEBUG")
            return price
        except Exception as e:
            log(f"❌ Erro buscando preço {symbol}: {e}", "ERROR")
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
        """Cria ordem market na Hyperliquid"""
        try:
            # Configurar leverage primeiro
            log(f"🔧 Configurando leverage {leverage}x para {symbol}", "DEBUG")
            self.hyperliquid.set_leverage(leverage, symbol, {"marginMode": "isolated"})
            
            # Buscar preço atual
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                log("❌ Preço inválido, não é possível criar ordem", "ERROR")
                return False
            
            # Calcular quantidade de coins com alavancagem
            # Fórmula: amount = (USD_a_gastar * leverage) / preço
            notional = amount_usd * leverage
            amount = notional / current_price
            
            # Arredondar quantidade conforme precisão do mercado
            amount = float(self.hyperliquid.amount_to_precision(symbol, amount))
            
            # Verificar valor mínimo
            notional_value = amount * current_price
            if notional_value < self.cfg.MIN_ORDER_USD:
                log(f"❌ Valor nocional muito baixo: ${notional_value:.2f} < ${self.cfg.MIN_ORDER_USD}", "ERROR")
                return False
            
            coin = symbol.split('/')[0]
            log(f"📤 Criando ordem: {side} {amount:.4f} {coin}", "INFO")
            log(f"   💰 USD investidos: ${amount_usd:.2f}", "INFO")
            log(f"   📊 Leverage: {leverage}x", "INFO")
            log(f"   💵 Valor nocional: ${notional:.2f}", "INFO")
            log(f"   📈 Preço: ${current_price:.4f}", "INFO")
            
            # Criar ordem market (Hyperliquid exige price para calcular slippage)
            order = self.hyperliquid.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                price=current_price,  # Necessário para Hyperliquid calcular slippage
                params={}
            )
            
            log(f"✅ Ordem criada com sucesso: {order}", "INFO")
            return True
            
        except Exception as e:
            log(f"❌ Erro criando ordem: {e}", "ERROR")
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
        
        # Executar ordem MARKET
        success = self.exchange.create_market_order(symbol, side, amount_usd, self.cfg.LEVERAGE)
        
        if success:
            # Registrar entrada com RSI e capturar trade_id
            trade_id = self.state.record_buy(current_price, amount_coins, coin, signal, rsi)
            
            # Calcular preços de SL e TP para referência
            stop_loss_roi = self.cfg.STOP_LOSS_PRICE_PCT * self.cfg.LEVERAGE
            take_profit_roi = self.cfg.TAKE_PROFIT_PRICE_PCT * self.cfg.LEVERAGE
            
            if signal == "LONG":
                stop_loss_price = current_price * (1 - self.cfg.STOP_LOSS_PRICE_PCT / 100.0)
                take_profit_price = current_price * (1 + self.cfg.TAKE_PROFIT_PRICE_PCT / 100.0)
            else:
                stop_loss_price = current_price * (1 + self.cfg.STOP_LOSS_PRICE_PCT / 100.0)
                take_profit_price = current_price * (1 - self.cfg.TAKE_PROFIT_PRICE_PCT / 100.0)
            
            log(f"", "INFO")
            log(f"🎯 ALVOS DEFINIDOS (monitoramento automático):", "INFO")
            log(f"   🔴 Stop Loss: ${stop_loss_price:.4f} (-{stop_loss_roi:.0f}% ROI)", "INFO")
            log(f"   🟢 Take Profit: ${take_profit_price:.4f} (+{take_profit_roi:.0f}% ROI)", "INFO")
            
            # Salvar alvos no estado para monitoramento (incluindo trade_id)
            self.state.state["active_targets"] = {
                "symbol": symbol,
                "coin": coin,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "amount": amount_coins,
                "signal": signal,
                "entry_rsi": rsi,
                "trade_id": trade_id  # Salvar trade_id para usar na venda
            }
            self.state.save_state()
            
            # Notificar Discord
            discord.send(
                f"{'🟢' if signal == 'LONG' else '🔴'} ENTRADA {signal} - {coin}",
                f"**Preço:** ${current_price:.4f}\n"
                f"**RSI:** {rsi:.2f}\n"
                f"**Capital usado:** ${amount_usd:.2f} ({self.cfg.ENTRY_CAPITAL_PCT}% do saldo)\n"
                f"**Leverage:** {self.cfg.LEVERAGE}x\n"
                f"**Valor nocional:** ${notional_value:.2f}\n"
                f"**Quantidade:** {amount_coins:.4f} {coin}\n\n"
                f"**Alvos automáticos:**\n"
                f"🔴 Stop Loss: ${stop_loss_price:.4f} ({-stop_loss_roi:+.0f}% ROI)\n"
                f"🟢 Take Profit: ${take_profit_price:.4f} ({take_profit_roi:+.0f}% ROI)",
                0x00ff00 if signal == "LONG" else 0xff0000
            )
        
        return success
    
    def monitor_and_execute_exits(self):
        """
        Monitora posições ativas e executa saídas quando atingem Stop Loss ou Take Profit.
        Sistema controlado pelo bot (não pela exchange).
        """
        # Verificar se há posição ativa
        active = self.state.state.get("active_targets")
        if not active:
            return
        
        symbol = active.get("symbol")
        coin = active.get("coin")
        entry_price = active.get("entry_price")
        stop_loss_price = active.get("stop_loss_price")
        take_profit_price = active.get("take_profit_price")
        amount = active.get("amount")
        signal = active.get("signal")
        entry_rsi = active.get("entry_rsi")
        trade_id = active.get("trade_id")
        
        if not all([symbol, coin, entry_price, stop_loss_price, take_profit_price, amount, signal, trade_id]):
            log("⚠️ Dados incompletos em active_targets, ignorando monitoramento", "WARN")
            return
        
        try:
            # Buscar preço atual
            ticker = self.exchange.hyperliquid.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calcular ROI atual
            if signal == "LONG":
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                price_change_pct = ((entry_price - current_price) / entry_price) * 100
            
            roi_current = price_change_pct * self.cfg.LEVERAGE
            
            # Verificar se atingiu Stop Loss ou Take Profit
            hit_stop_loss = False
            hit_take_profit = False
            
            if signal == "LONG":
                # LONG: SL abaixo, TP acima
                if current_price <= stop_loss_price:
                    hit_stop_loss = True
                elif current_price >= take_profit_price:
                    hit_take_profit = True
            else:  # SHORT
                # SHORT: SL acima, TP abaixo
                if current_price >= stop_loss_price:
                    hit_stop_loss = True
                elif current_price <= take_profit_price:
                    hit_take_profit = True
            
            # Executar saída se necessário
            if hit_stop_loss or hit_take_profit:
                exit_type = "Stop Loss" if hit_stop_loss else "Take Profit"
                emoji = "🔴" if hit_stop_loss else "🟢"
                
                log(f"{emoji} {exit_type} atingido para {coin}!", "INFO")
                log(f"   📊 Preço entrada: ${entry_price:.4f}", "INFO")
                log(f"   � Preço atual: ${current_price:.4f}", "INFO")
                log(f"   📊 ROI: {roi_current:+.2f}%", "INFO")
                
                # Executar ordem de saída (MARKET para garantir execução imediata)
                exit_side = "sell" if signal == "LONG" else "buy"
                
                # Calcular valor em USD para fechar posição
                amount_usd = amount * current_price
                
                success = self.exchange.create_market_order(
                    symbol,
                    exit_side,
                    amount_usd,
                    self.cfg.LEVERAGE
                )
                
                if success:
                    # Registrar venda no Google Sheets com mesmo trade_id da compra
                    reason = exit_type
                    self.state.record_sell(
                        current_price,
                        amount,
                        coin,
                        signal,
                        rsi=None,  # Não temos RSI na saída
                        reason=reason,
                        trade_id=trade_id  # Usar o mesmo ID da compra!
                    )
                    
                    # Notificar Discord
                    discord.send(
                        f"{emoji} {exit_type.upper()} EXECUTADO - {coin}",
                        f"**Preço de entrada:** ${entry_price:.4f}\n"
                        f"**Preço de saída:** ${current_price:.4f}\n"
                        f"**Quantidade:** {amount:.4f} {coin}\n"
                        f"**Operação:** {signal}\n"
                        f"**ROI:** {roi_current:+.2f}%\n"
                        f"**Trade ID:** {trade_id}",
                        0xff0000 if hit_stop_loss else 0x00ff00
                    )
                    
                    # Limpar estado
                    self.state.state["active_targets"] = {}
                    self.state.state["position_entries"] = []
                    self.state.save_state()
                    
                    log(f"✅ Posição {coin} fechada com sucesso!", "INFO")
                else:
                    log(f"❌ Erro ao executar ordem de saída para {coin}", "ERROR")
            else:
                # Apenas log de monitoramento (sem poluir muito)
                log(f"👀 Monitorando {coin}: Preço ${current_price:.4f} | ROI {roi_current:+.2f}% | SL ${stop_loss_price:.4f} | TP ${take_profit_price:.4f}", "DEBUG")
                
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
    log(f"   Stop Loss: {cfg.STOP_LOSS_PRICE_PCT:.1f}% preço = 10% ROI", "INFO")
    log(f"   Take Profit: {cfg.TAKE_PROFIT_PRICE_PCT:.1f}% preço = 20% ROI", "INFO")
    
    # Criar estratégia
    strategy = TradingStrategy(cfg)
    
    # Loop principal
    log("🔁 Entrando no loop principal (Ctrl+C para parar)", "INFO")
    
    # Intervalo de verificação (a cada 60 segundos para monitoramento rápido)
    check_interval = 60  # 60 segundos
    
    try:
        while True:
            strategy.run_cycle()
            
            log(f"⏰ Próximo ciclo em {check_interval} segundos...", "INFO")
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