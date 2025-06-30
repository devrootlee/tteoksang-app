import yfinance as yf
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 📌 Finviz 뉴스 크롤링 (제목 + URL)
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

            if score >= 0.05:
                emoji = "🔺"
            elif score <= -0.05:
                emoji = "🔻"
            else:
                emoji = "⚪️"

            news_items.append({
                "title": title,
                "url": link,
                "sentiment_emoji": emoji
            })

    print(f"📰 {ticker} 뉴스:")
    for item in news_items:
        print(f"- {item['sentiment_emoji']} {item['title']}")

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

# 📈 메인 분석 함수
def get_prev_day_price(ticker):
    try:
        data = yf.download(ticker, period="60d", interval="1d", auto_adjust=False).dropna()
        data = data.sort_index().tail(30)

        if len(data) < 20:
            print(f"❌ {ticker}: 거래일 부족 ({len(data)})")
            return None

        data["RSI"] = compute_rsi(data["Close"])
        ma_5, ma_20 = compute_moving_averages(data["Close"])
        data["bollinger_middle"] = data["Close"].rolling(window=20).mean()
        data["bollinger_std"] = data["Close"].rolling(window=20).std()
        data["bollinger_upper"] = data["bollinger_middle"] + (data["bollinger_std"] * 2)
        data["bollinger_lower"] = data["bollinger_middle"] - (data["bollinger_std"] * 2)

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
        prev_ma5 = round(ma_5.iloc[-2].item(), 2)
        prev_ma20 = round(ma_20.iloc[-2].item(), 2)

        # 평균 거래량
        recent_volumes = data["Volume"].iloc[-6:-1].dropna()
        avg_volume = float(recent_volumes.mean()) if not recent_volumes.empty else None
        volume_rate = round(volume / avg_volume, 2) if avg_volume and avg_volume > 0 else None

        # ✅ 뉴스 1번 조회 + 감성 변화 계산
        try:
            news_items = fetch_finviz_news(ticker, max_items=5)
            titles = [n["title"] for n in news_items]

            prev_titles = [{"title": t} for t in titles[:2]]
            today_titles = [{"title": t} for t in titles[2:]]

            sentiment_score_prev = analyze_sentiment(prev_titles)
            sentiment_score = analyze_sentiment(today_titles)
            sentiment_score_change = round(sentiment_score - sentiment_score_prev, 3)

        except:
            news_items = []
            sentiment_score = 0.0
            sentiment_score_prev = 0.0
            sentiment_score_change = 0.0

        # 옵션
        option_summary = get_option_distribution(ticker)

        # ✅ 점수 계산
        score = 0
        if isinstance(rsi, (int, float)) and (rsi < 40 or (35 <= rsi <= 60)): score += 1
        if trend == "상승": score += 1
        if isinstance(volume_rate, (int, float)) and volume_rate > 1.2: score += 1
        if sentiment_score > 0: score += 1
        if option_summary["max_call_strike"] is not None and option_summary["max_call_strike"] >= close:
            score += 1
        if (
            option_summary["max_call_volume"] is not None and
            option_summary["max_put_volume"] is not None and
            option_summary["max_call_volume"] > option_summary["max_put_volume"]
        ):
            score += 1

        # ✅ 결과
        return {
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
            "prev_ma_5": prev_ma5,
            "prev_ma_20": prev_ma20,
            "trend": trend,
            "deviation_pct": deviation_pct,
            "bollinger_upper": round(latest["bollinger_upper"].item(), 2),
            "bollinger_lower": round(latest["bollinger_lower"].item(), 2),
            "avg_volume_5d": round(avg_volume, 2) if avg_volume else None,
            "sentiment_score": sentiment_score,
            "sentiment_score_prev": sentiment_score_prev,
            "sentiment_score_change": sentiment_score_change,
            "score": score,
            "news": news_items,
            **option_summary
        }

    except Exception as e:
        print(f"❌ {ticker} 처리 실패: {e}")
        return None
