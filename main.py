import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from stock_daily_data import get_stock_data, create_stock_dataframe, evaluate_breakout, reset_channel_if_breakout, \
    filter_short_squeeze_potential
from stock_daily_data import (
    filter_uptrend_stocks, filter_pullback_stocks, filter_reversal_stocks,
    filter_downtrend_stocks, filter_uptrend_boundary_stocks, filter_downtrend_boundary_stocks,
    filter_call_dominant_stocks, filter_put_dominant_stocks, filter_call_breakout_stocks,
    filter_put_breakout_stocks, filter_overheated_stocks, get_combined_scan_tickers, filter_hidden_gems
)
from market_daily_data import (get_nasdaq_index, get_sp500_index, get_fear_greed_index, get_vix_index,
                               get_sector_flows, summarize_market_condition, get_futures_index)


# 캐싱된 데이터프레임 생성 함수
@st.cache_data
def cached_create_stock_dataframe(ticker_data, valid_tickers):
    return create_stock_dataframe(ticker_data, valid_tickers)


# 캐싱된 필터링 함수들
@st.cache_data
def cached_filter_uptrend_stocks(df):
    return filter_uptrend_stocks(df)

@st.cache_data
def cached_filter_pullback_stocks(df):
    return filter_pullback_stocks(df)

@st.cache_data
def cached_filter_reversal_stocks(df):
    return filter_reversal_stocks(df)

@st.cache_data
def cached_filter_downtrend_stocks(df):
    return filter_downtrend_stocks(df)

@st.cache_data
def cached_filter_uptrend_boundary_stocks(df):
    return filter_uptrend_boundary_stocks(df)

@st.cache_data
def cached_filter_downtrend_boundary_stocks(df):
    return filter_downtrend_boundary_stocks(df)


@st.cache_data
def cached_filter_call_dominant_stocks(df):
    return filter_call_dominant_stocks(df)


@st.cache_data
def cached_filter_put_dominant_stocks(df):
    return filter_put_dominant_stocks(df)


@st.cache_data
def cached_filter_call_breakout_stocks(df):
    return filter_call_breakout_stocks(df)

@st.cache_data
def cached_filter_put_breakout_stocks(df):
    return filter_put_breakout_stocks(df)

@st.cache_data
def cached_filter_overheated_stocks(df):
    return filter_overheated_stocks(df)

@st.cache_data
def cached_filter_short_squeeze_potential(df):
    return filter_short_squeeze_potential(df)


# UI 렌더링
st.set_page_config(page_title="📊 떡상", layout="wide")
st.title("📈🔥🚀 떡상")
tab1, tab2, tab3, tab4 = st.tabs(["📖 Read Me", "🛰️시장 분석", "📈 주식 분석", "💎 보석 발굴"])

