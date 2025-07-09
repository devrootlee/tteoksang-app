import streamlit as st
import pandas as pd
import base64
# swing_stock_data 함수는 별도 파일(swing_stock_data.py)에서 임포트됩니다.
from swing_stock_data import swing_stock_data  # 이 부분은 변경 없음


# ✅ 모바일 감지 함수 (변경 없음)
@st.cache_data(show_spinner=False)
def is_mobile_device():
    try:
        ua = st.experimental_user_agent()
        return ua and ua.device_family in ["iPhone", "Android"]
    except:
        return False

IS_MOBILE = is_mobile_device()

# ---
# ✅ 캐시/세션 초기화 버튼 수정: 모든 세션 상태를 지우는 대신, 캐시 데이터만 지우도록 변경
with st.sidebar:
    if st.button("🔁 캐시 데이터 초기화 (앱 오류 시 시도)", help="이 버튼은 계산에 사용된 캐시 데이터만 지웁니다. 추가된 종목 정보는 유지됩니다."):
        st.cache_data.clear()  # @st.cache_data 데코레이터로 캐시된 모든 데이터를 지웁니다.
        # Streamlit은 캐시가 지워지면 자동으로 전체 스크립트를 재실행합니다.
        # 따라서 여기서는 별도의 st.rerun() 호출이 필요하지 않습니다.


# ---

# 이미지 base64 인코딩 함수 (변경 없음)
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode()
    return encoded


# 이미지 파일 존재 여부 확인 및 로드 (변경 없음)
img_base64 = ""
try:
    img_base64 = get_image_base64("떡상-icon.jpg")
except FileNotFoundError:
    st.warning("떡상-icon.jpg 파일을 찾을 수 없습니다. 아이콘 없이 진행합니다.")
    # img_base64는 이미 빈 문자열로 초기화됨

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

# ✅ tab1: 안내문만 유지 (변경 없음)
with tab1:
    st.subheader("📖 Read Me")
    st.markdown("""
    이 앱은 종목 분석 및 스윙 트레이딩 추천 시스템을 포함한 투자 보조 도구입니다.
    사용자의 개인적인 투자 판단에 따라 활용하시기 바랍니다.
    """)

# ✅ tab2 (변경 없음)
with tab2:
    st.subheader("🛰️ 시장 분석")
    st.info("준비 중입니다.")

# ✅ tab4 (변경 없음)
with tab4:
    st.subheader("💎 숨겨진 보석 발굴기")
    st.info("준비 중입니다.")

