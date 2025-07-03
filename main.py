import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from stock_daily_data import get_stock_data, create_stock_dataframe, evaluate_breakout, reset_channel_if_breakout
from stock_daily_data import (
    filter_uptrend_stocks, filter_pullback_stocks, filter_reversal_stocks,
    filter_downtrend_stocks, filter_uptrend_boundary_stocks, filter_downtrend_boundary_stocks,
    filter_call_dominant_stocks, filter_put_dominant_stocks, filter_call_breakout_stocks,
    filter_put_breakout_stocks, filter_overheated_stocks
)
from coin_daily_data import get_coin_data, create_coin_dataframe

# UI 렌더링
st.set_page_config(page_title="📊 떡상", layout="wide")
st.title("📊 떡상")
tab1, tab2 = st.tabs(["📈 주식 분석", "💰 코인 분석"])

with tab1:
    # 세션 상태 초기화
    if "tickers" not in st.session_state:
        st.session_state.tickers = []
    if "ticker_data" not in st.session_state:
        st.session_state.ticker_data = {}
    if "new_ticker" not in st.session_state:
        st.session_state.new_ticker = None

    # 기본 티커 로딩
    default_tickers = ["OPTT", "SEZL", "QBTS", "AAPL", "AMZN", "APP", "INTC", "MSTR", "PLTR", "TSLA"]
    for t in default_tickers:
        if t not in st.session_state.tickers:
            with st.spinner(f"🔍 {t} 분석 중..."):
                info = get_stock_data(t)
                if info:
                    st.session_state.tickers.append(t)
                    st.session_state.ticker_data[t] = info

    # 새 티커 추가 처리
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
                else:
                    box = st.empty()
                    box.warning(f"❌ 데이터를 불러올 수 없는 종목: {new_ticker}")
                    time.sleep(5)
                    box.empty()
        st.session_state.new_ticker = None

    new_ticker = st.text_input("🎯 분석할 종목을 입력하세요 (하나씩 추가)", "").upper()
    if st.button("➕ 종목 추가") and new_ticker:
        st.session_state.new_ticker = new_ticker

    valid_tickers = [t for t in st.session_state.tickers if t in st.session_state.ticker_data]
    with st.expander("📋 현재 선택된 종목 / 삭제", expanded=False):
        if valid_tickers:
            cols = st.columns(len(valid_tickers))
            for i, ticker in enumerate(valid_tickers):
                with cols[i]:
                    if st.button(f"❌ {ticker}", key=f"del_{ticker}"):
                        st.session_state.tickers.remove(ticker)
                        st.session_state.ticker_data.pop(ticker, None)
                        st.rerun()
        else:
            st.markdown("➕ 종목을 추가해주세요!")

    for t in valid_tickers:
        st.session_state.ticker_data[t] = reset_channel_if_breakout(st.session_state.ticker_data[t])

    df = create_stock_dataframe(st.session_state.ticker_data, valid_tickers)
    if df is not None:
        st.subheader("📋 전체 분석 데이터")
        st.dataframe(df, use_container_width=True)

        with st.expander("📰 개별 종목 뉴스 확인", expanded=False):
            for t in valid_tickers:
                news = st.session_state.ticker_data[t].get("news", [])
                if news:
                    st.markdown(f"### {t} 뉴스")
                    for item in news:
                        emoji = item.get("sentiment_emoji", "⚪️")
                        st.markdown(f"- {emoji} {item['title']}")

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

        st.subheader("📈 상승 기대 종목")
        st.dataframe(filter_uptrend_stocks(df), use_container_width=True)

        st.subheader("📥 눌림목 매수 후보 종목")
        st.dataframe(filter_pullback_stocks(df), use_container_width=True)

        st.subheader("🌟 골든크로스 반등 시도")
        st.dataframe(filter_reversal_stocks(df), use_container_width=True)

        st.subheader("📉 하락 기대 종목")
        st.dataframe(filter_downtrend_stocks(df), use_container_width=True)

        st.subheader("⚖️ 상승 / 하락 양방향 경계 종목")
        col_up, col_down = st.columns(2)
        with col_up:
            st.markdown("### 📈 상승 경계 종목")
            st.dataframe(filter_uptrend_boundary_stocks(df), use_container_width=True)
        with col_down:
            st.markdown("### 📉 하락 경계 종목")
            st.dataframe(filter_downtrend_boundary_stocks(df), use_container_width=True)

        st.subheader("⚖️ 옵션 기반 상승/하락 기대 종목")
        col_up, col_down = st.columns(2)
        with col_up:
            st.markdown("### 📈 콜 중심 (상승 기대)")
            st.dataframe(filter_call_dominant_stocks(df), use_container_width=True)
        with col_down:
            st.markdown("### 📉 풋 중심 (하락 경계)")
            st.dataframe(filter_put_dominant_stocks(df), use_container_width=True)

        st.subheader("🔔 옵션 행사가 돌파된 종목")
        col_up, col_down = st.columns(2)
        with col_up:
            st.markdown("### 📈 콜 행사가 돌파")
            st.dataframe(filter_call_breakout_stocks(df), use_container_width=True)
        with col_down:
            st.markdown("### 📉 풋 행사가 하회")
            st.dataframe(filter_put_breakout_stocks(df), use_container_width=True)

        st.subheader("🔥 과열 경고 종목")
        st.dataframe(filter_overheated_stocks(df), use_container_width=True)
    else:
        st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")

