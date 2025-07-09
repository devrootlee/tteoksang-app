import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.trend import MACD

# ✅ 섹터별 기준 설정
SECTOR_PROFILES = {
    "Technology": {
        "rsi_range": (35, 75),
        "volume_rate_min": 1.0,
        "disparity_range": (95, 105),
        "high_low_max": 6.0
    },
    "Healthcare": {
        "rsi_range": (40, 68),
        "volume_rate_min": 1.2,
        "disparity_range": (97, 103),
        "high_low_max": 3.0
    },
    "Financial Services": {
        "rsi_range": (38, 72),
        "volume_rate_min": 1.0,
        "disparity_range": (95, 106),
        "high_low_max": 5.0
    },
    "Communication Services": {
        "rsi_range": (38, 72),
        "volume_rate_min": 1.1,
        "disparity_range": (95, 106),
        "high_low_max": 5.0
    },
    "Industrials": {
        "rsi_range": (40, 70),
        "volume_rate_min": 1.0,
        "disparity_range": (96, 104),
        "high_low_max": 4.0
    },
    "Consumer Cyclical": {
        "rsi_range": (37, 73),
        "volume_rate_min": 1.1,
        "disparity_range": (95, 106),
        "high_low_max": 6.0
    },
    "Energy": {
        "rsi_range": (38, 72),
        "volume_rate_min": 0.9,
        "disparity_range": (94, 107),
        "high_low_max": 4.5
    },
    "Default": {
        "rsi_range": (40, 70),
        "volume_rate_min": 1.1,
        "disparity_range": (96, 104),
        "high_low_max": 4.0
    }
}


