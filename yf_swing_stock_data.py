import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.trend import MACD

# yf 주가 분석

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
    try:
        # ✅ 주가 데이터 다운로드 및 유효성 검사 (120일선 계산을 위해 기간 확장)
        # period="1y"는 약 252거래일 데이터를 제공, 120일선 계산에 충분
        # auto_adjust=True로 변경: 분할/배당 조정된 가격으로 정확한 지표 계산
        download = yf.download(ticker, period="1y", interval="1d", auto_adjust=True).dropna()
        if download.empty or len(download) < 120: # 최소 120일 데이터는 필요하도록 강화
            return {"ticker": ticker.upper(), "Recommendation": "❌ 데이터 부족 또는 불충분"}

        # ✅ Ticker 정보 가져오기
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "Default")
        profile = SECTOR_PROFILES.get(sector, SECTOR_PROFILES["Default"])

        high_prices = download["High"].squeeze()
        low_prices = download["Low"].squeeze()
        close_prices = download["Close"].squeeze()

        # ✅ 전일 종가
        prev_close_price = round(close_prices.iloc[-1].item(), 2)

        # ✅ 현재가 (실시간 가격 우선, 없으면 전일 종가)
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

        # ✅ 기존 종가 + 현재가를 포함한 시리즈 생성 (실시간 반영을 위해)
        close_with_current = pd.concat(
            [close_prices, pd.Series([current_price], index=[close_prices.index[-1] + pd.Timedelta(days=1)])]
        )

        # ✅ 실시간 반영된 이동평균선 계산 (현재가 포함)
        ma_5 = round(close_with_current.tail(5).mean().item(), 2)
        ma_20 = round(close_with_current.tail(20).mean().item(), 2)

        # ✅ 전일 이동평균선 계산 (전일 종가 기준, 현재가 제외)
        prev_ma_5 = round(close_prices.tail(5).mean().item(), 2)
        prev_ma_20 = round(close_prices.tail(20).mean().item(), 2)
        prev_ma_60 = round(close_prices.tail(60).mean().item(), 2)
        prev_ma_120 = round(close_prices.tail(120).mean().item(), 2) # ✅ 120일 이동평균선 추가

        # ✅ 이동평균선 기반 추세 판단 + 지속일 계산
        sustained_days = 0
        # MA_5와 MA_20의 관계를 기준으로 추세 지속일 계산
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
        disparity_120 = round((prev_close_price / prev_ma_120) * 100 if prev_ma_120 != 0 else None, 2) # ✅ 120일 이격도 추가

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
        if macd_value > 0 and macd_value > macd_signal:
            macd_trend = "상승 지속" # 0선 위 골든크로스 또는 상승 지속

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
                # 옵션 데이터 로드 오류는 분석 실패로 이어지지 않도록 pass
                pass

        # ✅ 3일 연속 마감 여부 계산 (함수 내부에 통합)
        consecutive_close_status = "혼합" # 기본값
        days_to_check = 3
        if len(download) >= days_to_check:
            # 전일 대비 종가 변화율 계산
            download['Daily_Change'] = download['Close'].pct_change()

            # 3일 연속 양봉 (종가가 전일 종가보다 높은 경우)
            consecutive_positive = True
            for i in range(1, days_to_check + 1):
                if download['Daily_Change'].iloc[-i] <= 0: # 0보다 작거나 같으면 음봉으로 간주
                    consecutive_positive = False
                    break
            if consecutive_positive:
                consecutive_close_status = "3일 연속 양봉"
            else:
                # 3일 연속 음봉 (종가가 전일 종가보다 낮은 경우)
                consecutive_negative = True
                for i in range(1, days_to_check + 1):
                    if download['Daily_Change'].iloc[-i] >= 0: # 0보다 크거나 같으면 양봉으로 간주
                        consecutive_negative = False
                        break
                if consecutive_negative:
                    consecutive_close_status = "3일 연속 음봉"
        else:
            consecutive_close_status = "데이터 부족"


        # ✅ 지지선 계산 (20일선, 60일선, 120일선 기준)
        # 지지선 후보들을 리스트에 담고 유효한 값만 필터링
        candidate_supports = [prev_ma_20, prev_ma_60, prev_ma_120]
        valid_supports = sorted([s for s in candidate_supports if s is not None], reverse=True) # 높은 가격부터 정렬

        support_1st = valid_supports[0] if len(valid_supports) > 0 else None
        support_2nd = valid_supports[1] if len(valid_supports) > 1 else None
        support_3rd = valid_supports[2] if len(valid_supports) > 2 else None

        # ✅ 저항선 계산 (볼린저 상단, 5일선, 20일선, 60일선, 120일선, 52주 고가 기준)
        # 현재 가격보다 높은 저항선 후보들을 리스트에 담고 유효한 값만 필터링
        resistance_candidates = []
        if bb_upper is not None and current_price is not None and bb_upper > current_price:
            resistance_candidates.append(bb_upper)
        if prev_ma_5 is not None and current_price is not None and prev_ma_5 > current_price:
            resistance_candidates.append(prev_ma_5)
        if prev_ma_20 is not None and current_price is not None and prev_ma_20 > current_price:
            resistance_candidates.append(prev_ma_20)
        if prev_ma_60 is not None and current_price is not None and prev_ma_60 > current_price:
            resistance_candidates.append(prev_ma_60)
        if prev_ma_120 is not None and current_price is not None and prev_ma_120 > current_price:
            resistance_candidates.append(prev_ma_120)
        if high_52w is not None and current_price is not None and high_52w > current_price:
            resistance_candidates.append(high_52w)

        # 유효한 저항선 후보들을 낮은 가격부터 정렬하여 1차, 2차, 3차 저항선으로 할당
        valid_resistances = sorted([r for r in resistance_candidates if r is not None])

        resistance_1st = valid_resistances[0] if len(valid_resistances) > 0 else None
        resistance_2nd = valid_resistances[1] if len(valid_resistances) > 1 else None
        resistance_3rd = valid_resistances[2] if len(valid_resistances) > 2 else None


        # ✅ 가중치 기반 점수 계산
        score = 0.0
        rsi_min, rsi_max = profile["rsi_range"]
        disp_min, disp_max = profile["disparity_range"]

        # 1. 추세 (MA_5, MA_20, MA_60, MA_120) - 가장 중요
        if ma_5 is not None and ma_20 is not None:
            if ma_5 > ma_20: # 단기 상승 추세
                score += 1.5
                if trend == "골든크로스 발생": # 강력한 단기 매수 신호
                    score += 1.5
                elif sustained_days >= 5: # 상승 추세 지속
                    score += 0.5
                elif sustained_days >= 3:
                    score += 0.3
            elif ma_5 < ma_20 and prev_ma_5 is not None and prev_ma_20 is not None and prev_ma_5 >= prev_ma_20: # 데드크로스 발생
                score -= 1.5

        # 장기 추세 (MA_60, MA_120)
        if prev_ma_60 is not None and prev_ma_120 is not None:
            if prev_ma_60 > prev_ma_120: # 중장기 상승 추세
                score += 1.0
            else:
                score -= 0.5 # 중장기 하락 추세

        # 주가가 주요 장기 이평선 위에 있는지
        if current_price is not None:
            if prev_ma_120 is not None and current_price > prev_ma_120:
                score += 0.7 # 장기 추세선 위 (긍정적)
            elif prev_ma_60 is not None and current_price > prev_ma_60:
                score += 0.5 # 중기 추세선 위 (긍정적)

        # 2. RSI - 구간별 점수 (매수/매도 모멘텀)
        if latest_rsi is not None:
            # 과매도권 (매수 기회)
            if latest_rsi < 30:
                score += 1.0 # 강력한 반등 기대
            elif 30 <= latest_rsi < 40:
                score += 0.7 # 과매도권 진입 직전 (매수 준비)
            # 중립 및 상승 모멘텀 구간 (RSI 70 미만까지 긍정)
            elif 40 <= latest_rsi < 70: # 40 이상 70 미만은 긍정적인 모멘텀
                score += 1.2
            # ✅ 과매수권 (매도 고려/주의) - 70 이상으로 변경
            elif latest_rsi >= 70: # 70 이상은 과매수
                score -= 1.0

        # 3. 이격도 (MA_20 기준) - 적정 범위 중요 및 과대 이격 감점 강화
        if disparity_20 is not None:
            if disp_min <= disparity_20 <= disp_max: # 이상적인 범위 (96~104)
                score += 0.5
            elif disparity_20 > disp_max + 2: # 이격 과대 (과열)
                score -= 0.7
            elif disparity_20 < disp_min - 2: # 이격 과소 (과매도)
                score += 0.3

        # 4. 볼린저 밴드 위치 (현재가 기준) - 상단 돌파 직후 과열 고려
        if price_position == "상단 돌파": # 강한 모멘텀이지만, 이미 오버슈팅일 수 있음.
            score += 0.5
        elif price_position == "중간 이상": # 긍정적 위치
            score += 0.7
        elif price_position == "하단 근접": # 반등 가능성
            score += 0.4

        # 5. 갭 상승률 (단기 매매에 중요) - 갭 상승에 대한 감점 강화
        if gap_up_pct is not None:
            if gap_up_pct >= 2.0: # 2% 이상 갭 상승은 강한 매수세이지만, 단기 고점 위험
                score -= 0.5
            elif gap_up_pct >= 0.5: # 0.5% 이상 갭 상승 (긍정적이나, 아주 높지 않은 수준)
                score += 0.3
            elif gap_up_pct < -0.5: # 0.5% 이상 갭 하락은 부정적
                score -= 1.0

        # 6. MACD - 추세 전환/지속 신호
        if macd_trend == "양전환": # MACD 골든크로스
            score += 1.2
        elif macd_trend == "상승 지속" and macd_value > 0: # 0선 위에서 상승 지속
            score += 0.8
        elif macd_trend == "음전환": # MACD 데드크로스
            score -= 0.8
        elif macd_value < 0 and macd_value < macd_signal: # 0선 아래에서 하락 지속
            score -= 0.5

        # 7. 거래량 비율 (가장 중요 - 숨겨진 주식 발굴 핵심) - 폭증 시점 재고
        if volume_rate is not None:
            if volume_rate >= 3.0: # 3배 이상 폭증 (주의: 고점에서 터지는 경우도 있음)
                score += 1.5
            elif volume_rate >= 2.0: # 2배 이상 증가
                score += 1.2
            elif volume_rate >= profile["volume_rate_min"]: # 섹터 프로파일 기준 이상 (안정적 증가)
                score += 1.0
            elif volume_rate < 0.5: # 거래량 급감 (관심 감소, 단기 매매 부적합)
                score -= 1.0

        # 8. Stochastic Oscillator (매수/매도 모멘텀)
        if stoch_k is not None and stoch_d is not None:
            if stoch_k < 20 and stoch_k > stoch_d: # 과매도권에서 골든크로스 발생 (강한 반등 기대)
                score += 1.0
            elif 20 <= stoch_k <= 80: # 일반적인 범위 내
                if stoch_k > stoch_d: # 상승 추세 지속
                    score += 0.5
                else: # 하락 추세 지속
                    score += 0.2
            elif stoch_k > 80 and stoch_k < stoch_d: # 과매수권 데드크로스 (매도 신호)
                score -= 0.5

        # 9. 52주 고가/저가 비율 (너무 타이트하지 않게)
        if high_low_ratio is not None and high_low_ratio < profile["high_low_max"]:
            score += 0.3

        # 10. 고가 근접도 (신고가 근접 여부)
        if high_gap_pct is not None:
            if high_gap_pct <= 1.0: # 52주 고가 1% 이내 근접 (신고가 돌파 임박)
                score += 0.7
            elif high_gap_pct <= 5.0: # 5% 이내 근접
                score += 0.3

        # 11. 거래대금 (유동성 확인 - 단기 트레이딩 필수)
        if turnover_million is not None:
            if turnover_million >= 50: # 5천만 달러 이상 (충분한 유동성)
                score += 0.8
            elif turnover_million >= 10: # 천만 달러 이상
                score += 0.4
            elif turnover_million < 1: # 1백만 달러 미만 (유동성 매우 부족, 단기 매매 부적합)
                score -= 2.0

        # 12. 옵션 정보 (단기 트레이딩 핵심)
        if total_call_volume_all_strikes is not None and total_put_volume_all_strikes is not None:
            min_option_volume_threshold = 1000

            if total_call_volume_all_strikes + total_put_volume_all_strikes > min_option_volume_threshold:
                call_put_ratio_total = total_call_volume_all_strikes / (total_put_volume_all_strikes if total_put_volume_all_strikes > 0 else 0.1)

                if call_put_ratio_total > 2.0: # 콜 거래량 압도적 (강한 상승 기대)
                    score += 1.5
                elif call_put_ratio_total > 1.2: # 콜 거래량 우세
                    score += 0.8
                elif call_put_ratio_total < 0.5: # 풋 거래량 압도적 (강한 하락 기대)
                    score -= 0.8

            if max_call_strike is not None and max_call_volume is not None and current_price is not None and max_call_volume > 500:
                if max_call_strike > current_price: # 현재가보다 높은 콜 스트라이크에 대량 거래
                    call_strike_proximity_pct = (max_call_strike - current_price) / current_price * 100
                    if call_strike_proximity_pct <= 2.0: # 2% 이내 근접 (강력한 저항/돌파 기대)
                        score += 1.5
                    elif call_strike_proximity_pct <= 5.0: # 5% 이내
                        score += 0.8

            if max_put_strike is not None and max_put_volume is not None and current_price is not None and max_put_volume > 500:
                if max_put_strike < current_price: # 현재가보다 낮은 풋 스트라이크에 대량 거래
                    put_strike_proximity_pct = (current_price - max_put_strike) / current_price * 100
                    if put_strike_proximity_pct <= 2.0: # 2% 이내 근접 (강한 지지 기대)
                        score += 0.7
                    elif put_strike_proximity_pct <= 5.0:
                        score += 0.3

        # ✅ 3일 연속 마감 조건 점수 반영 (사용자 전략에 맞춰 변경)
        if consecutive_close_status == "3일 연속 양봉":
            score += 1.0 # 강한 상승 모멘텀이지만, 이미 많이 올랐을 수 있으므로 점수 조정
        elif consecutive_close_status == "3일 연속 음봉":
            score += 1.5 # ✅ 3일 연속 음봉은 매수 기회이므로 점수 가산
            # 3일 연속 음봉이면서 RSI가 과매도권(30 이하)에 진입했다면 추가 점수
            if latest_rsi is not None and latest_rsi <= 30:
                score += 1.0 # 강력한 반등 기대

        # 최종 점수가 음수가 되지 않도록 조정 (최소 점수는 0)
        if score < 0:
            score = 0

        # ✅ 추천 로직 강화 (종합 매수/매도 타점 전략 반영)
        recommendation = "⚠️ 관망 (혼조세)" # 기본값 변경

        # 매수/매도 신호 플래그 정의
        is_strong_buy_signal = False
        is_buy_consider_signal = False
        is_sell_consider_signal = False
        is_strong_sell_signal = False

        # ✅ is_good_rsi 판단 기준 변경 (RSI 70 미만까지 긍정으로 판단)
        is_good_rsi = latest_rsi is not None and 35 <= latest_rsi < 70
        is_good_disparity = disparity_20 is not None and 95 <= disparity_20 <= 105
        is_sufficient_volume = volume_rate is not None and volume_rate >= 1.2
        is_not_overheated_gap = gap_up_pct is not None and gap_up_pct < 2.0
        is_bullish_macd = macd_value is not None and macd_signal is not None and macd_value > macd_signal and macd_value > 0


        # --- 매수 신호 조합 ---
        # 1. 사용자 핵심 전략: 3일 연속 음봉 + RSI 과매도 (강력 매수)
        if consecutive_close_status == "3일 연속 음봉" and latest_rsi is not None and latest_rsi <= 40:
            if score >= 6.0 and volume_rate is not None and volume_rate >= profile["volume_rate_min"]: # 충분한 거래량
                is_strong_buy_signal = True
            elif score >= 5.0 and volume_rate is not None and volume_rate >= 0.8:
                is_buy_consider_signal = True

        # 2. 일반적인 상승 추세 매수 (눌림목)
        # 주가가 120일선 위에 있고, 20일선이 60일선 위에 있으며, RSI가 과매수권 아님
        if prev_ma_120 is not None and current_price is not None and current_price > prev_ma_120: # 장기 추세 상승
            if prev_ma_20 is not None and prev_ma_60 is not None and prev_ma_20 > prev_ma_60: # 중단기 정배열
                if is_good_rsi: # RSI 70 미만까지 긍정
                    if score >= 7.0 and macd_value is not None and macd_signal is not None and macd_value > macd_signal and volume_rate is not None and volume_rate >= profile["volume_rate_min"]:
                        is_buy_consider_signal = True # 📈 상승 추세 매수
                    elif score >= 6.0 and volume_rate is not None and volume_rate >= 0.8:
                        is_buy_consider_signal = True


        # 3. 지지선 근접 매수 (1차, 2차, 3차 지지선 활용)
        if current_price is not None:
            # 1차 지지선 (MA 20) 근접
            if support_1st is not None and abs((current_price - support_1st) / support_1st * 100) <= 1.0: # 1% 이내 근접
                if latest_rsi is not None and latest_rsi <= 60: # 과매수 아님 (RSI 60까지는 매수 고려)
                    if score >= 5.5 and volume_rate is not None and volume_rate >= 0.8:
                        is_buy_consider_signal = True
            # 2차 지지선 (MA 60) 근접
            elif support_2nd is not None and abs((current_price - support_2nd) / support_2nd * 100) <= 1.0: # 1% 이내 근접
                 if latest_rsi is not None and latest_rsi <= 55: # 과매수 아님 (RSI 55까지는 매수 고려)
                    if score >= 5.0 and volume_rate is not None and volume_rate >= 0.8:
                        is_buy_consider_signal = True
            # 3차 지지선 (MA 120) 근접
            elif support_3rd is not None and abs((current_price - support_3rd) / support_3rd * 100) <= 1.0: # 1% 이내 근접
                if latest_rsi is not None and latest_rsi <= 50: # 과매도권에 가까울수록 좋음 (RSI 50까지는 매수 고려)
                    if score >= 4.5 and volume_rate is not None and volume_rate >= 0.7:
                        is_buy_consider_signal = True


        # --- 매도 신호 조합 ---
        # 1. 과매수 + 모멘텀 약화 (강력 매도)
        if latest_rsi is not None and latest_rsi >= 70: # ✅ RSI 과매수 (70 이상)
            if stoch_k is not None and stoch_d is not None and stoch_k > 80 and stoch_k < stoch_d: # 스토캐스틱 과매수 데드크로스
                if macd_value is not None and macd_signal is not None and macd_value < macd_signal: # MACD 데드크로스
                    if score <= 5.0: # 점수가 낮아지면
                        is_strong_sell_signal = True
        # 2. 데드크로스 발생 (강력 매도)
        if trend == "데드크로스 발생":
            if score <= 4.0 and current_price is not None and prev_ma_60 is not None and current_price < prev_ma_60: # 60일선 아래 데드크로스면 더 강력
                is_strong_sell_signal = True

        # 3. 과매수 + 모멘텀 둔화 (매도 고려)
        if latest_rsi is not None and latest_rsi >= 65: # RSI 과매수권
            is_sell_consider_signal = True
        if stoch_k is not None and stoch_d is not None and stoch_k > stoch_d and stoch_k > 70: # 스토캐스틱 과매수권 유지
            is_sell_consider_signal = True
        if macd_value is not None and macd_signal is not None and macd_value < macd_signal: # MACD 음전환
            is_sell_consider_signal = True

        # 4. 저항선 근접 + 상승 둔화
        # 1차 저항선 (가장 가까운 저항) 근접 시 매도 고려
        if current_price is not None and resistance_1st is not None and \
           abs((current_price - resistance_1st) / resistance_1st * 100) <= 1.0: # 1% 이내 근접
            if latest_rsi is not None and latest_rsi >= 65: # RSI 높음
                if volume_rate is not None and volume_rate < 1.0: # 거래량 감소
                    is_sell_consider_signal = True
        # 52주 고가 근접 시 매도 고려
        if high_gap_pct is not None and high_gap_pct <= 1.0: # 52주 고가 1% 이내 근접
            if latest_rsi is not None and latest_rsi >= 70: # ✅ RSI 과열 (70 이상)
                is_sell_consider_signal = True


        # --- 최종 추천 결정 (우선순위) ---
        if is_strong_buy_signal:
            recommendation = "🔥 강력 매수 (과매도 반등)"
        elif is_strong_sell_signal:
            recommendation = "📉 강력 매도 (추세 이탈/과매수)"
        elif is_buy_consider_signal:
            recommendation = "✅ 매수 고려 (지지선 근접/모멘텀 전환)"
        elif is_sell_consider_signal:
            recommendation = "❌ 매도 고려 (과매수/저항)"
        # 다른 매수 신호가 아니지만 점수 좋고 장기 추세 양호
        elif score >= 7.0 and macd_value is not None and macd_signal is not None and macd_value > macd_signal and volume_rate is not None and volume_rate >= profile["volume_rate_min"] and current_price is not None and prev_ma_120 is not None and current_price > prev_ma_120:
            recommendation = "📈 상승 추세 매수"
        elif score >= 5.0:
            recommendation = "👀 관망 (추가 관찰)"
        else:
            recommendation = "⚠️ 관망 (혼조세)" # 기본값 유지


        result = {
            "ticker": ticker.upper(),
            "sector": sector,
            "current_price": current_price,
            "prev_close_price": prev_close_price,
            "MA_5": ma_5,
            "MA_20": ma_20,
            "MA_60": prev_ma_60,
            "MA_120": prev_ma_120,
            "RSI_14": latest_rsi,
            "Disparity_5": disparity_5,
            "Disparity_20": disparity_20,
            "Disparity_60": disparity_60,
            "Disparity_120": disparity_120,
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
            "Consecutive_Closes": consecutive_close_status,
            "Support_1st": support_1st, # 1차 지지선 (가장 가까운)
            "Support_2nd": support_2nd, # 2차 지지선 (그 다음 가까운)
            "Support_3rd": support_3rd, # 3차 지지선 (가장 먼)
            "Resistance_1st": resistance_1st, # 1차 저항선 (가장 가까운)
            "Resistance_2nd": resistance_2nd, # 2차 저항선 (그 다음 가까운)
            "Resistance_3rd": resistance_3rd, # 3차 저항선 (가장 먼)
            "Score": round(score, 1),
            "Recommendation": recommendation
        }

        return result
    except Exception as e:
        # 에러 발생 시 분석 실패 메시지 반환
        return {"ticker": ticker.upper(), "Recommendation": f"❌ 분석 실패: {e}"}

