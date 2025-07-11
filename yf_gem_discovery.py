import yfinance as yf
import pandas as pd
import random
import time
import requests
from bs4 import BeautifulSoup # pandas.read_html이 내부적으로 사용할 수 있음
from io import StringIO # pandas.read_html에서 문자열을 파일처럼 읽기 위해 필요
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer # 사용자 제공 코드에 포함되어 유지
from datetime import datetime # 사용자 제공 코드에 포함되어 유지
import urllib.request # 사용자 제공 코드에 포함되어 유지

# swing_stock_data 함수는 별도의 yf_swing_stock_data.py 파일에 있다고 가정합니다.
# 실제 실행 시 이 파일이 같은 디렉토리에 있어야 합니다.
from yf_swing_stock_data import swing_stock_data


def gem_discovery(limit_yahoo=50, search_limit=20):
    """
    Yahoo Finance의 'Most Active' 페이지 크롤링과 섹터별 스크리너 JSON API를
    활용하여 다양한 종목 티커를 수집합니다.

    Args:
        limit_yahoo (int): Yahoo Most Active 페이지에서 가져올 최대 종목 수.
        search_limit (int): 섹터별 스크리너에서 각 섹터당 가져올 최대 종목 수.

    Returns:
        list: 수집된 중복 없는 종목 티커 리스트 (알파벳 순으로 정렬).
    """
    tickers = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/555.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/555.36"
    }

    # ✅ 1. Yahoo Most Active 페이지 크롤링
    # 참고: pandas.read_html은 'lxml' 또는 'html5lib' 라이브러리가 필요합니다.
    # 만약 'Missing optional dependency' 오류가 발생하면 'pip install lxml' 또는 'pip install html5lib'을 실행하세요.
    try:
        url = "https://finance.yahoo.com/most-active/?count=50"  # count=50으로 설정하여 한 페이지에서 50개 가져오기 시도
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()

        # pandas.read_html은 HTML 테이블을 직접 파싱합니다.
        # StringIO를 사용하여 requests.text를 파일처럼 전달합니다.
        tables = pd.read_html(StringIO(res.text))

        yahoo_active_tickers = []
        for table in tables:
            if "Symbol" in table.columns:
                yahoo_active_tickers = table["Symbol"].dropna().astype(str).tolist()[:limit_yahoo]
                tickers.update(yahoo_active_tickers)
                # 이전 버전의 출력 형식을 유지하여 간결하게 표시
                print(f"✅ Yahoo Most Active 수집 완료: {len(yahoo_active_tickers)}개")
                break
        if not yahoo_active_tickers:
            print("❌ Yahoo Most Active 테이블에서 Symbol 컬럼을 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ Yahoo Most Active 티커 수집 실패: {e}")
    time.sleep(1)  # 요청 간격

    # ✅ 2. 섹터별 스크리너 (JSON 기반)
    screener_ids = {
        "Technology": "ms_technology",
        "Energy": "ms_energy",
        "Consumer Cyclical": "ms_consumer_cyclical",
        "Financial Services": "ms_financial_services",
        "Healthcare": "ms_healthcare",
        "Industrials": "ms_industrials",
        "Communication Services": "ms_communication_services",
        "Consumer Defensive": "ms_consumer_defensive",
        "Utilities": "ms_utilities",
        "Real Estate": "ms_real_estate",
        "Basic Materials": "ms_basic_materials"
    }

    for sector, scr_id in screener_ids.items():
        try:
            json_url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds={scr_id}&count={search_limit}"
            res = requests.get(json_url, headers=headers, timeout=5)
            res.raise_for_status()
            data = res.json()
            quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
            sector_tickers = [q["symbol"] for q in quotes if "symbol" in q]
            tickers.update(sector_tickers)
            print(f"✅ {sector} 스크리너 수집 완료: {len(sector_tickers)}개")
        except Exception as e:
            print(f"❌ {sector} 스크리너 수집 실패: {e}")
        time.sleep(0.5)  # 요청 간격

    # ✅ 결과 반환 (유효성 검사 및 정렬)
    result = sorted([t for t in tickers if isinstance(t, str) and t.strip()])  # 빈 문자열 제거
    print(f"📦 수집된 총 유니크 티커 수: {len(result)}개")
    return result


