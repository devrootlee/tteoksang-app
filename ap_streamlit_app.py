import streamlit as st
import pandas as pd
from ap_swing_stock_data import merge_swing_data  # 분리된 로직 파일에서 함수 임포트

# Streamlit 앱 시작
st.set_page_config(layout="wide", page_title="주식 스윙 분석기")

st.title("📈 주식 스윙 분석기")
st.markdown("""
이 앱은 Alpaca API를 사용하여 지정된 주식 종목에 대한 기술적 분석 지표를 계산하고,
이를 바탕으로 매수/매도 신호 및 투자 의견을 제공합니다.
""")

# --- 세션 상태 초기화 ---
if 'symbols_to_analyze' not in st.session_state:
    st.session_state.symbols_to_analyze = ["SMCI", "OPTT", "APP"]  # 초기 분석할 종목 리스트

if 'new_symbol_input_value' not in st.session_state:
    st.session_state.new_symbol_input_value = ""

# 분석 완료된 종목 목록과 그 결과를 저장하는 캐시
# {'ticker': {...analysis_data...}, 'ticker2': {...}} 형태
if 'all_swing_data_cache' not in st.session_state:
    st.session_state.all_swing_data_cache = {}

st.header("종목 관리")

# --- 종목 추가 로직 ---
def add_symbol_callback():
    new_symbol = st.session_state.new_symbol_input_value
    if new_symbol.strip():
        symbol_upper = new_symbol.strip().upper()
        if symbol_upper not in st.session_state.symbols_to_analyze:
            st.session_state.symbols_to_analyze.append(symbol_upper)
            st.success(f"'{symbol_upper}' 종목이 추가되었습니다.")
        else:
            st.warning(f"'{symbol_upper}'은(는) 이미 추가된 종목입니다.")
        st.session_state.new_symbol_input_value = ""  # 입력 필드 초기화

# 종목 추가 입력 필드
col_add, col_button = st.columns([3, 1])
with col_add:
    new_symbol_input = st.text_input(
        "새로운 종목 티커를 입력하세요 (예: NVDA)",
        key="new_symbol_input_value",
        value=st.session_state.new_symbol_input_value
    )
with col_button:
    st.write("")
    st.write("")
    st.button("종목 추가", on_click=add_symbol_callback)

# --- 개별 종목 재분석 함수 ---
def reanalyze_single_symbol(symbol_to_reanalyze):
    with st.spinner(f"'{symbol_to_reanalyze}' 종목을 재분석 중입니다..."):
        single_result = merge_swing_data(
            [symbol_to_reanalyze],  # 단일 종목 리스트로 전달
            rsi_period=14, ma_periods=[5, 20, 50], bb_period=20, bb_num_std_dev=2,
            macd_short=12, macd_long=26, macd_signal=9, vma_period=20,
            stoch_k_period=14, stoch_d_period=3, atr_period=14, adx_period=14
        )
        if single_result:
            st.session_state.all_swing_data_cache[symbol_to_reanalyze] = single_result[0]  # 첫 번째 (이자 유일한) 결과 저장
            st.success(f"'{symbol_to_reanalyze}' 종목 재분석 완료!")
        else:
            st.error(f"'{symbol_to_reanalyze}' 종목 재분석에 실패했습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요.")

# --- 현재 추가된 종목 리스트 표시 및 삭제/재분석 기능 ---
st.subheader("현재 분석 종목")
if st.session_state.symbols_to_analyze:
    symbols_container = st.container()
    with symbols_container:
        for symbol in st.session_state.symbols_to_analyze:
            col_sym, col_del, col_reanalyze = st.columns([3, 1, 1])
            with col_sym:
                st.markdown(f"**{symbol}**")
            with col_del:
                if st.button(f"삭제", key=f"delete_{symbol}"):
                    st.session_state.symbols_to_analyze.remove(symbol)
                    if symbol in st.session_state.all_swing_data_cache:
                        del st.session_state.all_swing_data_cache[symbol]
                    st.success(f"'{symbol}' 종목이 삭제되었습니다.")
                    st.rerun()
            with col_reanalyze:
                if st.button(f"재분석", key=f"reanalyze_{symbol}"):
                    reanalyze_single_symbol(symbol)

else:
    st.info("분석할 종목이 없습니다. 위에서 종목을 추가해주세요.")

st.markdown("---")