def swing_stock_data(ticker):
    download = yf.download(ticker, period="2y", interval="1d", auto_adjust=False).dropna()
    info = yf.Ticker(ticker).info
    sector = info.get("sector", "Default")
    profile = SECTOR_PROFILES.get(sector, SECTOR_PROFILES["Default"])

    high_prices = download["High"].squeeze()
    low_prices = download["Low"].squeeze()
    close_prices = download["Close"].squeeze()

    # # ✅ 전일 종가
    prev_close_price = round(close_prices.iloc[-1].item(), 2)

    # ✅ 현재가
    current_price = info.get("regularMarketPrice")
    if current_price is None or current_price == 0:
        current_price = prev_close_price
    else:
        current_price = round(current_price, 2)

    # ✅ 52주 고가/저가 및 근접도
    high_52w = round(download["High"].max().item(), 2)
    low_52w = round(download["Low"].min().item(), 2)
    high_gap_pct = round((high_52w - current_price) / high_52w * 100, 2) if high_52w else None
    low_gap_pct = round((current_price - low_52w) / low_52w * 100, 2) if low_52w else None
    high_low_ratio = round(high_52w / low_52w, 2) if low_52w else None

    # ✅ 기존 종가 + 현재가를 포함한 시리즈 생성
    close_with_current = pd.concat(
        [close_prices, pd.Series([current_price], index=[close_prices.index[-1] + pd.Timedelta(days=1)])]
    )

    # pd.set_option('display.max_rows', None)
    # print(close_with_current)
    # pd.reset_option('display.max_rows')

    # ✅ 실시간 반영된 이동평균선 계산
    ma_5 = round(close_with_current.tail(5).mean().item(), 2)
    ma_20 = round(close_with_current.tail(20).mean().item(), 2)

    # ✅ 전일 이동평균선 계산 (전일 종가 기준, 현재가 제외)
    prev_ma_5 = round(close_prices.tail(5).mean().item(), 2)
    prev_ma_20 = round(close_prices.tail(20).mean().item(), 2)
    prev_ma_60 = round(close_prices.tail(60).mean().item(), 2)

    # ✅ 이동평균선 기반 추세 판단 + 지속일 계산
    sustained_days = 0
    for i in range(1, len(close_prices)):
        ma_5_i = close_prices.shift(1).rolling(5).mean().iloc[-i]
        ma_20_i = close_prices.shift(1).rolling(20).mean().iloc[-i]
        if pd.isna(ma_5_i) or pd.isna(ma_20_i):
            break
        if (ma_5 > ma_20 and ma_5_i > ma_20_i) or (ma_5 < ma_20 and ma_5_i < ma_20_i):
            sustained_days += 1
        else:
            break

    if ma_5 > ma_20 and prev_ma_5 <= prev_ma_20:
        trend = "골든크로스 발생"
    elif ma_5 < ma_20 and prev_ma_5 >= prev_ma_20:
        trend = "데드크로스 발생"
    elif ma_5 > ma_20:
        trend = f"상승 ({sustained_days}일 지속)"
    elif ma_5 < ma_20:
        trend = f"하락 ({sustained_days}일 지속)"
    else:
        trend = "중립"

    # ✅ RSI (전일 종가 기준)
    rsi_series = RSIIndicator(close=close_prices, window=14).rsi()
    latest_rsi = round(rsi_series.iloc[-1].item(), 2)

    # ✅ 이격도 (전일 종가 기준)
    disparity_5 = round((prev_close_price / prev_ma_5) * 100 if prev_ma_5 != 0 else None, 2)
    disparity_20 = round((prev_close_price / prev_ma_20) * 100 if prev_ma_20 != 0 else None, 2)
    disparity_60 = round((prev_close_price / prev_ma_60) * 100 if prev_ma_60 != 0 else None, 2)

    # ✅ 볼린저 밴드 (전일 기준)
    bb = BollingerBands(close=close_prices, window=20, window_dev=2)
    bb_upper = round(bb.bollinger_hband().iloc[-1].item(), 2)
    bb_middle = round(bb.bollinger_mavg().iloc[-1].item(), 2)
    bb_lower = round(bb.bollinger_lband().iloc[-1].item(), 2)

    # ✅ 볼린저 밴드 + 위치 판단
    if current_price > bb_upper:
        price_position = "상단 돌파"
    elif current_price > bb_middle:
        price_position = "중간 이상"
    elif current_price < bb_lower:
        price_position = "하단 근접"
    else:
        price_position = "중간 이하"

    # ✅ 갭 상승률: 오늘 시가 vs 전일 종가 (%)
    today_open = download["Open"].iloc[-1].item()
    yday_close = close_prices.iloc[-2].item()
    gap_up_pct = round(((today_open - yday_close) / yday_close) * 100, 2) if yday_close != 0 else None

    # ✅ MACD & 시그널 라인 (ta 라이브러리 사용)
    macd_calc = MACD(close=close_prices)
    macd_value = round(macd_calc.macd().iloc[-1].item(), 2)
    macd_signal = round(macd_calc.macd_signal().iloc[-1].item(), 2)
    macd_trend = "양전환" if macd_value > macd_signal else "음전환"

    # ✅ 실시간 거래량 우선, 없으면 전일 거래량
    volume_today = info.get("volume")
    if volume_today is None or volume_today == 0:
        volume_today = download["Volume"].iloc[-1]

    # ✅ 거래량 비율 (최근 5일 평균 대비)
    recent_volumes = download["Volume"].iloc[-6:-1].dropna()
    avg_volume = recent_volumes.mean()

    # float 변환 안전 처리
    if hasattr(avg_volume, "item"):
        avg_volume = avg_volume.item()

    volume_rate = round(volume_today / avg_volume, 2) if avg_volume and avg_volume > 0 else None

    # ✅ 거래대금 (백만 달러 단위)
    turnover_million = round(volume_today * current_price / 1_000_000, 2)

    # ✅ Stochastic Oscillator
    stoch = StochasticOscillator(high_prices, low_prices, close_prices)
    stoch_k = float(round(stoch.stoch().iloc[-1], 2))
    stoch_d = float(round(stoch.stoch_signal().iloc[-1], 2))

    # ✅ 옵션 정보 추가
    options = yf.Ticker(ticker).options
    option_expiry = options[0] if options else None

    max_call_strike = max_call_volume = None
    max_put_strike = max_put_volume = None
    total_call_volume_all_strikes = None
    total_put_volume_all_strikes = None

    if option_expiry:
        try:
            opt_chain = yf.Ticker(ticker).option_chain(option_expiry)
            calls = opt_chain.calls.sort_values("volume", ascending=False)
            puts = opt_chain.puts.sort_values("volume", ascending=False)

            total_call_volume_all_strikes = calls["volume"].sum()
            total_put_volume_all_strikes = puts["volume"].sum()

            if not calls.empty:
                max_call_strike = float(calls.iloc[0]["strike"])
                max_call_volume = int(calls.iloc[0]["volume"])

            if not puts.empty:
                max_put_strike = float(puts.iloc[0]["strike"])
                max_put_volume = int(puts.iloc[0]["volume"])
        except Exception as e:
            print(f"[옵션 오류] {ticker}: {e}")

    # ✅ 가중치 기반 점수 계산
    score = 0.0
    rsi_min, rsi_max = profile["rsi_range"]
    disp_min, disp_max = profile["disparity_range"]

    # 1. 추세 (MA_5, MA_20) - 가장 중요 (높은 가중치)
    if ma_5 is not None and ma_20 is not None:
        if ma_5 > ma_20:  # 상승 추세
            score += 1.5
            if trend == "골든크로스 발생":  # 골든크로스는 강력한 매수 신호
                score += 1.0
            elif sustained_days >= 5:  # 5일 이상 상승 추세 지속
                score += 0.5
            elif sustained_days >= 3:  # 3일 이상 상승 추세 지속
                score += 0.3
        elif ma_5 < ma_20 and prev_ma_5 is not None and prev_ma_20 is not None and prev_ma_5 >= prev_ma_20:  # 데드크로스 발생 (감점)
            score -= 1.0  # 단기 매매에 부정적

    # 2. RSI - 구간별 점수 (단기 상승에 적합한 RSI 범위 세분화)
    if latest_rsi is not None:
        if 45 <= latest_rsi <= 65:  # 단기 트레이딩에 이상적인 범위
            score += 0.7
        elif rsi_min <= latest_rsi < 45 or 65 < latest_rsi <= rsi_max:  # 프로파일 기준 내, 약간 벗어남
            score += 0.3
        elif latest_rsi < 30:  # 과매도 (강력한 반등 기대)
            score += 0.5  # 과매도 시에는 반등 가능성을 보고 점수 부여
        elif latest_rsi > 75:  # 과매수 (과열, 단기 차익 실현 가능성)
            score -= 0.3

    # 3. 이격도 (MA_20 기준) - 적정 범위 중요
    if disparity_20 is not None:
        if disp_min <= disparity_20 <= disp_max:  # 이상적인 범위
            score += 0.5
        elif disparity_20 > disp_max + 2:  # 이격 과대 (과열)
            score -= 0.2

    # 4. 볼린저 밴드 위치 (현재가 기준)
    if price_position == "상단 돌파":  # 강한 모멘텀
        score += 1.0
    elif price_position == "중간 이상":  # 긍정적 위치
        score += 0.5
    elif price_position == "하단 근접":  # 반등 가능성
        score += 0.3

    # 5. 갭 상승률 (단기 매매에 중요)
    if gap_up_pct is not None:
        if gap_up_pct >= 2.0:  # 2% 이상 갭 상승은 강한 매수세
            score += 1.0
        elif gap_up_pct >= 0.5:  # 0.5% 이상 갭 상승
            score += 0.5
        elif gap_up_pct < -0.5:  # 0.5% 이상 갭 하락은 부정적
            score -= 0.5

    # 6. MACD - 추세 전환/지속 신호
    if macd_trend == "양전환 또는 상승 지속":
        if macd_value is not None and macd_signal is not None and macd_value > 0:  # MACD 0선 위 양전환/상승 지속 (강력)
            score += 1.2
        else:  # 0선 아래 양전환 또는 0선 위 상승 지속
            score += 0.7
    elif macd_trend == "음전환 또는 하락 지속":
        score -= 0.5

    # 7. 거래량 비율 (가장 중요 - 숨겨진 주식 발굴 핵심)
    if volume_rate is not None:
        if volume_rate >= 3.0:  # 3배 이상 폭증
            score += 2.0  # 매우 높은 가중치
        elif volume_rate >= 2.0:  # 2배 이상 증가
            score += 1.5
        elif volume_rate >= profile["volume_rate_min"]:  # 섹터 프로파일 기준 이상
            score += 1.0
        elif volume_rate < 0.5:  # 거래량 급감 (관심 감소, 단기 매매 부적합)
            score -= 0.7

    # 8. Stochastic Oscillator
    if stoch_k is not None and stoch_d is not None:
        if 20 <= stoch_k <= 80:  # 일반적인 범위 내
            score += 0.5
            if stoch_k > stoch_d and stoch_k > 20 and stoch_d < 30:  # 과매도권 탈출 골든크로스 직전/직후
                score += 0.5  # 추가 점수
        elif stoch_k < 20 and stoch_k > stoch_d:  # 과매도권에서 골든크로스 발생 (강한 반등 기대)
            score += 0.8

    # 9. 52주 고가/저가 비율 (너무 타이트하지 않게)
    if high_low_ratio is not None and high_low_ratio < profile["high_low_max"]:
        score += 0.3  # 과도한 변동성 없는 종목 선호

    # 10. 고가 근접도 (신고가 근접 여부)
    if high_gap_pct is not None:
        if high_gap_pct <= 3.0:  # 52주 고가 3% 이내 근접 (신고가 돌파 기대)
            score += 0.7
        elif high_gap_pct <= 10.0:  # 10% 이내 근접
            score += 0.3

    # 11. 거래대금 (유동성 확인 - 단기 트레이딩 필수)
    if turnover_million is not None:
        if turnover_million >= 50:  # 5천만 달러 이상 (충분한 유동성)
            score += 0.8
        elif turnover_million >= 10:  # 천만 달러 이상
            score += 0.4
        elif turnover_million < 1:  # 1백만 달러 미만 (유동성 매우 부족, 단기 매매 부적합)
            score -= 1.5  # 큰 감점!

    # 12. 옵션 정보 (단기 트레이딩 핵심)
    # total_call_volume_all_strikes, total_put_volume_all_strikes 변수가 제대로 넘어온다고 가정
    # (원래 함수 로직에서 옵션 데이터 오류 시 None으로 처리되었던 부분 고려)
    if total_call_volume_all_strikes is not None and total_put_volume_all_strikes is not None:
        # 최소 옵션 거래량 임계값 설정 (노이즈 제거)
        min_option_volume_threshold = 1000  # 모든 스트라이크 합계 기준

        if total_call_volume_all_strikes + total_put_volume_all_strikes > min_option_volume_threshold:
            # 콜/풋 총 거래량 비율
            call_put_ratio_total = total_call_volume_all_strikes / (
                total_put_volume_all_strikes if total_put_volume_all_strikes > 0 else 0.1)  # 0으로 나누는 것 방지

            if call_put_ratio_total > 2.0:  # 콜 거래량 압도적 우위 (강한 상승 기대)
                score += 1.5
            elif call_put_ratio_total > 1.2:  # 콜 거래량 우위
                score += 0.8
            elif call_put_ratio_total < 0.5:  # 풋 거래량 압도적 우위 (하락 경고)
                score -= 0.8

        # 최다 거래량 콜 스트라이크와 현재가 근접도
        if max_call_strike is not None and max_call_volume is not None and current_price is not None and max_call_volume > 500:  # 최소 거래량 500 이상
            if max_call_strike > current_price:  # 콜 스트라이크가 현재가보다 높을 때만 고려
                call_strike_proximity_pct = (max_call_strike - current_price) / current_price * 100
                if call_strike_proximity_pct <= 3.0:  # 현재가 3% 이내 (가장 강력한 저항/돌파 기대)
                    score += 1.2
                elif call_strike_proximity_pct <= 7.0:  # 현재가 7% 이내
                    score += 0.7

        # 최다 거래량 풋 스트라이크와 현재가 근접도 (지지선 형성 가능성)
        if max_put_strike is not None and max_put_volume is not None and current_price is not None and max_put_volume > 500:  # 최소 거래량 500 이상
            if max_put_strike < current_price:  # 풋 스트라이크가 현재가보다 낮을 때만 고려
                put_strike_proximity_pct = (current_price - max_put_strike) / current_price * 100
                if put_strike_proximity_pct <= 3.0:  # 현재가 3% 이내 (강한 지지 기대)
                    score += 0.5
                elif put_strike_proximity_pct <= 7.0:  # 현재가 7% 이내
                    score += 0.2

    # 최종 점수가 음수가 되지 않도록 조정 (최소 점수는 0)
    if score < 0:
        score = 0

    # ✅ 점수 판단
    if score >= 8.0:
        recommendation = "🔥 강한 매수"
    elif score >= 6.0:
        recommendation = "👀 관심 / 매수 준비"
    elif score >= 4.0:
        recommendation = "⚠️ 조심 / 관찰"
    else:
        recommendation = "❌ 보류 또는 약세"

    result = {
        "ticker": ticker.upper(),
        "sector": sector,
        "current_price": current_price,
        "prev_close_price": prev_close_price,
        "MA_5": ma_5,
        "MA_20": ma_20,
        "RSI_14": latest_rsi,
        "Disparity_5": disparity_5,
        "Disparity_20": disparity_20,
        "Disparity_60": disparity_60,
        "BB_Upper": bb_upper,
        "BB_Middle": bb_middle,
        "BB_Lower": bb_lower,
        "Price_Position": price_position,
        "Gap_Up_Pct": gap_up_pct,
        "MACD": macd_value,
        "MACD_Signal": macd_signal,
        "MACD_Trend": macd_trend,
        "Volume_Rate": volume_rate,
        "Volume_Turnover_Million": turnover_million,
        "Stoch_K": stoch_k,
        "Stoch_D": stoch_d,
        "52W_High": high_52w,
        "52W_Low": low_52w,
        "High_Proximity_Pct": high_gap_pct,
        "Low_Proximity_Pct": low_gap_pct,
        "option_expiry": option_expiry,
        "max_call_strike": max_call_strike,
        "max_call_volume": max_call_volume,
        "max_put_strike": max_put_strike,
        "max_put_volume": max_put_volume,
        "Trend": trend,
        "Score": round(score, 1),
        "Recommendation": recommendation
    }

    return result

if __name__ == '__main__':
    # swing_stock_data("APP")
    # swing_stock_data("HOOD")
    # swing_stock_data("NVO")
    swing_stock_data("OPTT")
    # swing_stock_data("INTC")
    # swing_stock_data("CRNC")
    # swing_stock_data("LAES")
    # swing_stock_data("MSTR")
    # swing_stock_data("JPM")
