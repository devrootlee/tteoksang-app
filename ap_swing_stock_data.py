import requests
from datetime import datetime, timedelta
import pandas as pd
import pytz
import streamlit as st

headers = {
    'accept': 'application/json',
    'APCA-API-KEY-ID': st.secrets['API_KEY_ID'],
    'APCA-API-SECRET-KEY': st.secrets['API_SECRET_KEY']
}

# ✅ 가격 기본 정보(1년치)
def price_base_data(symbols: list):
    price_base_url = 'https://data.alpaca.markets/v2/stocks/bars'
    latest_bar_url = 'https://data.alpaca.markets/v2/stocks/bars/latest'

    timeframe = '1D'
    print(headers)

    seoul_tz = pytz.timezone('Asia/Seoul')
    now_seoul = datetime.now(seoul_tz)
    today_date = now_seoul.date()

    end = today_date - timedelta(days=2)
    while end.weekday() >= 5: # 토(5) 또는 일(6)이면
        end -= timedelta(days=1)
    end = end.strftime('%Y-%m-%d')

    start = (datetime.strptime(end, '%Y-%m-%d').date() - timedelta(days=365)).strftime('%Y-%m-%d')

    daily_bar_params = {
        'symbols': ','.join(symbols),
        'timeframe': timeframe,
        'start': start,
        'end': end,
        'limit': '10000',
        'adjustment': 'raw',
        'feed': 'sip',
        'sort': 'asc'
    }

    daily_response = requests.get(price_base_url, headers=headers, params=daily_bar_params)
    daily_data = daily_response.json().get('bars', {})

    latest_params = {
        'symbols': ','.join(symbols),
        'feed': 'delayed_sip'
    }
    latest_response = requests.get(latest_bar_url, headers=headers, params=latest_params)
    latest_data = latest_response.json().get('bars', {})

    final_data = {}
    for symbol in symbols:
        final_data[symbol] = daily_data.get(symbol, [])
        if symbol in latest_data and latest_data[symbol] is not None:
            latest_bar_for_symbol = latest_data[symbol]
            final_data[symbol].append(latest_bar_for_symbol)
    return final_data

# ✅ rsi 계산
def calculate_rsi(price_data: dict, period: int = 14):
    rsi_results = {}
    for symbol, bars in price_data.items():
        if not bars or len(bars) < period + 1:
            rsi_results[symbol] = None
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']

        df['change'] = df['close'].diff()
        df['gain'] = df['change'].apply(lambda x: x if x > 0 else 0)
        df['loss'] = df['change'].apply(lambda x: abs(x) if x < 0 else 0)

        avg_gain = df['gain'].ewm(com=period - 1, adjust=False).mean()
        avg_loss = df['loss'].ewm(com=period - 1, adjust=False).mean()

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        rsi_results[symbol] = rsi.iloc[-1] if not rsi.empty else None
    return rsi_results

# ✅ MA(이동평균선) 계산
def calculate_ma(price_data: dict, periods: list = [5, 20, 50]):
    ma_results = {}
    for symbol, bars in price_data.items():
        if not bars:
            ma_results[symbol] = {f'ma_{p}': None for p in periods}
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']

        symbol_ma_data = {}
        for p in periods:
            if len(df) >= p:
                ma_value = df['close'].rolling(window=p).mean().iloc[-1]
                symbol_ma_data[f'ma_{p}'] = ma_value
            else:
                symbol_ma_data[f'ma_{p}'] = None
        ma_results[symbol] = symbol_ma_data
    return ma_results

# ✅ 볼린저 밴드 (Bollinger Bands) 계산
def calculate_bollinger_bands(price_data: dict, period: int = 20, num_std_dev: float = 2):
    bb_results = {}
    for symbol, bars in price_data.items():
        if not bars or len(bars) < period:
            bb_results[symbol] = {'bb_middle': None, 'bb_upper': None, 'bb_lower': None}
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']

        middle_band = df['close'].rolling(window=period).mean()
        std_dev = df['close'].rolling(window=period).std()
        upper_band = middle_band + (std_dev * num_std_dev)
        lower_band = middle_band - (std_dev * num_std_dev)

        bb_results[symbol] = {
            'bb_middle': middle_band.iloc[-1] if not middle_band.empty else None,
            'bb_upper': upper_band.iloc[-1] if not upper_band.empty else None,
            'bb_lower': lower_band.iloc[-1] if not lower_band.empty else None
        }
    return bb_results

