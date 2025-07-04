import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Nasdaq 100 지수 가져오기
def get_nasdaq_index():
    try:
        # Nasdaq 100 데이터 다운로드
        nasdaq = yf.download("^NDX", period="7d", interval="1d", auto_adjust=False)

        # 디버깅: 데이터와 컬럼 구조 출력
        print("Nasdaq 데이터:\n", nasdaq.head())
        print("Nasdaq 컬럼 구조:\n", nasdaq.columns)

        # 데이터프레임 유효성 검사
        if nasdaq is None or nasdaq.empty:
            return {"error": "Nasdaq 데이터가 비어 있습니다"}
        if len(nasdaq) < 2:
            return {"error": f"Nasdaq 데이터가 부족합니다. 데이터 길이: {len(nasdaq)}"}

        # 멀티인덱스 컬럼 처리
        if isinstance(nasdaq.columns, pd.MultiIndex):
            if ('Close', '^NDX') not in nasdaq.columns:
                return {"error": "멀티인덱스에서 'Close', '^NDX' 컬럼을 찾을 수 없습니다"}
            nasdaq_close = nasdaq[('Close', '^NDX')]
        else:
            if "Close" not in nasdaq.columns:
                return {"error": "Nasdaq 데이터에 'Close' 컬럼이 없습니다"}
            nasdaq_close = nasdaq["Close"]

        # 최신 종가와 이전 전일 종가 추출
        latest_close = nasdaq_close.iloc[-1]
        prev_close = nasdaq_close.iloc[-2]

        # 전일 종가 유효성 검사
        if pd.isna(latest_close) or pd.isna(prev_close):
            return {"error": "Nasdaq 전일 종가 데이터에 결측값이 있습니다"}
        if float(prev_close) == 0.0:
            return {"error": "Nasdaq 이전 종가가 0입니다"}

        # 결과 반환
        return {
            "날짜": nasdaq.index[-1].strftime('%Y-%m-%d'),
            "전일 종가": round(float(latest_close), 2),
            "등락률(%)": round((float(latest_close) - float(prev_close)) / float(prev_close) * 100, 2)
        }

    except Exception as e:
        return {"error": f"Nasdaq 데이터 가져오기 실패: {str(e)}"}


# S&P 500 지수 가져오기
def get_sp500_index():
    try:
        # S&P 500 데이터 다운로드
        sp500 = yf.download("^GSPC", period="7d", interval="1d", auto_adjust=False)

        # 디버깅: 데이터와 컬럼 구조 출력
        print("S&P 500 데이터:\n", sp500.head())
        print("S&P 500 컬럼 구조:\n", sp500.columns)

        # 데이터프레임 유효성 검사
        if sp500 is None or sp500.empty:
            return {"error": "S&P 500 데이터가 비어 있습니다"}
        if len(sp500) < 2:
            return {"error": f"S&P 500 데이터가 부족합니다. 데이터 길이: {len(sp500)}"}

        # 멀티인덱스 컬럼 처리
        if isinstance(sp500.columns, pd.MultiIndex):
            if ('Close', '^GSPC') not in sp500.columns:
                return {"error": "멀티인덱스에서 'Close', '^GSPC' 컬럼을 찾을 수 없습니다"}
            sp500_close = sp500[('Close', '^GSPC')]
        else:
            if "Close" not in sp500.columns:
                return {"error": "S&P 500 데이터에 'Close' 컬럼이 없습니다"}
            sp500_close = sp500["Close"]

        # 최신 종가와 이전 전일 종가 추출
        latest_close = sp500_close.iloc[-1]
        prev_close = sp500_close.iloc[-2]

        # 전일 종가 유효성 검사
        if pd.isna(latest_close) or pd.isna(prev_close):
            return {"error": "S&P 500 전일 종가 데이터에 결측값이 있습니다"}
        if float(prev_close) == 0.0:
            return {"error": "S&P 500 이전 종가가 0입니다"}

        # 결과 반환
        return {
            "날짜": sp500.index[-1].strftime('%Y-%m-%d'),
            "전일 종가": round(float(latest_close), 2),
            "등락률(%)": round((float(latest_close) - float(prev_close)) / float(prev_close) * 100, 2)
        }

    except Exception as e:
        return {"error": f"S&P 500 데이터 가져오기 실패: {str(e)}"}

# 공탐(공포탐욕) 지수
def get_fear_greed_index(vix_data=None):
    try:
        response = requests.get("https://api.alternative.me/fng/", timeout=5)
        data = response.json()

        if "data" not in data or not data["data"]:
            raise ValueError("API 응답에 유효한 데이터가 없음")

        latest = data["data"][0]
        index_value = int(latest["value"])
        status = latest["value_classification"]
        timestamp = datetime.fromtimestamp(int(latest["timestamp"])).strftime("%Y-%m-%d")

        return {
            "날짜": timestamp,
            "지수": index_value,
            "상태": status,
            "근사": False,
            "출처": "alternative.me"
        }

    except Exception as e:
        # fallback to VIX 기반 근사
        if vix_data and "전일 종가" in vix_data:
            vix = vix_data["전일 종가"]
            if vix < 15:
                index_value = 75
                status = "Greed"
            elif vix < 20:
                index_value = 50
                status = "Neutral"
            else:
                index_value = 25
                status = "Fear"

            return {
                "날짜": vix_data["날짜"],
                "지수": index_value,
                "상태": status,
                "근사": True,
                "출처": "VIX 기반 근사"
            }

        return {"error": f"공포탐욕 지수 가져오기 실패: {str(e)}"}

