import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.eastmoney.com"
}

# Try East Money with different headers
def test_em():
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": "0.000001",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56",
        "klt": 101,
        "fqt": 1,
        "end": "20301231",
        "lmt": 10
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        print(f"EM status: {resp.status_code}")
        print(f"EM text: {resp.text[:200]}")
    except Exception as e:
        print(f"EM Error: {e}")

# Sina A daily with ma=no to get raw OHLCV
def test_sina_a():
    url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = {
        "symbol": "sz000001",
        "scale": 240,
        "ma": "no",
        "datalen": 120
    }
    try:
        resp = requests.get(url, params=params, headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}, timeout=10)
        data = resp.json()
        import pandas as pd
        df = pd.DataFrame(data)
        print("Sina A cols:", df.columns.tolist())
        print(df.tail(2))
    except Exception as e:
        print(f"Sina Error: {e}")

test_em()
print()
test_sina_a()