with tab1:
    st.subheader("📖 Read Me")

    st.markdown("""
    ### 🧭 전체 개요
    본 애플리케이션은 **시장 전체 흐름**부터 **개별 종목 분석**, **숨겨진 보석 탐색**까지 지원하는 투자 보조 도구입니다.
    
    ---
    
    ### 📊 분석 방식 안내
    
    #### 📈 주요 기술 지표 기반
    - **RSI (상대강도지수)**: 과매수/과매도 여부를 판단하여 진입 시점 포착
    - **볼린저 밴드**: 변동성 대비 가격 포지션 분석 (밴드 하단 접근 시 매수 관심)
    - **이동평균 (5일, 20일)**: 골든크로스, 데드크로스 등 추세 판단
    - **갭 상승률**: 전일 종가 대비 시가 상승 갭 → 강세 신호
    - **이격도**: 현재가가 장기 평균 대비 과열됐는지 분석
    
    #### 💰 수급 관련 지표
    - **공매도 비율**: 숏 포지션이 많은 종목에 거래량이 붙을 경우 숏스퀴즈 가능성
    - **거래량 배율**: 최근 5일 평균 대비 현재 거래량이 높은 종목 우선 탐색
    - **옵션 데이터 (콜/풋 거래량, 행사가)**: 수요 집중 구간 확인
    
    #### 🔍 보석 발굴 알고리즘 (핵심 조건 요약)
    - RSI, 추세(상승/중립), 볼린저 기준 **매수 적정가 이하**
    - 공매도 수급, 거래량, 갭 상승 등 **복합 조건**을 만족
    - 종합 점수 **2.5점 이상**이면 후보로 선정
    
    ---
    
    ### 🛰️ 시장 분석 탭
    - 주요 지수, 변동성(VIX), 공포탐욕지수, 선물 흐름, 섹터별 ETF 등 종합 정보 제공
    
    ### 📈 주식 분석 탭
    - 종목별 주요 기술 지표 기반 평가 및 시각화
    
    ### 💎 보석 발굴기 탭
    - Yahoo Finance 데이터를 기반으로 매일 **실시간 종목 수집 및 분석**이 진행됩니다.
    
    #### ✅ 수집 경로:
    1. **실시간 거래량 상위 50개 종목**  
       → [`https://finance.yahoo.com/most-active`](https://finance.yahoo.com/most-active) 기준
    
    2. **핵심 5대 섹터에서 20개씩 수집**  
       → `Technology`, `Energy`, `Consumer Cyclical`, `Financial Services`, `Healthcare`
    
    총 약 100~150개 종목을 수집하여 아래 조건을 만족하는 종목을 보석 후보로 선정합니다:
    
    - RSI가 적절하고, 추세가 상승/중립이며  
    - 현재가가 **매수 적정가 이하**  
    - 공매도, 거래량, 옵션 등 수급 조건 일부 충족  
    - 종합 점수 ≥ 2.5점
    
    > ⚠️ 일부 상장폐지 종목이 포함될 수 있습니다. (Yahoo Finance 기준)
    
    ---
    
    ### ⚠️ 책임 한계 고지
    - 본 도구는 정보 제공 및 투자 판단 보조용일 뿐, 특정 종목의 매수/매도를 권유하지 않습니다.  
    - 투자의 최종 판단과 책임은 **당신의 손가락**에 있습니다. 📉📈  
    - 다시 말해... **수익은 당신의 통찰력, 손해는 당신의 손가락 탓**입니다. 🤷‍♂️✍️
    """)

with tab2:
    st.subheader("🛰️ 시장 분석")

    # ✅ 새로고침 버튼
    if st.button("📥 시장 지표 새로고침"):
        for key in ["nasdaq", "sp500", "vix", "fear_greed", "sector_df", "futures_nq", "futures_es", "market_data_loaded"]:
            st.session_state.pop(key, None)
        st.rerun()

    # ✅ 시장 데이터 초기 로딩 (캐싱)
    if "market_data_loaded" not in st.session_state:
        with st.spinner("📊 시장 데이터 불러오는 중..."):
            st.session_state["nasdaq"] = get_nasdaq_index()
            st.session_state["sp500"] = get_sp500_index()
            st.session_state["vix"] = get_vix_index()
            st.session_state["fear_greed"] = get_fear_greed_index(
                vix_data=st.session_state["vix"] if "error" not in st.session_state["vix"] else None
            )
            st.session_state["sector_df"] = get_sector_flows()
            st.session_state["futures_nq"] = get_futures_index("NQ=F", "Nasdaq 선물")
            st.session_state["futures_es"] = get_futures_index("ES=F", "S&P 선물")
            st.session_state["market_data_loaded"] = True

    # ✅ 세션에서 불러오기
    nasdaq = st.session_state["nasdaq"]
    sp500 = st.session_state["sp500"]
    vix = st.session_state["vix"]
    fear_greed = st.session_state["fear_greed"]
    sector_df = st.session_state["sector_df"]
    futures_nq = st.session_state["futures_nq"]
    futures_es = st.session_state["futures_es"]

    # ✅ 요약 생성 및 표시
    summary = summarize_market_condition(nasdaq, sp500, vix, fear_greed, sector_df, futures_nq, futures_es)
    st.markdown("### 🧭 시장 총평")
    st.success(summary)

    # ✅ 개별 지표 시각화
    st.markdown("### 📈 Nasdaq 100 지수")
    if "error" not in nasdaq:
        st.metric(
            label="Nasdaq 100",
            value=nasdaq["전일 종가"],
            delta=f"{nasdaq['등락률(%)']}%",
            delta_color="normal"
        )
    else:
        st.warning(nasdaq["error"])

    st.markdown("### 📈 S&P 500 지수")
    if "error" not in sp500:
        st.metric(
            label="S&P 500",
            value=sp500["전일 종가"],
            delta=f"{sp500['등락률(%)']}%",
            delta_color="normal"
        )
    else:
        st.warning(sp500["error"])

    st.markdown("### 📉 VIX 변동성 지수")
    if "error" not in vix:
        st.metric(
            label="VIX",
            value=vix["전일 종가"],
            delta=f"{vix['등락률(%)']}%",
            delta_color="inverse"
        )
    else:
        st.warning(vix["error"])

    st.markdown("### 😨 공포탐욕 지수")
    if "error" not in fear_greed:
        st.metric(
            label="Fear & Greed",
            value=fear_greed["지수"],
            delta=fear_greed["상태"],
            delta_color="normal"
        )
    else:
        st.warning(fear_greed["error"])

    # ✅ 선물 지수 시각화
    st.markdown("### 📊 선물 지수")
    col1, col2 = st.columns(2)
    with col1:
        if "error" not in futures_nq:
            price = futures_nq["현재가"]
            delta = futures_nq["등락률(%)"]
            if isinstance(price, pd.Series):
                price = price.item()
            delta_display = f"{delta}%" if isinstance(delta, (float, int)) else str(delta)
            st.metric("Nasdaq 선물", value=price, delta=delta_display, delta_color="normal")
        else:
            st.warning(futures_nq["error"])

    # 📌 S&P 선물
    with col2:
        if "error" not in futures_es:
            price = futures_es["현재가"]
            delta = futures_es["등락률(%)"]
            if isinstance(price, pd.Series):
                price = price.item()
            delta_display = f"{delta}%" if isinstance(delta, (float, int)) else str(delta)
            st.metric("S&P 선물", value=price, delta=delta_display, delta_color="normal")
        else:
            st.warning(futures_es["error"])

    # ✅ 섹터 흐름 시각화
    st.markdown("### 🔥 자금 유입 중인 섹터")
    if not sector_df.empty and "error" not in sector_df.columns:
        st.dataframe(sector_df.sort_values(by="전일대비(%)", ascending=False), use_container_width=True)
    else:
        error_msg = sector_df["error"].iloc[0] if "error" in sector_df.columns else "섹터 ETF 데이터를 불러오지 못했습니다."
        st.warning(error_msg)

