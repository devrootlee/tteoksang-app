import yfinance as yf
import requests
import pandas as pd
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

# 📌 Finviz 뉴스 크롤링
def fetch_finviz_news(ticker, max_items=5):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("table.fullview-news-outer tr")

    analyzer = SentimentIntensityAnalyzer()
    news_items = []

    for row in rows[:max_items]:
        a = row.select_one("a")
        if a:
            title = a.get_text(strip=True)
            link = a.get("href")
            score = analyzer.polarity_scores(title)["compound"]
            emoji = "🔺" if score >= 0.05 else "🔻" if score <= -0.05 else "⚪️"
            news_items.append({"title": title, "url": link, "sentiment_emoji": emoji})

    return news_items

# 감성 분석
def analyze_sentiment(items):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(item["title"])["compound"] for item in items]
    return round(sum(scores) / len(scores), 3) if scores else 0.0

# RSI 계산
def compute_rsi(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 이동평균
def compute_moving_averages(close_prices):
    return close_prices.rolling(window=5).mean(), close_prices.rolling(window=20).mean()

# 옵션 요약
def get_option_distribution(ticker, max_expiries=3):
    try:
        tk = yf.Ticker(ticker)
        today = datetime.utcnow().date()
        valid_expiries = [e for e in tk.options if datetime.strptime(e, "%Y-%m-%d").date() >= today]
        max_call = {"volume": 0}
        max_put = {"volume": 0}

        for expiry in valid_expiries[:max_expiries]:
            try:
                chain = tk.option_chain(expiry)
                calls = chain.calls[["strike", "volume"]].dropna()
                puts = chain.puts[["strike", "volume"]].dropna()
                if not calls.empty:
                    top_call = calls.sort_values(by="volume", ascending=False).iloc[0]
                    if top_call["volume"] > max_call["volume"]:
                        max_call = {"strike": float(top_call["strike"]), "volume": int(top_call["volume"]), "expiry": expiry}
                if not puts.empty:
                    top_put = puts.sort_values(by="volume", ascending=False).iloc[0]
                    if top_put["volume"] > max_put["volume"]:
                        max_put = {"strike": float(top_put["strike"]), "volume": int(top_put["volume"]), "expiry": expiry}
            except Exception:
                continue

        return {
            "option_expiry": max_call.get("expiry"),
            "max_call_strike": max_call.get("strike"),
            "max_call_volume": max_call.get("volume"),
            "max_put_strike": max_put.get("strike"),
            "max_put_volume": max_put.get("volume")
        }
    except Exception:
        return {
            "option_expiry": None,
            "max_call_strike": None,
            "max_call_volume": None,
            "max_put_strike": None,
            "max_put_volume": None
        }

# 리채널링
def reset_channel_if_breakout(meta):
    if meta["close"] > meta["sell_target"]:
        base = meta["ma_20"]
        new_sell = round(base * 1.08, 2)
        if new_sell > meta["close"]:
            meta["buy_target"] = round(base * 0.96, 2)
            meta["sell_target"] = new_sell
            meta["stop_loss"] = round(base * 0.96 * 0.98, 2)
            meta["채널 리셋됨"] = True
        else:
            meta["채널 리셋됨"] = False
    else:
        meta["채널 리셋됨"] = False
    return meta

# 점수 해석
def interpret_score(score):
    if score >= 5:
        return "🔥 강한 매수"
    elif score >= 3:
        return "⚖️ 중립~관망"
    return "⚠️ 주의/보류"

# 돌파 평가
def evaluate_breakout(meta):
    signals = 0
    reasons = []

    if meta["close"] > meta["buy_target"]:
        signals += 1
        reasons.append("채널 상단 돌파")
    if meta.get("volume_rate") and meta["volume_rate"] >= 1.2:
        signals += 1
        reasons.append("거래량↑")
    if 50 <= meta["rsi"] <= 72:
        signals += 1
        reasons.append("RSI 양호")
    if meta["ma_5"] > meta["ma_20"]:
        signals += 1
        reasons.append("골든크로스 유지")
    if meta["gap_pct"] > 0.3:
        signals += 1
        reasons.append("갭 상승")
    if 0 <= meta["deviation_pct"] <= 8:
        signals += 1
        reasons.append("이격도 정상")

    if signals >= 4:
        return "🔥 돌파 가능성 높음", reasons
    elif signals >= 2:
        return "⚖️ 관망 (부분 조건 만족)", reasons
    return "❌ 돌파 신호 아님", reasons

# 데이터프레임 생성
def create_stock_dataframe(ticker_data, valid_tickers):
    data = [ticker_data[t] for t in valid_tickers]
    if not data:
        return None

    df = pd.DataFrame(data)
    df = df[[
        "ticker",
        "date",
        "change_pct",
        "gap_pct",
        "high",
        "low",
        "close",
        "volume",
        "volume_rate",
        "rsi",
        "ma_5",
        "ma_20",
        "prev_ma_5",
        "prev_ma_20",
        "trend",
        "deviation_pct",
        "bollinger_upper",
        "bollinger_lower",
        "avg_volume_5d",
        "max_call_strike",
        "max_call_volume",
        "max_put_strike",
        "max_put_volume",
        "option_expiry",
        "buy_target",
        "sell_target",
        "stop_loss",
        "score"
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
        "max_call_strike": "콜 집중 행사가",
        "max_call_volume": "콜 거래량",
        "max_put_strike": "풋 집중 행사가",
        "max_put_volume": "풋 거래량",
        "option_expiry": "옵션 만기일",
        "buy_target": "매수 적정가",
        "sell_target": "기대 매도가",
        "stop_loss": "손절가",
        "score": "종합 점수"
    })
    df["점수 해석"] = df["종합 점수"].apply(interpret_score)
    return df

# 메인 데이터 수집 함수 (get_prev_day_price를 get_stock_data로 이름 변경)
def get_stock_data(ticker):
    try:
        data = yf.download(ticker, period="180d", interval="1d", auto_adjust=False).dropna()
        data = data.sort_index()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0] for c in data.columns]

        if len(data) < 30:
            return None

        # 볼린저 밴드 계산
        data["bollinger_middle"] = data["Close"].rolling(window=20).mean()
        data["bollinger_std"] = data["Close"].rolling(window=20).std()
        data["bollinger_upper"] = data["bollinger_middle"] + (data["bollinger_std"] * 2)
        data["bollinger_lower"] = data["bollinger_middle"] - (data["bollinger_std"] * 2)

        # 기타 지표
        data["RSI"] = compute_rsi(data["Close"])
        ma_5, ma_20 = compute_moving_averages(data["Close"])

        recent = data.tail(30)
        prev = recent.iloc[-2]
        latest = recent.iloc[-1]

        prev_close = float(prev["Close"])
        latest_close = float(latest["Close"])
        open_price = float(latest["Open"])
        change_pct = round((latest_close - prev_close) / prev_close * 100, 2)
        gap_pct = round((open_price - prev_close) / prev_close * 100, 2)

        volume = int(latest["Volume"])
        rsi = round(float(latest["RSI"]), 2)
        high = float(latest["High"])
        low = float(latest["Low"])
        close = float(latest["Close"])
        ma5_val = round(float(ma_5.iloc[-1]), 2)
        ma20_val = round(float(ma_20.iloc[-1]), 2)
        deviation_pct = round((close - ma20_val) / ma20_val * 100, 2)
        trend = "상승" if ma5_val > ma20_val else "하락"
        prev_ma5 = round(float(ma_5.iloc[-2]), 2)
        prev_ma20 = round(float(ma_20.iloc[-2]), 2)

        recent_volumes = recent["Volume"].iloc[-6:-1].dropna()
        avg_volume = float(recent_volumes.mean()) if not recent_volumes.empty else None
        volume_rate = round(volume / avg_volume, 2) if avg_volume and avg_volume > 0 else None

        # 전략적 매수/매도/손절가 계산
        boll_upper = float(latest["bollinger_upper"])
        boll_middle = float(latest["bollinger_middle"])
        boll_lower = float(latest["bollinger_lower"])
        buy_target = round(boll_lower + (boll_middle - boll_lower) * 0.3, 2)
        sell_target = round(boll_upper, 2)
        stop_loss = round(boll_lower * 0.99, 2)

        # 차트 데이터
        chart_data = data[["Close", "bollinger_upper", "bollinger_middle", "bollinger_lower"]].copy()
        chart_data = chart_data.astype(float)
        if isinstance(chart_data.index, pd.MultiIndex):
            chart_data = chart_data.reset_index(level="Ticker", drop=True)
        chart_data = chart_data.reset_index().rename(columns={"index": "Date"})
        chart_history = chart_data.to_dict(orient="records")

        # 뉴스 및 옵션
        news_items = fetch_finviz_news(ticker, max_items=5)
        sentiment_score = analyze_sentiment(news_items)
        option_summary = get_option_distribution(ticker)

        # 점수 계산
        score = 0
        if isinstance(rsi, (int, float)) and (rsi < 40 or (35 <= rsi <= 60)): score += 1
        if trend == "상승": score += 1
        if isinstance(volume_rate, (int, float)) and volume_rate > 1.2: score += 1
        if gap_pct > 1.0: score += 1
        if option_summary["max_call_strike"] is not None and option_summary["max_call_strike"] >= close:
            score += 1
        if (option_summary["max_call_volume"] is not None and
            option_summary["max_put_volume"] is not None and
            option_summary["max_call_volume"] > option_summary["max_put_volume"]):
            score += 1

        return {
            "date": latest.name.strftime('%Y-%m-%d'),
            "ticker": ticker,
            "change_pct": change_pct,
            "gap_pct": gap_pct,
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
            "volume_rate": volume_rate,
            "rsi": rsi,
            "ma_5": ma5_val,
            "ma_20": ma20_val,
            "prev_ma_5": prev_ma5,
            "prev_ma_20": prev_ma20,
            "trend": trend,
            "deviation_pct": deviation_pct,
            "bollinger_upper": round(boll_upper, 2),
            "bollinger_middle": round(boll_middle, 2),
            "bollinger_lower": round(boll_lower, 2),
            "avg_volume_5d": round(avg_volume, 2) if avg_volume else None,
            "sentiment_score": sentiment_score,
            "score": score,
            "news": news_items,
            "buy_target": buy_target,
            "sell_target": sell_target,
            "stop_loss": stop_loss,
            "chart_history": chart_history,
            **option_summary
        }
    except Exception:
        return None

