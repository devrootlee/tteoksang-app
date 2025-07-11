import yfinance as yf
import pandas as pd


def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        score = 0

        # RSI 계산 (14일 기준)
        df = stock.history(period="1mo")
        if len(df) < 15:
            return None  # 데이터 부족

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1]

        if latest_rsi < 30:
            score += 1  # 과매도 구간

        # 재무 지표
        pe_ratio = info.get("trailingPE", None)
        if pe_ratio is not None and 5 < pe_ratio < 30:
            score += 1

        roe = info.get("returnOnEquity", None)
        if roe is not None and roe > 0.1:
            score += 1

        de_ratio = info.get("debtToEquity", None)
        if de_ratio is not None and de_ratio < 100:
            score += 0.5

        return {
            "ticker": ticker,
            "score": score,
            "rsi": round(latest_rsi, 2),
            "pe": pe_ratio,
            "roe": roe,
            "de_ratio": de_ratio
        }

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None


def screen_stocks(tickers):
    results = []
    for ticker in tickers:
        result = analyze_stock(ticker)
        print(f"✅ {ticker} 분석 결과: {result}")
        if result and result['score'] >= 2:
            results.append(result)

    if results:
        return pd.DataFrame(results).sort_values(by="score", ascending=False)
    else:
        return pd.DataFrame(columns=["ticker", "score", "rsi", "pe", "roe", "de_ratio"])


if __name__ == "__main__":
    tickers = ["TSS"]  # 테스트용 티커 리스트



    filtered_df = screen_stocks(tickers)

    if not filtered_df.empty:
        print("\n📊 스크리닝 결과:")
        print(filtered_df)
    else:
        print("😢 조건을 만족하는 종목이 없습니다.")
