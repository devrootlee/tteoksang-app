import streamlit as st
import pandas as pd
import base64
import time  # sleep 함수를 위해 필요

# yf_swing_stock_data.py와 yf_market_data.py는 별도의 파일로 존재한다고 가정합니다.
# 실제 실행 시 이 파일들이 같은 디렉토리에 있어야 합니다.
from yf_swing_stock_data import swing_stock_data
from yf_market_data import market_data

# yf_gem_discovery.py에서 get_gem_candidates 함수 임포트
# 이 파일이 yf_gem_discovery.py와 같은 디렉토리에 있어야 합니다.
from yf_gem_discovery import get_gem_candidates


# 모바일 감지 함수 (변경 없음)
@st.cache_data(show_spinner=False)
def is_mobile_device():
    try:
        ua = st.experimental_user_agent()
        return "Mobile" in ua or "Android" in ua or "iPhone" in ua
    except:
        return False


IS_MOBILE = is_mobile_device()

# ---
# 캐시/세션 초기화 버튼 (변경 없음)
with st.sidebar:
    if st.button("🔁 캐시 데이터 초기화 (앱 오류 시 시도)", help="이 버튼은 계산에 사용된 캐시 데이터만 지웁니다. 추가된 종목 정보는 유지됩니다."):
        st.cache_data.clear()  # 캐시된 모든 데이터 지우기


# ---
# 이미지 base64 인코딩 함수 (변경 없음)
def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
        return encoded
    except FileNotFoundError:
        st.warning(f"Warning: Image file not found at {image_path}. Displaying without icon.")
        return ""


# 이미지 파일 로드 (변경 없음)
img_base64 = get_image_base64("떡상-icon.jpg")