def get_gem_candidates(
        num_to_sample=150,  # (안정적) 수집된 전체 티커 풀에서 샘플링하여 분석할 종목의 수 (증가)
        target_num_gems=20,  # (안정적) 최종적으로 찾을 보석 종목의 목표 개수 (적정 수준 유지)
        max_per=35,  # (안정적) 최대 PER (주가수익률) 기준 (미국 주식 특성 반영, 보수적 조정)
        max_psr=7,  # (안정적) 최대 PSR (주가매출액비율) 기준 (미국 주식 특성 반영, 보수적 조정)
        min_market_cap_billion=5,  # (안정적) 최소 시가총액 (억 달러) 기준 (50억 달러 이상 기업 선호)
        min_high_proximity_pct=10,  # 52주 고점 대비 최소 하락률 (%) (덜 오른/조정받은 기준)
        min_swing_score=6.5  # (안정적) swing_stock_data 분석 점수 최소 기준 (상향 조정)
):
    """
    Yahoo Finance에서 동적으로 수집한 종목들을 대상으로 최소 시가총액, 최대 PER/PSR,
    '덜 오르고' 기준과 기술적 매수 시그널을 통해 '숨겨진 보석' 종목들을 탐색합니다.

    Args:
        num_to_sample (int): gem_discovery에서 수집된 전체 종목 풀에서
                             무작위로 샘플링하여 swing_stock_data로 분석할 종목의 수.
                             (너무 많으면 시간이 오래 걸림)
        target_num_gems (int): 최종적으로 반환할 보석 종목의 목표 개수.
        max_per (float): PER 필터링을 위한 최대값.
        max_psr (float): PSR 필터링을 위한 최대값.
        min_market_cap_billion (float): 시가총액 필터링을 위한 최소값 (단위: 억 달러).
        min_high_proximity_pct (float): 52주 고점 대비 최소 하락률 (%).
                                        이 값 이상 하락한 종목을 '덜 오른/조정받은' 것으로 간주.
        min_swing_score (float): swing_stock_data 분석 점수 중 최소 기준.

    Returns:
        list: 발굴된 보석 종목들의 분석 결과 딕셔너리 리스트.
              (점수 기준으로 내림차순 정렬됨)
    """
    print(f"💎 보석 발굴 시작: {num_to_sample}개 종목 샘플링 후 분석 (재무/시가총액 필터링 적용)")

    # ✅ gem_discovery 함수를 호출하여 초기 종목 풀 확보
    initial_ticker_pool = gem_discovery(limit_yahoo=50, search_limit=10)

    if not initial_ticker_pool:
        print("❌ 초기 종목 풀을 수집할 수 없습니다. 보석 발굴 중단.")
        return []

    # 초기 종목 풀에서 무작위로 샘플링
    # initial_ticker_pool이 num_to_sample보다 작을 경우, 전체 리스트 사용
    tickers_to_process = random.sample(initial_ticker_pool, min(num_to_sample, len(initial_ticker_pool)))

    potential_gems = []
    processed_count = 0

    for ticker in tickers_to_process:
        processed_count += 1
        print(f"  -> {ticker} 상세 분석 중... ({processed_count}/{len(tickers_to_process)})")

        try:
            # 1. yfinance에서 기본 정보 가져오기 (PER, PSR, 시가총액)
            info = yf.Ticker(ticker).info

            per = info.get("trailingPE")
            psr = info.get("priceToSalesTrailing12Months")
            market_cap = info.get("marketCap")  # 단위: 달러

            # ✅ 2. 재무 필터링: PER, PSR, 시가총액 기준 적용
            # None 값 처리 및 기준 적용
            if (per is None or per > max_per) or \
                    (psr is None or psr > max_psr) or \
                    (market_cap is None or market_cap < min_market_cap_billion * 1_000_000_000):
                print(
                    f"    - {ticker}: 재무 필터링 불통과 (PER: {per if per is not None else 'N/A'}, PSR: {psr if psr is not None else 'N/A'}, 시총: {market_cap / 1_000_000_000 if market_cap else 'N/A'}B)")
                continue  # 다음 종목으로 넘어감

            # 3. swing_stock_data를 통한 심층 분석
            analysis_result = swing_stock_data(ticker)

            if "Recommendation" in analysis_result and "❌ 분석 실패" not in analysis_result["Recommendation"]:
                # 4. "덜 오르고" 기준 적용 (52주 고가 대비 하락률)
                high_proximity_pct = analysis_result.get("High_Proximity_Pct")

                if high_proximity_pct is not None and high_proximity_pct >= min_high_proximity_pct:
                    # 5. 최종 "보석" 기준: 매수 추천 & 점수 기준
                    if analysis_result["Recommendation"] in ["🔥 강력 매수 (과매도 반등)", "✅ 매수 고려 (지지선 근접/모멘텀 전환)",
                                                             "📈 상승 추세 매수"]:
                        if analysis_result.get("Score") is not None and analysis_result["Score"] >= min_swing_score:
                            # ✅ PER, PSR, MarketCap 정보를 analysis_result에 추가
                            analysis_result['PER'] = per
                            analysis_result['PSR'] = psr
                            analysis_result['MarketCap'] = market_cap # 달러 단위로 저장

                            potential_gems.append(analysis_result)
                            print(
                                f"    ✅ {ticker}: 보석 후보로 발굴! (점수: {analysis_result['Score']:.1f}, 추천: {analysis_result['Recommendation']})")

            # API 요청 빈도 조절 (과도한 요청 방지)
            time.sleep(0.5)  # 0.5초 대기

        except Exception as e:
            print(f"    ❌ {ticker} 분석 중 오류 발생: {e}")
            time.sleep(1)  # 오류 발생 시 더 길게 대기
            continue

    # 점수 기준으로 내림차순 정렬
    sorted_gems = sorted(potential_gems, key=lambda x: x.get("Score", 0), reverse=True)

    # 목표 개수만큼만 반환
    final_gems = sorted_gems[:target_num_gems]

    print(f"💎 보석 발굴 완료: 총 {len(final_gems)}개의 보석 종목 발굴.")
    return final_gems