# ✅ MACD (Moving Average Convergence Divergence) 계산
def calculate_macd(price_data: dict, short_period: int = 12, long_period: int = 26, signal_period: int = 9):
    macd_results = {}
    for symbol, bars in price_data.items():
        required_data_length = long_period + signal_period - 1
        if not bars or len(bars) < required_data_length:
            macd_results[symbol] = {'macd_line': None, 'macd_signal': None, 'macd_histogram': None}
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']

        ema_short = df['close'].ewm(span=short_period, adjust=False).mean()
        ema_long = df['close'].ewm(span=long_period, adjust=False).mean()
        macd_line = ema_short - ema_long
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        macd_histogram = macd_line - signal_line

        macd_results[symbol] = {
            'macd_line': macd_line.iloc[-1] if not macd_line.empty else None,
            'macd_signal': signal_line.iloc[-1] if not signal_line.empty else None,
            'macd_histogram': macd_histogram.iloc[-1] if not macd_histogram.empty else None
        }
    return macd_results

# ✅ 거래량 지표 (VMA, OBV) 계산
def calculate_volume_indicators(price_data: dict, vma_period: int = 20):
    volume_results = {}
    for symbol, bars in price_data.items():
        if not bars:
            volume_results[symbol] = {'vma': None, 'obv': None}
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']
        df['volume'] = df['v']

        vma = None
        if len(df) >= vma_period:
            vma = df['volume'].rolling(window=vma_period).mean().iloc[-1]

        latest_obv = None
        if len(df) > 1:
            obv_values = [0]
            for i in range(1, len(df)):
                if df['close'].iloc[i] > df['close'].iloc[i - 1]:
                    obv_values.append(obv_values[-1] + df['volume'].iloc[i])
                elif df['close'].iloc[i] < df['close'].iloc[i - 1]:
                    obv_values.append(obv_values[-1] - df['volume'].iloc[i])
                else:
                    obv_values.append(obv_values[-1])
            latest_obv = obv_values[-1]
        elif len(df) == 1:
            latest_obv = 0

        volume_results[symbol] = {
            'vma': vma,
            'obv': latest_obv
        }
    return volume_results

# ✅ 스토캐스틱 오실레이터 (Stochastic Oscillator) 계산
def calculate_stochastic_oscillator(price_data: dict, k_period: int = 14, d_period: int = 3):
    stoch_results = {}
    for symbol, bars in price_data.items():
        required_data_length = k_period + d_period - 1
        if not bars or len(bars) < required_data_length:
            stoch_results[symbol] = {'stoch_k': None, 'stoch_d': None}
            continue

        df = pd.DataFrame(bars)
        df['close'] = df['c']
        df['high'] = df['h']
        df['low'] = df['l']

        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()

        fast_k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low + 1e-10))
        slow_d = fast_k.rolling(window=d_period).mean()

        stoch_results[symbol] = {
            'stoch_k': fast_k.iloc[-1] if not fast_k.empty else None,
            'stoch_d': slow_d.iloc[-1] if not slow_d.empty else None
        }
    return stoch_results

# ✅ ATR (Average True Range) 계산
def calculate_atr(price_data: dict, period: int = 14):
    atr_results = {}
    for symbol, bars in price_data.items():
        required_data_length = period + 1
        if not bars or len(bars) < required_data_length:
            atr_results[symbol] = None
            continue

        df = pd.DataFrame(bars)
        df['high'] = df['h']
        df['low'] = df['l']
        df['close'] = df['c']

        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = true_range.ewm(span=period, adjust=False).mean()

        atr_results[symbol] = atr.iloc[-1] if not atr.empty else None
    return atr_results