# --- 전체 재분석 함수 ---
def reanalyze_all_symbols():
    if st.session_state.symbols_to_analyze:
        with st.spinner("모든 종목을 재분석 중입니다... 잠시만 기다려 주세요."):
            all_results = merge_swing_data(
                st.session_state.symbols_to_analyze,
                rsi_period=14, ma_periods=[5, 20, 50], bb_period=20, bb_num_std_dev=2,
                macd_short=12, macd_long=26, macd_signal=9, vma_period=20,
                stoch_k_period=14, stoch_d_period=3, atr_period=14, adx_period=14
            )
            if all_results:
                st.session_state.all_swing_data_cache = {}
                for result in all_results:
                    st.session_state.all_swing_data_cache[result['ticker']] = result
                st.success("모든 종목 재분석 완료!")
            else:
                st.error("모든 종목 재분석에 실패했습니다. 일부 종목의 데이터가 없거나 API 오류일 수 있습니다.")
        st.rerun()
    else:
        st.warning("분석할 종목이 없습니다. 종목을 추가해주세요.")

# --- 분석 버튼 및 전체 재분석 버튼 ---
col_start, col_reanalyze_all = st.columns(2)

with col_start:
    if st.button("새로 추가된 종목 분석 시작", key="start_analysis_button"):
        if st.session_state.symbols_to_analyze:
            symbols_to_process = [
                s for s in st.session_state.symbols_to_analyze
                if s not in st.session_state.all_swing_data_cache
            ]

            if not symbols_to_process:
                st.info("새롭게 분석할 종목이 없습니다. 개별 재분석 또는 전체 재분석을 사용하세요.")
            else:
                with st.spinner(f"{', '.join(symbols_to_process)} 종목 데이터를 가져오고 분석 중입니다... 잠시만 기다려 주세요."):
                    newly_analyzed_results = merge_swing_data(
                        symbols_to_process,
                        rsi_period=14, ma_periods=[5, 20, 50], bb_period=20, bb_num_std_dev=2,
                        macd_short=12, macd_long=26, macd_signal=9, vma_period=20,
                        stoch_k_period=14, stoch_d_period=3, atr_period=14, adx_period=14
                    )

                if newly_analyzed_results:
                    for result in newly_analyzed_results:
                        ticker = result['ticker']
                        st.session_state.all_swing_data_cache[ticker] = result
                    st.success("새롭게 추가된 종목 분석 완료!")
                else:
                    st.warning(
                        f"{', '.join(symbols_to_process)} 종목 중 일부 또는 전체 데이터 가져오기 및 분석에 실패했습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요.")
        else:
            st.warning("분석할 종목이 없습니다. 종목을 추가해주세요.")

with col_reanalyze_all:
    if st.button("모든 종목 전체 재분석", key="reanalyze_all_button"):
        reanalyze_all_symbols()

### 📊 분석 결과 요약 및 상세 분석