# --- 함수 테스트를 위한 예시 코드 (UI 없음) ---
if __name__ == '__main__':
    print("--- 숨겨진 보석 발굴기 테스트 시작 ---")

    # 파라미터 조정하여 테스트 가능
    # 안정적인 설정을 기본값으로 사용하거나, 필요에 따라 조정
    found_gems = get_gem_candidates(
        num_to_sample=150,  # 150개 종목 샘플링
        target_num_gems=20,  # 최종 20개 목표
        max_per=35,  # PER 35 이하
        max_psr=7,  # PSR 7 이하
        min_market_cap_billion=5,  # 시가총액 50억 달러 이상
        min_high_proximity_pct=10,  # 52주 고점 대비 10% 이상 하락
        min_swing_score=6.5  # 스윙 분석 점수 6.5 이상
    )

    print("\n--- 발굴된 보석 종목 요약 ---")
    if found_gems:
        for gem in found_gems:
            # 이제 gem 딕셔너리에 PER, PSR, MarketCap이 직접 포함되어 있습니다.
            market_cap_val = gem.get('MarketCap')
            per_val = gem.get('PER')
            psr_val = gem.get('PSR')

            market_cap_str = f"{market_cap_val / 1_000_000_000:.2f}B" if market_cap_val is not None else "N/A"
            per_str = f"{per_val:.2f}" if per_val is not None else "N/A"
            psr_str = f"{psr_val:.2f}" if psr_val is not None else "N/A"

            print(f"  - 종목: {gem['ticker']}, 현재가: ${gem['current_price']:.2f}, "
                  f"시총: {market_cap_str}, PER: {per_str}, PSR: {psr_str}, "
                  f"52주 고점 근접도: {gem['High_Proximity_Pct']:.2f}%, "
                  f"RSI: {gem['RSI_14']:.2f}, 점수: {gem['Score']:.1f}, 추천: {gem['Recommendation']}")
    else:
        print("조건에 맞는 보석 종목을 찾을 수 없습니다.")

    print("\n--- 숨겨진 보석 발굴기 테스트 종료 ---")