# 필터링 함수들
def filter_uptrend_stocks(df):
    return df[
        (df["RSI"] <= 65) &
        (df["거래량배율"] >= 1.2) &
        (df["추세"] == "상승") &
        (df["5일이평"] > df["20일이평"]) &
        ((df["콜 집중 행사가"].notna() & (df["콜 집중 행사가"] >= df["종가"] * 0.98)) | df["콜 집중 행사가"].isna()) &
        ((df["콜 거래량"].notna() & df["풋 거래량"].notna() & (df["콜 거래량"] >= df["풋 거래량"] * 1.2)) | df["콜 거래량"].isna())
    ]

def filter_pullback_stocks(df):
    return df[
        (df["RSI"] >= 40) &
        (df["RSI"] <= 58) &
        (df["갭상승률(%)"] > 0.3) &
        (df["거래량배율"] >= 1.1) &
        (df["5일이평"] > df["20일이평"]) &
        (df["종가"] < df["볼린저상단"] * 0.99)
    ]

def filter_reversal_stocks(df):
    return df[
        (df["전일 5일이평"] < df["전일 20일이평"]) &
        (df["5일이평"] > df["20일이평"]) &
        (df["갭상승률(%)"] > 0.2) &
        (df["거래량"] >= df["5일평균거래량"] * 1.3) &
        (df["종가"] < df["볼린저하단"] * 1.01) &
        (df["RSI"] < 70)
    ]

