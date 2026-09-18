import time
import os
import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP

# Configuração das chaves via Variáveis de Ambiente
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")

# Inicialização da sessão Bybit (USDT Perpetual / Futures)
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

SYMBOL = "BTCUSDT"
CATEGORY = "linear"
TIMEFRAME = "5"      # Velas de 5 minutos
POSITION_QTY = 0.001 # Tamanho da posição em BTC

def fetch_klines():
    """Procura as últimas 200 velas de 5m do BTCUSDT"""
    response = session.get_kline(
        category=CATEGORY,
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=200
    )
    raw_data = response['result']['list']
    
    df = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df = df.iloc[::-1].reset_index(drop=True)
    
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    return df

def calculate_indicators(df):
    """Calcula a EMA 20 e a VWAP"""
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return df

def check_open_positions():
    """Verifica se já existe uma posição aberta no BTCUSDT"""
    positions = session.get_positions(category=CATEGORY, symbol=SYMBOL)
    for pos in positions['result']['list']:
        if float(pos['size']) > 0:
            return True
    return False

def run_bot():
    print("🤖 Bot iniciado e a monitorizar BTCUSDT 5m...")
    
    while True:
        try:
            if check_open_positions():
                print("⏳ Posição já aberta. A aguardar fecho...")
                time.sleep(60)
                continue

            df = fetch_klines()
            df = calculate_indicators(df)
            
            last_candle = df.iloc[-2]
            
            close_price = last_candle['close']
            open_price = last_candle['open']
            ema20 = last_candle['ema20']
            vwap = last_candle['vwap']
            low_price = last_candle['low']
            
            is_vwap_bull = close_price > vwap
            is_ema_bull = close_price > ema20
            is_green_candle = close_price > open_price
            
            if is_vwap_bull and is_ema_bull and is_green_candle:
                print(f"🚀 SINAL DETETADO! Preço: {close_price} | VWAP: {vwap:.2f} | EMA20: {ema20:.2f}")
                stop_loss = round(low_price * 0.999, 2)
                
                order = session.place_order(
                    category=CATEGORY,
                    symbol=SYMBOL,
                    side="Buy",
                    orderType="Market",
                    qty=str(POSITION_QTY),
                    stopLoss=str(stop_loss),
                    timeInForce="GTC"
                )
                print(f"✅ Posição Aberta com sucesso! ID da Ordem: {order['result']['orderId']}")
            else:
                print("💤 Sem sinal na última vela. A aguardar próxima verificação...")

        except Exception as e:
            print(f"⚠️ Erro no processamento: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
          
