import yfinance as yf
import requests
import pandas as pd
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
from datetime import datetime

# 옵션 요약 (지나간 만기 제거 + 여러 만기 스캔)
def get_option_distribution(ticker, max_expiries=3):
    try:
        tk = yf.Ticker(ticker)
        today = datetime.utcnow().date()

        # 오늘 이후의 유효한 만기일만 필터링
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
                        max_call = {
                            "strike": float(top_call["strike"]),
                            "volume": int(top_call["volume"]),
                            "expiry": expiry
                        }
                if not puts.empty:
                    top_put = puts.sort_values(by="volume", ascending=False).iloc[0]
                    if top_put["volume"] > max_put["volume"]:
                        max_put = {
                            "strike": float(top_put["strike"]),
                            "volume": int(top_put["volume"]),
                            "expiry": expiry
                        }
            except Exception as e:
                print(f"⚠️ {ticker} 옵션 만기 {expiry} 처리 실패: {e}")
                continue

        return {
            "option_expiry": max_call.get("expiry"),
            "max_call_strike": max_call.get("strike"),
            "max_call_volume": max_call.get("volume"),
            "max_put_strike": max_put.get("strike"),
            "max_put_volume": max_put.get("volume")
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
        data = yf.download(ticker, period="180d", interval="1d", auto_adjust=False).dropna()
        data = data.sort_index()

        # ✅ MultiIndex 열일 경우 → 첫 번째 레벨만 유지 (ex: ('Close', 'AAPL') → 'Close')
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0] for c in data.columns]

        if len(data) < 30:
            print(f"❌ {ticker}: 거래일 부족 ({len(data)})")
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

        # 전략적 매수/매도/손절가 계산 (float 강제 변환)
        boll_upper = float(latest["bollinger_upper"])
        boll_middle = float(latest["bollinger_middle"])
        boll_lower = float(latest["bollinger_lower"])
        buy_target = round(boll_lower + (boll_middle - boll_lower) * 0.3, 2)
        sell_target = round(boll_upper, 2)
        stop_loss = round(boll_lower * 0.99, 2)

        # 📊 시각화용 180일 데이터 (멀티인덱스 안전하게 해제)
        chart_data = data[["Close", "bollinger_upper", "bollinger_middle", "bollinger_lower"]].copy()
        chart_data = chart_data.astype(float)

        if isinstance(chart_data.index, pd.MultiIndex):
            chart_data = chart_data.reset_index(level="Ticker", drop=True)

        chart_data = chart_data.reset_index()  # index → 컬럼으로
        chart_data.rename(columns={"index": "Date"}, inplace=True)  # index → Date 컬럼으로 명시
        chart_history = chart_data.to_dict(orient="records")

        # 뉴스 수집
        try:
            news_items = fetch_finviz_news(ticker, max_items=5)
            sentiment_score = analyze_sentiment(news_items)
        except:
            news_items = []
            sentiment_score = 0.0

        option_summary = get_option_distribution(ticker)

        # ✅ 점수 계산
        score = 0
        if isinstance(rsi, (int, float)) and (rsi < 40 or (35 <= rsi <= 60)): score += 1
        if trend == "상승": score += 1
        if isinstance(volume_rate, (int, float)) and volume_rate > 1.2: score += 1
        if gap_pct > 1.0: score += 1
        if option_summary["max_call_strike"] is not None and option_summary["max_call_strike"] >= close:
            score += 1
        if (
            option_summary["max_call_volume"] is not None and
            option_summary["max_put_volume"] is not None and
            option_summary["max_call_volume"] > option_summary["max_put_volume"]
        ):
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

    except Exception as e:
        print(f"❌ {ticker} 처리 실패: {e}")
        return None