# --- 매수/매도 로직 함수 추가 ---
def determine_trade_signals(symbol_data: dict):
    current_price = symbol_data.get('current_price')
    previous_close = symbol_data.get('previous_close')

    rsi = symbol_data.get('rsi')
    ma_5 = symbol_data.get('ma_5')
    ma_20 = symbol_data.get('ma_20')
    ma_50 = symbol_data.get('ma_50')
    bb_upper = symbol_data.get('bb_upper')
    bb_lower = symbol_data.get('bb_lower')
    macd_line = symbol_data.get('macd_line')
    macd_signal = symbol_data.get('macd_signal')
    stoch_k = symbol_data.get('stoch_k')
    stoch_d = symbol_data.get('stoch_d')
    atr = symbol_data.get('atr')

    buy_signal_reasons = []
    sell_signal_reasons = []

    buy_target_price = None
    sell_target_price = None

    if current_price is None or previous_close is None:
        return {'buy_signal': False, 'sell_signal': False, 'trade_opinion': '데이터 부족',
                'buy_reasons': [], 'sell_reasons': [],
                'buy_target_price': None, 'sell_target_price': None}

    # --- 매수 신호 판단 ---
    # 1. RSI 과매도 (30 이하)
    if rsi is not None and rsi <= 30:
        buy_signal_reasons.append("RSI 과매도 (<= 30)")

    # 2. 이동평균선 정배열 (MA5 > MA20 > MA50) 및 현재가가 MA50 위에 있을 때
    if ma_5 is not None and ma_20 is not None and ma_50 is not None:
        if ma_5 > ma_20 and ma_20 > ma_50 and current_price > ma_50:
            buy_signal_reasons.append("이동평균선 정배열 및 주가 MA50 상회")
        # 골든 크로스 (MA5가 MA20을 상향 돌파, 이전 값과 비교해야 정확하지만 현재 값으로만 판단)
        elif ma_5 > ma_20 and current_price > ma_5:
            buy_signal_reasons.append("MA5가 MA20 상회하며 주가 상승 추세")

    # 2-1. 추가: 현재가가 모든 주요 이동평균선 위에 위치 (GPT 분석 반영)
    if (current_price is not None and
        ma_5 is not None and current_price > ma_5 and
        ma_20 is not None and current_price > ma_20 and
        ma_50 is not None and current_price > ma_50):
        buy_signal_reasons.append("현재가가 모든 주요 이동평균선 위에 위치")


    # 3. 볼린저 밴드 하단 근접 또는 하단 이탈 후 회복
    if current_price is not None and bb_lower is not None and bb_upper is not None:
        if current_price < bb_lower * 1.01:
            buy_signal_reasons.append("볼린저 밴드 하단 근접")

    # 4. MACD 매수 신호 (MACD 라인이 시그널 라인 상회)
    if macd_line is not None and macd_signal is not None and macd_line > macd_signal:
        buy_signal_reasons.append("MACD 골든크로스 (MACD > Signal)")

    # 5. 스토캐스틱 과매도 및 상승 전환 (K가 D를 상회, K<=20)
    if stoch_k is not None and stoch_d is not None and stoch_k <= 20 and stoch_k > stoch_d:
        buy_signal_reasons.append("스토캐스틱 과매도 구간에서 상승 전환 (K > D, K<=20)")

    # 6. ATR 활용 변동성 돌파 매수
    if atr is not None and current_price is not None and previous_close is not None:
        if current_price > (previous_close + atr):
            buy_signal_reasons.append(f"ATR 상향 돌파 (전일 종가 + {atr:.2f} 이상)")

    # --- 매도 신호 판단 ---
    # 1. RSI 과매수 (70 이상)
    if rsi is not None and rsi >= 70:
        sell_signal_reasons.append("RSI 과매수 (>= 70)")

    # 2. 이동평균선 역배열 (MA5 < MA20 < MA50) 및 현재가가 MA50 아래에 있을 때
    if ma_5 is not None and ma_20 is not None and ma_50 is not None:
        if ma_5 < ma_20 and ma_20 < ma_50 and current_price < ma_50:
            sell_signal_reasons.append("이동평균선 역배열 및 주가 MA50 하회")
        # 데드 크로스 (MA5가 MA20을 하향 돌파)
        elif ma_5 < ma_20 and current_price < ma_5:
            sell_signal_reasons.append("MA5가 MA20 하회하며 주가 하락 추세")

    # 3. 볼린저 밴드 상단 근접 또는 상단 이탈 후 회복
    if current_price is not None and bb_upper is not None:
        if current_price > bb_upper * 0.99:
            sell_signal_reasons.append("볼린저 밴드 상단 근접")

    # 4. MACD 매도 신호 (MACD 라인이 시그널 라인 하회)
    if macd_line is not None and macd_signal is not None and macd_line < macd_signal:
        sell_signal_reasons.append("MACD 데드크로스 (MACD < Signal)")

    # 5. 스토캐스틱 과매수 및 하락 전환 (K가 D를 하회, K>=80)
    if stoch_k is not None and stoch_d is not None and stoch_k >= 80 and stoch_k < stoch_d:
        sell_signal_reasons.append("스토캐스틱 과매수 구간에서 하락 전환 (K < D, K>=80)")

    # 6. ATR 활용 변동성 돌파 매도 (또는 손절)
    if atr is not None and current_price is not None and previous_close is not None:
        if current_price < (previous_close - atr):
            sell_signal_reasons.append(f"ATR 하향 돌파 (전일 종가 - {atr:.2f} 이하)")

    # --- 매수/매도 적정 가격 판단 ---
    if bb_lower is not None:
        buy_target_price = bb_lower
    elif ma_20 is not None:
        buy_target_price = ma_20

    if bb_upper is not None:
        sell_target_price = bb_upper
    elif ma_20 is not None:
        sell_target_price = ma_20

    # --- 최종 신호 결정 로직 (우선순위 및 상호 배타적 판단) ---
    actual_buy_signal = len(buy_signal_reasons) > 0
    actual_sell_signal = len(sell_signal_reasons) > 0

    trade_opinion = "관망"

    if actual_buy_signal and actual_sell_signal:
        # ATR 돌파가 발생하면 해당 방향으로 강한 신호로 간주
        if "ATR 상향 돌파" in buy_signal_reasons:
            trade_opinion = "강력 매수 (ATR 돌파 포함 혼조)"
        elif "ATR 하향 돌파" in sell_signal_reasons:
            trade_opinion = "강력 매도 (ATR 돌파 포함 혼조)"
        # 그 외의 경우 (ATR 돌파가 없거나, 다른 이유로 혼조일 때)
        elif len(buy_signal_reasons) > len(sell_signal_reasons) and rsi is not None and rsi <= 35:
            trade_opinion = "매수 고려 (혼조세 속 매수 우위)"
        elif len(sell_signal_reasons) > len(buy_signal_reasons) and rsi is not None and rsi >= 65:
            trade_opinion = "매도 고려 (혼조세 속 매도 우위)"
        else:
            trade_opinion = "혼조 (매수/매도 신호 충돌)"

    elif actual_buy_signal:
        trade_opinion = "매수"
    elif actual_sell_signal:
        trade_opinion = "매도"
    else:
        trade_opinion = "관망"

    return {
        'buy_signal': actual_buy_signal,
        'buy_reasons': buy_signal_reasons,
        'buy_target_price': buy_target_price,
        'sell_signal': actual_sell_signal,
        'sell_reasons': sell_signal_reasons,
        'sell_target_price': sell_target_price,
        'trade_opinion': trade_opinion
    }

