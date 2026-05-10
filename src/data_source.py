# -*- coding: utf-8 -*-
"""
Stock Data Module - Sina Real-time API (reliable, no 403)
Supports: A-share (SSE/SZSE), HK Stock (HKEX via Sina)
"""

import akshare as ak
import pandas as pd
import requests
import time
from typing import List, Optional

# ── Sina Real-time Quotes ─────────────────────────────────

def _sina_headers():
    return {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }


def _parse_sina_a(text: str) -> Optional[dict]:
    """Parse Sina A-share response line"""
    if '="";' in text or '="" ' in text:
        return None
    try:
        # var hq_str_sh600519="贵州茅台,1850.000,1838.000,1848.000,1868.000,1831.200,1848.000,1848.000,1837.300,1838.000,1837.300,1837.000,1837.000,1847.800,8,1837.300,1837.000,2016,2019,10.00,11.54,8.40,4.17,5.58,5.89,14.67,3.58,14.58,14.59,1.21,2.30,1.00,0.65,14.67,0.00,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0;
        # Fields: 0=name,1=open,2=close/prev,3=current,4=high,5=low,...
        val = text.split('="')[1].rstrip('";')
        parts = val.split(",")
        if len(parts) < 32:
            return None
        name    = parts[0]
        open_p  = _to_float(parts[1])
        prev    = _to_float(parts[2])
        current = _to_float(parts[3])
        high    = _to_float(parts[4])
        low     = _to_float(parts[5])
        vol     = _to_float(parts[8])   # volume in shares
        amount  = _to_float(parts[9])   # amount in CNY
        date    = parts[30] if len(parts) > 30 else ""
        time_   = parts[31] if len(parts) > 31 else ""

        change = round(current - prev, 2) if (current and prev) else None
        pct    = round((current / prev - 1) * 100, 2) if (current and prev) else None

        return {
            "name": name, "open": open_p, "prev_close": prev,
            "current": current, "high": high, "low": low,
            "vol": vol, "amount": amount,
            "change": change, "pct": pct,
            "date": date, "time": time_,
        }
    except Exception:
        return None


def _parse_sina_hk(text: str) -> Optional[dict]:
    """Parse Sina HK stock response"""
    if '="";' in text or '="" ' in text:
        return None
    try:
        val = text.split('="')[1].rstrip('";')
        parts = val.split(",")
        if len(parts) < 10:
            return None
        name    = parts[0]
        prev    = _to_float(parts[2])
        current = _to_float(parts[3])
        open_p  = _to_float(parts[5])
        vol     = _to_float(parts[6])
        high    = _to_float(parts[7])
        low     = _to_float(parts[8])
        amount  = _to_float(parts[12]) if len(parts) > 12 else None

        change = round(current - prev, 2) if (current and prev) else None
        pct    = round((current / prev - 1) * 100, 2) if (current and prev) else None

        return {
            "name": name, "open": open_p, "prev_close": prev,
            "current": current, "high": high, "low": low,
            "vol": vol, "amount": amount,
            "change": change, "pct": pct,
            "date": "", "time": "",
        }
    except Exception:
        return None


def _to_float(v):
    try:
        return round(float(v), 2)
    except Exception:
        return None


# Sina A-share code prefix: sh=6xxxxx, sz=0xxxxx/3xxxxx
def _sina_code(code: str) -> str:
    code = code.strip().zfill(6)
    if code.startswith(("6", "5")):
        return f"sh{code}"
    else:
        return f"sz{code}"


# ── Public API ─────────────────────────────────────────────

