# -*- coding: utf-8 -*-
"""Plotly K-line chart with volume, MA, BOLL, and S/R levels"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, Dict


def render_kline_chart(
    hist_df: pd.DataFrame,
    code: str = "",
    name: str = "",
    sr_data: Optional[Dict] = None,
) -> None:
    """Render interactive K-line chart with overlays"""
    if hist_df.empty:
        st.warning("无历史数据可用于绘制K线图")
        return

    df = hist_df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in required):
        st.warning(f"历史数据缺少必要列: {required}")
        return

    # 日期列
    date_col = "day" if "day" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])

    # ── 图表选项 ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_ma = st.checkbox("均线 MA", value=True, key="kline_ma")
    with col2:
        show_boll = st.checkbox("布林带 BOLL", value=False, key="kline_boll")
    with col3:
        show_sr = st.checkbox("支撑/压力", value=False, key="kline_sr")
    with col4:
        days = st.selectbox("周期", [30, 60, 120, 250, 500],
                            index=2, key="kline_days",
                            label_visibility="collapsed")

    plot_df = df.tail(days)

    # ── 计算指标 ──
    if show_ma:
        for p in [5, 10, 20, 60]:
            if len(plot_df) >= p:
                plot_df[f"MA{p}"] = plot_df["close"].rolling(p).mean()

    if show_boll and len(plot_df) >= 20:
        plot_df["BOLL_MID"] = plot_df["close"].rolling(20).mean()
        std = plot_df["close"].rolling(20).std()
        plot_df["BOLL_UP"] = plot_df["BOLL_MID"] + 2 * std
        plot_df["BOLL_DN"] = plot_df["BOLL_MID"] - 2 * std

    # ── 创建子图 (K线 + 成交量) ──
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{name}({code}) K线图" if name else f"{code} K线图", "成交量"),
    )

    # ── K线 (Candlestick) ──
    colors = ["#dc3545" if plot_df["close"].iloc[i] >= plot_df["open"].iloc[i] else "#28a745"
              for i in range(len(plot_df))]
    fig.add_trace(
        go.Candlestick(
            x=plot_df[date_col],
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="K线",
            increasing_line_color="#dc3545",
            decreasing_line_color="#28a745",
            increasing_fillcolor="#dc3545",
            decreasing_fillcolor="#28a745",
        ),
        row=1, col=1,
    )

    # ── MA 均线 ──
    ma_colors = {5: "#ff6b6b", 10: "#ffd93d", 20: "#6bcb77", 60: "#4d96ff"}
    if show_ma:
        for p in [5, 10, 20, 60]:
            col_name = f"MA{p}"
            if col_name in plot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=plot_df[date_col],
                        y=plot_df[col_name],
                        mode="lines",
                        name=f"MA{p}",
                        line=dict(color=ma_colors.get(p, "#888"), width=1.2),
                        opacity=0.8,
                    ),
                    row=1, col=1,
                )

    # ── BOLL 布林带 ──
    if show_boll and "BOLL_UP" in plot_df.columns:
        boll_color = "rgba(128, 128, 128, 0.3)"
        # 上轨
        fig.add_trace(
            go.Scatter(
                x=plot_df[date_col], y=plot_df["BOLL_UP"],
                mode="lines", name="BOLL上轨",
                line=dict(color="#aaa", width=1, dash="dash"),
                opacity=0.6,
            ),
            row=1, col=1,
        )
        # 中轨
        fig.add_trace(
            go.Scatter(
                x=plot_df[date_col], y=plot_df["BOLL_MID"],
                mode="lines", name="BOLL中轨",
                line=dict(color="#888", width=1),
                opacity=0.6,
            ),
            row=1, col=1,
        )
        # 下轨
        fig.add_trace(
            go.Scatter(
                x=plot_df[date_col], y=plot_df["BOLL_DN"],
                mode="lines", name="BOLL下轨",
                line=dict(color="#aaa", width=1, dash="dash"),
                fill="tonexty", fillcolor=boll_color,
                opacity=0.6,
            ),
            row=1, col=1,
        )

    # ── S/R 支撑压力位 (水平线) ──
    if show_sr and sr_data:
        hlines = []
        for s in sr_data.get("supports", []):
            hlines.append({
                "y": s["price"], "color": "#28a745",
                "label": f"S: {s['label']} ({s['price']})"
            })
        for r in sr_data.get("resistances", []):
            hlines.append({
                "y": r["price"], "color": "#dc3545",
                "label": f"R: {r['label']} ({r['price']})"
            })
        for hl in hlines:
            fig.add_hline(
                y=hl["y"], line_dash="dot", line_color=hl["color"],
                line_width=1, opacity=0.7,
                annotation_text=hl["label"],
                annotation_position="right",
                annotation_font_size=10,
                row=1, col=1,
            )

    # ── 成交量柱状图 ──
    vol_colors = ["#dc3545" if plot_df["close"].iloc[i] >= plot_df["open"].iloc[i] else "#28a745"
                  for i in range(len(plot_df))]
    fig.add_trace(
        go.Bar(
            x=plot_df[date_col],
            y=plot_df["volume"] if "volume" in plot_df.columns else plot_df["vol"],
            name="成交量",
            marker_color=vol_colors,
            opacity=0.5,
            showlegend=False,
        ),
        row=2, col=1,
    )

    # ── 布局 ──
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(title="价格", showgrid=True, gridcolor="#eee"),
        xaxis2=dict(showgrid=False),
        yaxis2=dict(title="成交量", showgrid=False),
    )

    # 移除范围滑块默认的日期按钮
    fig.update_xaxes(rangeslider_visible=False)

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "displaylogo": False,
    })


def render_compare_chart(
    df1: pd.DataFrame, name1: str,
    df2: pd.DataFrame, name2: str,
    days: int = 120,
) -> None:
    """Render normalized comparison chart for two stocks"""
    if df1.empty or df2.empty:
        st.warning("数据不足，无法对比")
        return

    def normalize(df):
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        date_col = "day" if "day" in df.columns else df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        base = df["close"].iloc[0]
        df["norm"] = df["close"] / base * 100
        return df[[date_col, "norm"]].tail(days)

    n1 = normalize(df1)
    n2 = normalize(df2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=n1.iloc[:, 0], y=n1["norm"],
        mode="lines", name=name1,
        line=dict(color="#dc3545", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=n2.iloc[:, 0], y=n2["norm"],
        mode="lines", name=name2,
        line=dict(color="#4d96ff", width=2),
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="#888", opacity=0.5)
    fig.update_layout(
        template="plotly_white",
        height=400,
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(title="标准化价格 (100=基期)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
