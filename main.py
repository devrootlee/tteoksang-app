import streamlit as st
import pandas as pd
import time
import altair as alt
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

# ✅ 분석 데이터 표시
data = [st.session_state.ticker_data[t] for t in valid_tickers]
if data:
    df = pd.DataFrame(data)

    df = df[
        [
            "ticker",
            "date",
            "change_pct",
            "gap_pct",
            "high",
            "low",
            "close",
            "volume",
            "volume_rate",
            "rsi",
            "ma_5",
            "ma_20",
            "prev_ma_5",
            "prev_ma_20",
            "trend",
            "deviation_pct",
            "bollinger_upper",
            "bollinger_lower",
            "avg_volume_5d",
            "max_call_strike",
            "max_call_volume",
            "max_put_strike",
            "max_put_volume",
            "option_expiry",
            "buy_target",
            "sell_target",
            "stop_loss",
            "score"
        ]
    ]

    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df = df.dropna(subset=["change_pct"])

    df = df.rename(columns={
        "ticker": "종목코드",
        "date": "날짜",
        "change_pct": "등락률(%)",
        "gap_pct": "갭상승률(%)",
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
        "max_call_strike": "콜 집중 행사가",
        "max_call_volume": "콜 거래량",
        "max_put_strike": "풋 집중 행사가",
        "max_put_volume": "풋 거래량",
        "option_expiry": "옵션 만기일",
        "buy_target": "매수 적정가",
        "sell_target": "기대 매도가",
        "stop_loss": "손절가",
        "score": "종합 점수",
    })

    def interpret_score(score):
        if score >= 5:
            return "🔥 강한 매수"
        elif score >= 3:
            return "⚖️ 중립~관망"
        else:
            return "⚠️ 주의/보류"

    df["점수 해석"] = df["종합 점수"].apply(interpret_score)

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

    # 📊 종목별 180일 차트 시각화
    with st.expander("📊 종목별 180일 차트", expanded=False):
        for t in valid_tickers:
            meta = st.session_state.ticker_data[t]
            chart_data = meta.get("chart_history")
            if chart_data:
                df_chart = pd.DataFrame(chart_data)

                if "Date" not in df_chart.columns:
                    st.warning(f"{t}의 차트에 'Date' 컬럼이 없습니다.")
                    continue

                df_chart["Date"] = pd.to_datetime(df_chart["Date"])
                max_date = df_chart["Date"].max()
                min_date = df_chart["Date"].min()

                # ✅ 채널 영역용 DataFrame
                channel_df = pd.DataFrame({
                    "Date": [min_date, max_date],
                    "buy": [meta["buy_target"]] * 2,
                    "sell": [meta["sell_target"]] * 2,
                    "stop": [meta["stop_loss"]] * 2
                })

                # ✅ 차트 기반
                chart_base = alt.Chart(df_chart).encode(x="Date:T")

                # ✅ 채널 영역 (buy~sell)
                band = alt.Chart(channel_df).mark_area(opacity=0.15, color='green').encode(
                    x="Date:T",
                    y="buy:Q",
                    y2="sell:Q"
                )

                # ✅ Stop loss 선
                stop_line = alt.Chart(channel_df).mark_rule(color="red", strokeDash=[4, 2]).encode(y="stop:Q")

                # ✅ 가격선
                close_line = chart_base.mark_line(color="white").encode(y="Close:Q")
                upper_line = chart_base.mark_line(strokeDash=[4, 2], color="red").encode(y="bollinger_upper:Q")
                middle_line = chart_base.mark_line(strokeDash=[2, 2], color="gray").encode(y="bollinger_middle:Q")
                lower_line = chart_base.mark_line(strokeDash=[4, 2], color="blue").encode(y="bollinger_lower:Q")


                # ✅ 가격 라벨 표시
                def price_label(y_val, label, color):
                    return alt.Chart(pd.DataFrame({
                        "Date": [max_date],
                        "y": [y_val],
                        "text": [f"{label}: {y_val:.2f}"]
                    })).mark_text(
                        align="left", dx=5, dy=-5, color=color, fontSize=11
                    ).encode(
                        x="Date:T", y="y:Q", text="text:N"
                    )


                buy_label = price_label(meta["buy_target"], "매수", "green")
                sell_label = price_label(meta["sell_target"], "목표", "orange")
                stop_label = price_label(meta["stop_loss"], "손절", "red")

                st.markdown(f"#### 📈 {t}")
                chart = (
                        band + stop_line +
                        close_line + upper_line + middle_line + lower_line +
                        buy_label + sell_label + stop_label
                ).properties(height=320).interactive().configure_view(clip=False)

                st.altair_chart(chart, use_container_width=True)

    # 📈 상승 기대 종목 (갭 조건 제거)
    st.subheader("📈 상승 기대 종목")
    st.dataframe(
        df[
            (df["RSI"] <= 65) &  # 과열 방지
            (df["거래량배율"] >= 1.2) &  # 평균 대비 20% 이상 증가한 거래량
            (df["추세"] == "상승") &
            (df["5일이평"] > df["20일이평"]) &
            (
                    (df["콜 집중 행사가"].notna() & (df["콜 집중 행사가"] >= df["종가"] * 0.98)) |
                    (df["콜 집중 행사가"].isna())
            ) &
            (
                    (df["콜 거래량"].notna() & df["풋 거래량"].notna() & (df["콜 거래량"] >= df["풋 거래량"] * 1.2)) |
                    (df["콜 거래량"].isna())
            )
            ],
        use_container_width=True
    )

    # 📥 눌림목 매수 후보 종목 (갭 조건 완화)
    st.subheader("📥 눌림목 매수 후보 종목")
    st.dataframe(
        df[
            (df["RSI"] >= 40) &
            (df["RSI"] <= 58) &
            (df["갭상승률(%)"] > 0.3) &
            (df["거래량배율"] >= 1.1) &
            (df["5일이평"] > df["20일이평"]) &
            (df["종가"] < df["볼린저상단"] * 0.99)  # 과열 방지
            ],
        use_container_width=True
    )

    # 🌟 반전 시도 필터 (갭 조건 완화)
    st.subheader("🌟 골든크로스 반등 시도")
    st.dataframe(
        df[
            (df["전일 5일이평"] < df["전일 20일이평"]) &
            (df["5일이평"] > df["20일이평"]) &
            (df["갭상승률(%)"] > 0.2) &
            (df["거래량"] >= df["5일평균거래량"] * 1.3) &
            (df["종가"] < df["볼린저하단"] * 1.01) &
            (df["RSI"] < 70)  # 과열 방지
            ],
        use_container_width=True
    )

    # 📉 하락 기대 종목
    st.subheader("📉 하락 기대 종목")
    st.dataframe(
        df[
            (df["RSI"] >= 68) &
            (df["갭상승률(%)"] < -1.0) &
            (df["거래량배율"] >= 1.2) &
            (df["추세"] == "하락") &
            (
                    (df["풋 집중 행사가"].notna() & (df["풋 집중 행사가"] <= df["종가"] * 1.02)) |
                    (df["풋 집중 행사가"].isna())
            ) &
            (
                    (df["풋 거래량"].notna() & df["콜 거래량"].notna() & (df["풋 거래량"] >= df["콜 거래량"] * 1.2)) |
                    (df["풋 거래량"].isna())
            )
            ],
        use_container_width=True
    )

    # 🚀 갭 상승 + 거래량 급등 종목
    st.subheader("🚀 갭 상승 + 거래량 급등 종목")
    st.dataframe(
        df[
            (df["갭상승률(%)"] > 2.0) &
            (df["거래량배율"] > 1.8) &
            (df["RSI"] < 75) &
            (df["추세"] == "상승")
        ],
        use_container_width=True
    )

    # ⚖️ 상승 / 하락 경계 종목 (갭 조건 제거)
    st.subheader("⚖️ 상승 / 하락 양방향 경계 종목")
    col_up, col_down = st.columns(2)
    with col_up:
        st.markdown("### 📈 상승 경계 종목")
        st.dataframe(
            df[
                (df["RSI"] < 48) &
                (df["5일이평"] > df["20일이평"]) &
                (df["거래량배율"] > 0.9)
                ],
            use_container_width=True
        )
    with col_down:
        st.markdown("### 📉 하락 경계 종목")
        st.dataframe(
            df[
                (df["RSI"] >= 52) &
                (df["RSI"] <= 70) &
                (df["5일이평"] < df["20일이평"]) &
                (df["거래량배율"] > 1.0)
                ],
            use_container_width=True
        )

    # ⚖️ 옵션 중심 기대/경계 종목
    st.subheader("⚖️ 옵션 기반 상승/하락 기대 종목")
    col_up, col_down = st.columns(2)

    with col_up:
        st.markdown("### 📈 콜 중심 (상승 기대)")
        st.dataframe(
            df[
                (df["콜 거래량"] > df["풋 거래량"]) &
                (df["콜 집중 행사가"].notna()) &
                (df["콜 집중 행사가"] > df["종가"]) &
                ((df["콜 집중 행사가"] - df["종가"]) / df["종가"] < 0.05)
                ],
            use_container_width=True
        )
    with col_down:
        st.markdown("### 📉 풋 중심 (하락 경계)")
        st.dataframe(
            df[
                (df["풋 거래량"] > df["콜 거래량"]) &
                (df["풋 집중 행사가"].notna()) &
                (df["풋 집중 행사가"] < df["종가"]) &
                ((df["종가"] - df["풋 집중 행사가"]) / df["종가"] < 0.05)
                ],
            use_container_width=True
        )
    # 🔔 옵션 행사가 돌파 종목 (콜 상회 or 풋 하회)
    st.subheader("🔔 옵션 행사가 돌파된 종목")
    col_up, col_down = st.columns(2)

    with col_up:
        st.markdown("### 📈 콜 행사가 돌파")
        st.dataframe(
            df[
                (df["콜 거래량"] > df["풋 거래량"]) &
                (df["콜 집중 행사가"].notna()) &
                (df["종가"] > df["콜 집중 행사가"])
                ],
            use_container_width=True
        )
    with col_down:
        st.markdown("### 📉 풋 행사가 하회")
        st.dataframe(
            df[
                (df["풋 거래량"] > df["콜 거래량"]) &
                (df["풋 집중 행사가"].notna()) &
                (df["종가"] < df["풋 집중 행사가"])
                ],
            use_container_width=True
        )

    # 🔥 과열 경고 종목
    st.subheader("🔥 과열 경고 종목")
    st.dataframe(
        df[
            (df["RSI"] >= 75) &
            (df["갭상승률(%)"] > 2.0) &
            (df["거래량배율"] >= 2.2) &
            (df["이격도(%)"] >= 10)
            ],
        use_container_width=True
    )

else:
    st.warning("분석 가능한 데이터가 없습니다. 종목을 추가해주세요.")