def get_realtime_quotes(codes: List[str]) -> List[dict]:
    """
    Get real-time quotes via Sina API (reliable, no 403)
    Supports A-share (6xxxxx/0xxxxx) and HK (hkxxxxxx)
    """
    if not codes:
        return []

    results = []
    sina_codes = []
    hk_codes   = []
    code_map    = {}  # sina_code -> original_code

    HK_CODES = {
        "00700","09988","03690","01810","09618","09888","06618",
        "06160","02318","00941","00939","01398","00992","02628",
        "02382","06690","02328","01339","01833","03968","02600",
    }

    for c in codes:
        c = c.strip().zfill(6)
        if not c.isdigit() or len(c) != 6:
            continue
        if c in HK_CODES:
            hk_codes.append(c)
            code_map[f"hk{c}"] = c
            sina_codes.append(f"hk{c}")
        else:
            sc = _sina_code(c)
            code_map[sc] = c
            sina_codes.append(sc)

    # Batch request (max ~50 per call)
    batch_size = 45
    for i in range(0, len(sina_codes), batch_size):
        batch = sina_codes[i:i+batch_size]
        url = "https://hq.sinajs.cn/list=" + ",".join(batch)
        try:
            resp = requests.get(url, headers=_sina_headers(), timeout=15)
            resp.encoding = "gbk"
            lines = resp.text.strip().split("\n")
            for line in lines:
                if 'hq_str_' not in line:
                    continue
                raw_code = line.split('hq_str_')[1].split('=')[0]
                if raw_code in code_map:
                    orig = code_map[raw_code]
                    is_hk = raw_code.startswith("hk")
                    data = _parse_sina_hk(line) if is_hk else _parse_sina_a(line)
                    if data:
                        data["code"]   = orig
                        data["market"] = "HK" if is_hk else "A"
                        results.append(data)
        except Exception as e:
            print(f"Sina request error: {e}")
            continue

    return results


def get_stock_realtime(code: str) -> Optional[dict]:
    """Single stock realtime"""
    results = get_realtime_quotes([code])
    return results[0] if results else None


# ── Historical Data (Sina API only — no akshare) ───────────

