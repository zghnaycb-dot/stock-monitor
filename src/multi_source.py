# -*- coding: utf-8 -*-
"""
多数据源管理器 (Multi-Source Data Manager)
============================================
支持多数据源自动故障转移，统一接口，自动降级
数据源：新浪、东方财富(akshare)、雅虎财经(yfinance)、腾讯财经
"""

import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import requests
import pandas as pd

# ── 日志配置 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("multi_source")


# ═══════════════════════════════════════════════════════════
# 统一数据格式定义
# ═══════════════════════════════════════════════════════════

def normalize_realtime_entry(raw: dict, source: str, code: str = "") -> dict:
    """
    将各数据源返回的原始字典规范化为统一格式。
    统一格式字段:
        code, name, current, open, prev_close, high, low,
        vol, amount, change, pct, market, source, time, date
    """
    return {
        "code": code or raw.get("code", ""),
        "name": raw.get("name", ""),
        "current": raw.get("current") or raw.get("price") or raw.get("close"),
        "open": raw.get("open"),
        "prev_close": raw.get("prev_close"),
        "high": raw.get("high"),
        "low": raw.get("low"),
        "vol": raw.get("vol") or raw.get("volume"),
        "amount": raw.get("amount"),
        "change": raw.get("change"),
        "pct": raw.get("pct"),
        "market": raw.get("market", "A"),
        "source": source,
        "time": raw.get("time", ""),
        "date": raw.get("date", ""),
    }


# ═══════════════════════════════════════════════════════════
# 超时常量
# ═══════════════════════════════════════════════════════════

TIMEOUT_REALTIME = 8     # 实时行情超时(秒)
TIMEOUT_HISTORY  = 15    # 历史K线超时(秒)
TIMEOUT_NEWS     = 10    # 新闻/涨跌榜超时(秒)


# ═══════════════════════════════════════════════════════════
# 基础数据源抽象类
# ═══════════════════════════════════════════════════════════

