import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
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

    # 📊 핵심 가격대 요약 차트 (정렬된 수평선)
    def evaluate_breakout(meta):
        signals = 0
        reasons = []

        if meta["close"] > meta["buy_target"]:
            signals += 1
            reasons.append("채널 상단 돌파")

        if meta.get("volume_rate") and meta["volume_rate"] >= 1.2:
            signals += 1
            reasons.append("거래량↑")

        if 50 <= meta["rsi"] <= 72:
            signals += 1
            reasons.append("RSI 양호")

        if meta["ma_5"] > meta["ma_20"]:
            signals += 1
            reasons.append("골든크로스 유지")

        if meta["gap_pct"] > 0.3:
            signals += 1
            reasons.append("갭 상승")

        if 0 <= meta["deviation_pct"] <= 8:
            signals += 1
            reasons.append("이격도 정상")

        if signals >= 4:
            status = "🔥 돌파 가능성 높음"
        elif signals >= 2:
            status = "⚖️ 관망 (부분 조건 만족)"
        else:
            status = "❌ 돌파 신호 아님"

        return status, reasons


    with st.expander("📊 핵심 가격대 요약 (Plotly)", expanded=False):
        for t in valid_tickers:
            meta = st.session_state.ticker_data[t]
            breakout_status = evaluate_breakout(meta)

            price_lines = [
                {"label": "손절가", "price": meta["stop_loss"], "color": "red"},
                {"label": "매수 적정가", "price": meta["buy_target"], "color": "green"},
                {"label": "전일 종가", "price": meta["close"], "color": "white"},
                {"label": "기대 매도가", "price": meta["sell_target"], "color": "orange"},
            ]

            fig = go.Figure()

            for p in price_lines:
                fig.add_shape(
                    type="line",
                    x0=0, x1=1, xref="paper",
                    y0=p["price"], y1=p["price"],
                    line=dict(color=p["color"], width=2),
                )
                fig.add_annotation(
                    x=0.5, xref="paper",
                    y=p["price"], yref="y",
                    text=f"{p['label']}: {p['price']:.2f}",
                    showarrow=False,
                    font=dict(color=p["color"], size=13),
                    xanchor="center", yanchor="bottom",
                    bgcolor="rgba(0,0,0,0.6)",
                    borderpad=4
                )

            # ✅ 상단 상태 표시 텍스트
            status, reasons = evaluate_breakout(meta)
            reasons_str = " / ".join(reasons)
            combined_text = f"🚦 {status}  ｜  📋 {reasons_str}"

            # 상단 좌측 고정 표시
            fig.add_annotation(
                x=0, xref="paper",
                y=max(p["price"] for p in price_lines) + 10, yref="y",
                text=combined_text,
                showarrow=False,
                font=dict(size=13, color="yellow"),
                xanchor="left", yanchor="top",
                bgcolor="rgba(0,0,0,0.7)",
                borderpad=6
            )

            fig.update_layout(
                height=320,
                margin=dict(l=60, r=60, t=50, b=40),
                yaxis=dict(
                    title="가격",
                    range=[
                        min(p["price"] for p in price_lines) - 5,
                        max(p["price"] for p in price_lines) + 10
                    ]
                ),
                plot_bgcolor="black",
                paper_bgcolor="black",
                font=dict(color="white"),
                showlegend=False
            )

            st.markdown(f"#### 📊 {t} ({meta['date']} 기준)")
            st.plotly_chart(fig, use_container_width=True)


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