# VIX 지수 가져오기
def get_vix_index():
    try:
        # VIX 데이터 다운로드
        vix = yf.download("^VIX", period="7d", interval="1d", auto_adjust=False)

        # 디버깅: 데이터와 컬럼 구조 출력
        print("VIX 데이터:\n", vix)
        print("컬럼 구조:\n", vix.columns)

        # 데이터프레임이 비어 있는지 확인
        if vix is None or vix.empty:
            return {"error": "VIX 데이터가 비어 있습니다"}

        # 최소 2개의 데이터 포인트 확인
        if len(vix) < 2:
            return {"error": f"VIX 데이터가 부족합니다. 데이터 길이: {len(vix)}"}

        # 멀티인덱스 컬럼 처리
        if isinstance(vix.columns, pd.MultiIndex):
            try:
                # 'Close' 컬럼을 멀티인덱스에서 추출
                vix_close = vix[('Close', '^VIX')]
                print("멀티인덱스에서 추출된 Close 컬럼:\n", vix_close)
            except KeyError as ke:
                return {"error": f"멀티인덱스에서 'Close' 컬럼을 찾을 수 없습니다: {str(ke)}"}
        else:
            # 단일 인덱스 컬럼 처리
            if "Close" not in vix.columns:
                return {"error": "VIX 데이터에 'Close' 컬럼이 없습니다"}
            vix_close = vix["Close"]
            print("단일 인덱스에서 추출된 Close 컬럼:\n", vix_close)

        # 최신 종가와 이전 전일 종가 추출
        latest_close = vix_close.iloc[-1]
        prev_close = vix_close.iloc[-2]

        # 전일 종가 데이터 유효성 검사
        if pd.isna(latest_close) or pd.isna(prev_close):
            return {"error": "전일 종가 데이터에 결측값이 있습니다"}
        if float(prev_close) == 0.0:
            return {"error": "이전 종가가 0입니다"}

        # 결과 반환
        return {
            "날짜": vix.index[-1].strftime('%Y-%m-%d'),
            "전일 종가": round(float(latest_close), 2),
            "등락률(%)": round((float(latest_close) - float(prev_close)) / float(prev_close) * 100, 2)
        }

    except KeyError as ke:
        return {"error": f"KeyError 발생: {str(ke)}"}
    except Exception as e:
        return {"error": f"VIX 데이터 가져오기 실패: {str(e)}"}

# 섹터 흐름
def get_sector_flows():
    sector_etfs = {
        # 전통 섹터
        "기술": "XLK",
        "헬스케어": "XLV",
        "금융": "XLF",
        "소비재": "XLY",
        "산업재": "XLI",
        "소재": "XLB",
        "유틸리티": "XLU",
        "부동산": "XLRE",
        "에너지": "XLE",
        "필수소비재": "XLP",
        "커뮤니케이션": "XLC",

        # 신성장 테마
        "양자컴퓨팅": "QTUM",
        "AI/로보틱스": "BOTZ",
        "반도체": "SOXX",
        "사이버보안": "CIBR",
        "우주산업": "ARKX",
        "클린에너지": "ICLN"
    }

    tickers = list(sector_etfs.values())
    try:
        # 6일치 데이터 (5일 평균 + 오늘)
        data = yf.download(tickers, period="6d", interval="1d", group_by="ticker", auto_adjust=False)
        results = []

        for sector, ticker in sector_etfs.items():
            try:
                if ticker not in data:
                    continue
                df = data[ticker].dropna()
                if len(df) < 6:
                    continue

                prev_close = df["Close"].iloc[-2]
                latest_close = df["Close"].iloc[-1]
                latest_volume = df["Volume"].iloc[-1]
                avg_volume = df["Volume"].iloc[-6:-1].mean()

                if any(pd.isna([prev_close, latest_close, latest_volume, avg_volume])) or prev_close == 0 or avg_volume == 0:
                    continue

                pct = (latest_close - prev_close) / prev_close * 100
                volume_rate = latest_volume / avg_volume

                # 상태 해석
                if pct > 0 and volume_rate >= 1.3:
                    상태 = "자금 유입 뚜렷"
                elif pct > 0:
                    상태 = "가격 상승"
                elif pct <= 0 and volume_rate >= 1.3:
                    상태 = "거래량 급증 (하락)"
                else:
                    상태 = "약세"

                results.append({
                    "섹터": sector,
                    "ETF": ticker,
                    "현재가": round(latest_close, 2),
                    "전일대비(%)": round(pct, 2),
                    "거래량배율": round(volume_rate, 2),
                    "상태": 상태
                })
            except Exception:
                continue

        return pd.DataFrame(results) if results else pd.DataFrame(columns=["섹터", "ETF", "현재가", "전일대비(%)", "거래량배율", "상태"])
    except Exception as e:
        return pd.DataFrame({"error": [f"섹터 데이터 가져오기 실패: {str(e)}"]})