class BaseDataSource:
    """
    数据源基类。
    所有具体数据源必须实现以下接口。
    属性 priority 数值越小优先级越高。
    """

    name: str = "base"
    priority: int = 999

    def realtime_quotes(self, codes: List[str]) -> List[dict]:
        """
        获取实时行情列表。
        返回: List[dict]，每个 dict 需包含 code/name/current/open/prev_close/high/low/vol/amount/change/pct/market/time/date
        出错时返回空列表。
        """
        raise NotImplementedError

    def historical_kline(self, code: str, period: str = "daily") -> pd.DataFrame:
        """
        获取历史K线数据。
        返回: DataFrame，列名为 [day, open, high, low, close, volume]，index 为 datetime。
        出错时返回空 DataFrame。
        """
        raise NotImplementedError

    def market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """
        获取涨跌榜。
        market: "gainers"(涨幅) | "losers"(跌幅) | "turnover"(成交额)
        返回: List[dict]，每项包含 code/name/price/pct/amount/volume
        """
        raise NotImplementedError

    def news(self, limit: int = 10) -> List[dict]:
        """
        获取财经新闻。
        返回: List[dict]，每项包含 time/title/source/url
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """快速检测数据源是否可用（发送一个轻量请求）"""
        raise NotImplementedError

    def health_check(self) -> bool:
        """完整健康检查（带超时）"""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def _to_float(v, default=None):
    try:
        return round(float(v), 4) if v not in (None, "", "N/A") else default
    except Exception:
        return default


def _sina_code(code: str) -> str:
    """将原始代码转为新浪格式前缀"""
    code = str(code).strip().zfill(6)
    if code.startswith(("6", "5")):
        return f"sh{code}"
    else:
        return f"sz{code}"


def _sina_headers() -> dict:
    return {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def _eastmoney_headers() -> dict:
    return {
        "Referer": "https://data.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


# ═══════════════════════════════════════════════════════════
# 新浪财经数据源
# ═══════════════════════════════════════════════════════════

class SinaDataSource(BaseDataSource):
    """
    新浪财经数据源。
    API:
        - A股实时: https://hq.sinajs.cn/list=sh600519,sz000001
        - 港股实时: https://hq.sinajs.cn/list=hk00700
        - A股历史K线: https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
        - 港股历史K线: https://stock.finance.sina.com.cn/hkstock/api/json_v2.php/MarketData.getHKStockDailyKLine
        - 新闻: https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509
    """

    name = "sina"
    priority = 1

    # 港股代码集合（用于判断是否是港股）
    HK_CODES = {
        "00700","09988","03690","01810","09618","09888","06618",
        "06160","02318","00941","00939","01398","00992","02628",
        "02382","06690","02328","01339","01833","03968","02600",
    }

    def _parse_a(self, line: str) -> Optional[dict]:
        """解析新浪A股行情行"""
        if '="";' in line or '="" ' in line or 'hq_str_' not in line:
            return None
        try:
            raw_code = line.split("hq_str_")[1].split("=")[0]
            val = line.split('="')[1].rstrip('";')
            parts = val.split(",")
            if len(parts) < 32:
                return None
            name    = parts[0]
            open_p  = _to_float(parts[1])
            prev    = _to_float(parts[2])
            current = _to_float(parts[3])
            high    = _to_float(parts[4])
            low     = _to_float(parts[5])
            vol     = _to_float(parts[8])
            amount  = _to_float(parts[9])
            date    = parts[30] if len(parts) > 30 else ""
            time_   = parts[31] if len(parts) > 31 else ""
            change  = round(current - prev, 2) if (current and prev) else None
            pct     = round((current / prev - 1) * 100, 2) if (current and prev) else None

            # 去掉 sh/sz 前缀得到原始代码
            code = raw_code[2:] if raw_code.startswith(("sh", "sz")) else raw_code

            return {
                "code": code,
                "name": name,
                "current": current,
                "open": open_p,
                "prev_close": prev,
                "high": high,
                "low": low,
                "vol": vol,
                "amount": amount,
                "change": change,
                "pct": pct,
                "market": "A",
                "source": "sina",
                "time": time_,
                "date": date,
            }
        except Exception:
            return None

    def _parse_hk(self, line: str) -> Optional[dict]:
        """解析新浪港股行情行"""
        if '="";' in line or '="" ' in line or 'hq_str_' not in line:
            return None
        try:
            raw_code = line.split("hq_str_")[1].split("=")[0]
            val = line.split('="')[1].rstrip('";')
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
            change  = round(current - prev, 2) if (current and prev) else None
            pct     = round((current / prev - 1) * 100, 2) if (current and prev) else None

            code = raw_code[2:] if raw_code.startswith("hk") else raw_code

            return {
                "code": code,
                "name": name,
                "current": current,
                "open": open_p,
                "prev_close": prev,
                "high": high,
                "low": low,
                "vol": vol,
                "amount": amount,
                "change": change,
                "pct": pct,
                "market": "HK",
                "source": "sina",
                "time": "",
                "date": "",
            }
        except Exception:
            return None

    def realtime_quotes(self, codes: List[str]) -> List[dict]:
        """获取实时行情"""
        if not codes:
            return []

        sina_codes = []
        code_map = {}   # sina_code -> (原始code, is_hk)

        for c in codes:
            c = str(c).strip().zfill(6)
            if not c.isdigit() or len(c) != 6:
                continue
            if c in self.HK_CODES:
                sc = f"hk{c}"
                code_map[sc] = (c, True)
                sina_codes.append(sc)
            else:
                sc = _sina_code(c)
                code_map[sc] = (c, False)
                sina_codes.append(sc)

        results = []
        batch_size = 45

        for i in range(0, len(sina_codes), batch_size):
            batch = sina_codes[i:i + batch_size]
            url = "https://hq.sinajs.cn/list=" + ",".join(batch)
            try:
                resp = requests.get(url, headers=_sina_headers(), timeout=TIMEOUT_REALTIME)
                resp.encoding = "gbk"
                for line in resp.text.strip().split("\n"):
                    if "hq_str_" not in line:
                        continue
                    raw_code = line.split("hq_str_")[1].split("=")[0]
                    if raw_code not in code_map:
                        continue
                    orig, is_hk = code_map[raw_code]
                    data = self._parse_hk(line) if is_hk else self._parse_a(line)
                    if data:
                        results.append(data)
            except Exception as e:
                logger.warning("[Sina] realtime_quotes 批次请求失败: %s", e)
                continue

        return results

    def historical_kline(self, code: str, period: str = "daily") -> pd.DataFrame:
        """获取历史K线"""
        scale_map = {"daily": 240, "weekly": 240, "monthly": 240,
                     "60": 60, "30": 30, "15": 15, "5": 5}
        scale = scale_map.get(str(period), 240)
        datalen = 120 if scale == 240 else 100

        c = str(code).strip().lower().replace("hk", "").zfill(5)
        is_hk = c in self.HK_CODES or str(code).lower().startswith("hk")

        try:
            if is_hk:
                sina_sym = f"hk{c}"
                url = ("https://stock.finance.sina.com.cn/hkstock/api/json_v2.php/"
                       "MarketData.getHKStockDailyKLine")
                params = {"symbol": sina_sym, "type": "day", "datalen": datalen}
            else:
                sina_sym = _sina_code(code)
                url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                       "CN_MarketData.getKLineData")
                params = {"symbol": sina_sym, "scale": scale, "ma": "no", "datalen": datalen}

            resp = requests.get(url, params=params, headers=_sina_headers(), timeout=TIMEOUT_HISTORY)
            data = resp.json()

            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                rename = {
                    "day": "day", "date": "day",
                    "open": "open", "high": "high",
                    "low": "low", "close": "close",
                    "volume": "volume", "vol": "volume", "成交量": "volume",
                }
                df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
                for col in ["day", "open", "high", "low", "close", "volume"]:
                    if col not in df.columns:
                        df[col] = None
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df[["day", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
                return df.tail(120)
            return pd.DataFrame()
        except Exception as e:
            logger.warning("[Sina] historical_kline(%s) 失败: %s", code, e)
            return pd.DataFrame()

    def market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """获取涨跌榜（使用新浪实时接口）"""
        try:
            sh_codes = [f"sh60{str(i).zfill(4)}" for i in range(1, 400)]
            sz_codes = [f"sz00{str(i).zfill(4)}" for i in range(1, 500)]
            all_codes = sh_codes[:100] + sh_codes[100:200] + sh_codes[200:300] + \
                        sz_codes[:100] + sz_codes[100:200] + sz_codes[200:300] + \
                        sz_codes[300:400] + sz_codes[400:500]

            all_quotes = []
            for chunk in [all_codes[i:i + 100] for i in range(0, len(all_codes), 100)]:
                url = "https://hq.sinajs.cn/list=" + ",".join(chunk)
                try:
                    r = requests.get(url, headers=_sina_headers(), timeout=TIMEOUT_NEWS)
                    if r.status_code != 200:
                        continue
                    r.encoding = "gbk"
                    for line in r.text.strip().split("\n"):
                        if 'hq_str_' not in line:
                            continue
                        try:
                            raw_code = line.split('hq_str_')[1].split('=')[0]
                            data_part = line.split('"')[1] if '"' in line else ""
                            if not data_part:
                                continue
                            fields = data_part.split(",")
                            if len(fields) < 32:
                                continue
                            name = fields[0]
                            current = _to_float(fields[3])
                            pct = _to_float(fields[32]) if len(fields) > 32 else 0
                            volume = _to_float(fields[8])
                            amount = _to_float(fields[9])
                            if current and current > 0:
                                all_quotes.append({
                                    "code": raw_code[2:],
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

            if market == "gainers":
                sorted_q = sorted(all_quotes, key=lambda x: x.get("pct", 0), reverse=True)
            elif market == "losers":
                sorted_q = sorted(all_quotes, key=lambda x: x.get("pct", 0))
            else:
                sorted_q = sorted(all_quotes, key=lambda x: x.get("amount", 0), reverse=True)

            return sorted_q[:limit]
        except Exception as e:
            logger.warning("[Sina] market_top 失败: %s", e)
            return []

    def news(self, limit: int = 10) -> List[dict]:
        """获取财经新闻"""
        try:
            url = ("https://feed.mix.sina.com.cn/api/roll/get?"
                   "pageid=153&lid=2509&k=&num=50&page=1")
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn/",
            }
            r = requests.get(url, headers=headers, timeout=TIMEOUT_NEWS)
            if r.status_code != 200:
                return []
            data = r.json()
            if data.get("result") and data["result"].get("data"):
                news_list = []
                for item in data["result"]["data"][:limit]:
                    news_list.append({
                        "time": (item.get("ctime", "")[:10] if item.get("ctime") else ""),
                        "title": item.get("title", ""),
                        "source": item.get("media_name", ""),
                        "url": item.get("url", ""),
                    })
                return news_list
            return []
        except Exception as e:
            logger.warning("[Sina] news 失败: %s", e)
            return []

    def is_available(self) -> bool:
        """快速可用性检测（只请求一只股票）"""
        try:
            url = "https://hq.sinajs.cn/list=sh600519"
            r = requests.get(url, headers=_sina_headers(), timeout=3)
            return r.status_code == 200 and "hq_str_sh600519" in r.text
        except Exception:
            return False

    def health_check(self) -> bool:
        """完整健康检查"""
        return self.is_available()


# ═══════════════════════════════════════════════════════════
# 东方财富数据源（通过 akshare）
# ═══════════════════════════════════════════════════════════

class EastMoneyDataSource(BaseDataSource):
    """
    东方财富数据源（通过 akshare 实现）。
    akshare API:
        - stock_zh_a_spot_em()   实时行情（全部A股）
        - stock_zh_a_hist()       历史K线
        - stock_news_em()          新闻
        - stock_zh_a_change_em()   涨跌榜
    """

    name = "eastmoney"
    priority = 2

    def __init__(self):
        super().__init__()
        self._spot_cache = None
        self._spot_cache_time = 0
        self._spot_cache_ttl = 30  # 缓存30秒

    def realtime_quotes(self, codes: List[str]) -> List[dict]:
        """获取实时行情"""
        try:
            import akshare as ak
            now = time.time()
            # 缓存避免每次调用都请求全部A股（耗时太长）
            if self._spot_cache is None or (now - self._spot_cache_time) > self._spot_cache_ttl:
                df = ak.stock_zh_a_spot_em()
                self._spot_cache = df
                self._spot_cache_time = now
            else:
                df = self._spot_cache

            results = []
            for code in codes:
                code = str(code).strip().zfill(6)
                row = df[df["代码"] == code]
                if row.empty:
                    continue
                r = row.iloc[0]
                results.append({
                    "code": code,
                    "name": str(r.get("名称", "")),
                    "current": _to_float(r.get("最新价")),
                    "open": _to_float(r.get("今开")),
                    "prev_close": _to_float(r.get("昨收")),
                    "high": _to_float(r.get("最高")),
                    "low": _to_float(r.get("最低")),
                    "vol": _to_float(r.get("成交量")),
                    "amount": _to_float(r.get("成交额")),
                    "change": _to_float(r.get("涨跌额")),
                    "pct": _to_float(r.get("涨跌幅")),
                    "market": "A",
                    "source": "eastmoney",
                    "time": "",
                    "date": "",
                })
            return results
        except Exception as e:
            logger.warning("[EastMoney] realtime_quotes 失败: %s", e)
            return []

    def historical_kline(self, code: str, period: str = "daily") -> pd.DataFrame:
        """获取历史K线"""
        try:
            import akshare as ak
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly",
                          "60": "60", "30": "30", "15": "15", "5": "5"}
            ak_period = period_map.get(str(period), "daily")
            adjust = "qfq"

            df = ak.stock_zh_a_hist(symbol=code, period=ak_period, adjust=adjust, start_date="20180101")
            if df is not None and not df.empty:
                rename = {
                    "日期": "day", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                }
                df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
                for col in ["day", "open", "high", "low", "close", "volume"]:
                    if col not in df.columns:
                        df[col] = None
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                return df[["day", "open", "high", "low", "close", "volume"]].tail(120)
            return pd.DataFrame()
        except Exception as e:
            logger.warning("[EastMoney] historical_kline(%s) 失败: %s", code, e)
            return pd.DataFrame()

    def market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """获取涨跌榜（直连东方财富 push2 API，不依赖 akshare）"""
        try:
            # push2.eastmoney.com 是东方财富公开行情接口，无需 akshare
            base = "https://push2.eastmoney.com/api/qt/clist/get"
            if market == "gainers":
                fid, po = "f3", "0"  # 按涨跌幅降序
            elif market == "losers":
                fid, po = "f3", "1"  # 按涨跌幅升序
            else:
                fid, po = "f5", "0"  # 按成交额降序

            params = {
                "pn": "1",
                "pz": str(limit),
                "po": po,
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": fid,
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20",
            }
            r = requests.get(base, params=params, headers=_eastmoney_headers(), timeout=TIMEOUT_REALTIME)
            data = r.json().get("data")
            if not data:
                return []

            results = []
            for item in data.get("diff", []):
                results.append({
                    "code": str(item.get("f12", "")),
                    "name": str(item.get("f14", "")),
                    "price": _to_float(item.get("f2")),
                    "pct": _to_float(item.get("f3")),
                    "change": _to_float(item.get("f4")),
                    "amount": _to_float(item.get("f6")),
                    "volume": _to_float(item.get("f5")),
                    "high": _to_float(item.get("f15")),
                    "low": _to_float(item.get("f16")),
                    "open": _to_float(item.get("f17")),
                    "prev_close": _to_float(item.get("f18")),
                    "market": "A",
                })
            return results
        except Exception as e:
            logger.warning("[EastMoney] market_top 失败: %s", e)
            return []

    def news(self, limit: int = 10) -> List[dict]:
        """获取财经新闻（通过东方财富）"""
        try:
            import akshare as ak
            df = ak.stock_news_em(symbol="全球")
            if df is None or df.empty:
                return []
            news_list = []
            for _, r in df.head(limit).iterrows():
                news_list.append({
                    "time": str(r.get("发布时间", ""))[:10],
                    "title": str(r.get("新闻标题", "")),
                    "source": str(r.get("文章来源", "")),
                    "url": str(r.get("新闻链接", "")),
                })
            return news_list
        except Exception as e:
            logger.warning("[EastMoney] news 失败: %s", e)
            return []

    def is_available(self) -> bool:
        """快速检测东方财富是否可用"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            return df is not None and not df.empty
        except Exception:
            return False

    def health_check(self) -> bool:
        return self.is_available()


