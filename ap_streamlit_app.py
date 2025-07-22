import streamlit as st
import pandas as pd
import base64
import numpy as np

# ap_swing_stock_data.py 파일에서 필요한 함수들을 임포트합니다.
try:
    from ap_swing_stock_data import merge_swing_data
except ImportError:
    st.error("오류: 'ap_swing_stock_data.py' 파일을 찾을 수 없습니다. 동일한 디렉토리에 있는지 확인해주세요.")
    st.stop()


# 모바일 감지 함수 (캐시 유지 시간 개발 중에는 짧게, 배포 시 길게)
@st.cache_data(show_spinner=False, ttl=3600)
def is_mobile_device():
    try:
        # Streamlit 버전이 낮아 st.experimental_user_agent() 오류가 발생할 수 있음.
        # 이 함수가 문제를 일으키면 주석 처리하거나 제거해야 합니다.
        ua = st.experimental_user_agent()
        return "Mobile" in ua or "Android" in ua or "iPhone" in ua
    except:
        return False


IS_MOBILE = is_mobile_device()

# ---
# 캐시/세션 초기화 버튼
with st.sidebar:
    if st.button("🔁 캐시 데이터 초기화 (앱 오류 시 시도)", help="이 버튼은 계산에 사용된 캐시 데이터만 지웁니다. 추가된 종목 정보는 유지됩니다."):
        st.cache_data.clear()
        st.rerun()


# ---
# 이미지 base64 인코딩 함수
def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
        return encoded
    except FileNotFoundError:
        st.warning(f"Warning: Image file not found at {image_path}. Displaying without icon.")
        return ""


# 이미지 파일 로드 (경로 확인 필수)
img_base64 = get_image_base64("떡상-icon.jpg")

# UI 렌더링 설정
st.set_page_config(page_title="📊 떡상", layout="wide")

