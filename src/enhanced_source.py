# -*- coding: utf-8 -*-
"""Enhanced Data Source - 资金流向、板块行情、市场情绪、支撑压力位"""

import requests
import numpy as np
import pandas as pd
from typing import List, Dict, Optional

def _h():
    return {"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}

def _f(v):
    try: return round(float(v), 2)
    except: return None

# ── 1. 资金流向 (东方财富) ────────────────────────────
def get_capital_flow(code: str) -> Optional[Dict]:
    """获取个股资金流向：主力/超大单/大单/中单/小单净流入(万元)"""
    try:
        code = code.strip().zfill(6)
        secid = f"1.{code}" if code.startswith(("6","5")) else f"0.{code}"
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        r = requests.get(url, params={
            "secid": secid,
            "fields": "f62,f64,f70,f66,f72,f78,f84",
            "forcect": "1"
        }, headers=_h(), timeout=10)
        d = r.json().get("data", {})
        if not d:
            return None
        main_net = _f(d.get("f62", 0))
        if main_net and main_net > 0:
            st, sc = "主力流入", "#dc3545"
        elif main_net and main_net < 0:
            st, sc = "主力流出", "#28a745"
        else:
            st, sc = "资金平衡", "#888"
        return {
            "main_net": main_net,
            "super_large": _f(d.get("f66", 0)),
            "large": _f(d.get("f72", 0)),
            "medium": _f(d.get("f78", 0)),
            "small": _f(d.get("f84", 0)),
            "main_in": _f(d.get("f64", 0)),
            "main_out": _f(d.get("f70", 0)),
            "status": st,
            "status_color": sc,
        }
    except Exception as e:
        print(f"Capital flow err {code}: {e}")
        return None

# ── 2. 板块行情 ──────────────────────────────────────
def get_sector_performance() -> List[Dict]:
    """获取行业板块涨跌排行 Top 50"""
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        r = requests.get(url, params={
            "pn": "1", "pz": "50", "po": "1", "np": "1",
            "fltt": "2", "invt": "2", "fid": "f3", "fs": "m:90+t2",
            "fields": "f2,f3,f12,f14,f104,f105,f128,f136,f140,f152",
            "forcect": "1",
        }, headers=_h(), timeout=10)
        data = r.json().get("data", {})
        if not data:
            return []
        sectors = []
        for item in data.get("diff", []):
            rc, fc = item.get("f104", 0), item.get("f105", 0)
            total = rc + fc
            sectors.append({
                "name": item.get("f14", ""),
                "pct": _f(item.get("f3", 0)),
                "price": _f(item.get("f2", 0)),
                "rise_count": rc,
                "fall_count": fc,
                "rise_ratio": round(rc / total * 100, 1) if total > 0 else 0,
                "lead_stock": item.get("f128", ""),
                "lead_pct": _f(item.get("f136", 0)),
                "turnover": _f(item.get("f140", 0)),
                "main_flow": _f(item.get("f152", 0)),
            })
        sectors.sort(key=lambda x: x.get("pct", 0) or 0, reverse=True)
        return sectors
    except Exception as e:
        print(f"Sector err: {e}")
        return []

# ── 3. 市场情绪 ──────────────────────────────────────
def get_market_breadth() -> Optional[Dict]:
    """市场宽度：涨跌家数、涨停跌停、情绪判断"""
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        r = requests.get(url, params={
            "pn": "1", "pz": "5000",
            "fs": "m:0+t6,m:0+t80,m:1+t2,m:1+t23",
            "fields": "f3",
        }, headers=_h(), timeout=15)
        data = r.json().get("data", {})
        if not data:
            return None
        up = dn = fl = lu = ld = 0
        for item in data.get("diff", []):
            pct = _f(item.get("f3", 0))
            if pct is None: fl += 1
            elif pct >= 9.9: lu += 1; up += 1
            elif pct <= -9.9: ld += 1; dn += 1
            elif pct > 0: up += 1
            elif pct < 0: dn += 1
            else: fl += 1
        total = up + dn + fl
        up_pct = round(up / total * 100, 1) if total > 0 else 0
        if up_pct >= 60: sentiment, sdesc = "🔥 亢奋", "市场普涨，注意追高风险"
        elif up_pct >= 45: sentiment, sdesc = "☀️ 偏暖", "市场氛围较好"
        elif up_pct >= 35: sentiment, sdesc = "😐 中性", "市场分化，精选个股"
        elif up_pct >= 20: sentiment, sdesc = "🌧️ 偏冷", "市场弱势，控制仓位"
        else: sentiment, sdesc = "❄️ 恐慌", "市场普跌，注意止损"
        return {
            "total": total, "up": up, "down": dn, "flat": fl,
            "up_pct": up_pct, "limit_up": lu, "limit_down": ld,
            "sentiment": sentiment, "sdesc": sdesc,
        }
    except Exception as e:
        print(f"Breadth err: {e}")
        return None

# ── 4. 支撑压力位 ────────────────────────────────────
def calc_support_resistance(hist_df: pd.DataFrame, current_price: float = None) -> Dict:
    """计算支撑位、压力位、Pivot Point"""
    if hist_df.empty:
        return {"supports": [], "resistances": [], "pivot": None}
    closes = hist_df["close"].values
    highs = hist_df["high"].values
    lows = hist_df["low"].values
    if len(closes) < 10:
        return {"supports": [], "resistances": [], "pivot": None}
    cur = current_price or float(closes[-1])
    levels = []
    for n, label in [(20, "20日"), (60, "60日"), (120, "120日")]:
        if len(closes) >= n:
            wh, wl = float(np.max(highs[-n:])), float(np.min(lows[-n:]))
            st = 3 if n >= 60 else 2
            if wh > cur:
                levels.append({"price": round(wh, 2), "type": "R", "label": f"{label}高点", "strength": st})
            if wl < cur:
                levels.append({"price": round(wl, 2), "type": "S", "label": f"{label}低点", "strength": st})
    for p in [5, 10, 20, 60]:
        if len(closes) >= p:
            ma = round(float(np.mean(closes[-p:])), 2)
            st = 3 if p >= 20 else 2
            levels.append({"price": ma, "type": "R" if ma > cur else "S", "label": f"MA{p}", "strength": st})
    if len(highs) >= 2:
        ph, pl, pc2 = float(highs[-2]), float(lows[-2]), float(closes[-2])
        pivot = round((ph + pl + pc2) / 3, 2)
        r1 = round(2 * pivot - pl, 2)
        s1 = round(2 * pivot - ph, 2)
        r2 = round(pivot + (ph - pl), 2)
        s2 = round(pivot - (ph - pl), 2)
        for pv, lb, tp in [(r2, "R2", "R"), (r1, "R1", "R"), (s1, "S1", "S"), (s2, "S2", "S")]:
            if pv > 0:
                levels.append({"price": pv, "type": tp, "label": lb, "strength": 1})
    seen = set()
    supports, resistances = [], []
    for lv in levels:
        key = str(lv["price"])
        if key in seen: continue
        seen.add(key)
        if lv["type"] == "S" and lv["price"] < cur:
            supports.append(lv)
        elif lv["type"] == "R" and lv["price"] > cur:
            resistances.append(lv)
    supports.sort(key=lambda x: x["price"], reverse=True)
    supports = supports[:5]
    resistances.sort(key=lambda x: x["price"])
    resistances = resistances[:5]
    pivot_val = round((float(highs[-1]) + float(lows[-1]) + float(closes[-1])) / 3, 2)
    return {"supports": supports, "resistances": resistances, "pivot": pivot_val}