# ✅ 데이터 전체 머지
def merge_swing_data(symbols: list, rsi_period: int = 14, ma_periods: list = [5, 20, 50], bb_period: int = 20,
                     bb_num_std_dev: float = 2, macd_short: int = 12, macd_long: int = 26, macd_signal: int = 9,
                     vma_period: int = 20, stoch_k_period: int = 14, stoch_d_period: int = 3, atr_period: int = 14):

    historical_price_data = price_base_data(symbols)
    if not historical_price_data:
        return []

    calculated_rsi_data = calculate_rsi(historical_price_data, period=rsi_period)
    calculated_ma_data = calculate_ma(historical_price_data, periods=ma_periods)
    calculated_bb_data = calculate_bollinger_bands(historical_price_data, period=bb_period, num_std_dev=bb_num_std_dev)
    calculated_macd_data = calculate_macd(historical_price_data, short_period=macd_short, long_period=macd_long,
                                          signal_period=macd_signal)
    calculated_volume_data = calculate_volume_indicators(historical_price_data, vma_period=vma_period)
    calculated_stoch_data = calculate_stochastic_oscillator(historical_price_data, k_period=stoch_k_period,
                                                            d_period=stoch_d_period)
    calculated_atr_data = calculate_atr(historical_price_data, period=atr_period)

    final_data_list = []
    for symbol in symbols:
        current_price = None
        previous_close = None

        bars = historical_price_data.get(symbol)
        if bars and len(bars) >= 2:
            current_price_bar = bars[-1]
            previous_day_bar = bars[-2]
            current_price = current_price_bar['c']
            previous_close = previous_day_bar['c']
        elif bars and len(bars) == 1:
            current_price_bar = bars[-1]
            current_price = current_price_bar['c']
            previous_close = current_price
        else:
            current_price = None
            previous_close = None

        symbol_indicators = {
            'current_price': current_price,
            'previous_close': previous_close,
            'rsi': calculated_rsi_data.get(symbol),
            'ma_5': calculated_ma_data.get(symbol, {}).get('ma_5'),
            'ma_20': calculated_ma_data.get(symbol, {}).get('ma_20'),
            'ma_50': calculated_ma_data.get(symbol, {}).get('ma_50'),
            'bb_middle': calculated_bb_data.get(symbol, {}).get('bb_middle'),
            'bb_upper': calculated_bb_data.get(symbol, {}).get('bb_upper'),
            'bb_lower': calculated_bb_data.get(symbol, {}).get('bb_lower'),
            'macd_line': calculated_macd_data.get(symbol, {}).get('macd_line'),
            'macd_signal': calculated_macd_data.get(symbol, {}).get('macd_signal'),
            'macd_histogram': calculated_macd_data.get(symbol, {}).get('macd_histogram'),
            'vma': calculated_volume_data.get(symbol, {}).get('vma'),
            'obv': calculated_volume_data.get(symbol, {}).get('obv'),
            'stoch_k': calculated_stoch_data.get(symbol, {}).get('stoch_k'),
            'stoch_d': calculated_stoch_data.get(symbol, {}).get('stoch_d'),
            'atr': calculated_atr_data.get(symbol)
        }

        trade_signals = determine_trade_signals(symbol_indicators)

        buy_reasons_str = ', '.join(trade_signals['buy_reasons']) if trade_signals['buy_reasons'] else '해당 없음'
        sell_reasons_str = ', '.join(trade_signals['sell_reasons']) if trade_signals['sell_reasons'] else '해당 없음'

        item_data = {
            'ticker': symbol,
            'current_price': current_price,
            'previous_close': previous_close,
            'rsi': symbol_indicators['rsi'],
            'ma_5': symbol_indicators['ma_5'],
            'ma_20': symbol_indicators['ma_20'],
            'ma_50': symbol_indicators['ma_50'],
            'bb_middle': symbol_indicators['bb_middle'],
            'bb_upper': symbol_indicators['bb_upper'],
            'bb_lower': symbol_indicators['bb_lower'],
            'macd_line': symbol_indicators['macd_line'],
            'macd_signal': symbol_indicators['macd_signal'],
            'macd_histogram': symbol_indicators['macd_histogram'],
            'vma': symbol_indicators['vma'],
            'obv': symbol_indicators['obv'],
            'stoch_k': symbol_indicators['stoch_k'],
            'stoch_d': symbol_indicators['stoch_d'],
            'atr': symbol_indicators['atr'],
            'buy_signal': trade_signals['buy_signal'],
            'buy_reasons': buy_reasons_str,
            'buy_target_price': trade_signals['buy_target_price'],
            'sell_signal': trade_signals['sell_signal'],
            'sell_reasons': sell_reasons_str,
            'sell_target_price': trade_signals['sell_target_price'],
            'trade_opinion': trade_signals['trade_opinion']
        }

        final_data_list.append(item_data)
    return final_data_list
