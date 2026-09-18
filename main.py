import os
import time
from threading import Thread
from flask import Flask
import pandas as pd
from pybit.unified_trading import HTTP

# ------------------------------------------------------------------
# 1. SERVIDOR FLASK (Para o UptimeRobot manter o Render ativo)
# ------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Trading Bybit está ativo e a funcionar!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Inicia o Flask numa thread secundária
Thread(target=run_flask, daemon=True).start()

# ------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA BYBIT E VARIÁVEIS DE AMBIENTE
# ------------------------------------------------------------------
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")

# Conexão com a API da Bybit (Live / Unified Account)
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

SYMBOL = "BTCUSDT"
CATEGORY = "linear"
QTY = "0.001"        # Tamanho da posição (~$80 no mercado atual)
TIMEFRAME = "5"      # Gráfico de 5 Minutos

# ------------------------------------------------------------------
# 3. ESTRATÉGIA DE EMA RÁPIDA (EMA 9 + EMA 21)
# ------------------------------------------------------------------
def get_klines():
    """Obtém as últimas velas da Bybit"""
    try:
        response = session.get_kline(
            category=CATEGORY,
            symbol=SYMBOL,
            interval=TIMEFRAME,
            limit=50
        )
        data = response['result']['list']
        
        # Converter para DataFrame (A Bybit devolve do mais recente para o mais antigo)
        df = pd.DataFrame(data, columns=[
            'startTime', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # Converter colunas numéricas
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Inverter para ordem cronológica correta (antigo -> recente)
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[ERRO OBTER K LINES]: {e}")
        return None

def check_signal(df):
    """Calcula indicadores e verifica condições de entrada"""
    if df is None or len(df) < 25:
        return "HOLD"

    # Cálculo das EMAs 9 e 21
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # Selecionar a última vela FECHADA (iloc[-2])
    last_candle = df.iloc[-2]

    # Condições da Estratégia
    cond_price_above_ema9 = last_candle['close'] > last_candle['ema9']
    cond_ema_cross = last_candle['ema9'] > last_candle['ema21']
    cond_green_candle = last_candle['close'] > last_candle['open']

    # Imprimir estado no log para acompanhamento
    print(f"[ANALISE] Preço: {last_candle['close']} | EMA9: {round(last_candle['ema9'], 2)} | EMA21: {round(last_candle['ema21'], 2)}")

    if cond_price_above_ema9 and cond_ema_cross and cond_green_candle:
        return "BUY"

    return "HOLD"

# ------------------------------------------------------------------
# 4. GESTÃO DE POSIÇÕES E EXECUÇÃO
# ------------------------------------------------------------------
def get_open_positions():
    """Verifica se já existe alguma posição aberta"""
    try:
        res = session.get_positions(category=CATEGORY, symbol=SYMBOL)
        positions = res['result']['list']
        for p in positions:
            if float(p['size']) > 0:
                return True
        return False
    except Exception as e:
        print(f"[ERRO VERIFICAR POSICAO]: {e}")
        return True # Retorna True por segurança para evitar ordens duplicadas

def execute_buy():
    """Envia a ordem de compra Market para a Bybit"""
    try:
        order = session.place_order(
            category=CATEGORY,
            symbol=SYMBOL,
            side="Buy",
            orderType="Market",
            qty=QTY,
            timeInForce="GTC"
        )
        print(f"🚀 [ORDEM EXECUTADA COM SUCESSO]: {order}")
    except Exception as e:
        print(f"❌ [ERRO AO COLOCAR ORDEM]: {e}")

# ------------------------------------------------------------------
# 5. LOOP PRINCIPAL DE NAVEGAÇÃO / MONITORIZAÇÃO
# ------------------------------------------------------------------
print("🤖 Bot de Trading Iniciado com sucesso. A monitorizar mercado...")

while True:
    try:
        # 1. Verificar se já há posição aberta
        has_position = get_open_positions()

        if not has_position:
            # 2. Buscar dados e analisar sinal
            df_klines = get_klines()
            signal = check_signal(df_klines)

            if signal == "BUY":
                print("🟢 Sinal de COMPRA detetado! A enviar ordem...")
                execute_buy()
            else:
                print("⏳ Condições não preenchidas. A aguardar...")
        else:
            print("📊 Posição já aberta no mercado. A monitorizar...")

    except Exception as e:
        print(f"[ERRO NO LOOP]: {e}")

    # Aguarda 30 segundos antes de realizar nova verificação
    time.sleep(30)
    
