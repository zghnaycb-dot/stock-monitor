# -*- coding: utf-8 -*-
"""Simple strategy backtesting for A-share stocks"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Tuple
import plotly.graph_objects as go


def backtest_ma_cross(df: pd.DataFrame) -> Dict:
    """MA金叉死叉策略回测: MA5上穿MA20买入，下穿卖出"""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["signal"] = 0
    df.loc[df["ma5"] > df["ma20"], "signal"] = 1
    df.loc[df["ma5"] < df["ma20"], "signal"] = -1
    df["position"] = df["signal"].diff()
    df["buy"] = df["position"] == 2   # -1 -> 1 (金叉)
    df["sell"] = df["position"] == -2  # 1 -> -1 (死叉)
    return _calc_metrics(df, "MA金叉死叉")


def backtest_rsi(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> Dict:
    """RSI超买超卖策略回测"""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["signal"] = 0
    df["buy"] = df["rsi"] < oversold
    df["sell"] = df["rsi"] > overbought
    return _calc_metrics(df, f"RSI({oversold}/{overbought})")


def backtest_buy_hold(df: pd.DataFrame) -> Dict:
    """买入持有策略基准"""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df["buy"] = False
    df.loc[df.index[0], "buy"] = True
    df["sell"] = False
    df.loc[df.index[-1], "sell"] = True
    return _calc_metrics(df, "买入持有")


def _calc_metrics(df: pd.DataFrame, name: str) -> Dict:
    """计算回测指标"""
    capital = 100000
    cash = capital
    shares = 0
    trades = []
    equity_curve = []
    initial_price = df["close"].iloc[0] if len(df) > 0 else 1

    for i in range(len(df)):
        price = df["close"].iloc[i]
        if df["buy"].iloc[i] and cash > 0:
            shares = int(cash / price / 100) * 100
            cost = shares * price
            if shares > 0:
                cash -= cost
                trades.append({"type": "buy", "price": price, "shares": shares, "cost": cost})
        elif df["sell"].iloc[i] and shares > 0:
            proceeds = shares * price
            cash += proceeds
            trades.append({"type": "sell", "price": price, "shares": shares, "proceeds": proceeds})
            shares = 0
        equity = cash + shares * price
        equity_curve.append(equity)

    if not trades:
        return {"name": name, "trades": [], "final_equity": capital,
                "return": 0, "win_rate": 0, "max_dd": 0,
                "equity_curve": equity_curve, "initial": capital}

    final_equity = equity_curve[-1]
    total_return = (final_equity / capital - 1) * 100

    # 胜率
    wins = 0
    sell_trades = [t for t in trades if t["type"] == "sell"]
    for st_i in sell_trades:
        if st_i["proceeds"] > st_i.get("cost_basis", 0):
            wins += 1
    win_rate = round(wins / len(sell_trades) * 100, 1) if sell_trades else 0

    # 最大回撤
    peak = capital
    max_dd = 0
    for e in equity_curve:
        peak = max(peak, e)
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    return {
        "name": name, "trades": trades, "final_equity": final_equity,
        "return": total_return, "win_rate": win_rate, "max_dd": round(max_dd, 1),
        "equity_curve": equity_curve, "initial": capital,
    }


def render_backtest_tab(hist_df: pd.DataFrame, name: str) -> None:
    """渲染回测界面"""
    if hist_df.empty:
        st.warning("无历史数据可用于回测")
        return

    st.markdown("### 📊 策略回测")

    col1, col2 = st.columns([1, 2])

    with col1:
        strategy = st.radio(
            "回测策略",
            ["买入持有", "MA金叉死叉", "RSI超买超卖"],
            key="bt_strategy",
        )

    if strategy == "买入持有":
        result = backtest_buy_hold(hist_df)
    elif strategy == "MA金叉死叉":
        result = backtest_ma_cross(hist_df)
    else:
        result = backtest_rsi(hist_df)

    # 指标
    c1, c2, c3, c4 = st.columns(4)
    ret = result["return"]
    c1.metric("总收益率", f"{ret:.2f}%",
              delta=f"{ret:+.2f}%")
    c2.metric("胜率", f"{result['win_rate']}%")
    c3.metric("最大回撤", f"{result['max_dd']}%",
              delta=f"-{result['max_dd']}%")
    c4.metric("交易次数", len(result["trades"]))

    # 权益曲线
    if result["equity_curve"]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=result["equity_curve"],
            mode="lines",
            name="权益曲线",
            line=dict(color="#4d96ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(77, 150, 255, 0.1)",
        ))
        fig.add_hline(y=result["initial"], line_dash="dash", line_color="#888",
                      annotation_text="初始资金")
        fig.update_layout(
            template="plotly_white", height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis=dict(title="权益 (元)"),
            hovermode="x",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    # 交易明细
    if result["trades"]:
        with st.expander(f"交易明细 ({len(result['trades'])} 笔)", expanded=False):
            for t in result["trades"]:
                if t["type"] == "buy":
                    st.markdown(f"🟢 买入 @{t['price']:.2f} x {t['shares']}股 = {t['cost']:.0f}元")
                else:
                    st.markdown(f"🔴 卖出 @{t['price']:.2f} x {t['shares']}股 = {t['proceeds']:.0f}元")