# CSS 스타일 주입
st.markdown(
    """
    <style>
    .main-header {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 3em;
        margin-bottom: 0px;
    }
    .stock-summary-table {
        margin-top: 20px;
        margin-bottom: 30px;
    }
    .stDataFrame > div > div { /* Target the inner div of st.dataframe for styling */
        border-radius: 10px;
        overflow: hidden; /* Ensures border-radius applies to corners */
    }
    table th {
        background-color: #f0f2f6 !important; /* Header background */
        color: #333 !important;
        font-weight: bold !important;
    }

    /* Detailed Card Styles (from previous iteration, slightly modified) */
    .stock-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
        background-color: #f9f9f9;
    }
    .stock-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }
    .stock-card-ticker {
        font-size: 2.5em;
        font-weight: bold;
        color: #333;
    }
    .stock-card-opinion {
        font-size: 1.5em;
        font-weight: bold;
        padding: 5px 10px;
        border-radius: 5px;
        color: white;
        text-align: center;
        display: inline-block; /* 추가: 텍스트 길이에 맞춰 배경색이 적용되도록 */
        margin-left: 10px; /* 추가: expander 제목과의 간격 */
    }
    /* Opinion specific colors for detailed card - same as before */
    .opinion-buy { background-color: #4CAF50; }
    .opinion-strong-buy { background-color: #28a745; }
    .opinion-sell { background-color: #f44336; }
    .opinion-strong-sell { background-color: #dc3545; }
    .opinion-neutral { background-color: #ffc107; color: #333;}
    .opinion-mixed { background-color: #6c757d; }

    .metric-group {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 15px;
    }
    .metric-item {
        background-color: #e9ecef;
        padding: 8px 12px;
        border-radius: 5px;
        font-size: 0.9em;
        min-width: 150px;
        text-align: center;
    }
    .metric-label {
        font-weight: bold;
        color: #555;
    }
    .metric-value {
        color: #000;
    }
    .reason-list {
        margin-left: 20px;
        padding-left: 0;
        list-style-type: disc;
    }
    .stButton > button {
        width: 100%;
    }
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 10px;
        box-shadow: 1px 1px 5px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }
    /* Expander title styling */
    .stExpander > div > div > p {
        font-weight: bold;
        font-size: 1.2em; /* expander 제목 폰트 크기 조정 */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <h1 class="main-header">
        {'<img src="data:image/jpeg;base64,' + img_base64 + '" width="64">' if img_base64 else ''}
        떡상
    </h1>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(["📖 Read Me", "🛰️ 시장 분석", "📈 주식 분석", "💎 보석 발굴"])

# tab1: 안내문
with tab1:
    st.subheader("📖 Read Me")
    st.markdown("""
    이 앱은 종목 분석 및 스윙 트레이딩 추천 시스템을 포함한 투자 보조 도구입니다.
    사용자의 개인적인 투자 판단에 따라 활용하시기 바랍니다.
    """)

# tab2: 시장 분석
with tab2:
    st.subheader("🛰️ 미국장 시장 실시간 분석")
    st.markdown("이 탭은 미국 시장 전반에 대한 실시간 분석 정보를 제공할 예정입니다.")

# ---
# tab3: 주식 분석
with tab3:
    st.subheader("📈 종목 스윙 분석")
    st.markdown("""
     분석하고 싶은 종목 티커를 추가하고 엔터를 누르거나 '종목 추가' 버튼을 눌러보세요.
     추가 즉시 분석이 시작되며, 결과는 아래 표에 표시됩니다.
     """)

    # 세션 상태 초기화
    if 'tickers_to_analyze' not in st.session_state:
        st.session_state.tickers_to_analyze = []
    if 'analyzed_data' not in st.session_state:
        # merge_swing_data에서 반환되는 딕셔너리 키와 정확히 일치시켜야 합니다.
        default_columns = [
            'ticker', 'current_price', 'previous_close', 'rsi',
            'ma_5', 'ma_20', 'ma_50', 'bb_middle', 'bb_upper', 'bb_lower',
            'macd_line', 'macd_signal', 'macd_histogram', 'vma', 'obv',
            'stoch_k', 'stoch_d', 'atr', 'buy_signal', 'buy_reasons',
            'buy_target_price', 'sell_signal', 'sell_reasons', 'sell_target_price',
            'trade_opinion'
        ]
        st.session_state.analyzed_data = pd.DataFrame(columns=default_columns)

        # 숫자형 컬럼에 대한 기본 타입 지정
        numeric_cols = [
            'current_price', 'previous_close', 'rsi',
            'ma_5', 'ma_20', 'ma_50', 'bb_middle', 'bb_upper', 'bb_lower',
            'macd_line', 'macd_signal', 'macd_histogram', 'vma', 'obv',
            'stoch_k', 'stoch_d', 'atr', 'buy_target_price', 'sell_target_price'
        ]
        for col in numeric_cols:
            if col in st.session_state.analyzed_data.columns:
                st.session_state.analyzed_data[col] = st.session_state.analyzed_data[col].astype(float)

    new_ticker_input = st.text_input("분석할 종목 티커 입력 (예: AAPL, MSFT)", key="ticker_input").strip().upper()


    def add_and_analyze_ticker():
        if new_ticker_input and new_ticker_input not in st.session_state.tickers_to_analyze:
            st.session_state.tickers_to_analyze.append(new_ticker_input)
            st.success(f"'{new_ticker_input}'가 분석 목록에 추가되었습니다.")

            with st.spinner(f"'{new_ticker_input}' 분석 중..."):
                try:
                    single_result = merge_swing_data([new_ticker_input])
                    if single_result:
                        new_row_df = pd.DataFrame(single_result)

                        # 기존 데이터프레임과 새로 추가될 데이터프레임의 컬럼 순서를 맞춥니다.
                        missing_cols_in_new = set(st.session_state.analyzed_data.columns) - set(new_row_df.columns)
                        for col in missing_cols_in_new:
                            new_row_df[col] = np.nan

                        missing_cols_in_existing = set(new_row_df.columns) - set(st.session_state.analyzed_data.columns)
                        for col in missing_cols_in_existing:
                            st.session_state.analyzed_data[col] = np.nan

                        new_row_df = new_row_df[st.session_state.analyzed_data.columns]

                        if not st.session_state.analyzed_data.empty and \
                                new_ticker_input in st.session_state.analyzed_data['ticker'].values:
                            # 이미 있는 종목이면 업데이트
                            for col in new_row_df.columns:
                                st.session_state.analyzed_data.loc[
                                    st.session_state.analyzed_data['ticker'] == new_ticker_input, col
                                ] = new_row_df[col].iloc[0]
                        else:
                            # 새로운 종목이면 추가
                            st.session_state.analyzed_data = pd.concat([st.session_state.analyzed_data, new_row_df],
                                                                       ignore_index=True)
                        st.success(f"'{new_ticker_input}' 분석 완료!")
                    else:
                        st.warning(f"'{new_ticker_input}'에 대한 분석 데이터를 가져오지 못했습니다. 데이터가 비어있을 수 있습니다.")
                except Exception as e:
                    st.error(f"'{new_ticker_input}' 분석 중 오류가 발생했습니다: {e}")
            st.rerun()
        elif new_ticker_input in st.session_state.tickers_to_analyze:
            st.warning(f"'{new_ticker_input}'는 이미 분석 목록에 있습니다.")


    col_add_ticker_btn, _ = st.columns([1, 4])
    with col_add_ticker_btn:
        st.button("종목 추가", on_click=add_and_analyze_ticker)

    st.markdown("---")

    if st.session_state.tickers_to_analyze:
        st.write(f"현재 분석된 종목: **{', '.join(st.session_state.tickers_to_analyze)}**")

        if st.button("🗑️ 모든 분석 데이터 및 종목 삭제", help="목록에 있는 모든 종목과 그 분석 결과를 삭제합니다."):
            st.session_state.tickers_to_analyze = []
            st.session_state.analyzed_data = pd.DataFrame(columns=st.session_state.analyzed_data.columns)
            st.success("모든 종목과 분석 데이터가 삭제되었습니다.")
            st.rerun()

        st.markdown("---")

        if not st.session_state.analyzed_data.empty:
            st.subheader("📝 요약 분석 결과 (한눈에 보기)")

            # 요약 테이블에 표시할 컬럼 정의
            summary_display_columns = [
                'ticker', 'current_price', 'trade_opinion', 'buy_target_price', 'sell_target_price',
                'rsi', 'ma_5', 'ma_20'
            ]
            # 실제 데이터프레임에 존재하는 컬럼만 선택
            actual_summary_columns = [col for col in summary_display_columns if
                                      col in st.session_state.analyzed_data.columns]

            # 요약 정보용 데이터프레임 생성 및 포맷팅 (copy() 중요)
            summary_df = st.session_state.analyzed_data[actual_summary_columns].copy()

            # 컬럼명 변경 (요약 테이블용)
            summary_df.rename(columns={
                'ticker': '티커',
                'current_price': '현재가',
                'trade_opinion': '최종 의견',
                'buy_target_price': '매수 적정가',
                'sell_target_price': '매도 적정가',
                'rsi': 'RSI',
                'ma_5': 'MA(5)',
                'ma_20': 'MA(20)'
            }, inplace=True)

            # 숫자형 컬럼 포맷팅 (summary_df에만 적용)
            for col in ['현재가', '매수 적정가', '매도 적정가', 'RSI', 'MA(5)', 'MA(20)']:
                if col in summary_df.columns:
                    summary_df[col] = summary_df[col].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                    )


            # 요약 테이블의 '최종 의견'에 따라 행 색상 지정 함수
            def highlight_summary_row(row):
                opinion = row['최종 의견']
                bg_color = ''
                if opinion == '매수':
                    bg_color = '#e6ffe6'  # Light Green
                elif opinion == '강력 매수 (ATR 돌파 포함 혼조)':
                    bg_color = '#ccffcc'  # Lighter Green
                elif opinion == '매도':
                    bg_color = '#ffe6e6'  # Light Red
                elif opinion == '강력 매도 (ATR 돌파 포함 혼조)':
                    bg_color = '#ffcccc'  # Lighter Red
                elif '혼조' in opinion:  # '혼조 (매수/매도 신호 충돌)' 포함
                    bg_color = '#fffacd'  # Lemon Chiffon (Yellowish)
                elif opinion == '관망':
                    bg_color = '#f0f8ff'  # Alice Blue (Light Blue)

                # Streamlit의 .style.apply는 각 셀에 인라인 스타일을 적용합니다.
                return [f'background-color: {bg_color}' for _ in row]


            st.dataframe(
                summary_df.style.apply(highlight_summary_row, axis=1),
                hide_index=True,
                use_container_width=True,
                height=300  # 요약 테이블 높이 제한
            )

            st.markdown("---")
            st.subheader("📊 상세 분석 결과 (종목별 펼쳐보기)")

            # 각 종목별 카드를 동적으로 생성 (st.expander 사용)
            sorted_analyzed_data = st.session_state.analyzed_data.sort_values(by='ticker').reset_index(drop=True)

            for i, row in sorted_analyzed_data.iterrows():
                ticker = row['ticker']
                trade_opinion = row['trade_opinion']

                # 최종 의견에 따라 CSS 클래스 결정
                opinion_class = "opinion-mixed"
                if trade_opinion == '매수':
                    opinion_class = "opinion-buy"
                elif trade_opinion == '강력 매수 (ATR 돌파 포함 혼조)':
                    opinion_class = "opinion-strong-buy"
                elif trade_opinion == '매도':
                    opinion_class = "opinion-sell"
                elif trade_opinion == '강력 매도 (ATR 돌파 포함 혼조)':
                    opinion_class = "opinion-strong-sell"
                elif trade_opinion == '관망':
                    opinion_class = "opinion-neutral"

                # st.expander를 사용하여 상세 내용을 숨김/펼침 가능하게 함
                # title에 HTML을 직접 넣는 대신, 텍스트와 HTML 마크다운을 조합
                expander_title = f"**{ticker}** - 최종 의견: "
                expander_markdown = f"<span class='stock-card-opinion {opinion_class}'>{trade_opinion}</span>"

                # Expander 제목에 HTML을 직접 삽입하는 대신, st.expander 외부에서 표시하고 내부에서 상세 정보를 보여주는 방식으로 변경
                # 또는, st.expander의 title 자체는 순수 텍스트로 두고, 내부에서 다시 의견을 강조
                with st.expander(f"**{ticker}** - 최종 의견: {trade_opinion}"):  # unsafe_allow_html 제거
                    # 상세 카드 내부 내용 시작
                    # 여기서는 'trade_opinion'을 다시 강조하기 위해 HTML 사용
                    st.markdown(f'<div class="stock-card">', unsafe_allow_html=True)
                    st.markdown(
                        f"""
                        <div class="stock-card-header">
                            <span class="stock-card-ticker">{ticker}</span>
                            <span class="stock-card-opinion {opinion_class}">{trade_opinion}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # 주요 가격 정보
                    st.markdown("#### 💰 주요 가격 정보")
                    col_price1, col_price2, col_price3 = st.columns(3)
                    with col_price1:
                        st.metric("현재가", f"{row['current_price']:.2f}" if pd.notna(row['current_price']) else "N/A")
                    with col_price2:
                        st.metric("매수 적정가",
                                  f"{row['buy_target_price']:.2f}" if pd.notna(row['buy_target_price']) else "N/A")
                    with col_price3:
                        st.metric("매도 적정가",
                                  f"{row['sell_target_price']:.2f}" if pd.notna(row['sell_target_price']) else "N/A")

                    st.markdown("#### 📈 지표 분석")

                    # 지표들을 그룹으로 묶어 표시
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">RSI</div><div class="metric-value">{row["rsi"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">ATR</div><div class="metric-value">{row["atr"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("##### 이동평균선")
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">MA(5)</div><div class="metric-value">{row["ma_5"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">MA(20)</div><div class="metric-value">{row["ma_20"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">MA(50)</div><div class="metric-value">{row["ma_50"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("##### 볼린저 밴드")
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">BB 상단</div><div class="metric-value">{row["bb_upper"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">BB 중앙</div><div class="metric-value">{row["bb_middle"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">BB 하단</div><div class="metric-value">{row["bb_lower"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("##### MACD")
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">MACD 라인</div><div class="metric-value">{row["macd_line"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">시그널 라인</div><div class="metric-value">{row["macd_signal"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">히스토그램</div><div class="metric-value">{row["macd_histogram"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("##### 스토캐스틱")
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">Stoch K</div><div class="metric-value">{row["stoch_k"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">Stoch D</div><div class="metric-value">{row["stoch_d"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("##### 거래량 지표")
                    st.markdown('<div class="metric-group">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">VMA</div><div class="metric-value">{row["vma"]:.2f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metric-item"><div class="metric-label">OBV</div><div class="metric-value">{row["obv"]:.0f}</div></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # 매수/매도 신호 이유
                    st.markdown("#### 💬 신호 이유")
                    # pd.Series의 값은 문자열이 아닐 수 있으므로 isinstance 체크
                    buy_reasons = row['buy_reasons'].split(', ') if isinstance(row['buy_reasons'], str) and row[
                        'buy_reasons'] != '해당 없음' else []
                    sell_reasons = row['sell_reasons'].split(', ') if isinstance(row['sell_reasons'], str) and row[
                        'sell_reasons'] != '해당 없음' else []

                    col_reasons1, col_reasons2 = st.columns(2)
                    with col_reasons1:
                        st.markdown("**매수 신호:**")
                        if buy_reasons:
                            for reason in buy_reasons:
                                st.markdown(f"- {reason}")
                        else:
                            st.markdown("- 해당 없음")
                    with col_reasons2:
                        st.markdown("**매도 신호:**")
                        if sell_reasons:
                            for reason in sell_reasons:
                                st.markdown(f"- {reason}")
                        else:
                            st.markdown("- 해당 없음")

                    # 재분석 및 삭제 버튼 (개별 카드 내)
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_actions1, col_actions2 = st.columns(2)
                    with col_actions1:
                        if st.button(f"🔄 재분석", key=f"reanalyze_{ticker}_expander"):
                            with st.spinner(f"'{ticker}' 재분석 중..."):
                                try:
                                    updated_data = merge_swing_data([ticker])
                                    if updated_data:
                                        updated_row_df = pd.DataFrame(updated_data)
                                        missing_cols_in_updated = set(st.session_state.analyzed_data.columns) - set(
                                            updated_row_df.columns)
                                        for col in missing_cols_in_updated:
                                            updated_row_df[col] = np.nan
                                        updated_row_df = updated_row_df[st.session_state.analyzed_data.columns]

                                        for key in updated_row_df.columns:
                                            st.session_state.analyzed_data.loc[
                                                st.session_state.analyzed_data['ticker'] == ticker, key
                                            ] = updated_row_df[key].iloc[0]
                                        st.success(f"'{ticker}' 재분석 완료!")
                                    else:
                                        st.warning(f"'{ticker}' 재분석 데이터를 가져오지 못했습니다.")
                                except Exception as e:
                                    st.error(f"'{ticker}' 재분석 중 오류 발생: {e}")
                            st.rerun()
                    with col_actions2:
                        if st.button(f"🗑️ 삭제", key=f"delete_{ticker}_expander"):
                            st.session_state.tickers_to_analyze.remove(ticker)
                            st.session_state.analyzed_data = st.session_state.analyzed_data[
                                st.session_state.analyzed_data['ticker'] != ticker
                                ].reset_index(drop=True)
                            st.success(f"'{ticker}'가 목록에서 삭제되었습니다.")
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)  # stock-card 닫기
                # 상세 카드 내부 내용 끝 (expander 닫힘)

        else:
            st.info("아직 분석된 종목 데이터가 없습니다. 종목을 추가하고 '종목 추가' 버튼을 눌러주세요.")

    else:
        st.info("분석할 종목이 없습니다. 위에 티커를 입력하고 '종목 추가' 버튼을 눌러주세요.")

# tab4: 보석 발굴 (기존 코드)
with tab4:
    st.subheader("💎 숨겨진 보석 발굴기")
    st.markdown("""
    이 기능은 시장의 주요 종목들 중 현재 가격이 52주 고점 대비 많이 하락했거나 (덜 오르고),
    재무적으로 안정적이며, 저희 시스템의 매수 추천 점수가 높은 잠재적인 '보석' 종목들을 찾아드립니다.
    분석에는 시간이 다소 소요될 수 있습니다.
    """)