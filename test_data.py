# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd

print("Testing akshare...")

# A股
try:
    df = ak.stock_zh_a_spot_em()
    print("A-share total rows:", len(df))
    print("Columns:", df.columns.tolist()[:8])
    sample = df[df["\u4ee3\u7801"].astype(str).isin(["000001","600519","000858"])]
    print("Sample data:", sample[["\u4ee3\u7801","\u540d\u79f0","\u6700\u65b0\u4ef7","\u6da8\u8d8b\u5e45"]].to_string())
except Exception as e:
    print("A-share ERROR:", e)

# HK
try:
    url = "https://hq.sinajs.cn/list=hk00700"
    headers = {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    import requests
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = "gbk"
    print("HK Tencent:", r.text[:200])
except Exception as e:
    print("HK ERROR:", e)