# ═══════════════════════════════════════════════════════════
# 雅虎财经数据源（通过 yfinance）
# ═══════════════════════════════════════════════════════════

class YahooDataSource(BaseDataSource):
    """
    雅虎财经数据源（通过 yfinance 实现）。
    yfinance 代码映射:
        沪市: 600519.SS
        深市: 000001.SZ
        港股: 00700.HK
    优势: 历史数据最完整，可获取数年数据
    """

    name = "yahoo"
    priority = 3

    def _map_code(self, code: str) -> str:
        """将A股/港股代码转为雅虎格式"""
        code = str(code).strip().zfill(6)
        if code.startswith(("6", "5")):
            return f"{code}.SS"  # Shanghai
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"  # Shenzhen
        elif code.startswith("7"):  # 简单假设7开头是港股
            return f"{code}.HK"
        return f"{code}.SS"

    def realtime_quotes(self, codes: List[str]) -> List[dict]:
        """获取实时行情（通过 ticker info，yfinance 对实时支持较弱）"""
        try:
            import yfinance as yf
            results = []
            for code in codes:
                try:
                    ycode = self._map_code(code)
                    ticker = yf.Ticker(ycode)
                    info = ticker.fast_info
                    if info is None:
                        continue
                    price = info.get("last_price") or info.get("previous_close")
                    prev = info.get("previous_close")
                    results.append({
                        "code": str(code).strip().zfill(6),
                        "name": str(ticker.info.get("shortName", "")),
                        "current": _to_float(price),
                        "open": _to_float(info.get("open")),
                        "prev_close": _to_float(prev),
                        "high": _to_float(info.get("day_high")),
                        "low": _to_float(info.get("day_low")),
                        "vol": _to_float(info.get("last_volume")),
                        "amount": None,
                        "change": round(price - prev, 2) if (price and prev) else None,
                        "pct": round((price / prev - 1) * 100, 2) if (price and prev) else None,
                        "market": "A",
                        "source": "yahoo",
                        "time": "",
                        "date": "",
                    })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.warning("[Yahoo] realtime_quotes 失败: %s", e)
            return []

    def historical_kline(self, code: str, period: str = "daily") -> pd.DataFrame:
        """获取历史K线（yfinance 的强项）"""
        try:
            import yfinance as yf

            period_map = {
                "daily": ("3mo", "1d"),
                "weekly": ("6mo", "1wk"),
                "monthly": ("2y", "1mo"),
                "60": (None, "60m"),
                "30": (None, "30m"),
                "15": (None, "15m"),
                "5": (None, "5m"),
            }
            cfg = period_map.get(str(period), ("3mo", "1d"))

            ycode = self._map_code(code)
            ticker = yf.Ticker(ycode)

            if cfg[0]:
                df = ticker.history(period=cfg[0], interval=cfg[1])
            else:
                df = ticker.history(period="7d", interval=cfg[1])

            if df is None or df.empty:
                return pd.DataFrame()

            df = df.reset_index()
            # yfinance 列名: Open, High, Low, Close, Volume
            rename = {
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume", "Datetime": "day",
            }
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            for col in ["day", "open", "high", "low", "close", "volume"]:
                if col not in df.columns:
                    df[col] = None
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            # 格式化日期
            if "day" in df.columns:
                df["day"] = df["day"].dt.strftime("%Y-%m-%d")
            return df[["day", "open", "high", "low", "close", "volume"]].tail(120)
        except Exception as e:
            logger.warning("[Yahoo] historical_kline(%s) 失败: %s", code, e)
            return pd.DataFrame()

    def market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """雅虎财经涨跌榜（通过 S&P 500 ETF 间接实现）"""
        # yfinance 不直接提供涨跌榜，这里返回空列表降级到其他源
        return []

    def news(self, limit: int = 10) -> List[dict]:
        """获取财经新闻"""
        try:
            import yfinance as yf
            # 获取主要指数的新闻作为替代
            tickers = ["^GSPC", "^HSI", "000001.SS"]
            news_list = []
            for ycode in tickers[:1]:
                try:
                    ticker = yf.Ticker(ycode)
                    news = ticker.news
                    if news:
                        for item in news[:limit]:
                            news_list.append({
                                "time": "",
                                "title": item.get("title", ""),
                                "source": item.get("publisher", ""),
                                "url": item.get("link", ""),
                            })
                except Exception:
                    continue
            return news_list[:limit]
        except Exception as e:
            logger.warning("[Yahoo] news 失败: %s", e)
            return []

    def is_available(self) -> bool:
        try:
            import yfinance as yf
            ticker = yf.Ticker("AAPL")
            info = ticker.fast_info
            return info is not None
        except Exception:
            return False

    def health_check(self) -> bool:
        return self.is_available()


