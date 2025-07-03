# 📈 떡상앱 (Tteoksang App)

> "감성 + 기술적 + 수급 지표를 결합한 주가 분석 앱"

Streamlit을 기반으로 제작된 주식 종목 분석 웹 애플리케이션입니다.  
Finviz 뉴스, RSI, 이동평균, 볼린저밴드, 옵션 데이터 등을 활용하여  
'떡상 기대 종목'을 탐색합니다.

---

## 🚀 주요 기능

- 🔍 종목 실시간 분석 (`Yahoo Finance + Finviz`) - 90일 기준
- 📈 RSI, 이동평균, 볼린저밴드 기반 기술적 분석
- 🔮 옵션 수급 집중도 분석 (콜/풋 거래량)
- 🔄 골든크로스 + 반등 기대 시그널 탐지
- 🧠 종목 점수화 및 투자 의견 분류

---

## 🧰 사용 기술

- `Python 3.9+`
- `Streamlit`
- `yfinance`
- `beautifulsoup4`
- `vaderSentiment`
- `pandas`

---

## 🛠 설치 방법

```bash
git clone https://github.com/yourname/tteoksang-app.git
cd tteoksang-app
pip install -r requirements.txt
streamlit run app.py
