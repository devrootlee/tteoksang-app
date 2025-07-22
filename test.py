import requests

def test():

    url = "https://data.alpaca.markets/v2/stocks/bars?symbols=AAPL&timeframe=1D&start=2025-07-11&end=2025-07-21&limit=1000&adjustment=raw&feed=sip&sort=asc"

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": "PKJLJZQ1C92G108XPJ63",
        "APCA-API-SECRET-KEY": "rnmlWzTAPCcZuwEgWWiwTRdW0kEiRW5lkiWqWwIg"
    }

    response = requests.get(url, headers=headers)

    print(response.text)

if __name__ == '__main__':
     test()