# ═══════════════════════════════════════════════════════════
# 腾讯财经数据源
# ═══════════════════════════════════════════════════════════

class TencentDataSource(BaseDataSource):
    """
    腾讯财经数据源。
    API: http://qt.gtimg.cn/q=sh600519,sz000001
    返回格式类似新浪，但字段用 ~ 分隔，顺序不同。
    字段顺序（以sh600519为例）:
        0=name, 1=open, 2=prev_close, 3=current, 4=high, 5=low,
        6=buy1, 7=sell1, 8=vol, 9=amount, 10=...,
        30=date, 31=time, 32=pct(涨跌%), ...
    """

    name = "tencent"
    priority = 4

    HK_CODES = {
        "00700","09988","03690","01810","09618","09888","06618",
        "06160","02318","00941","00939","01398","00992","02628",
    }

    def _tencent_code(self, code: str) -> str:
        """将原始代码转为腾讯格式"""
        code = str(code).strip().zfill(6)
        if code.startswith(("6", "5")):
            return f"sh{code}"
        elif code in self.HK_CODES:
            return f"hk{code}"
        else:
            return f"sz{code}"

    def realtime_quotes(self, codes: List[str]) -> List[dict]:
        """获取实时行情"""
        if not codes:
            return []

        tc_codes = [self._tencent_code(c) for c in codes]
        url = "http://qt.gtimg.cn/q=" + ",".join(tc_codes)

        try:
            resp = requests.get(url, timeout=TIMEOUT_REALTIME)
            resp.encoding = "gbk"
            results = []
            lines = resp.text.strip().split("\n")

            for i, line in enumerate(lines):
                if '="";' in line or '=""' in line or "~" not in line:
                    continue
                try:
                    parts = line.split("~")
                    if len(parts) < 40:
                        continue
                    code = str(codes[i]).strip().zfill(6) if i < len(codes) else ""
                    current = _to_float(parts[3])
                    prev    = _to_float(parts[4])
                    open_p  = _to_float(parts[5])
                    high    = _to_float(parts[33])
                    low     = _to_float(parts[34])
                    vol     = _to_float(parts[6])
                    amount  = _to_float(parts[37])
                    pct     = _to_float(parts[32])
                    change  = round(current - prev, 2) if (current and prev) else None

                    results.append({
                        "code": code,
                        "name": parts[1],
                        "current": current,
                        "open": open_p,
                        "prev_close": prev,
                        "high": high,
                        "low": low,
                        "vol": vol,
                        "amount": amount,
                        "change": change,
                        "pct": pct,
                        "market": "HK" if code in self.HK_CODES else "A",
                        "source": "tencent",
                        "time": parts[30] if len(parts) > 30 else "",
                        "date": parts[29] if len(parts) > 29 else "",
                    })
                except Exception:
                    continue

            return results
        except Exception as e:
            logger.warning("[Tencent] realtime_quotes 失败: %s", e)
            return []

    def historical_kline(self, code: str, period: str = "daily") -> pd.DataFrame:
        """
        腾讯历史K线接口。
        注意: 腾讯历史K线 API 较复杂，此处降级返回空DataFrame，
        实际历史数据由其他数据源提供。
        """
        return pd.DataFrame()

    def market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """腾讯财经涨跌榜（暂不支持，返回空列表降级）"""
        return []

    def news(self, limit: int = 10) -> List[dict]:
        """腾讯财经新闻（暂不支持，返回空列表降级）"""
        return []

    def is_available(self) -> bool:
        try:
            url = "http://qt.gtimg.cn/q=sh600519"
            r = requests.get(url, timeout=3)
            return r.status_code == 200 and "~" in r.text
        except Exception:
            return False

    def health_check(self) -> bool:
        return self.is_available()