with tab3:
    st.subheader("📈 주식 분석")

    # 세션 상태 초기화
    if "tickers" not in st.session_state:
        st.session_state.tickers = []
    if "ticker_data" not in st.session_state:
        st.session_state.ticker_data = {}
    if "new_ticker" not in st.session_state:
        st.session_state.new_ticker = None
    if "cached_df" not in st.session_state:
        st.session_state.cached_df = None
    if "cached_filters" not in st.session_state:
        st.session_state.cached_filters = {}

    # 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        with st.spinner("🔍 데이터를 새로고침 중..."):
            # 기존 티커 데이터 갱신
            for t in st.session_state.tickers:
                info = get_stock_data(t)
                if info:
                    st.session_state.ticker_data[t] = info
                else:
                    st.warning(f"❌ {t} 데이터 갱신 실패")
            # 캐시된 데이터프레임 및 필터 결과 초기화
            st.session_state.cached_df = None
            st.session_state.cached_filters = {}
            st.success("✅ 데이터 새로고침 완료!")

    # 기본 티커 로딩 (최초 실행 시에만)
    default_tickers = ["OPTT", "QBTS", "APP", "INTC", "PLTR", "TSLA"]
    if not st.session_state.tickers:  # 최초 실행 시에만 기본 티커 로드
        for t in default_tickers:
            if t not in st.session_state.ticker_data:
                with st.spinner(f"🔍 {t} 분석 중..."):
                    info = get_stock_data(t)
                    if info:
                        st.session_state.tickers.append(t)
                        st.session_state.ticker_data[t] = info

    # 새 티커 추가 처리
    new_ticker = st.text_input("🎯 분석할 종목을 입력하세요 (하나씩 추가)", "").upper()
    if st.button("➕ 종목 추가") and new_ticker:
        st.session_state.new_ticker = new_ticker

    if st.session_state.new_ticker:
        new_ticker = st.session_state.new_ticker
        if new_ticker in st.session_state.tickers:
            st.toast(f"⚠️ 이미 추가된 종목입니다: {new_ticker}", icon="⚠️")
        else:
            with st.spinner(f"🔍 {new_ticker} 분석 중..."):
                info = get_stock_data(new_ticker)
                if info:
                    st.session_state.tickers.append(new_ticker)
                    st.session_state.ticker_data[new_ticker] = info
                    # 새 티커 추가 후 캐시된 데이터프레임 무효화
                    st.session_state.cached_df = None
                    st.session_state.cached_filters = {}
                else:
                    box = st.empty()
                    box.warning(f"❌ 데이터를 불러올 수 없는 종목: {new_ticker}")
                    time.sleep(5)
                    box.empty()
        st.session_state.new_ticker = None

    # 티커 삭제 처리
    valid_tickers = [t for t in st.session_state.tickers if t in st.session_state.ticker_data]
    with st.expander("📋 현재 선택된 종목 / 삭제", expanded=False):
        if valid_tickers:
            cols = st.columns(len(valid_tickers))
            for i, ticker in enumerate(valid_tickers):
                with cols[i]:
                    if st.button(f"❌ {ticker}", key=f"del_{ticker}"):
                        st.session_state.tickers.remove(ticker)
                        st.session_state.ticker_data.pop(ticker, None)
                        # 티커 삭제 후 캐시된 데이터프레임 무효화
                        st.session_state.cached_df = None
                        st.session_state.cached_filters = {}
                        st.rerun()
        else:
            st.markdown("➕ 종목을 추가해주세요!")

    # 리채널링 적용
    for t in valid_tickers:
        st.session_state.ticker_data[t] = reset_channel_if_breakout(st.session_state.ticker_data[t])

    # 데이터프레임 생성 (캐싱 활용)
    if valid_tickers:
        if st.session_state.cached_df is None:  # 캐시된 데이터프레임이 없으면 새로 생성
            st.session_state.cached_df = cached_create_stock_dataframe(st.session_state.ticker_data, valid_tickers)

        df = st.session_state.cached_df
        if df is not None:
            st.subheader("📋 전체 분석 데이터")
            st.dataframe(df, use_container_width=True)

            # 뉴스 표시
            with st.expander("📰 개별 종목 뉴스 확인", expanded=False):
                for t in valid_tickers:
                    news = st.session_state.ticker_data[t].get("news", [])
                    if news:
                        st.markdown(f"### {t} 뉴스")
                        for item in news:
                            emoji = item.get("sentiment_emoji", "⚪️")
                            st.markdown(f"- {emoji} {item['title']}")

            # 핵심 가격대 차트
            with st.expander("📊 핵심 가격대 요약 (Plotly)", expanded=False):
                for t in valid_tickers:
                    meta = st.session_state.ticker_data[t]
                    status, reasons = evaluate_breakout(meta)
                    reasons_str = " / ".join(reasons)
                    combined_text = f"🚦 {status}  ｜  📋 {reasons_str}"

                    price_lines = [
                        {"label": "손절가", "price": meta["stop_loss"], "color": "red"},
                        {"label": "매수 적정가", "price": meta["buy_target"], "color": "green"},
                        {"label": "전일 종가", "price": meta["close"], "color": "white"},
                        {"label": "기대 매도가", "price": meta["sell_target"], "color": "orange"},
                    ]

                    fig = go.Figure()
                    for p in price_lines:
                        fig.add_shape(type="line", x0=0, x1=1, xref="paper", y0=p["price"], y1=p["price"],
                                      line=dict(color=p["color"], width=2))
                        fig.add_annotation(x=0.5, xref="paper", y=p["price"], yref="y",
                                           text=f"{p['label']}: {p['price']:.2f}",
                                           showarrow=False, font=dict(color=p["color"], size=13),
                                           xanchor="center", yanchor="bottom", bgcolor="rgba(0,0,0,0.6)", borderpad=4)

                    fig.add_annotation(x=0, xref="paper", y=max(p["price"] for p in price_lines) + 10, yref="y",
                                       text=combined_text, showarrow=False, font=dict(size=13, color="yellow"),
                                       xanchor="left", yanchor="top", bgcolor="rgba(0,0,0,0.7)", borderpad=6)

                    fig.update_layout(height=320, margin=dict(l=60, r=60, t=50, b=40),
                                      yaxis=dict(title="가격", range=[min(p["price"] for p in price_lines) - 5,
                                                                    max(p["price"] for p in price_lines) + 10]),
                                      plot_bgcolor="black", paper_bgcolor="black", font=dict(color="white"),
                                      showlegend=False)

                    st.markdown(f"#### 📊 {t} ({meta['date']} 기준)")
                    st.plotly_chart(fig, use_container_width=True)

            # 필터링 결과 (캐싱 활용)
            if not st.session_state.cached_filters:  # 캐시된 필터 결과가 없으면 새로 계산
                st.session_state.cached_filters = {
                    "uptrend": cached_filter_uptrend_stocks(df),
                    "pullback": cached_filter_pullback_stocks(df),
                    "reversal": cached_filter_reversal_stocks(df),
                    "downtrend": cached_filter_downtrend_stocks(df),
                    "uptrend_boundary": cached_filter_uptrend_boundary_stocks(df),
                    "downtrend_boundary": cached_filter_downtrend_boundary_stocks(df),
                    "call_dominant": cached_filter_call_dominant_stocks(df),
                    "put_dominant": cached_filter_put_dominant_stocks(df),
                    "call_breakout": cached_filter_call_breakout_stocks(df),
                    "put_breakout": cached_filter_put_breakout_stocks(df),
                    "overheated": cached_filter_overheated_stocks(df),
                    "short_squeeze": cached_filter_short_squeeze_potential(df)
                }

            # 상승 전략 필터
            with st.expander("📈 상승/반등 전략 종목"):
                st.markdown("#### 🔥 상승 기대 종목")
                st.dataframe(st.session_state.cached_filters["uptrend"], use_container_width=True)
                st.markdown("#### 📥 눌림목 매수 후보")
                st.dataframe(st.session_state.cached_filters["pullback"], use_container_width=True)
                st.markdown("#### 🌟 골든크로스 반등 시도")
                st.dataframe(st.session_state.cached_filters["reversal"], use_container_width=True)

            # 하락 전략 필터
            with st.expander("📉 하락/경계 전략 종목"):
                st.markdown("#### 📉 하락 기대 종목")
                st.dataframe(st.session_state.cached_filters["downtrend"], use_container_width=True)
                col_up, col_down = st.columns(2)
                with col_up:
                    st.markdown("### 📈 상승 경계")
                    st.dataframe(st.session_state.cached_filters["uptrend_boundary"], use_container_width=True)
                with col_down:
                    st.markdown("### 📉 하락 경계")
                    st.dataframe(st.session_state.cached_filters["downtrend_boundary"], use_container_width=True)

            # 옵션 기반 분석
            with st.expander("💸 옵션 기반 종목 필터"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 📈 콜 중심")
                    st.dataframe(st.session_state.cached_filters["call_dominant"], use_container_width=True)
                    st.markdown("#### 📈 콜 행사가 돌파")
                    st.dataframe(st.session_state.cached_filters["call_breakout"], use_container_width=True)
                with col2:
                    st.markdown("#### 📉 풋 중심")
                    st.dataframe(st.session_state.cached_filters["put_dominant"], use_container_width=True)
                    st.markdown("#### 📉 풋 행사가 하회")
                    st.dataframe(st.session_state.cached_filters["put_breakout"], use_container_width=True)

            # 숏 스퀴즈 가능성
            st.subheader("🔥 숏 스퀴즈 가능성?")
            st.dataframe(st.session_state.cached_filters["short_squeeze"], use_container_width=True)

            # 과열 경고
            st.subheader("⚠️ 과열 경고 종목")
            st.dataframe(st.session_state.cached_filters["overheated"], use_container_width=True)

        else:
            st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")
    else:
        st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")

with tab4:
    st.subheader("💎 숨겨진 보석 발굴기(상장폐지된 주식이 발견될 수 있습니다.)")

    # 버튼 클릭 → 스캔 시작
    if st.button("🔍 자동 스캔 시작"):
        with st.spinner("보석 종목 스캔 중..."):
            tickers = get_combined_scan_tickers(limit_yahoo=50, search_limit=20)
            ticker_data = {}

            for t in tickers:
                info = get_stock_data(t)
                if info:
                    ticker_data[t] = info

            df = create_stock_dataframe(ticker_data, list(ticker_data.keys()))
            gems = filter_hidden_gems(df)

            # ✅ 세션 상태에 저장
            st.session_state.auto_gems_df = df
            st.session_state.auto_gems_result = gems
            st.session_state.auto_gems_ticker_data = ticker_data

    # ✅ 세션 상태가 있으면 항상 보여주기
    if "auto_gems_result" in st.session_state:
        gems = st.session_state.auto_gems_result
        if gems is None or gems.empty:
            st.info("💤 아직 보석 같은 종목이 없습니다.")
        else:
            st.success(f"💎 {len(gems)}개 종목이 발굴되었습니다!")
            st.dataframe(gems.sort_values(by="종합 점수", ascending=False), use_container_width=True)
    else:
        st.info("🔍 먼저 [자동 스캔 시작]을 눌러주세요.")