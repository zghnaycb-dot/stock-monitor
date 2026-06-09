# -*- coding: utf-8 -*-
"""
背离 & 分型检测模块 (30分钟级别)
=====================================
顶背离 / 底背离  +  顶分型 / 底分型

来自缠论：
  顶分型 = 相邻3根K线，中间K线高点为三者最高 → 潜在顶部
  底分型 = 相邻3根K线，中间K线低点为三者最低 → 潜在底部
背离：
  顶背离 = 价格创新高，MACD/RSI 未创新高 → 看跌
  底背离 = 价格创新低，MACD/RSI 未创新低 → 看涨
"""

import pandas as pd
import numpy as np
import akshare as ak
from typing import Optional, Dict, List, Tuple

# ── 30分钟K线获取 ──────────────────────────────────────────

def get_30min_kline(code: str, periods: int = 300) -> Optional[pd.DataFrame]:
    """
    获取30分钟K线数据（新浪分钟级接口，备用东方财富EM接口）
    code:  6位股票代码（如 000001）
    periods: 获取根数（默认300根≈60个交易日）
    返回: DataFrame with columns [open, close, high, low, volume, timestamp]
    """
    try:
        # 判断市场：sh/sz
        market = "sh" if code.startswith("6") else "sz"
        sym = market + code

        # 优先使用新浪接口（更稳定）
        df = None
        for _attempt in range(2):
            try:
                df = ak.stock_zh_a_minute(symbol=sym, period="30")
                break
            except Exception:
                pass

        # 新浪失败则尝试东方财富EM接口
        if (df is None or df.empty):
            try:
                df = ak.stock_zh_a_hist_min_em(
                    symbol=sym,
                    period="30",
                    adjust="qfq",
                )
            except Exception:
                pass

        if df is None or df.empty:
            return None

        # 标准化列名（不同版本 akshare 列名可能不同）
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if "时间" in c or "date" in cl or "timestamp" in cl or "day" in cl:
                col_map[c] = "timestamp"
            elif "开" in c or "open" in cl:
                col_map[c] = "open"
            elif "收" in c or "close" in cl:
                col_map[c] = "close"
            elif "高" in c or "high" in cl:
                col_map[c] = "high"
            elif "低" in c or "low" in cl:
                col_map[c] = "low"
            elif "量" in c or "volume" in cl:
                col_map[c] = "volume"
        df = df.rename(columns=col_map)

        # 确保数值列是 float
        for col in ["open", "close", "high", "low", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 时间列
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # 取最近 periods 根
        df = df.tail(periods).reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[divergence] get_30min_kline error: {e}")
        return None


# ── 分型检测（缠论定义）────────────────────────────────────

def detect_fractals(df: pd.DataFrame, min_gap: int = 3) -> Dict[str, List[dict]]:
    """
    检测顶分型 & 底分型（缠论严格定义）

    顶分型：连续3根K线 K1,K2,K3，满足
      high(K2) > high(K1) 且 high(K2) > high(K3)
      → K2 是中间位置(index=i)，实际检测 index i-1, i, i+1

    底分型：连续3根K线 K1,K2,K3，满足
      low(K2) < low(K1) 且 low(K2) < low(K3)

    min_gap: 两个分型之间最少间隔K线数（过滤过于密集的信号）
    """
    if df is None or df.empty or len(df) < 3:
        return {"top_fractals": [], "bottom_fractals": []}

    df = df.copy()
    highs = df["high"].values
    lows  = df["low"].values

    top_fractals   = []
    bottom_fractals = []

    last_top_idx   = -999
    last_bottom_idx = -999

    for i in range(1, len(df) - 1):
        # 顶分型
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            if i - last_top_idx >= min_gap:
                top_fractals.append({
                    "idx":       i,
                    "price":     round(highs[i], 2),
                    "timestamp": df.iloc[i].get("timestamp", i),
                    "type":      "顶分型",
                })
                last_top_idx = i

        # 底分型
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            if i - last_bottom_idx >= min_gap:
                bottom_fractals.append({
                    "idx":       i,
                    "price":     round(lows[i], 2),
                    "timestamp": df.iloc[i].get("timestamp", i),
                    "type":      "底分型",
                })
                last_bottom_idx = i

    return {
        "top_fractals":    top_fractals,
        "bottom_fractals": bottom_fractals,
    }


# ── 技术指标计算 ──────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI 相对强弱指数"""
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(series: pd.Series,
                 fast: int = 12, slow: int = 26, signal: int = 9
                 ) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """返回 (DIF, DEA, MACD柱)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    bar = (dif - dea) * 2.0
    return dif, dea, bar


# ── 背离检测 ──────────────────────────────────────────────

def detect_divergence(df: pd.DataFrame,
                      lookback: int = 80) -> Dict[str, List[dict]]:
    """
    检测顶背离 & 底背离（基于价格高点/低点 + MACD DIF + RSI）

    顶背离：最近若干K线内，价格创新高，但 MACD DIF 或 RSI 未创新高
    底背离：最近若干K线内，价格创新低，但 MACD DIF 或 RSI 未创新低
    """
    if df is None or df.empty or len(df) < lookback:
        return {"top_divergence": [], "bottom_divergence": []}

    df = df.copy().tail(lookback).reset_index(drop=True)

    # 计算指标
    df["rsi"]      = compute_rsi(df["close"], 14)
    dif, dea, bar  = compute_macd(df["close"])
    df["macd_dif"] = dif
    df["macd_dea"]  = dea
    df["macd_bar"]  = bar

    top_div    = []
    bottom_div = []

    # ── 找价格高点（局部极大值）────────────────────────────
    for i in range(5, len(df) - 5):
        # 局部高点：i 是周围10根K线的最高价
        if df.loc[i, "high"] == df["high"].iloc[i-5:i+6].max():
            # 找前一个高点
            for j in range(i - 10, 0, -1):
                if df.loc[j, "high"] == df["high"].iloc[max(0, j-5):j+6].max():
                    # 价格创新高，指标未创新高 → 顶背离
                    if (df.loc[i, "high"] > df.loc[j, "high"] and
                        (df.loc[i, "macd_dif"] < df.loc[j, "macd_dif"] or
                         df.loc[i, "rsi"]       < df.loc[j, "rsi"])):
                        top_div.append({
                            "idx":         i,
                            "price":       round(df.loc[i, "high"], 2),
                            "macd_dif":    round(df.loc[i, "macd_dif"], 4),
                            "rsi":         round(df.loc[i, "rsi"], 2),
                            "prev_price":  round(df.loc[j, "high"], 2),
                            "prev_macd":   round(df.loc[j, "macd_dif"], 4),
                            "prev_rsi":    round(df.loc[j, "rsi"], 2),
                            "timestamp":   df.loc[i].get("timestamp", i),
                            "prev_idx":    j,
                        })
                    break

    # ── 找价格低点（局部极小值）────────────────────────────
    for i in range(5, len(df) - 5):
        if df.loc[i, "low"] == df["low"].iloc[i-5:i+6].min():
            for j in range(i - 10, 0, -1):
                if df.loc[j, "low"] == df["low"].iloc[max(0, j-5):j+6].min():
                    # 价格创新低，指标未创新低 → 底背离
                    if (df.loc[i, "low"] < df.loc[j, "low"] and
                        (df.loc[i, "macd_dif"] > df.loc[j, "macd_dif"] or
                         df.loc[i, "rsi"]       > df.loc[j, "rsi"])):
                        bottom_div.append({
                            "idx":         i,
                            "price":       round(df.loc[i, "low"], 2),
                            "macd_dif":    round(df.loc[i, "macd_dif"], 4),
                            "rsi":         round(df.loc[i, "rsi"], 2),
                            "prev_price":  round(df.loc[j, "low"], 2),
                            "prev_macd":   round(df.loc[j, "macd_dif"], 4),
                            "prev_rsi":    round(df.loc[j, "rsi"], 2),
                            "timestamp":   df.loc[i].get("timestamp", i),
                            "prev_idx":    j,
                        })
                    break

    return {
        "top_divergence":    top_div[-8:],    # 最多返回最近8个
        "bottom_divergence": bottom_div[-8:],
    }


# ── Streamlit 渲染 ──────────────────────────────────────────

def render_divergence_tab(code: str, name: str, current_price: float = 0):
    """
    在 Streamlit Tab 中渲染 30分钟级别背离 & 分型分析结果。
    调用方式：render_divergence_tab(sel_code, sel_name, current_price)
    """
    import streamlit as st

    st.markdown(f"### 🔍 30分钟级别 · 顶底背离 & 分型分析")
    st.caption(f"股票：**{name}**（`{code}`）| 周期：30分钟 | 当前价：{current_price:.2f}" if current_price else
               f"股票：**{name}**（`{code}`）| 周期：30分钟")

    with st.spinner("正在获取30分钟K线数据..."):
        df = get_30min_kline(code, periods=300)

    if df is None or df.empty:
        st.error("⚠️ 无法获取30分钟K线数据，请检查股票代码或网络（需要 akshare 能访问东方财富）")
        return

    # 计算指标（供图表使用）
    df = df.copy()
    df["rsi"] = compute_rsi(df["close"], 14)
    dif, dea, bar = compute_macd(df["close"])
    df["macd_dif"]  = dif
    df["macd_dea"]  = dea
    df["macd_bar"]  = bar

    fractals   = detect_fractals(df, min_gap=3)
    divergence = detect_divergence(df, lookback=100)

    # ── 信号汇总 ──────────────────────────────────────
    n_top    = len(fractals["top_fractals"])
    n_bottom = len(fractals["bottom_fractals"])
    n_top_div    = len(divergence["top_divergence"])
    n_bottom_div = len(divergence["bottom_divergence"])

    sig_cols = st.columns(4)
    with sig_cols[0]:
        st.metric("🔺 顶分型", n_top)
    with sig_cols[1]:
        st.metric("🔻 底分型", n_bottom)
    with sig_cols[2]:
        st.metric("🔴 顶背离", n_top_div)
    with sig_cols[3]:
        st.metric("🟢 底背离", n_bottom_div)

    # 综合预警
    if n_top_div > 0:
        st.error(f"⚠️ **顶背离预警**：发现 {n_top_div} 处顶背离信号，价格可能见顶回落！")
    if n_bottom_div > 0:
        st.success(f"✅ **底背离机会**：发现 {n_bottom_div} 处底背离信号，价格可能见底反弹！")

    st.markdown("---")

    # ── 左侧：分型  |  右侧：背离 ────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 🔺 顶分型（潜在顶部反转）")
        tops = fractals["top_fractals"]
        if tops:
            for t in tops[-10:]:
                ts = t["timestamp"]
                ts_str = ts.strftime("%m-%d %H:%M") if hasattr(ts, "strftime") else f"K线#{t['idx']}"
                st.markdown(f"- `{ts_str}` 高点 **{t['price']}**")
        else:
            st.caption("暂无顶分型信号")

        st.markdown("#### 🔻 底分型（潜在底部反转）")
        bottoms = fractals["bottom_fractals"]
        if bottoms:
            for b in bottoms[-10:]:
                ts = b["timestamp"]
                ts_str = ts.strftime("%m-%d %H:%M") if hasattr(ts, "strftime") else f"K线#{b['idx']}"
                st.markdown(f"- `{ts_str}` 低点 **{b['price']}**")
        else:
            st.caption("暂无底分型信号")

    with col_right:
        st.markdown("#### 🔴 顶背离（看跌）")
        top_div = divergence["top_divergence"]
        if top_div:
            for d in top_div:
                st.markdown(
                    f"**K线#{d['idx']}** 价={d['price']}  "
                    f"DIF={d['macd_dif']}（前高{d['prev_macd']}） "
                    f"RSI={d['rsi']}（前高{d['prev_rsi']}）\n"
                    f"→ ⚠️ **顶背离，警惕下跌**"
                )
        else:
            st.caption("暂无顶背离信号")

        st.markdown("#### 🟢 底背离（看涨）")
        bottom_div = divergence["bottom_divergence"]
        if bottom_div:
            for d in bottom_div:
                st.markdown(
                    f"**K线#{d['idx']}** 价={d['price']}  "
                    f"DIF={d['macd_dif']}（前低{d['prev_macd']}） "
                    f"RSI={d['rsi']}（前低{d['prev_rsi']}）\n"
                    f"→ ✅ **底背离，关注反弹**"
                )
        else:
            st.caption("暂无底背离信号")

    # ── K线图（Plotly）──────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 30分钟K线图（标注分型 & 背离）")

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.72, 0.28],
            subplot_titles=("30分钟K线", "MACD"),
        )

        # ---- 主图：K线 ----
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="30min K线",
                increasing_line_color="#e63946",   # A股红涨
                decreasing_line_color="#2a9d8f",   # A股绿跌
            ),
            row=1, col=1,
        )

        # 顶分型标注
        for t in fractals["top_fractals"]:
            fig.add_annotation(
                x=t["idx"], y=df.loc[t["idx"], "high"],
                text="顶", showarrow=True, arrowhead=2,
                arrowcolor="red", font=dict(color="red", size=10),
                row=1, col=1,
            )

        # 底分型标注
        for b in fractals["bottom_fractals"]:
            fig.add_annotation(
                x=b["idx"], y=df.loc[b["idx"], "low"],
                text="底", showarrow=True, arrowhead=2,
                arrowcolor="green", font=dict(color="green", size=10),
                ay=15,
                row=1, col=1,
            )

        # 顶背离标注
        for d in divergence["top_divergence"]:
            fig.add_annotation(
                x=d["idx"], y=df.loc[d["idx"], "high"],
                text="🔴顶背离", showarrow=True, arrowhead=2,
                arrowcolor="#dc3545", font=dict(color="#dc3545", size=9),
                ay=-25,
                row=1, col=1,
            )

        # 底背离标注
        for d in divergence["bottom_divergence"]:
            fig.add_annotation(
                x=d["idx"], y=df.loc[d["idx"], "low"],
                text="🟢底背离", showarrow=True, arrowhead=2,
                arrowcolor="#28a745", font=dict(color="#28a745", size=9),
                ay=25,
                row=1, col=1,
            )

        # ---- 副图：MACD ----
        colors = ["#e63946" if v >= 0 else "#2a9d8f" for v in df["macd_bar"]]
        fig.add_trace(
            go.Bar(x=df.index, y=df["macd_bar"], name="MACD柱", marker_color=colors),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["macd_dif"], mode="lines", name="DIF",
                       line=dict(color="#f4a261", width=1.5)),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df["macd_dea"], mode="lines", name="DEA",
                       line=dict(color="#2a9d8f", width=1.5)),
            row=2, col=1,
        )

        fig.update_layout(
            height=720,
            xaxis_rangeslider_visible=False,
            plot_bgcolor="#f8f9fa",
            paper_bgcolor="#f8f9fa",
            font=dict(family="Noto Sans SC, Microsoft YaHei, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(showgrid=True, gridcolor="#e9ecef", row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#e9ecef", row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#e9ecef", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("⚠️ 需要安装 `plotly` 才能显示K线图：`pip install plotly`")
    except Exception as e:
        st.warning(f"绘图失败：{e}")

    st.caption("💡 分型定义（缠论）：顶分型=中间K线高点 > 左右邻K高点；底分型=中间K线低点 < 左右邻K低点")
    st.caption("💡 背离定义：顶背离=价格新高但指标未新高；底背离=价格新低但指标未新低")