# 이 아래는 함수 테스트를 위한 예시 코드입니다.
# UI 코드는 포함되어 있지 않습니다.
if __name__ == '__main__':
    # 검색할 주식 목록 (예시)
    sample_tickers = [
        "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META", "TSLA", # 기술주
        "JPM", "BAC", "WFC", # 금융주
        "UNH", "JNJ", "LLY", # 헬스케어
        "XOM", "CVX", # 에너지
        "HD", "WMT", # 소비재
        "CAT", "GE", # 산업재
        "VZ", "T", # 통신 서비스
        "KO", "PG", # 필수 소비재
        "ADBE", "CRM", # 소프트웨어
        "SMCI", "AMD", # 반도체
        "SPG", "PLD" # 리츠
    ]

    found_stocks = []

    print(f"--- {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} 기준 주식 분석 시작 ---")

    for ticker in sample_tickers:
        print(f"Analyzing {ticker}...")
        result = swing_stock_data(ticker)
        found_stocks.append(result)

    print("\n--- 분석 결과 ---")
    if found_stocks:
        for stock in found_stocks:
            print(f"\n티커: {stock['ticker']} ({stock['sector']})")
            print(f"현재가: ${stock['current_price']:.2f}")
            print(f"RSI(14): {stock['RSI_14']:.2f}")
            print(f"거래량 비율: {stock['Volume_Rate']:.2f}x")
            print(f"MACD 추세: {stock['MACD_Trend']} (MACD: {stock['MACD']:.2f}, Signal: {stock['MACD_Signal']:.2f})")
            print(f"이격도(20): {stock['Disparity_20']:.2f}%")
            print(f"거래대금: ${stock['Volume_Turnover_Million']:.2f}M")
            print(f"3일 연속 마감: {stock['Consecutive_Closes']}")
            print(f"1차 지지선 (MA 20): ${stock['Support_1st']:.2f}")
            print(f"2차 지지선 (MA 60): ${stock['Support_2nd']:.2f}")
            print(f"3차 지지선 (MA 120): ${stock['Support_3rd']:.2f}")
            print(f"1차 저항선: ${stock['Resistance_1st']:.2f}") # 저항선 출력 추가
            print(f"2차 저항선: ${stock['Resistance_2nd']:.2f}") # 저항선 출력 추가
            print(f"3차 저항선: ${stock['Resistance_3rd']:.2f}") # 저항선 출력 추가
            print(f"종합 점수: {stock['Score']:.1f}")
            print(f"추천: {stock['Recommendation']}")
            print("-" * 30)
    else:
        print("현재 조건에 맞는 주식을 찾을 수 없습니다.")

    print("\n--- 분석 완료 ---")