# ═══════════════════════════════════════════════════════════
# 多数据源管理器
# ═══════════════════════════════════════════════════════════

class DataSourceManager:
    """
    多数据源管理器。
    核心能力:
        1. 自动注册多个数据源
        2. 按优先级自动故障转移
        3. 统一接口，隐藏底层细节
        4. 健康状态监控与降级
        5. 数据去重与合并
    """

    # 连续失败多少次后暂时跳过该源
    FAIL_THRESHOLD = 3
    # 降级后多少秒恢复
    COOLDOWN_SECONDS = 30

    def __init__(self):
        self.sources: Dict[str, BaseDataSource] = {}
        # 健康状态: name -> {ok, last_ok, fail_count, last_fail_time}
        self.health: Dict[str, Dict[str, Any]] = {}
        # 各功能的偏好数据源优先级列表
        self.preference: Dict[str, List[str]] = {
            "realtime":   ["sina", "tencent", "eastmoney", "yahoo"],
            "historical": ["sina", "yahoo", "eastmoney"],
            "market_top": ["eastmoney", "sina"],
            "news":       ["sina", "eastmoney", "yahoo"],
        }

    def register(self, name: str, source: BaseDataSource) -> None:
        """注册一个数据源"""
        self.sources[name] = source
        self.health[name] = {
            "ok": True,
            "last_ok": time.time(),
            "fail_count": 0,
            "last_fail_time": 0,
        }
        logger.info("数据源注册: %s (priority=%d)", name, source.priority)

    def auto_register(self) -> None:
        """自动注册所有已知数据源"""
        self.register("sina",      SinaDataSource())
        self.register("eastmoney", EastMoneyDataSource())
        self.register("yahoo",     YahooDataSource())
        self.register("tencent",   TencentDataSource())
        logger.info("已自动注册 %d 个数据源", len(self.sources))

    def _is_degraded(self, name: str) -> bool:
        """检查数据源是否处于降级冷却期"""
        h = self.health.get(name)
        if not h:
            return True
        if h["fail_count"] >= self.FAIL_THRESHOLD:
            elapsed = time.time() - h["last_fail_time"]
            if elapsed < self.COOLDOWN_SECONDS:
                return True
            else:
                # 冷却结束，重置计数
                h["fail_count"] = 0
        return False

    def _mark_success(self, name: str) -> None:
        """标记数据源成功"""
        h = self.health.get(name)
        if h:
            h["ok"] = True
            h["last_ok"] = time.time()
            h["fail_count"] = 0

    def _mark_failure(self, name: str) -> None:
        """标记数据源失败"""
        h = self.health.get(name)
        if h:
            h["fail_count"] += 1
            h["last_fail_time"] = time.time()
            if h["fail_count"] >= self.FAIL_THRESHOLD:
                h["ok"] = False
                logger.warning(
                    "[%s] 连续失败 %d 次，进入 %ds 降级冷却期",
                    name, self.FAIL_THRESHOLD, self.COOLDOWN_SECONDS
                )

    def _get_ordered_sources(self, feature: str) -> List[str]:
        """获取某功能按优先级排序且未降级的数据源列表"""
        pref = self.preference.get(feature, list(self.sources.keys()))
        return [name for name in pref if name in self.sources and not self._is_degraded(name)]

    def get_realtime(self, codes: List[str]) -> List[dict]:
        """
        获取实时行情。
        按优先级尝试各数据源，直到成功。
        返回统一的行情列表。
        """
        if not codes:
            return []

        for name in self._get_ordered_sources("realtime"):
            src = self.sources[name]
            try:
                results = src.realtime_quotes(codes)
                if results:
                    self._mark_success(name)
                    # 补充 source 字段（如果数据源未设置）
                    for r in results:
                        r.setdefault("source", name)
                    logger.info("[%s] 实时行情成功，获取 %d 条", name, len(results))
                    return results
                else:
                    self._mark_failure(name)
            except Exception as e:
                logger.warning("[%s] 实时行情异常: %s", name, e)
                self._mark_failure(name)

        logger.error("所有数据源实时行情均失败: %s", codes)
        return []

    def get_historical(self, code: str, period: str = "daily") -> pd.DataFrame:
        """
        获取历史K线数据。
        尝试所有数据源，返回第一个成功且非空的结果。
        """
        for name in self._get_ordered_sources("historical"):
            src = self.sources[name]
            try:
                df = src.historical_kline(code, period)
                if df is not None and not df.empty:
                    self._mark_success(name)
                    logger.info("[%s] 历史K线(%s)成功，%d 条", name, code, len(df))
                    return df
                else:
                    self._mark_failure(name)
            except Exception as e:
                logger.warning("[%s] 历史K线(%s)异常: %s", name, code, e)
                self._mark_failure(name)

        logger.error("所有数据源历史K线均失败: %s", code)
        return pd.DataFrame()

    def get_market_top(self, market: str = "gainers", limit: int = 10) -> List[dict]:
        """
        获取涨跌榜。
        market: "gainers"(涨幅) | "losers"(跌幅) | "turnover"(成交额)
        """
        for name in self._get_ordered_sources("market_top"):
            src = self.sources[name]
            try:
                results = src.market_top(market, limit)
                if results:
                    self._mark_success(name)
                    logger.info("[%s] 涨跌榜(%s)成功，%d 条", name, market, len(results))
                    return results
                else:
                    self._mark_failure(name)
            except Exception as e:
                logger.warning("[%s] 涨跌榜异常: %s", name, e)
                self._mark_failure(name)

        logger.error("所有数据源涨跌榜均失败: market=%s", market)
        return []

    def get_news(self, limit: int = 10) -> List[dict]:
        """获取财经新闻"""
        for name in self._get_ordered_sources("news"):
            src = self.sources[name]
            try:
                results = src.news(limit)
                if results:
                    self._mark_success(name)
                    logger.info("[%s] 财经新闻成功，%d 条", name, len(results))
                    return results
                else:
                    self._mark_failure(name)
            except Exception as e:
                logger.warning("[%s] 财经新闻异常: %s", name, e)
                self._mark_failure(name)

        logger.error("所有数据源财经新闻均失败")
        return []

    def get_health_report(self) -> dict:
        """
        获取各数据源健康状态报告。
        返回格式:
        {
            "sina":      {"ok": True,  "fail_count": 0, "last_ok": timestamp, "degraded": False},
            "eastmoney": {"ok": False, "fail_count": 3, "last_ok": timestamp, "degraded": True},
            ...
        }
        """
        report = {}
        for name, h in self.health.items():
            degraded = self._is_degraded(name)
            src = self.sources.get(name)
            report[name] = {
                "ok":         h.get("ok", False),
                "fail_count": h.get("fail_count", 0),
                "last_ok":    h.get("last_ok", 0),
                "degraded":   degraded,
                "priority":   src.priority if src else 999,
                "available":  name in self.sources and not degraded,
            }
        return report

    def set_preference(self, feature: str, order: List[str]) -> None:
        """设置某功能的偏好数据源顺序"""
        self.preference[feature] = order


# ═══════════════════════════════════════════════════════════
# 全局单例管理器
# ═══════════════════════════════════════════════════════════

_manager: Optional[DataSourceManager] = None


def get_manager() -> DataSourceManager:
    """获取全局单例 DataSourceManager（延迟初始化）"""
    global _manager
    if _manager is None:
        _manager = DataSourceManager()
        _manager.auto_register()
    return _manager