if st.session_state.all_swing_data_cache:
    all_swing_data_summary = [
        st.session_state.all_swing_data_cache[s]
        for s in st.session_state.symbols_to_analyze
        if s in st.session_state.all_swing_data_cache
    ]

    if all_swing_data_summary:
        st.header("📊 분석 결과 요약")
        summary_df_data = []
        for item in all_swing_data_summary:
            summary_df_data.append({
                "종목": item['ticker'],
                "현재가": f"{item['current_price']:.2f}" if item['current_price'] is not None else "N/A",
                "RSI": f"{item['rsi']:.2f}" if item['rsi'] is not None else "N/A",
                "MA(5)": f"{item['ma_5']:.2f}" if item['ma_5'] is not None else "N/A",
                "MA(20)": f"{item['ma_20']:.2f}" if item['ma_20'] is not None else "N/A",
                "MA(50)": f"{item['ma_50']:.2f}" if item['ma_50'] is not None else "N/A",
                "ADX": f"{item['adx']:.2f}" if item['adx'] is not None else "N/A",
                "투자 의견": item['trade_opinion'],
                "매수 적정가": f"{item['buy_target_price']:.2f}" if item['buy_target_price'] is not None else "N/A",
                "매도 적정가": f"{item['sell_target_price']:.2f}" if item['sell_target_price'] is not None else "N/A",
            })
        summary_df = pd.DataFrame(summary_df_data)
        st.dataframe(summary_df, use_container_width=True)

        st.header("🔍 상세 분석")
        for item in all_swing_data_summary:
            with st.expander(f"**{item['ticker']} 상세 분석**"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="현재가",
                              value=f"{item['current_price']:.2f}" if item['current_price'] is not None else "N/A")
                with col2:
                    st.metric(label="전일 종가",
                              value=f"{item['previous_close']:.2f}" if item['previous_close'] is not None else "N/A")
                with col3:
                    opinion_color = "green" if "매수" in item['trade_opinion'] else (
                        "red" if "매도" in item['trade_opinion'] else "orange")
                    st.markdown(f"**<span style='color:{opinion_color}'>최종 투자 의견: {item['trade_opinion']}</span>**",
                                unsafe_allow_html=True)

                st.subheader("기술 지표")
                st.write(f"**RSI (14)**: {item['rsi']:.2f}" if item['rsi'] is not None else "N/A")
                st.write(f"**이동평균선 (MA)**: ")
                st.write(f"  - MA 5: {item['ma_5']:.2f}" if item['ma_5'] is not None else "N/A")
                st.write(f"  - MA 20: {item['ma_20']:.2f}" if item['ma_20'] is not None else "N/A")
                st.write(f"  - MA 50: {item['ma_50']:.2f}" if item['ma_50'] is not None else "N/A")
                st.write(f"**볼린저 밴드 (20, 2)**: ")
                st.write(f"  - 중간 밴드: {item['bb_middle']:.2f}" if item['bb_middle'] is not None else "N/A")
                st.write(f"  - 상단 밴드: {item['bb_upper']:.2f}" if item['bb_upper'] is not None else "N/A")
                st.write(f"  - 하단 밴드: {item['bb_lower']:.2f}" if item['bb_lower'] is not None else "N/A")
                st.write(f"**MACD (12, 26, 9)**: ")
                st.write(f"  - MACD 라인: {item['macd_line']:.2f}" if item['macd_line'] is not None else "N/A")
                st.write(f"  - 시그널 라인: {item['macd_signal']:.2f}" if item['macd_signal'] is not None else "N/A")
                st.write(f"  - 히스토그램: {item['macd_histogram']:.2f}" if item['macd_histogram'] is not None else "N/A")
                st.write(f"**거래량 지표**: ")
                st.write(f"  - VMA (20): {item['vma']:.2f}" if item['vma'] is not None else "N/A")
                st.write(f"  - 현재 거래량: {item['volume']:.0f}" if item['volume'] is not None else "N/A")
                st.write(f"  - OBV: {item['obv']:.0f}" if item['obv'] is not None else "N/A")
                st.write(f"**스토캐스틱 오실레이터 (14, 3)**: ")
                st.write(f"  - %K: {item['stoch_k']:.2f}" if item['stoch_k'] is not None else "N/A")
                st.write(f"  - %D: {item['stoch_d']:.2f}" if item['stoch_d'] is not None else "N/A")
                st.write(f"**ATR (14)**: {item['atr']:.2f}" if item['atr'] is not None else "N/A")
                st.write(f"**ADX (14)**: ")
                st.write(f"  - ADX: {item['adx']:.2f}" if item['adx'] is not None else "N/A")
                st.write(f"  - +DI: {item['plus_di']:.2f}" if item['plus_di'] is not None else "N/A")
                st.write(f"  - -DI: {item['minus_di']:.2f}" if item['minus_di'] is not None else "N/A")

                st.subheader("거래 신호 및 적정가")
                st.markdown(f"**매수 신호 이유**: {item['buy_reasons']}")
                st.markdown(f"**매도 신호 이유**: {item['sell_reasons']}")
                st.write(
                    f"**매수 적정가**: {item['buy_target_price']:.2f}" if item['buy_target_price'] is not None else "N/A")
                st.write(
                    f"**매도 적정가**: {item['sell_target_price']:.2f}" if item['sell_target_price'] is not None else "N/A")
    else:
        st.info("현재 분석된 종목 데이터가 없습니다. 종목을 추가하고 분석을 시작해주세요.")
else:
    st.info("현재 분석된 종목 데이터가 없습니다. 종목을 추가하고 분석을 시작해주세요.")

st.markdown("---")
st.info("데이터는 지연될 수 있으며, 투자 결정은 항상 신중하게 하십시오.")