# UI 렌더링 (변경 없음)
st.set_page_config(page_title="📊 떡상", layout="wide")
st.markdown(
    f"""
    <h1 style="display: flex; align-items: center; gap: 10px;">
        {'<img src="data:image/jpeg;base64,' + img_base64 + '" width="64">' if img_base64 else ''}
        떡상
    </h1>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(["📖 Read Me", "🛰️시장 분석", "📈 주식 분석", "💎 보석 발굴"])

# tab1: 안내문 (변경 없음)
with tab1:
    st.subheader("📖 Read Me")
    st.markdown("""
    이 앱은 종목 분석 및 스윙 트레이딩 추천 시스템을 포함한 투자 보조 도구입니다.
    사용자의 개인적인 투자 판단에 따라 활용하시기 바랍니다.
    """)

# tab2: 시장 분석 (변경 없음)
with tab2:
    st.subheader("🛰️ 미국장 시장 실시간 분석")


    @st.cache_data(ttl=300)
    def get_market_data_cached():
        return market_data()


    with st.spinner("🚀 시장 데이터 불러오는 중..."):
        market_outlook = get_market_data_cached()

    if "error" in market_outlook:
        st.error(f"시장 데이터 로드 중 오류 발생: {market_outlook['error']}")
        st.info("데이터는 실시간으로 변동되거나 일시적으로 불안정할 수 있습니다. 잠시 후 다시 시도해주세요.")
    else:
        outlook_details = market_outlook['OverallMarketOutlook']
        st.markdown(f"#### **{outlook_details['summary']}**")

        if outlook_details.get("no_sector_trend"):
            st.caption("섹터별 특별한 추세가 감지되지 않습니다.")
        else:
            if outlook_details['strong_sectors']:
                st.markdown(f"- **주요 강세 섹터:** {', '.join(outlook_details['strong_sectors'])}")
            if outlook_details['weak_sectors']:
                st.markdown(f"- **주요 약세 섹터:** {', '.join(outlook_details['weak_sectors'])}")
        st.caption("이 판단은 주요 지수, 변동성, 시장 심리 및 섹터별 흐름을 종합한 결과입니다.")

        st.markdown("---")
        st.markdown("### 🔍 주요 지수 현황")
        col_nq, col_sp, col_vix = st.columns(3)

        with col_nq:
            st.metric(label="**나스닥 선물 (NQ=F)**",
                      value=f"{market_outlook['NASDAQ']['price']:,}",
                      delta=f"{market_outlook['NASDAQ']['change']:.2f}%")
            st.caption(f"상태: {market_outlook['NASDAQ']['status']}")
        with col_sp:
            st.metric(label="**S&P500 선물 (ES=F)**",
                      value=f"{market_outlook['S&P500']['price']:,}",
                      delta=f"{market_outlook['S&P500']['change']:.2f}%")
            st.caption(f"상태: {market_outlook['S&P500']['status']}")
        with col_vix:
            st.metric(label="**변동성 지수 (VIX)**",
                      value=f"{market_outlook['VIX']['price']:.2f}",
                      delta=f"{market_outlook['VIX']['change']:.2f}%")
            st.caption(f"상태: {market_outlook['VIX']['status']}")

        st.markdown("---")
        st.markdown("### 📊 시장 심리: 공포 탐욕 지수")
        fgi_col1, fgi_col2 = st.columns([1, 2])
        with fgi_col1:
            st.metric(label="**현재 공포 탐욕 값**", value=market_outlook['FearGreedIndex']['value'])
        with fgi_col2:
            st.markdown(f"**상태:** {market_outlook['FearGreedIndex']['status']}")
            st.caption(f"상세 설명: {market_outlook['FearGreedIndex']['comment']}")

        st.markdown("---")
        st.markdown("### 📈 주요 섹터별 트렌드")
        sector_df_data = []
        for name, info in market_outlook['Sectors'].items():
            sector_df_data.append({"섹터명": name, "티커": info['ticker'], "상태": info['status']})
        sector_table_df = pd.DataFrame(sector_df_data)
        st.dataframe(sector_table_df, use_container_width=True, hide_index=True)

# tab3: 주식 분석 (수정 반영)
with tab3:
    st.subheader("📈 주식 분석")

    # 세션 상태 변수 초기화
    if "tickers" not in st.session_state:
        st.session_state.tickers = []
    if "ticker_data" not in st.session_state:
        st.session_state.ticker_data = {}
    if "default_tickers_loaded" not in st.session_state:
        st.session_state.default_tickers_loaded = False
    if "reanalyze_trigger" not in st.session_state:
        st.session_state.reanalyze_trigger = None  # 재분석 트리거용 상태 변수

    # 신규 종목 입력
    new_input = st.text_input("🎯 분석할 종목 입력 (예: AAPL)", "")
    if st.button("➕ 종목 추가") and new_input:
        symbol = new_input.strip().upper()
        if symbol in st.session_state.tickers:
            st.warning(f"이미 추가된 종목입니다: {symbol}")
        else:
            with st.spinner(f"🔍 {symbol} 분석 중..."):
                data = swing_stock_data(symbol)
                if data and "Recommendation" in data and "❌ 분석 실패" not in data["Recommendation"]:
                    st.session_state.tickers.append(symbol)
                    st.session_state.ticker_data[symbol] = data
                else:
                    st.error(f"❌ 데이터를 불러올 수 없거나 분석에 실패했습니다: {symbol}. 오류: {data.get('Recommendation', '알 수 없음')}")
            st.rerun()


    # 종목 삭제 함수
    def delete_ticker_callback(ticker_to_delete):
        if ticker_to_delete in st.session_state.tickers:
            st.session_state.tickers.remove(ticker_to_delete)
            st.session_state.ticker_data.pop(ticker_to_delete, None)


    # 종목 재분석 함수
    def reanalyze_ticker_callback(ticker_to_reanalyze):
        st.session_state.ticker_data.pop(ticker_to_reanalyze, None)
        st.session_state.reanalyze_trigger = ticker_to_reanalyze


    # 재분석 트리거 처리
    if st.session_state.reanalyze_trigger:
        ticker_to_reanalyze = st.session_state.reanalyze_trigger
        with st.spinner(f"🔍 {ticker_to_reanalyze} 재분석 중..."):
            data = swing_stock_data(ticker_to_reanalyze)
            if data and "Recommendation" in data and "❌ 분석 실패" not in data["Recommendation"]:
                st.session_state.ticker_data[ticker_to_reanalyze] = data
            else:
                st.error(
                    f"❌ {ticker_to_reanalyze} 재분석 중 데이터 로드 실패. 잠시 후 다시 시도해주세요. 오류: {data.get('Recommendation', '알 수 없음')}")
        st.session_state.reanalyze_trigger = None
        st.rerun()

    # 종목 삭제 및 재분석 UI
    if st.session_state.tickers:
        with st.expander("🗑️ 종목 관리 (삭제/재분석)", expanded=False):
            for t in list(st.session_state.tickers):
                col1, col2, col3 = st.columns([4, 1.5, 1])
                with col1:
                    st.markdown(f"**{t}**")
                with col2:
                    st.button("🔄 재분석", key=f"reanalyze_btn_{t}", on_click=reanalyze_ticker_callback, args=(t,))
                with col3:
                    st.button("삭제", key=f"del_btn_{t}", on_click=delete_ticker_callback, args=(t,))
                if t not in st.session_state.tickers:
                    st.rerun()

    # 기본 종목 로딩
    if not st.session_state.tickers and not st.session_state.default_tickers_loaded:
        default_tickers = ["OPTT", "APP", "LAES", "TSSI"]
        default_load_successful_count = 0
        for t in default_tickers:
            with st.spinner(f" {t} 분석 중..."):
                data = swing_stock_data(t)
                if data and "Recommendation" in data and "❌ 분석 실패" not in data["Recommendation"]:
                    st.session_state.tickers.append(t)
                    st.session_state.ticker_data[t] = data
                    default_load_successful_count += 1
                else:
                    st.warning(f"기본 종목 '{t}' 로드 실패: {data.get('Recommendation', '알 수 없음')}")

        st.session_state.default_tickers_loaded = True
        if default_load_successful_count > 0:
            st.rerun()

    # 유효한 티커 필터링
    valid_tickers = [t for t in st.session_state.tickers if t in st.session_state.ticker_data]

    # 핵심 요약 테이블
    if valid_tickers:
        st.markdown("### ✅ 핵심 요약 테이블")
        rows = []
        for t in valid_tickers:
            data = st.session_state.ticker_data[t]
            rows.append({
                "종목": data.get("ticker"),
                "현재가": f"${data.get('current_price'):.2f}" if data.get('current_price') is not None else "N/A",
                "점수": f"{data.get('Score'):.1f}",
                "추천": data.get("Recommendation")
            })

        rec_df = pd.DataFrame(rows).sort_values(by="점수", ascending=False)
        st.dataframe(rec_df, use_container_width=True, hide_index=True)

        # 개별 종목 지표 상세 보기
        with st.expander("📊 개별 종목 지표 상세 보기"):
            for t in valid_tickers:
                data = st.session_state.ticker_data[t]
                st.markdown(f"#### {t} - {data.get('Recommendation')} ({data.get('Score')}점)")

                # 가격/추세 지표
                st.markdown("##### 📉 가격/추세 지표")
                trend_data = {
                    "지표": ["현재가", "전일 종가", "5일 MA", "20일 MA", "60일 MA", "120일 MA", "추세"],
                    "값": [
                        f"${data.get('current_price'):.2f}" if data.get('current_price') is not None else "N/A",
                        f"${data.get('prev_close_price'):.2f}" if data.get('prev_close_price') is not None else "N/A",
                        f"${data.get('MA_5'):.2f}" if data.get('MA_5') is not None else "N/A",
                        f"${data.get('MA_20'):.2f}" if data.get('MA_20') is not None else "N/A",
                        f"${data.get('MA_60'):.2f}" if data.get('MA_60') is not None else "N/A",
                        f"${data.get('MA_120'):.2f}" if data.get('MA_120') is not None else "N/A",
                        data.get("Trend", "N/A")
                    ]
                }
                st.dataframe(pd.DataFrame(trend_data), hide_index=True, use_container_width=True)

                # 모멘텀/수급 지표
                st.markdown("##### 📊 모멘텀/수급 지표")
                momentum_data = {
                    "지표": ["RSI(14)", "Stoch K", "Stoch D", "MACD", "MACD Signal", "MACD 추세", "거래량 배율", "거래대금(M$)"],
                    "값": [
                        f"{data.get('RSI_14'):.2f}" if data.get('RSI_14') is not None else "N/A",
                        f"{data.get('Stoch_K'):.2f}" if data.get('Stoch_K') is not None else "N/A",
                        f"{data.get('Stoch_D'):.2f}" if data.get('Stoch_D') is not None else "N/A",
                        f"{data.get('MACD'):.2f}" if data.get('MACD') is not None else "N/A",
                        f"{data.get('MACD_Signal'):.2f}" if data.get('MACD_Signal') is not None else "N/A",
                        data.get("MACD_Trend", "N/A"),
                        f"{data.get('Volume_Rate'):.2f}x" if data.get('Volume_Rate') is not None else "N/A",
                        f"${data.get('Volume_Turnover_Million'):.2f}" if data.get(
                            'Volume_Turnover_Million') is not None else "N/A"
                    ]
                }
                st.dataframe(pd.DataFrame(momentum_data), hide_index=True, use_container_width=True)

                # 시장 위치/기타 지표
                st.markdown("##### 📦 시장 위치/기타 지표")
                market_pos_data = {
                    "지표": ["52주 고가 근접도(%)", "52주 저가 근접도(%)", "볼린저 상단", "볼린저 중간", "볼린저 하단", "현재가 BB 위치", "갭 상승률(%)",
                           "3일 연속 마감"],
                    "값": [
                        f"{data.get('High_Proximity_Pct'):.2f}" if data.get(
                            'High_Proximity_Pct') is not None else "N/A",
                        f"{data.get('Low_Proximity_Pct'):.2f}" if data.get('Low_Proximity_Pct') is not None else "N/A",
                        f"${data.get('BB_Upper'):.2f}" if data.get('BB_Upper') is not None else "N/A",
                        f"${data.get('BB_Middle'):.2f}" if data.get('BB_Middle') is not None else "N/A",
                        f"${data.get('BB_Lower'):.2f}" if data.get('BB_Lower') is not None else "N/A",
                        data.get("Price_Position", "N/A"),
                        f"{data.get('Gap_Up_Pct'):.2f}" if data.get('Gap_Up_Pct') is not None else "N/A",
                        data.get("Consecutive_Closes", "N/A")
                    ]
                }
                st.dataframe(pd.DataFrame(market_pos_data), hide_index=True, use_container_width=True)

                # 옵션 정보
                if data.get('option_expiry'):
                    st.markdown("##### 💹 옵션 정보")
                    option_data = {
                        "지표": ["옵션 만기일", "최대 콜 스트라이크", "최대 콜 거래량", "최대 풋 스트라이크", "최대 풋 거래량"],
                        "값": [
                            data.get('option_expiry', "N/A"),
                            f"${data.get('max_call_strike'):.2f}" if data.get('max_call_strike') is not None else "N/A",
                            f"{data.get('max_call_volume'):,}" if data.get('max_call_volume') is not None else "N/A",
                            f"${data.get('max_put_strike'):.2f}" if data.get('max_put_strike') is not None else "N/A",
                            f"{data.get('max_put_volume'):,}" if data.get('max_put_volume') is not None else "N/A"
                        ]
                    }
                    st.dataframe(pd.DataFrame(option_data), hide_index=True, use_container_width=True)

                # 지지선 정보
                st.markdown("---")
                st.markdown("##### 📍 현재 가격 및 지지선 위치")
                current_price = data.get('current_price')
                support_1st = data.get('Support_1st')
                support_2nd = data.get('Support_2nd')
                support_3rd = data.get('Support_3rd')

                support_level_data = {
                    "지표": ["현재가", "1차 지지선 (MA 20)", "2차 지지선 (MA 60)", "3차 지지선 (MA 120)"],
                    "값": [
                        f"${current_price:.2f}" if current_price is not None else "N/A",
                        f"${support_1st:.2f}" if support_1st is not None else "N/A",
                        f"${support_2nd:.2f}" if support_2nd is not None else "N/A",
                        f"${support_3rd:.2f}" if support_3rd is not None else "N/A"
                    ]
                }
                st.dataframe(pd.DataFrame(support_level_data), hide_index=True, use_container_width=True)

                if current_price is not None and support_1st is not None and support_2nd is not None and support_3rd is not None:
                    if current_price >= support_1st:
                        st.success(
                            f"**현재 가격 (${current_price:.2f})**은 1차 지지선 (${support_1st:.2f}) 위에 있습니다. 긍정적인 신호입니다.")
                    elif current_price >= support_2nd and current_price < support_1st:
                        st.warning(
                            f"**현재 가격 (${current_price:.2f})**은 1차 지지선 (${support_1st:.2f}) 아래에 있지만, 2차 지지선 (${support_2nd:.2f}) 위에 있습니다. 2차 지지선에서의 반등을 기대할 수 있습니다.")
                    elif current_price >= support_3rd and current_price < support_2nd:
                        st.warning(
                            f"**현재 가격 (${current_price:.2f})**은 2차 지지선 (${support_2nd:.2f}) 아래에 있지만, 3차 지지선 (${support_3rd:.2f}) 위에 있습니다. 장기 지지선에서의 반등을 기대할 수 있습니다.")
                    elif current_price < support_3rd:
                        st.error(
                            f"**현재 가격 (${current_price:.2f})**은 3차 지지선 (${support_3rd:.2f}) 아래에 있습니다. 장기 추세 이탈 가능성이 있으니 매우 주의가 필요합니다.")
                    else:
                        st.info("현재 가격과 지지선 위치를 파악할 수 없습니다.")
                else:
                    st.info("지지선 정보를 불러올 수 없습니다. (데이터 부족 또는 계산 오류)")

                st.markdown("---")

                # 저항선 정보 추가
                st.markdown("##### ⛰️ 현재 가격 및 저항선 위치")
                resistance_1st = data.get('Resistance_1st')
                resistance_2nd = data.get('Resistance_2nd')
                resistance_3rd = data.get('Resistance_3rd')

                resistance_level_data = {
                    "지표": ["현재가", "1차 저항선", "2차 저항선", "3차 저항선"],
                    "값": [
                        f"${current_price:.2f}" if current_price is not None else "N/A",
                        f"${resistance_1st:.2f}" if resistance_1st is not None else "N/A",
                        f"${resistance_2nd:.2f}" if resistance_2nd is not None else "N/A",
                        f"${resistance_3rd:.2f}" if resistance_3rd is not None else "N/A"
                    ]
                }
                st.dataframe(pd.DataFrame(resistance_level_data), hide_index=True, use_container_width=True)

                if current_price is not None and resistance_1st is not None and resistance_2nd is not None and resistance_3rd is not None:
                    if current_price <= resistance_1st:
                        st.success(
                            f"**현재 가격 (${current_price:.2f})**은 1차 저항선 (${resistance_1st:.2f}) 아래에 있습니다. 상승 여력이 있을 수 있습니다.")
                    elif current_price <= resistance_2nd and current_price > resistance_1st:
                        st.warning(
                            f"**현재 가격 (${current_price:.2f})**은 1차 저항선 (${resistance_1st:.2f})을 돌파했지만, 2차 저항선 (${resistance_2nd:.2f}) 아래에 있습니다. 추가 상승 시 2차 저항선에 유의해야 합니다.")
                    elif current_price <= resistance_3rd and current_price > resistance_2nd:
                        st.warning(
                            f"**현재 가격 (${current_price:.2f})**은 2차 저항선 (${resistance_2nd:.2f})을 돌파했지만, 3차 저항선 (${resistance_3rd:.2f}) 아래에 있습니다. 장기 저항선 돌파 여부가 중요합니다.")
                    elif current_price > resistance_3rd:
                        st.error(
                            f"**현재 가격 (${current_price:.2f})**은 3차 저항선 (${resistance_3rd:.2f}) 위에 있습니다. 강한 상승 모멘텀이지만, 과열될 수 있으니 주의가 필요합니다.")
                    else:
                        st.info("현재 가격과 저항선 위치를 파악할 수 없습니다.")
                else:
                    st.info("저항선 정보를 불러올 수 없습니다. (데이터 부족 또는 계산 오류)")

                st.markdown("---")  # 각 종목 상세 보기 구분선

    else:
        st.warning("분석할 종목이 없습니다. 새로운 종목을 추가해주세요.")

# tab4: 보석 발굴 (UI 간소화 및 최적화)
with tab4:
    st.subheader("💎 숨겨진 보석 발굴기")
    st.markdown("""
    이 기능은 시장의 주요 종목들 중 현재 가격이 52주 고점 대비 많이 하락했거나 (덜 오르고),
    재무적으로 안정적이며, 저희 시스템의 매수 추천 점수가 높은 잠재적인 '보석' 종목들을 찾아드립니다.
    분석에는 시간이 다소 소요될 수 있습니다.
    """)

    # 세션 상태 변수 초기화 (보석 발굴기 전용)
    if "gem_discovery_results" not in st.session_state:
        st.session_state.gem_discovery_results = []
    if "gem_discovery_running" not in st.session_state:
        st.session_state.gem_discovery_running = False

    # 보석 발굴 시작 버튼
    if st.button("💎 보석 발굴 시작", key="start_gem_discovery_btn"):
        st.session_state.gem_discovery_running = True
        st.session_state.gem_discovery_results = []  # 이전 결과 초기화
        st.rerun()  # 버튼 클릭 후 바로 재실행하여 진행 상태 표시

    # 보석 발굴 진행 중인 경우
    if st.session_state.gem_discovery_running:
        st.info("🚀 보석 발굴 중입니다. 잠시만 기다려 주세요...")

        # 진행 상황을 보여줄 placeholder
        progress_text_placeholder = st.empty()
        progress_bar_placeholder = st.progress(0)

        with st.spinner("💎 보석 발굴 진행 중... (시간이 다소 소요될 수 있습니다)"):
            # get_gem_candidates 함수 호출 (안정적인 설정 값 직접 전달)
            # 이 함수는 이제 PER, PSR, MarketCap을 반환 딕셔너리에 포함합니다.
            found_gems = get_gem_candidates(
                num_to_sample=150,
                target_num_gems=20,
                max_per=35,
                max_psr=7,
                min_market_cap_billion=5,  # 50억 달러
                min_high_proximity_pct=10,
                min_swing_score=6.5
            )
            st.session_state.gem_discovery_results = found_gems
            st.session_state.gem_discovery_running = False

        # 작업 완료 후 프로그레스 바 숨기기
        progress_text_placeholder.empty()
        progress_bar_placeholder.empty()
        st.rerun()  # 완료 후 UI 업데이트

    # 발굴된 보석 종목이 있을 경우 또는 발굴이 완료된 경우 결과 표시
    if not st.session_state.gem_discovery_running and st.session_state.gem_discovery_results:
        st.markdown("### ✨ 발굴된 보석 종목")
        gem_rows = []
        for gem in sorted(st.session_state.gem_discovery_results, key=lambda x: x.get("Score", 0), reverse=True):
            # gem 딕셔너리에 PER, PSR, MarketCap이 직접 포함되어 있으므로 바로 사용합니다.
            market_cap_val = gem.get('MarketCap')
            per_val = gem.get('PER')
            psr_val = gem.get('PSR')

            market_cap_str = f"{market_cap_val / 1_000_000_000:.2f}B" if market_cap_val is not None else "N/A"
            per_str = f"{per_val:.2f}" if per_val is not None else "N/A"
            psr_str = f"{psr_val:.2f}" if psr_val is not None else "N/A"

            gem_rows.append({
                "종목": gem.get("ticker"),
                "현재가": f"${gem.get('current_price'):.2f}" if gem.get('current_price') is not None else "N/A",
                "시총": market_cap_str,
                "PER": per_str,
                "PSR": psr_str,
                "52주 고점 근접도(%)": f"{gem.get('High_Proximity_Pct'):.2f}",
                "RSI": f"{gem.get('RSI_14'):.2f}",
                "점수": f"{gem.get('Score'):.1f}",
                "추천": gem.get("Recommendation")
            })
        st.dataframe(pd.DataFrame(gem_rows), use_container_width=True, hide_index=True)
        st.info(f"총 {len(st.session_state.gem_discovery_results)}개의 잠재적 보석 종목이 발굴되었습니다.")
    elif not st.session_state.gem_discovery_running and not st.session_state.gem_discovery_results:
        st.info("발굴된 종목이 없습니다. '보석 발굴 시작' 버튼을 눌러 다시 시도해 보세요.")
