# coin_daily_data.py
import pandas as pd
import ccxt

def get_coin_data(symbol="BTC/USDT"):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        if len(df) < 20:
            return None

        # RSI 계산
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # 이동 평균 계산
        df["ma_5"] = df["close"].rolling(window=5).mean()
        df["ma_20"] = df["close"].rolling(window=20).mean()

        # 볼린저 밴드 계산
        df["bollinger_middle"] = df["close"].rolling(window=20).mean()
        df["bollinger_std"] = df["close"].rolling(window=20).std()
        df["bollinger_upper"] = df["bollinger_middle"] + (df["bollinger_std"] * 2)
        df["bollinger_lower"] = df["bollinger_middle"] - (df["bollinger_std"] * 2)

        # 기타 계산
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        change_pct = round((latest["close"] - prev["close"]) / prev["close"] * 100, 2)
        gap_pct = round((latest["open"] - prev["close"]) / prev["close"] * 100, 2)
        trend = "상승" if latest["ma_5"] > latest["ma_20"] else "하락"
        deviation_pct = round((latest["close"] - latest["ma_20"]) / latest["ma_20"] * 100, 2)

        recent_volumes = df["volume"].iloc[-6:-1]
        avg_volume = recent_volumes.mean() if not recent_volumes.empty else 0
        volume_rate = round(latest["volume"] / avg_volume, 2) if avg_volume else None

        # 점수 계산
        score = 0
        if latest["rsi"] < 60: score += 1
        if volume_rate and volume_rate >= 1.2: score += 1
        if trend == "상승": score += 1
        if gap_pct > 1.0: score += 1
        if 0 <= deviation_pct <= 8: score += 1

        return {
            "date": latest.name.strftime('%Y-%m-%d'),
            "ticker": symbol.replace("/", ""),
            "change_pct": change_pct,
            "gap_pct": gap_pct,
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
            "volume_rate": volume_rate,
            "rsi": round(latest["rsi"], 2),
            "ma_5": round(latest["ma_5"], 2),
            "ma_20": round(latest["ma_20"], 2),
            "prev_ma_5": round(float(df["ma_5"].iloc[-2]), 2),
            "prev_ma_20": round(float(df["ma_20"].iloc[-2]), 2),
            "trend": trend,
            "deviation_pct": deviation_pct,
            "bollinger_upper": round(float(latest["bollinger_upper"]), 2),
            "bollinger_middle": round(float(latest["bollinger_middle"]), 2),
            "bollinger_lower": round(float(latest["bollinger_lower"]), 2),
            "avg_volume_5d": round(avg_volume, 2) if avg_volume else None,
            "buy_target": round(float(latest["bollinger_lower"]) + (float(latest["bollinger_middle"]) - float(latest["bollinger_lower"])) * 0.3, 2),
            "sell_target": round(float(latest["bollinger_upper"]), 2),
            "stop_loss": round(float(latest["bollinger_lower"]) * 0.99, 2),
            "score": score
        }
    except Exception as e:
        print(f"❌ 코인 데이터 오류 ({symbol}): {e}")
        return None

def create_coin_dataframe(ticker_data, valid_tickers):
    data = [ticker_data[t] for t in valid_tickers]
    if not data:
        return None

    df = pd.DataFrame(data)
    df = df[[
        "ticker", "date", "change_pct", "gap_pct", "high", "low", "close", "volume",
        "volume_rate", "rsi", "ma_5", "ma_20", "prev_ma_5", "prev_ma_20", "trend",
        "deviation_pct", "bollinger_upper", "bollinger_lower", "avg_volume_5d",
        "buy_target", "sell_target", "stop_loss", "score"
    ]]
    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df = df.dropna(subset=["change_pct"])

    df = df.rename(columns={
        "ticker": "종목코드",
        "date": "날짜",
        "change_pct": "등락률(%)",
        "gap_pct": "갭상승률(%)",
        "high": "전일고가",
        "low": "전일저가",
        "close": "종가",
        "volume": "거래량",
        "volume_rate": "거래량배율",
        "rsi": "RSI",
        "ma_5": "5일이평",
        "ma_20": "20일이평",
        "prev_ma_5": "전일 5일이평",
        "prev_ma_20": "전일 20일이평",
        "trend": "추세",
        "deviation_pct": "이격도(%)",
        "bollinger_upper": "볼린저상단",
        "bollinger_lower": "볼린저하단",
        "avg_volume_5d": "5일평균거래량",
        "buy_target": "매수 적정가",
        "sell_target": "기대 매도가",
        "stop_loss": "손절가",
        "score": "종합 점수"
    })
    df["점수 해석"] = df["종합 점수"].apply(lambda x: "🔥 강한 매수" if x >= 5 else "⚖️ 중립~관망" if x >= 3 else "⚠️ 주의/보류")
    return df