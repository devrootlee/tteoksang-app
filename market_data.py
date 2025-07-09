import yfinance as yf
import fear_and_greed
import pandas as pd

def market_data():

    try:
        # ✅ 선물 지수 현재가
        nq_future_price = yf.Ticker("NQ=F").info.get("regularMarketPrice")
        sp_future_price = yf.Ticker("ES=F").info.get("regularMarketPrice")

        # ✅ 필요한 심볼을 한 번에 다운로드
        data = yf.download(["^NDX", "^GSPC", "^VIX"], period="7d", interval="1d", group_by="ticker", auto_adjust=False)

        # ✅ 나스닥 지수
        nq = data["^NDX"]
        if nq.empty or len(nq) < 2:
            raise ValueError("나스닥 데이터 부족")

        nq_prev_close = nq["Close"].iloc[-2].item()
        nq_ma_5 = nq["Close"].tail(5).mean().item()
        nq_ma_7 = nq["Close"].mean().item()
        nq_vol_rate = nq["Volume"].iloc[-1].item() / nq["Volume"].tail(5).mean().item()
        nq_gap_pct = round(((nq_future_price - nq_prev_close) / nq_prev_close) * 100, 2)

        if nq_future_price is None:
            nq_status = "❓ 정보 없음"
        elif nq_gap_pct > 1.0 and nq_vol_rate >= 1:
            nq_status = "🚀 갭상승 + 강한 수급"
        elif nq_future_price > nq_ma_5 and nq_vol_rate >= 1:
            nq_status = "✅ 상승세 유지"
        elif nq_future_price < nq_ma_7 and nq_vol_rate < 0.8:
            nq_status = "⚠️ 약세 또는 관망"
        else:
            nq_status = "⏸️ 중립 흐름"

        # ✅ S&P500 지수
        sp = data["^GSPC"]
        if sp.empty or len(sp) < 2:
            raise ValueError("S&P500 데이터 부족")

        sp_prev_close = sp["Close"].iloc[-2].item()
        sp_ma_5 = sp["Close"].tail(5).mean().item()
        sp_ma_7 = sp["Close"].mean().item()
        sp_vol_rate = sp["Volume"].iloc[-1].item() / sp["Volume"].tail(5).mean().item()
        sp_gap_pct = round(((sp_future_price - sp_prev_close) / sp_prev_close) * 100, 2)

        if sp_future_price is None:
            sp_status = "❓ 정보 없음"
        elif sp_gap_pct > 1.0 and sp_vol_rate >= 1:
            sp_status = "🚀 갭상승 + 강한 수급"
        elif sp_future_price > sp_ma_5 and sp_vol_rate >= 1:
            sp_status = "✅ 상승세 유지"
        elif sp_future_price < sp_ma_7 and sp_vol_rate < 0.8:
            sp_status = "⚠️ 약세 또는 관망"
        else:
            sp_status = "⏸️ 중립 흐름"

        # ✅ VIX 지수
        vix = data["^VIX"]
        vix_now = vix["Close"].iloc[-1].item()
        vix_prev = vix["Close"].iloc[-2].item()
        vix_ma_5 = vix["Close"].tail(5).mean().item()
        vix_change = ((vix_now - vix_prev) / vix_prev) * 100

        if vix_now >= 25:
            vix_status = "🚨 고변동성 구간"
        elif vix_now <= 14:
            vix_status = "🟢 안정적"
        elif vix_change >= 8:
            vix_status = "🔺 급등 (불안 심리 확산)"
        elif vix_change <= -8:
            vix_status = "🔻 급락 (공포 해소)"
        elif vix_now > vix_ma_5:
            vix_status = "⚠️ 점진적 불안"
        else:
            vix_status = "⏸️ 중립 흐름"

        # ✅ 공포탐욕지수
        fgi_value = None
        fgi_comment = "데이터 없음"
        fgi_status = "❓ 정보 없음"

        try:
            fgi_data = fear_and_greed.get()
            fgi_value = round(fgi_data.value, 2)
            fgi_comment = fgi_data.description

            if fgi_value is not None:
                if fgi_value <= 20:
                    fgi_status = "😱 극심한 공포 (Extreme Fear)"
                elif fgi_value <= 40:
                    fgi_status = "😨 공포 (Fear)"
                elif fgi_value <= 60:
                    fgi_status = " neutral (중립)"
                elif fgi_value <= 70:  # 70까지는 '탐욕'으로 분류
                    fgi_status = "🤑 탐욕 (Greed)"
                else:  # 70 초과는 '과열 경고'로 분류
                    fgi_status = "🚨 과열 경고 (Potential Overheating)"

        except Exception as e:
            fgi_comment = f"공포탐욕지수 데이터 오류: {e}"
            fgi_status = "❌ 데이터 로드 실패"

        #  ✅ 섹터별 정보 (SPDR ETF 사용)
        sector_etfs = {
            "Technology": {"korean_name": "기술주", "ticker": "XLK"},
            "Healthcare": {"korean_name": "헬스케어", "ticker": "XLV"},
            "Financials": {"korean_name": "금융주", "ticker": "XLF"},
            "Consumer Discretionary": {"korean_name": "경기소비재", "ticker": "XLY"},
            "Communication Services": {"korean_name": "통신서비스", "ticker": "XLC"},
            "Industrials": {"korean_name": "산업재", "ticker": "XLI"},
            "Consumer Staples": {"korean_name": "필수소비재", "ticker": "XLP"},
            "Energy": {"korean_name": "에너지", "ticker": "XLE"},
            "Utilities": {"korean_name": "유틸리티", "ticker": "XLU"},
            "Real Estate": {"korean_name": "부동산", "ticker": "XLRE"},
            "Materials": {"korean_name": "소재", "ticker": "XLB"}
        }
        sectors_data = {}
        sector_tickers = [info["ticker"] for info in sector_etfs.values()]

        sector_download = yf.download(sector_tickers, period="5d", interval="1d", group_by="ticker", auto_adjust=False)

        strong_sectors = []  # 강세 섹터 리스트
        weak_sectors = []  # 약세 섹터 리스트

        for sector_name_eng, info in sector_etfs.items():
            ticker = info["ticker"]
            korean_name = info["korean_name"]

            # yfinance MultiIndex 또는 단일 티커 DataFrame 처리
            if len(sector_tickers) > 1 and ticker in sector_download.columns:
                sector_df = sector_download[ticker]
            elif len(sector_tickers) == 1:  # 단일 티커 다운로드 시
                sector_df = sector_download
            else:
                sector_df = pd.DataFrame()  # 데이터가 없는 경우 빈 DataFrame

            sector_status = "❓ 데이터 부족"
            if not sector_df.empty and len(sector_df) >= 2:
                current_price = sector_df["Close"].iloc[-1].item()
                prev_close = sector_df["Close"].iloc[-2].item()
                ma_5 = sector_df["Close"].tail(5).mean().item()

                price_change = round(((current_price - prev_close) / prev_close) * 100, 2)

                if current_price > ma_5 and price_change > 0.5:
                    sector_status = "🟢 강세 (상승 추세)"
                    strong_sectors.append(korean_name)  # 강세 섹터 추가
                elif current_price < ma_5 and price_change < -0.5:
                    sector_status = "🔴 약세 (하락 추세)"
                    weak_sectors.append(korean_name)  # 약세 섹터 추가
                else:
                    sector_status = "⏸️ 중립 (횡보 또는 혼조)"

            sectors_data[korean_name] = {  # 한글명으로 저장
                "ticker": ticker,
                "status": sector_status
            }

        # --- ✅ 종합 판단 ---
        overall_market_outlook = "🤔 판단 불가"  # 기본값

        # VIX 지수가 가장 중요, 고변동성 구간이면 최우선 경고
        if vix_status == "🚨 고변동성 구간":
            overall_market_outlook = "🚨 극심한 시장 불안정 (매우 위험)"
        # 공포탐욕지수 기반 판단
        elif fgi_status == "😱 극심한 공포 (Extreme Fear)":
            overall_market_outlook = "📉 극심한 공포/침체 (잠재적 매수 기회)"
        elif fgi_status == "🚨 과열 경고 (Potential Overheating)":
            overall_market_outlook = "📈 시장 과열 경고 (하락 위험 증가)"
        elif fgi_status == "😨 공포 (Fear)":
            overall_market_outlook = "⚠️ 시장 공포/불확실성 (신중 접근)"
        elif fgi_status == "🤑 탐욕 (Greed)":
            overall_market_outlook = "✅ 시장 강세 유지 (상승세 지속)"
        elif fgi_status == " neutral (중립)":
            overall_market_outlook = "⏸️ 중립적인 시장 흐름"

        # VIX와 FGI가 명확하지 않을 때, 나스닥과 S&P500의 흐름을 보조적으로 판단
        if overall_market_outlook == "🤔 판단 불가" or overall_market_outlook == "⏸️ 중립적인 시장 흐름":
            # 두 지수 모두 상승세 유지일 경우
            if nq_status == "✅ 상승세 유지" and sp_status == "✅ 상승세 유지":
                overall_market_outlook = "🟢 전반적인 시장 상승세 유지"
            # 두 지수 모두 약세 또는 관망일 경우
            elif nq_status == "⚠️ 약세 또는 관망" and sp_status == "⚠️ 약세 또는 관망":
                overall_market_outlook = "🟠 전반적인 시장 약세/관망"
            # 하나는 상승, 하나는 중립/약세이거나 그 반대의 경우
            elif (nq_status == "✅ 상승세 유지" and sp_status in ["⏸️ 중립 흐름", "⚠️ 약세 또는 관망"]) or \
                    (sp_status == "✅ 상승세 유지" and nq_status in ["⏸️ 중립 흐름", "⚠️ 약세 또는 관망"]):
                overall_market_outlook = "↔️ 혼조세 또는 불확실한 시장"
            elif nq_status == "❓ 정보 없음" or sp_status == "❓ 정보 없음":
                overall_market_outlook = "❓ 일부 정보 부족으로 판단 어려움"

        # 만약 fgi_status가 '데이터 로드 실패'였다면 최종 판단도 '판단 불가'로 변경
        if fgi_status == "❌ 데이터 로드 실패":
            overall_market_outlook = "❌ 핵심 데이터(공포탐욕지수) 로드 실패로 판단 불가"

        # --- 종합 판단 메시지 구성 ---
        overall_market_outlook_details = {
            "summary": overall_market_outlook,
            "strong_sectors": strong_sectors,
            "weak_sectors": weak_sectors
        }
        if not strong_sectors and not weak_sectors:
            overall_market_outlook_details["no_sector_trend"] = True

        return {
            "NASDAQ": {
                "price": nq_future_price,
                "change": nq_gap_pct,
                "status": nq_status
            },
            "S&P500": {
                "price": sp_future_price,
                "change": sp_gap_pct,
                "status": sp_status
            },
            "VIX": {
                "price": round(vix_now, 2),
                "change": round(vix_change, 2),
                "status": vix_status
            },
            "FearGreedIndex": {
                "value": fgi_value,
                "comment": fgi_comment,
                "status": fgi_status
            },
            "Sectors": sectors_data,
            "OverallMarketOutlook": overall_market_outlook_details
        }

    except Exception as e:
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    print(market_data())