# ---
# ✅ tab3: 주식 추천 분석 시스템 (수정 반영)
with tab3:
    st.subheader("📈 주식 분석")

    # 세션 상태 변수 초기화
    if "tickers" not in st.session_state:
        st.session_state.tickers = []
    if "ticker_data" not in st.session_state:
        st.session_state.ticker_data = {}
    if "default_tickers_loaded" not in st.session_state:
        st.session_state.default_tickers_loaded = False

    # 신규 종목 입력
    new_input = st.text_input("🎯 분석할 종목 입력 (예: AAPL)", "")
    if st.button("➕ 종목 추가") and new_input:
        symbol = new_input.strip().upper()
        if symbol in st.session_state.tickers:
            st.warning(f"이미 추가된 종목입니다: {symbol}")
        else:
            with st.spinner(f"🔍 {symbol} 분석 중..."):
                data = swing_stock_data(symbol)
                if data:
                    st.session_state.tickers.append(symbol)
                    st.session_state.ticker_data[symbol] = data
                else:
                    st.error(f"❌ 데이터를 불러올 수 없습니다: {symbol}")
            st.rerun()  # 새 종목 추가 후 UI 업데이트를 위해 필요


    # 종목 삭제 함수 (on_click 콜백 내부의 st.rerun() 제거)
    def delete_ticker_callback(ticker_to_delete):
        if ticker_to_delete in st.session_state.tickers:
            st.session_state.tickers.remove(ticker_to_delete)
            st.session_state.ticker_data.pop(ticker_to_delete, None)

    # ✅ 종목 재분석 함수: 콜백 내에서 직접 재분석 수행 및 결과 업데이트
    def reanalyze_ticker_callback(ticker_to_reanalyze):
        # 기존 데이터 제거 (캐시 무효화 효과)
        st.session_state.ticker_data.pop(ticker_to_reanalyze, None)

        # 재분석 수행
        with st.spinner(f"🔍 {ticker_to_reanalyze} 재분석 중..."):
            data = swing_stock_data(ticker_to_reanalyze)
            if data:
                st.session_state.ticker_data[ticker_to_reanalyze] = data
            else:
                # 재분석 실패 시, 해당 종목을 ticker_data에서 제거 상태로 유지하거나,
                # 실패를 명시하는 데이터를 넣을 수 있습니다.
                # 여기서는 명확한 에러 메시지를 위해 제거 상태로 두겠습니다.
                st.error(f"❌ {ticker_to_reanalyze} 재분석 중 데이터 로드 실패. 잠시 후 다시 시도해주세요.")

    # 종목 삭제 및 재분석 UI
    if st.session_state.tickers:
        with st.expander("🗑️ 종목 관리 (삭제/재분석)", expanded=False):
            # 리스트 복사본을 사용하여 순회 중 원본 리스트 수정으로 인한 오류 방지
            for t in list(st.session_state.tickers):
                # 3개의 컬럼으로 구성: 종목코드 | 재분석 버튼 | 삭제 버튼
                col1, col2, col3 = st.columns([4, 1.5, 1])
                with col1:
                    st.markdown(f"**{t}**")
                with col2:
                    # 재분석 버튼
                    # key는 고유해야 하므로 f-string 사용
                    st.button("🔄 재분석", key=f"reanalyze_btn_{t}", on_click=reanalyze_ticker_callback, args=(t,))
                with col3:
                    st.button("삭제", key=f"del_btn_{t}", on_click=delete_ticker_callback, args=(t,))

    # 기본 종목 로딩 (앱 첫 실행 시만)
    if not st.session_state.tickers and not st.session_state.default_tickers_loaded:
        default_tickers = ["OPTT", "QBTS", "APP", "INTC", "PLTR", "CRNC"]
        default_load_successful_count = 0
        for t in default_tickers:
            with st.spinner(f"🔍 {t} 분석 중..."):
                data = swing_stock_data(t)
                if data:
                    st.session_state.tickers.append(t)
                    st.session_state.ticker_data[t] = data
                    default_load_successful_count += 1

        st.session_state.default_tickers_loaded = True

        if default_load_successful_count > 0:
            st.rerun()  # 기본 종목 로드 후 UI를 강제로 새로고침하여 삭제/재분석 버튼 표시

    # ✅ 유효한 티커만 필터링 (이제 이 부분에서 재분석을 직접 수행하지 않음)
    # 재분석은 reanalyze_ticker_callback에서 처리되므로,
    # 여기서는 단순히 st.session_state.ticker_data에 있는 종목만 필터링합니다.
    valid_tickers = [t for t in st.session_state.tickers if t in st.session_state.ticker_data]

    # 나머지 UI 렌더링 (변경 없음)
    if valid_tickers:
        st.markdown("### ✅ 핵심 요약 테이블")
        rows = []
        for t in valid_tickers:
            data = st.session_state.ticker_data[t]
            rows.append({
                "종목코드": data.get("ticker"),
                "섹터": data.get("sector"),
                "현재가": data.get("current_price"),
                "추세": data.get("Trend"),
                "RSI": data.get("RSI_14"),
                "MACD": data.get("MACD"),
                "점수": data.get("Score"),
                "추천": data.get("Recommendation")
            })

        rec_df = pd.DataFrame(rows).sort_values(by="점수", ascending=False)
        st.dataframe(rec_df, use_container_width=True)

        with st.expander("📊 개별 종목 지표 상세 보기 (분류별)"):
            for t in valid_tickers:
                data = st.session_state.ticker_data[t]
                st.markdown(f"#### {t} - {data.get('Recommendation')} ({data.get('Score')}점)")

                with st.container():
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**📉 추세 관련**")
                        st.write("추세:", data.get("Trend"))
                        st.write("5일 이동평균:", data.get("MA_5"))
                        st.write("20일 이동평균:", data.get("MA_20"))
                        st.write("20일 이격도(%):", data.get("Disparity_20"))

                    with col2:
                        st.markdown("**📊 모멘텀/수급**")
                        st.write("RSI(14일):", data.get("RSI_14"))
                        st.write("스토캐스틱 K:", data.get("Stoch_K"))
                        st.write("MACD:", data.get("MACD"))
                        st.write("거래량 배율:", data.get("Volume_Rate"))

                    with col3:
                        st.markdown("**📦 시장 위치/기타**")
                        st.write("52주 고가 근접도(%):", data.get("High_Proximity_Pct"))
                        st.write("볼린저 밴드 위치:", data.get("Price_Position"))
                        st.write("거래대금 (백만 달러):", data.get("Volume_Turnover_Million"))
                        st.write("옵션 콜/풋 거래량:", f"{data.get('max_call_volume', 0)} / {data.get('max_put_volume', 0)}")
    else:
        st.warning("분석할 종목이 없습니다. 새로운 종목을 추가해주세요.")