import streamlit as st
import pandas as pd
import time
from stock_daily_data import get_prev_day_price  # 수정된 분석 함수 (감성 변화율 제거됨)

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

# ✅ 분석 데이터 표시
data = [st.session_state.ticker_data[t] for t in valid_tickers]
if data:
    df = pd.DataFrame(data)

    df = df[
        [
            "ticker", "date", "change_pct", "high", "low", "close", "volume", "volume_rate",
            "rsi", "ma_5", "ma_20", "prev_ma_5", "prev_ma_20", "trend", "deviation_pct",
            "bollinger_upper", "bollinger_lower", "avg_volume_5d", "sentiment_score",
            "max_call_strike", "max_call_volume", "max_put_strike", "max_put_volume",
            "option_expiry", "score"
        ]
    ]

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
        "prev_ma_5": "전일 5일이평",
        "prev_ma_20": "전일 20일이평",
        "trend": "추세",
        "deviation_pct": "이격도(%)",
        "bollinger_upper": "볼린저상단",
        "bollinger_lower": "볼린저하단",
        "avg_volume_5d": "5일평균거래량",
        "sentiment_score": "감성점수",
        "max_call_strike": "콜 집중 행사가",
        "max_call_volume": "콜 거래량",
        "max_put_strike": "풋 집중 행사가",
        "max_put_volume": "풋 거래량",
        "option_expiry": "옵션 만기일",
        "score": "종합 점수"
    })

    # ✅ 점수 해석 컬럼 추가
    def interpret_score(score):
        if score >= 5:
            return "🔥 강한 매수"
        elif score >= 3:
            return "⚖️ 중립~관망"
        else:
            return "⚠️ 주의/보류"

    df["점수 해석"] = df["종합 점수"].apply(interpret_score)

    # ✅ 원본 테이블 표시
    st.subheader("📋 전체 분석 데이터")
    st.dataframe(df, use_container_width=True)

    # ✅ 뉴스 확인용
    with st.expander("📰 개별 종목 뉴스 확인", expanded=False):
        for t in valid_tickers:
            news = st.session_state.ticker_data[t].get("news", [])
            if news:
                st.markdown(f"### {t} 뉴스")
                for item in news:
                    emoji = item.get("sentiment_emoji", "⚪️")
                    st.markdown(f"- {emoji} {item['title']}")

    # 🌟 반전 시도 필터
    st.subheader("🌟 골든크로스 + 볼린저 하단 반등 시도")
    st.dataframe(
        df[
            (df["전일 5일이평"] < df["전일 20일이평"]) &
            (df["5일이평"] > df["20일이평"]) &
            (df["종가"] < df["볼린저하단"]) &
            (df["거래량"] > df["5일평균거래량"] * 1.8) &
            (df["감성점수"] > 0.0)
        ],
        use_container_width=True,
    )

    # 📈 상승 기대 종목
    st.subheader("📈 상승 기대 종목")
    st.dataframe(
        df[
            (
                ((df["RSI"] < 40) | ((df["RSI"] >= 35) & (df["RSI"] <= 60))) &
                (df["추세"] == "상승") &
                (df["감성점수"] > 0.0) &
                (df["거래량배율"] > 1.2)
            ) & (
                (df["콜 집중 행사가"].notna() & (df["콜 집중 행사가"] >= df["종가"])) |
                (df["콜 집중 행사가"].isna())
            ) & (
                (df["콜 거래량"].notna() & df["풋 거래량"].notna() & (df["콜 거래량"] > df["풋 거래량"])) |
                (df["콜 거래량"].isna())
            )
        ],
        use_container_width=True,
    )

    # 📥 눌림목 매수 후보 종목
    st.subheader("📥 눌림목 매수 후보 종목")
    st.dataframe(
        df[
            (df["RSI"] >= 40) & (df["RSI"] <= 50) &
            (df["5일이평"] > df["20일이평"]) &
            (df["종가"] < df["볼린저상단"]) &
            (df["감성점수"] >= -0.1) &
            (df["거래량배율"] > 1.15)
        ],
        use_container_width=True
    )

    # 📉 하락 기대 종목
    st.subheader("📉 하락 기대 종목")
    st.dataframe(
        df[
            (
                (df["RSI"] >= 60) &
                (df["추세"] == "하락") &
                (df["감성점수"] < 0.0) &
                (df["거래량배율"] > 1.2)
            ) & (
                (df["풋 집중 행사가"].notna() & (df["풋 집중 행사가"] <= df["종가"])) |
                (df["풋 집중 행사가"].isna())
            ) & (
                (df["풋 거래량"].notna() & df["콜 거래량"].notna() & (df["풋 거래량"] > df["콜 거래량"])) |
                (df["풋 거래량"].isna())
            )
        ],
        use_container_width=True,
    )

    # 📈📉 상승 / 하락 양방향 경계 종목
    st.subheader("⚖️ 상승 / 하락 양방향 경계 종목")
    col_up, col_down = st.columns(2)
    with col_up:
        st.markdown("### 📈 상승 기대 종목")
        st.dataframe(
            df[
                (df["RSI"] < 40) &
                (df["거래량배율"] > 1.2) &
                (df["감성점수"] > 0.0) &
                (df["5일이평"] > df["20일이평"])
            ],
            use_container_width=True
        )
    with col_down:
        st.markdown("### 📉 하락 경계 종목")
        st.dataframe(
            df[
                (df["RSI"] >= 45) & (df["RSI"] <= 60) &
                (df["감성점수"] < 0.0) &
                (df["5일이평"] < df["20일이평"])
            ],
            use_container_width=True
        )

else:
    st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")