with tab2:
    # 세션 상태 초기화
    if "coin_tickers" not in st.session_state:
        st.session_state.coin_tickers = []
    if "coin_ticker_data" not in st.session_state:
        st.session_state.coin_ticker_data = {}
    if "new_coin_ticker" not in st.session_state:
        st.session_state.new_coin_ticker = None

    # 기본 코인 로딩
    default_coins = ["BTC/USDT", "ETH/USDT"]
    for coin in default_coins:
        if coin not in st.session_state.coin_tickers:
            with st.spinner(f"🔍 {coin} 분석 중..."):
                info = get_coin_data(coin)
                if info:
                    st.session_state.coin_tickers.append(coin)
                    st.session_state.coin_ticker_data[coin] = info

    # 코인 심볼 입력 및 추가
    symbol = st.text_input("🔍 분석할 코인 심볼 (예: BTC/USDT)", "BTC/USDT").upper()
    if st.button("➕ 코인 추가"):
        st.session_state.new_coin_ticker = symbol

    # 새 코인 추가 처리
    if st.session_state.new_coin_ticker:
        new_ticker = st.session_state.new_coin_ticker
        if new_ticker in st.session_state.coin_tickers:
            st.toast(f"⚠️ 이미 추가된 코인입니다: {new_ticker}", icon="⚠️")
        else:
            with st.spinner(f"🔍 {new_ticker} 분석 중..."):
                info = get_coin_data(new_ticker)
                if info:
                    st.session_state.coin_tickers.append(new_ticker)
                    st.session_state.coin_ticker_data[new_ticker] = info
                else:
                    box = st.empty()
                    box.warning(f"❌ 데이터를 불러올 수 없는 코인: {new_ticker}")
                    time.sleep(5)
                    box.empty()
        st.session_state.new_coin_ticker = None

    # 선택된 코인 목록 표시 및 삭제
    valid_coin_tickers = [t for t in st.session_state.coin_tickers if t in st.session_state.coin_ticker_data]
    with st.expander("📋 현재 선택된 코인 / 삭제", expanded=False):
        if valid_coin_tickers:
            cols = st.columns(len(valid_coin_tickers))
            for i, ticker in enumerate(valid_coin_tickers):
                with cols[i]:
                    if st.button(f"❌ {ticker}", key=f"del_coin_{ticker}"):
                        st.session_state.coin_tickers.remove(ticker)
                        st.session_state.coin_ticker_data.pop(ticker, None)
                        st.rerun()
        else:
            st.markdown("➕ 코인을 추가해주세요!")

    # 데이터프레임 생성 및 표시
    if valid_coin_tickers:
        df = create_coin_dataframe(st.session_state.coin_ticker_data, valid_coin_tickers)
        if df is not None:
            st.subheader("📋 코인 분석 데이터")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("분석 가능한 데이터가 없습니다.")
    else:
        st.warning("분석 가능한 코인이 없습니다. 코인을 추가해주세요.")
