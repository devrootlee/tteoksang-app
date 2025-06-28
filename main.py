import streamlit as st
import pandas as pd
from stock_daily_data import get_prev_day_price

st.set_page_config(page_title="📊 떡상", layout="wide")
st.title("📊미국 주식 단타치기 30일 데이터")

tickers = [
    "HOOD",
    "APP",
    "VICI"
]

data = []
for ticker in tickers:
    info = get_prev_day_price(ticker)
    if info:
        data.append(info)

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

    df = df.dropna(subset=["change_pct"])
    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df = df.dropna(subset=["change_pct"])

    df = df.rename(columns={
        "ticker": "종목코드",
        "date": "날짜",
        "change_pct": "등락률(%)",
        "high": "최고가",
        "low": "최저가",
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

    # 🎯 자동 추천: 롱/숏 전략 분리
    st.subheader("📈 롱 포지션 유망 종목")
    long_candidates = df[
        (df["RSI"] < 35) &
        (df["등락률(%)"] < -1) &
        (df["콜 집중 행사가"] > df["종가"]) &
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["추세"] == "상승") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] > 0.2)  # ✅ 긍정 뉴스 포함
        ]
    st.dataframe(long_candidates, use_container_width=True)

    st.subheader("🪃 하락 추세지만 반등 가능성 있는 종목")
    rebound_candidates = df[
        (df["RSI"] < 35) &
        (df["등락률(%)"] < -1) &
        (df["콜 집중 행사가"] > df["종가"]) &
        (df["콜 거래량"] > df["풋 거래량"]) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] > 0.0)  # ✅ 최소 중립 이상
        ]
    st.dataframe(rebound_candidates, use_container_width=True)

    st.subheader("📉 숏 포지션 유망 종목")
    short_candidates = df[
        (df["RSI"] > 70) &
        (df["등락률(%)"] > 1) &
        (df["풋 집중 행사가"] < df["종가"]) &
        (df["풋 거래량"] > df["콜 거래량"]) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.5) &
        (df["감성점수"] < -0.2)  # ✅ 부정 뉴스 있으면 숏 강화
        ]
    st.dataframe(short_candidates, use_container_width=True)

    st.subheader("📈 더 상승할 여력 있는 종목")
    rising_candidates = df[
        (df["RSI"] >= 35) & (df["RSI"] <= 60) &
        (df["추세"] == "상승") &
        (df["거래량배율"] > 1.2) &
        (df["콜 집중 행사가"] >= df["종가"]) &
        (df["감성점수"] > 0.0)  # ✅ 긍정 뉴스 조건 추가
        ]
    st.dataframe(rising_candidates, use_container_width=True)

    st.subheader("📉 더 하락할 여력 있는 종목")
    falling_candidates = df[
        (df["RSI"] >= 60) & (df["RSI"] <= 80) &
        (df["추세"] == "하락") &
        (df["거래량배율"] > 1.2) &
        (df["풋 집중 행사가"] <= df["종가"]) &
        (df["감성점수"] < 0.0)  # ✅ 부정 뉴스 조건 추가
        ]
    st.dataframe(falling_candidates, use_container_width=True)


else:
    st.warning("불러올 수 있는 데이터가 없습니다.")