def filter_downtrend_stocks(df):
    return df[
        (df["RSI"] >= 68) &
        (df["갭상승률(%)"] < -1.0) &
        (df["거래량배율"] >= 1.2) &
        (df["추세"] == "하락") &
        ((df["풋 집중 행사가"].notna() & (df["풋 집중 행사가"] <= df["종가"] * 1.02)) | df["풋 집중 행사가"].isna()) &
        ((df["풋 거래량"].notna() & df["콜 거래량"].notna() & (df["풋 거래량"] >= df["콜 거래량"] * 1.2)) | df["풋 거래량"].isna())
    ]

def filter_uptrend_boundary_stocks(df):
    return df[
        (df["RSI"] < 48) &
        (df["5일이평"] > df["20일이평"]) &
        (df["거래량배율"] > 0.9)
    ]

def filter_downtrend_boundary_stocks(df):
    return df[
        (df["RSI"] >= 52) &
        (df["RSI"] <= 70) &
        (df["5일이평"] < df["20일이평"]) &
        (df["거래량배율"] > 1.0)
    ]

def filter_call_dominant_stocks(df):
    return df[
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["콜 집중 행사가"].notna()) &
        (df["콜 집중 행사가"] > df["종가"]) &
        ((df["콜 집중 행사가"] - df["종가"]) / df["종가"] < 0.05)
    ]

def filter_put_dominant_stocks(df):
    return df[
        (df["풋 거래량"] > df["콜 거래량"]) &
        (df["풋 집중 행사가"].notna()) &
        (df["풋 집중 행사가"] < df["종가"]) &
        ((df["종가"] - df["풋 집중 행사가"]) / df["종가"] < 0.05)
    ]

def filter_call_breakout_stocks(df):
    return df[
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["콜 집중 행사가"].notna()) &
        (df["종가"] > df["콜 집중 행사가"])
    ]

def filter_put_breakout_stocks(df):
    return df[
        (df["풋 거래량"] > df["콜 거래량"]) &
        (df["풋 집중 행사가"].notna()) &
        (df["종가"] < df["풋 집중 행사가"])
    ]

def filter_overheated_stocks(df):
    return df[
        (df["RSI"] >= 75) &
        (df["갭상승률(%)"] > 2.0) &
        (df["거래량배율"] >= 2.2) &
        (df["이격도(%)"] >= 10)
    ]