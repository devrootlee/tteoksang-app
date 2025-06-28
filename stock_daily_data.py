import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 📌 Finviz 뉴스 크롤링
def fetch_finviz_news(ticker, max_items=5):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("table.fullview-news-outer tr")
    titles = []
    for row in rows[:max_items]:
        a = row.select_one("a")
        if a:
            titles.append(a.get_text(strip=True))
    print(f"📰 {ticker} 뉴스 제목:")
    for t in titles:
        print("-", t)
    return titles

# 감성 분석
def analyze_sentiment(texts):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(t)["compound"] for t in texts]
    return round(sum(scores) / len(scores), 3) if scores else 0.0

# RSI 계산
def compute_rsi(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 이동평균
def compute_moving_averages(close_prices):
    ma_5 = close_prices.rolling(window=5).mean()
    ma_20 = close_prices.rolling(window=20).mean()
    return ma_5, ma_20

# 옵션 요약
def get_option_distribution(ticker):
    try:
        tk = yf.Ticker(ticker)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        calls = chain.calls[["strike", "volume"]].dropna().copy()
        puts = chain.puts[["strike", "volume"]].dropna().copy()
        max_call_row = calls.sort_values(by="volume", ascending=False).iloc[0]
        max_put_row = puts.sort_values(by="volume", ascending=False).iloc[0]
        return {
            "option_expiry": expiry,
            "max_call_strike": float(max_call_row["strike"]),
            "max_call_volume": int(max_call_row["volume"]),
            "max_put_strike": float(max_put_row["strike"]),
            "max_put_volume": int(max_put_row["volume"]),
        }
    except Exception as e:
        print(f"❌ 옵션 분포 오류: {ticker} - {e}")
        return {
            "option_expiry": None,
            "max_call_strike": None,
            "max_call_volume": None,
            "max_put_strike": None,
            "max_put_volume": None
        }

# 📈 메인
def get_prev_day_price(ticker):
    try:
        data = yf.download(ticker, period="60d", interval="1d", auto_adjust=False)
        data = data.sort_index().tail(30)

        if len(data) < 20:
            print(f"❌ {ticker}: 거래일 부족 ({len(data)})")
            return None

        data["RSI"] = compute_rsi(data["Close"])
        ma_5, ma_20 = compute_moving_averages(data["Close"])

        prev = data.iloc[-2]
        latest = data.iloc[-1]

        prev_close = prev["Close"].item()
        latest_close = latest["Close"].item()
        change_pct = round((latest_close - prev_close) / prev_close * 100, 2)

        volume = int(latest["Volume"].item())
        rsi = round(latest["RSI"].item(), 2)
        high = latest["High"].item()
        low = latest["Low"].item()
        close = latest["Close"].item()
        ma5_val = round(ma_5.iloc[-1].item(), 2)
        ma20_val = round(ma_20.iloc[-1].item(), 2)
        deviation_pct = round((close - ma20_val) / ma20_val * 100, 2)
        trend = "상승" if ma5_val > ma20_val else "하락"

        recent_volumes = data["Volume"].iloc[-6:-1].dropna()
        try:
            avg_volume = float(recent_volumes.mean())
            volume_rate = round(volume / avg_volume, 2) if avg_volume > 0 else None
        except:
            volume_rate = None

        # ✅ 뉴스 감성 점수 (Finviz)
        try:
            titles = fetch_finviz_news(ticker)
            sentiment_score = analyze_sentiment(titles)
        except:
            sentiment_score = 0.0

        option_summary = get_option_distribution(ticker)

        result = {
            "date": latest.name.strftime('%Y-%m-%d'),
            "ticker": ticker,
            "change_pct": change_pct,
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
            "volume_rate": volume_rate,
            "rsi": rsi,
            "ma_5": ma5_val,
            "ma_20": ma20_val,
            "trend": trend,
            "deviation_pct": deviation_pct,
            "sentiment_score": sentiment_score,  # ✅ 추가 완료
            **option_summary
        }

        print(result)
        return result

    except Exception as e:
        print(f"❌ {ticker} 처리 실패: {e}")
        return None
