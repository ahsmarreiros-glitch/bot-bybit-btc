def check_signal(df):
    """
    Estratégia de Tendência Rápida (EMA 9 + EMA 21 + Volume)
    Captura impulsos fortes de preço como o rompimento das 14:35.
    """
    # 1. Cálculo das Médias Móveis Exponenciais
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # 2. Cálculo da Média de Volume (últimas 20 velas)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()

    # Seleciona a última vela que FECHOU (iloc[-2]) para evitar sinais falsos de velas em aberto
    last_candle = df.iloc[-2]

    # Condições de Entrada:
    # A) Preço de fecho acima da EMA 9
    cond_price_above_ema9 = last_candle['close'] > last_candle['ema9']
    
    # B) Tendência de alta nas Médias (EMA 9 acima da EMA 21)
    cond_ema_cross = last_candle['ema9'] > last_candle['ema21']
    
    # C) Confirmação de Vela Verde (Fecho maior que Abertura)
    cond_green_candle = last_candle['close'] > last_candle['open']
    
    # D) Opcional: Volume acima da média recente (garante força no movimento)
    cond_volume_strength = last_candle['volume'] > last_candle['vol_ma']

    # Validação do Sinal de COMPRA (LONG)
    if cond_price_above_ema9 and cond_ema_cross and cond_green_candle and cond_volume_strength:
        print(f"[SINAL DETETADO] Compra em {last_candle['close']} USDT (EMA9: {round(last_candle['ema9'], 2)} | EMA21: {round(last_candle['ema21'], 2)})")
        return "BUY"

    return "HOLD"
    
