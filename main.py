import streamlit as st
import pandas as pd
import time
from stock_daily_data import get_prev_day_price

# ✅ 세션 상태 초기화
if "tickers" not in st.session_state:
    st.session_state.tickers = []
if "ticker_data" not in st.session_state:
    st.session_state.ticker_data = {}

# ✅ Streamlit 설정
st.set_page_config(page_title="📊 떡상", layout="wide")
st.title("📊 떡상")

# ✅ 종목 추가 입력
new_ticker = st.text_input("🎯 분석할 종목을 입력하세요 (하나씩 추가)", "").upper()
if st.button("➕ 종목 추가") and new_ticker:
    if new_ticker in st.session_state.tickers:
        st.toast(f"⚠️ 이미 추가된 종목입니다: {new_ticker}", icon="⚠️")
    else:
        info = get_prev_day_price(new_ticker)
        if info:
            st.session_state.tickers.append(new_ticker)
            st.session_state.ticker_data[new_ticker] = info
        else:
            box = st.empty()
            box.warning(f"❌ 데이터를 불러올 수 없는 종목: {new_ticker}")
            time.sleep(5)
            box.empty()

# ✅ 삭제 UI
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

# ✅ 분석 데이터
data = [st.session_state.ticker_data[t] for t in valid_tickers]
if data:
    df = pd.DataFrame(data)
    df = df[[
        "ticker",
        "date",
        "change_pct",
        "high",
        "low",
        "close",
        "volume",
        "volume_rate",
        "rsi",
        "ma_5",
        "ma_20",
        "trend",
        "deviation_pct",
        "sentiment_score",
        "max_call_strike",
        "max_call_volume",
        "max_put_strike",
        "max_put_volume",
        "option_expiry"
    ]]

    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df = df.dropna(subset=["change_pct"])

    df = df.rename(columns={
        "ticker": "종목코드",
        "date": "날짜",
        "change_pct": "등락률(%)",
        "high": "전일고가",
        "low": "전일저가",
        "close": "종가",
        "volume": "거래량",
        "volume_rate": "거래량배율",
        "rsi": "RSI",
        "ma_5": "5일이평",
        "ma_20": "20일이평",
        "trend": "추세",
        "deviation_pct": "이격도(%)",
        "sentiment_score": "감성점수",
        "max_call_strike": "콜 집중 행사가",
        "max_call_volume": "콜 거래량",
        "max_put_strike": "풋 집중 행사가",
        "max_put_volume": "풋 거래량",
        "option_expiry": "옵션 만기일"
    })

    st.dataframe(df, use_container_width=True)

    # 🎯 포지션 필터링
    st.subheader("📈 롱 포지션 유망 종목")
    st.dataframe(df[
        (df["RSI"] < 35) &
        (df["등락률(%)"] < -1) &
        (df["콜 집중 행사가"] > df["종가"]) &
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["추세"] == "상승") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] > 0.2) &
        (df["종가"] > df["전일고가"])
    ], use_container_width=True)

    st.subheader("🪃 하락 추세지만 반등 가능성 있는 종목")
    st.dataframe(df[
        (df["RSI"] < 35) &
        (df["등락률(%)"] < -1) &
        (df["콜 집중 행사가"] > df["종가"]) &
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] > 0.0) &
        (df["종가"] > df["전일저가"])
    ], use_container_width=True)

    st.subheader("📉 숏 포지션 유망 종목")
    st.dataframe(df[
        (df["RSI"] > 70) &
        (df["등락률(%)"] > 1) &
        (df["풋 집중 행사가"] < df["종가"]) &
        (df["풋 거래량"] > df["콜 거래량"]) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] < -0.2) &
        (df["종가"] < df["전일저가"])
    ], use_container_width=True)

    st.subheader("📈 더 상승할 여력 있는 종목")
    st.dataframe(df[
        (df["RSI"] >= 35) & (df["RSI"] <= 60) &
        (df["추세"] == "상승") &
        (df["거래량배율"] > 1.2) &
        (df["콜 집중 행사가"] >= df["종가"]) &
        (df["감성점수"] > 0.0) &
        (df["종가"] > df["전일저가"])
    ], use_container_width=True)

    st.subheader("📉 더 하락할 여력 있는 종목")
    st.dataframe(df[
        (df["RSI"] >= 60) & (df["RSI"] <= 80) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.2) &
        (df["풋 집중 행사가"] <= df["종가"]) &
        (df["감성점수"] < 0.0) &
        (df["종가"] < df["전일저가"])
    ], use_container_width=True)

else:
    st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")