def get_historical_data(code: str, period: str = "daily") -> pd.DataFrame:
    """
    Get OHLCV history for technical analysis.
    All via Sina API — no akshare dependency.
    
    period: 'daily' (scale=240) | '60' | '30' | '15' | '5' (minutes)
    Returns DataFrame with columns: day, open, high, low, close, volume
    """
    # Determine scale from period
    scale_map = {"daily": 240, "weekly": 240, "monthly": 240,
                 "60": 60, "30": 30, "15": 15, "5": 5}
    scale = scale_map.get(str(period), 240)
    datalen = 120 if scale == 240 else 100

    # Normalize code
    c = str(code).strip().lower().replace("hk", "").zfill(5)
    HK_CODES = {
        "00700","09988","03690","01810","09618","09888","06618",
        "06160","02318","00941","00939","01398","00992","02628",
    }
    is_hk = c in HK_CODES or code.lower().startswith("hk")

    try:
        if is_hk:
            # HK minute K via Sina
            sina_sym = f"hk{c}"
            url = "https://stock.finance.sina.com.cn/hkstock/api/json_v2.php/MarketData.getHKStockDailyKLine"
            params = {"symbol": sina_sym, "type": "day", "datelen": datalen}
        else:
            # A-share minute K via Sina
            sina_sym = _sina_code(code)
            url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            params = {"symbol": sina_sym, "scale": scale, "ma": "no", "datalen": datalen}

        resp = requests.get(url, params=params, headers=_sina_headers(), timeout=15)
        data = resp.json()

        if data and isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            # Standardize column names: Sina returns ['day','open','high','low','close','volume']
            rename = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ("day", "date"):
                    rename[col] = "day"
                elif col_lower == "open":
                    rename[col] = "open"
                elif col_lower == "high":
                    rename[col] = "high"
                elif col_lower == "low":
                    rename[col] = "low"
                elif col_lower == "close":
                    rename[col] = "close"
                elif col_lower in ("volume", "vol", "成交量"):
                    rename[col] = "volume"
            df = df.rename(columns=rename)
            # Ensure required columns exist
            for col in ["day", "open", "high", "low", "close", "volume"]:
                if col not in df.columns:
                    df[col] = None
            # Numeric conversion
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df[["day", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
            return df.tail(120)
        return pd.DataFrame()
    except Exception as e:
        print(f"Historical data error for {code}: {e}")
        return pd.DataFrame()


# ── Technical Indicators ──────────────────────────────────

def calc_ma(prices: pd.Series, period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return round(float(prices.rolling(period).mean().iloc[-1]), 3)


def calc_ema(prices: pd.Series, period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return round(float(prices.ewm(span=period, adjust=False).mean().iloc[-1]), 3)


def calc_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    deltas = prices.diff()
    gain = deltas.clip(lower=0).rolling(period).mean().iloc[-1]
    loss = (-deltas.clip(upper=0)).rolling(period).mean().iloc[-1]
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def calc_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_bar = 2 * (dif - dea)
    return round(float(dif.iloc[-1]), 4), round(float(dea.iloc[-1]), 4), round(float(macd_bar.iloc[-1]), 4)


def calc_boll(prices: pd.Series, period: int = 20, std_mult: float = 2.0):
    if len(prices) < period:
        return None, None, None
    ma  = prices.rolling(period).mean().iloc[-1]
    std = prices.rolling(period).std().iloc[-1]
    return round(ma + std_mult * std, 3), round(ma, 3), round(ma - std_mult * std, 3)


def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3):
    """KDJ (RSV -> K -> D -> J)"""
    if len(close) < n:
        return None, None, None
    lows  = low.rolling(n).min()
    highs = high.rolling(n).max()
    rsv   = (close - lows) / (highs - lows + 1e-9) * 100
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return round(float(k.iloc[-1]), 2), round(float(d.iloc[-1]), 2), round(float(j.iloc[-1]), 2)


def get_technical_indicators(code: str, period: str = "daily") -> dict:
    """Full technical indicator analysis"""
    df = get_historical_data(code, period=period)
    if df is None or df.empty or len(df) < 30:
        return {}

    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df.get("vol", pd.Series([0]*len(df)))

    latest_close = float(close.iloc[-1])

    # MAs
    ma5  = calc_ma(close, 5)
    ma10 = calc_ma(close, 10)
    ma20 = calc_ma(close, 20)
    ma60 = calc_ma(close, 60) if len(close) >= 60 else None

    # MA cross
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            ma_cross = "BULLISH (5>10>20)"
        elif ma5 < ma10 < ma20:
            ma_cross = "BEARISH (5<10<20)"
        else:
            ma_cross = "MIXED"
    else:
        ma_cross = "Insufficient data"

    # RSI
    rsi6  = calc_rsi(close, 6)
    rsi14 = calc_rsi(close, 14)
    rsi26 = calc_rsi(close, 26)

    # MACD
    dif, dea, macd_bar = calc_macd(close)
    macd_cross = ("Golden X" if (dif and dea and dif > dea) else "Death X")

    # BOLL
    boll_up, boll_mid, boll_low = calc_boll(close)
    if boll_low and latest_close:
        boll_pos = (latest_close - boll_low) / (boll_up - boll_low + 1e-9) * 100
        boll_pos = round(boll_pos, 1)
    else:
        boll_pos = None

    # KDJ
    k, d, j = calc_kdj(high, low, close)

    # Volume
    vol5_avg = float(vol.rolling(5).mean().iloc[-1]) if len(vol) >= 5 else None
    vol_ratio = round(float(vol.iloc[-1]) / vol5_avg, 2) if vol5_avg and vol5_avg > 0 else None

    # Trend (based on MAs)
    if ma5 and ma20 and ma60:
        if ma5 > ma20 > ma60:
            short_t, mid_t, long_t = "UP", "UP", "UP"
        elif ma5 < ma20 < ma60:
            short_t, mid_t, long_t = "DOWN", "DOWN", "DOWN"
        elif ma5 > ma20:
            short_t, mid_t = "UP", "SIDEWAYS"
        else:
            short_t, mid_t = "DOWN", "SIDEWAYS"
        long_t = "UP" if ma20 > ma60 else "DOWN"
    else:
        short_t = mid_t = long_t = "N/A"

    return {
        "close": latest_close,
        "ma": {
            "MA5": ma5, "MA10": ma10, "MA20": ma20, "MA60": ma60,
            "cross": ma_cross,
        },
        "rsi": {
            "6": rsi6, "14": rsi14, "26": rsi26,
        },
        "macd": {
            "DIF": dif, "DEA": dea, "BAR": macd_bar,
            "cross": macd_cross,
        },
        "boll": {
            "upper": boll_up, "mid": boll_mid, "lower": boll_low,
            "pos_pct": boll_pos,
        },
        "kdj": {
            "K": k, "D": d, "J": j,
        },
        "volume": {
            "ratio": vol_ratio,
            "avg_5d": round(vol5_avg, 0) if vol5_avg else None,
        },
        "trend": {
            "short": short_t, "mid": mid_t, "long": long_t,
        }
    }


# ── Smart Signals (Rule-based) ───────────────────────────

def generate_signals(tech: dict) -> dict:
    """
    Multi-indicator buy/sell signal system
    Returns: {score, signals, recommendation, summary}
    Score: -100 (strong sell) to +100 (strong buy)
    """
    if not tech:
        return {"score": 0, "signals": [], "recommendation": "Insufficient data", "summary": ""}

    score = 0
    signals = []

    ma = tech.get("ma", {})
    rsi = tech.get("rsi", {})
    macd = tech.get("macd", {})
    boll = tech.get("boll", {})
    kdj = tech.get("kdj", {})
    trend = tech.get("trend", {})

    close = tech.get("close", 0)

    # MA signals
    ma_cross = ma.get("cross", "")
    if "BULLISH" in str(ma_cross):
        score += 25
        signals.append({"indicator": "MA", "signal": "BUY", "weight": 25,
                         "text": "5>10>20, golden cross confirmed"})
    elif "BEARISH" in str(ma_cross):
        score -= 25
        signals.append({"indicator": "MA", "signal": "SELL", "weight": 25,
                         "text": "5<10<20, death cross confirmed"})

    # RSI signals
    rsi14 = rsi.get("14")
    if rsi14:
        if rsi14 < 30:
            score += 20
            signals.append({"indicator": "RSI(14)", "signal": "BUY", "weight": 20,
                             "text": f"RSI={rsi14} < 30, oversold"})
        elif rsi14 > 70:
            score -= 20
            signals.append({"indicator": "RSI(14)", "signal": "SELL", "weight": 20,
                             "text": f"RSI={rsi14} > 70, overbought"})
        elif 50 < rsi14 <= 60:
            score += 5
            signals.append({"indicator": "RSI(14)", "signal": "BUY", "weight": 5,
                             "text": f"RSI={rsi14}, bullish zone"})

    # MACD signals
    dif = macd.get("DIF")
    dea = macd.get("DEA")
    mac = macd.get("cross", "")
    if "Golden" in str(mac):
        score += 20
        signals.append({"indicator": "MACD", "signal": "BUY", "weight": 20,
                         "text": "MACD golden cross, bullish momentum"})
    elif "Death" in str(mac):
        score -= 20
        signals.append({"indicator": "MACD", "signal": "SELL", "weight": 20,
                         "text": "MACD death cross, bearish momentum"})
    if dif and dea and macd.get("BAR"):
        if dif > 0 and macd.get("BAR", 0) > 0:
            score += 5
            signals.append({"indicator": "MACD", "signal": "BUY", "weight": 5,
                             "text": "MACD above 0 axis, positive momentum"})
        elif dif < 0 and macd.get("BAR", 0) < 0:
            score -= 5
            signals.append({"indicator": "MACD", "signal": "SELL", "weight": 5,
                             "text": "MACD below 0 axis, negative momentum"})

    # KDJ signals
    k = kdj.get("K")
    d = kdj.get("D")
    j = kdj.get("J")
    if k and d and j:
        if k < 20 and d < 20:
            score += 10
            signals.append({"indicator": "KDJ", "signal": "BUY", "weight": 10,
                             "text": f"KDJ oversold K={k} D={d}, potential rebound"})
        elif k > 80 and d > 80:
            score -= 10
            signals.append({"indicator": "KDJ", "signal": "SELL", "weight": 10,
                             "text": f"KDJ overbought K={k} D={d}, risk elevated"})
        elif k > d and d < 50:
            score += 5
            signals.append({"indicator": "KDJ", "signal": "BUY", "weight": 5,
                             "text": "KDJ golden cross forming"})

    # BOLL signals
    boll_pos = boll.get("pos_pct")
    boll_mid = boll.get("mid")
    if boll_pos is not None:
        if boll_pos < 20:
            score += 15
            signals.append({"indicator": "BOLL", "signal": "BUY", "weight": 15,
                             "text": f"Price near lower BOLL ({boll_pos:.0f}%), oversold"})
        elif boll_pos > 80:
            score -= 15
            signals.append({"indicator": "BOLL", "signal": "SELL", "weight": 15,
                             "text": f"Price near upper BOLL ({boll_pos:.0f}%), overbought"})
        elif boll_mid and close > boll_mid:
            score += 5
            signals.append({"indicator": "BOLL", "signal": "BUY", "weight": 5,
                             "text": "Price above BOLL mid-line"})

    # Trend signals
    if trend.get("short") == "UP":
        score += 5
        signals.append({"indicator": "Trend", "signal": "BUY", "weight": 5,
                         "text": "Short-term uptrend confirmed"})
    elif trend.get("short") == "DOWN":
        score -= 5
        signals.append({"indicator": "Trend", "signal": "SELL", "weight": 5,
                         "text": "Short-term downtrend confirmed"})

    # Final recommendation
    score = max(-100, min(100, score))
    if score >= 50:
        recommendation = "STRONG BUY"
        summary = "Multiple indicators bullish, consider buying on pullbacks"
    elif score >= 20:
        recommendation = "BUY"
        summary = "Moderate bullish signal, wait for better entry point"
    elif score <= -50:
        recommendation = "STRONG SELL"
        summary = "Multiple indicators bearish, consider reducing position"
    elif score <= -20:
        recommendation = "SELL"
        summary = "Moderate bearish signal, caution advised"
    else:
        recommendation = "HOLD"
        summary = "Mixed signals, wait for clearer direction"

    # Price-based trading suggestion
    price_suggestion = _generate_price_suggestion(tech, score)

    return {
        "score": score,
        "signals": signals,
        "recommendation": recommendation,
        "summary": summary,
        "price_suggestion": price_suggestion,
    }


def _generate_price_suggestion(tech: dict, score: int) -> dict:
    """Generate specific buy/sell price levels based on technical indicators"""
    if not tech:
        return {}

    close = tech.get("close", 0)
    if not close:
        return {}

    ma = tech.get("ma", {})
    boll = tech.get("boll", {})
    rsi = tech.get("rsi", {})

    ma5 = ma.get("MA5")
    ma10 = ma.get("MA10")
    ma20 = ma.get("MA20")
    boll_up = boll.get("upper")
    boll_low = boll.get("lower")
    rsi14 = rsi.get("14")

    buy_levels = []
    sell_levels = []

    # Buy levels (support levels)
    if ma5 and ma5 < close:
        buy_levels.append({"price": round(ma5, 2), "reason": "MA5支撑", "strength": "弱"})
    if ma10 and ma10 < close:
        buy_levels.append({"price": round(ma10, 2), "reason": "MA10支撑", "strength": "中"})
    if ma20 and ma20 < close:
        buy_levels.append({"price": round(ma20, 2), "reason": "MA20支撑", "strength": "强"})
    if boll_low:
        buy_levels.append({"price": round(boll_low, 2), "reason": "BOLL下轨", "strength": "强"})

    # Sell levels (resistance levels)
    if ma5 and ma5 > close:
        sell_levels.append({"price": round(ma5, 2), "reason": "MA5压力", "strength": "弱"})
    if ma10 and ma10 > close:
        sell_levels.append({"price": round(ma10, 2), "reason": "MA10压力", "strength": "中"})
    if ma20 and ma20 > close:
        sell_levels.append({"price": round(ma20, 2), "reason": "MA20压力", "strength": "强"})
    if boll_up:
        sell_levels.append({"price": round(boll_up, 2), "reason": "BOLL上轨", "strength": "强"})

    # Sort by distance from current price
    buy_levels = sorted(buy_levels, key=lambda x: abs(x["price"] - close))[:3]
    sell_levels = sorted(sell_levels, key=lambda x: abs(x["price"] - close))[:3]

    # Generate action text
    if score >= 30:
        action = "逢低买入"
        action_detail = f"建议在{buy_levels[0]['price'] if buy_levels else '支撑位'}附近分批建仓"
    elif score <= -30:
        action = "逢高卖出"
        action_detail = f"建议在{sell_levels[0]['price'] if sell_levels else '压力位'}附近减仓"
    else:
        action = "观望为主"
        action_detail = "信号不明确，建议等待更好的买卖点"

    return {
        "action": action,
        "detail": action_detail,
        "buy_levels": buy_levels,
        "sell_levels": sell_levels,
        "stop_loss": round(close * 0.95, 2) if close else None,  # 5% stop loss
        "take_profit": round(close * 1.10, 2) if close else None,  # 10% take profit
    }


def generate_dayt_suggestion(tech: dict, quote: dict = None) -> dict:
    """
    Generate day trading (做T) suggestions
    做T: Buy low sell high within the same day for profit
    """
    if not tech:
        return {"available": False, "reason": "数据不足"}

    close = tech.get("close", 0)
    high = tech.get("high", close)
    low = tech.get("low", close)

    if not close:
        return {"available": False, "reason": "价格数据缺失"}

    ma = tech.get("ma", {})
    boll = tech.get("boll", {})
    kdj = tech.get("kdj", {})
    rsi = tech.get("rsi", {})
    macd = tech.get("macd", {})

    # Calculate day trading range
    day_high = high if high else close * 1.03
    day_low = low if low else close * 0.97

    boll_up = boll.get("upper")
    boll_low = boll.get("lower")
    boll_mid = boll.get("mid")
    ma5 = ma.get("MA5")
    ma10 = ma.get("MA10")
    k = kdj.get("K")
    d = kdj.get("D")
    j = kdj.get("J")
    rsi14 = rsi.get("14")
    dif = macd.get("DIF")
    dea = macd.get("DEA")

    # Determine trend direction for T
    trend_score = 0

    # KDJ signal for day trading
    kdj_signal = ""
    if k and d and j:
        if j < 0:
            trend_score += 2
            kdj_signal = "J值超卖，适合低吸"
        elif j > 100:
            trend_score -= 2
            kdj_signal = "J值超买，适合高抛"
        elif k > d and k < 50:
            trend_score += 1
            kdj_signal = "KDJ金叉，可低吸"
        elif k < d and k > 50:
            trend_score -= 1
            kdj_signal = "KDJ死叉，可高抛"

    # RSI signal
    rsi_signal = ""
    if rsi14:
        if rsi14 < 30:
            trend_score += 2
            rsi_signal = "RSI超卖区，可低吸"
        elif rsi14 > 70:
            trend_score -= 2
            rsi_signal = "RSI超买区，可高抛"
        elif rsi14 < 45:
            trend_score += 1
            rsi_signal = "RSI偏低，有反弹空间"
        elif rsi14 > 55:
            trend_score -= 1
            rsi_signal = "RSI偏高，有回调风险"

    # BOLL signal
    boll_signal = ""
    boll_pos = boll.get("pos_pct")
    if boll_pos is not None:
        if boll_pos < 10:
            trend_score += 2
            boll_signal = "触及下轨，强支撑"
        elif boll_pos > 90:
            trend_score -= 2
            boll_signal = "触及上轨，强压力"
        elif boll_pos < 30:
            trend_score += 1
            boll_signal = "接近下轨，支撑区"
        elif boll_pos > 70:
            trend_score -= 1
            boll_signal = "接近上轨，压力区"

    # Calculate suggested buy/sell prices for T
    buy_price = None
    sell_price = None

    # Buy price: below current price
    if boll_low and boll_low < close:
        buy_price = round(boll_low, 2)
        buy_reason = "BOLL下轨支撑"
    elif ma5 and ma5 < close:
        buy_price = round(ma5, 2)
        buy_reason = "MA5支撑"
    else:
        buy_price = round(close * 0.98, 2)
        buy_reason = "当前价下方2%"

    # Sell price: above current price
    if boll_up and boll_up > close:
        sell_price = round(boll_up, 2)
        sell_reason = "BOLL上轨压力"
    elif ma5 and ma5 > close:
        sell_price = round(ma5, 2)
        sell_reason = "MA5压力"
    else:
        sell_price = round(close * 1.02, 2)
        sell_reason = "当前价上方2%"

    # Determine action
    if trend_score >= 3:
        action = "适合低吸做T"
        action_type = "BUY_T"
    elif trend_score <= -3:
        action = "适合高抛做T"
        action_type = "SELL_T"
    elif trend_score >= 1:
        action = "可尝试低吸"
        action_type = "LIGHT_BUY"
    elif trend_score <= -1:
        action = "可尝试高抛"
        action_type = "LIGHT_SELL"
    else:
        action = "观望，不适合做T"
        action_type = "HOLD"

    # Calculate expected profit range
    if buy_price and sell_price:
        profit_pct = round((sell_price - buy_price) / buy_price * 100, 2)
    else:
        profit_pct = None

    return {
        "available": True,
        "action": action,
        "action_type": action_type,
        "trend_score": trend_score,
        "buy_price": buy_price,
        "buy_reason": buy_reason,
        "sell_price": sell_price,
        "sell_reason": sell_reason,
        "profit_pct": profit_pct,
        "signals": {
            "kdj": kdj_signal,
            "rsi": rsi_signal,
            "boll": boll_signal,
        },
        "tips": _get_dayt_tips(trend_score, kdj_signal, rsi_signal, boll_signal),
    }


def _get_dayt_tips(score: int, kdj: str, rsi: str, boll: str) -> list:
    """Generate practical tips for day trading"""
    tips = []

    if score >= 3:
        tips.append("📊 多项指标显示超卖，可考虑分批低吸")
        tips.append("⚠️ 设好止损位，控制仓位在1/3以内")
    elif score <= -3:
        tips.append("📊 多项指标显示超买，可考虑分批高抛")
        tips.append("⚠️ 如有底仓可在压力位附近卖出，低位回补")
    else:
        tips.append("📊 指标信号不明确，建议观望为主")

    if kdj:
        tips.append(f"🔸 KDJ: {kdj}")
    if rsi:
        tips.append(f"🔸 RSI: {rsi}")
    if boll:
        tips.append(f"🔸 BOLL: {boll}")

    tips.append("💡 做T原则: 严守纪律，快进快出，宁可错过不可做错")

    return tips


# ── Market Top ─────────────────────────────────────────────

def get_market_top(market: str = "gainers", limit: int = 10) -> list:
    """
    获取涨幅榜/跌幅榜/成交额榜
    使用新浪实时行情数据（akshare东方财富接口不稳定）
    """
    try:
        # 使用新浪行情接口获取所有A股实时数据
        # 沪市前100 + 深市前100 的热门股票
        sh_codes = [f"sh60{str(i).zfill(4)}" for i in range(1, 400)]  # 沪市主板
        sz_codes = [f"sz00{str(i).zfill(4)}" for i in range(1, 500)]  # 深市主板
        
        all_quotes = []
        
        # 分批获取（每次100个）
        for codes_chunk in [sh_codes[:100], sh_codes[100:200], sh_codes[200:300],
                            sz_codes[:100], sz_codes[100:200], sz_codes[200:300],
                            sz_codes[300:400], sz_codes[400:500]]:
            codes_str = ",".join(codes_chunk)
            url = f"https://hq.sinajs.cn/list={codes_str}"
            headers = {"Referer": "https://finance.sina.com.cn"}
            
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    lines = r.text.strip().split("\n")
                    for line in lines:
                        if 'hq_str_' in line:
                            try:
                                # 解析: var hq_str_sh600519="..."
                                code_part = line.split('hq_str_')[1].split('=')[0]
                                data_part = line.split('"')[1]
                                if not data_part:  # 空数据跳过
                                    continue
                                fields = data_part.split(",")
                                if len(fields) >= 32:
                                    name = fields[0]
                                    current = _to_float(fields[3])
                                    pct = _to_float(fields[32]) if len(fields) > 32 else 0
                                    volume = _to_float(fields[8])
                                    amount = _to_float(fields[9])
                                    
                                    if current and current > 0:
                                        all_quotes.append({
                                            "code": code_part[2:],  # 去掉 sh/sz 前缀
                                            "name": name,
                                            "price": current,
                                            "pct": pct,
                                            "amount": amount,
                                            "volume": volume,
                                            "market": "A",
                                        })
                            except Exception:
                                continue
            except Exception:
                continue
        
        # 排序
        if market == "gainers":
            sorted_quotes = sorted(all_quotes, key=lambda x: x.get("pct", 0), reverse=True)
        elif market == "losers":
            sorted_quotes = sorted(all_quotes, key=lambda x: x.get("pct", 0))
        else:  # turnover
            sorted_quotes = sorted(all_quotes, key=lambda x: x.get("amount", 0), reverse=True)
        
        return sorted_quotes[:limit]
        
    except Exception as e:
        print(f"get_market_top error: {e}")
        return []


# ── Fundamentals ──────────────────────────────────────────

def get_background_info(code: str) -> dict:
    info = {}
    try:
        profile = ak.stock_individual_info_em(symbol=code)
        info_dict = dict(zip(profile["item"].tolist(), profile["value"].tolist()))
        info["industry"]  = info_dict.get("行业", "")
        info["total_shares"] = info_dict.get("总股本", "")
        info["float_shares"] = info_dict.get("流通股本", "")
    except Exception:
        pass

    try:
        fin = ak.stock_financial_analysis_indicator(symbol=code, start_year="2023")
        if fin is not None and not fin.empty:
            latest = fin.iloc[0]
            info["financial"] = {
                "ROE":         _to_float(latest.get("净资产收益率(%)", 0) or 0),
                "gross_margin": _to_float(latest.get("销售毛利率(%)", 0) or 0),
                "debt_ratio":   _to_float(latest.get("负债率(%)", 0) or 0),
            }
    except Exception:
        pass

    return info


# ── News ─────────────────────────────────────────────────

def get_stock_news(limit: int = 10) -> list:
    """
    获取财经新闻
    使用新浪财经新闻接口（akshare接口不稳定）
    """
    try:
        # 新浪财经新闻 RSS
        url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=50&page=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.sina.com.cn/",
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        
        data = r.json()
        if data.get("result") and data["result"].get("data"):
            news_list = []
            for item in data["result"]["data"][:limit]:
                news_list.append({
                    "time": item.get("ctime", "")[:10] if item.get("ctime") else "",
                    "title": item.get("title", ""),
                    "source": item.get("media_name", ""),
                    "url": item.get("url", ""),
                })
            return news_list
        
        return []
        
    except Exception as e:
        print(f"get_stock_news error: {e}")
        return []


# ── 多数据源管理器（向后兼容） ─────────────────────────────
from multi_source import DataSourceManager, get_manager

_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = DataSourceManager()
        _manager.auto_register()
    return _manager

# 覆盖原有函数，路由到多数据源管理器
def get_realtime_quotes(codes):
    return get_manager().get_realtime(codes)

def get_historical_kline(code, period='daily', days=None, **kwargs):
    return get_manager().get_historical(code, period)

# 向后兼容别名
get_historical_data = get_historical_kline

def get_market_top(market='gainers', limit=10):
    return get_manager().get_market_top(market, limit)

def get_stock_news(limit=10):
    return get_manager().get_news(limit)