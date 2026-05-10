# -*- coding: utf-8 -*-
"""支撑/压力位 - 自动计算关键价格水平 + 可视化"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from enhanced_source import calc_support_resistance
from data_source import get_historical_kline


def render_support_resistance_tab(sel_code: str, current_price: float):
    """渲染独立支撑/压力位分析 Tab"""
    st.markdown("#### 支撑/压力位全景分析")

    with st.spinner("计算多周期支撑/压力位..."):
        kd = get_historical_kline(sel_code, days=120)

    if kd.empty:
        st.warning("需要历史数据来计算支撑/压力位")
        return

    sr = calc_support_resistance(kd, current_price)

    if not sr or (not sr.get("supports") and not sr.get("resistances")):
        st.warning("数据不足，无法计算有效支撑/压力位")
        return

    supports = sr.get("supports", [])
    resistances = sr.get("resistances", [])

    # ── K线图 + 水平线标注 ──
    recent = kd.tail(90)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=recent["day"],
        open=recent["open"],
        high=recent["high"],
        low=recent["low"],
        close=recent["close"],
        name="K线",
        increasing=dict(line=dict(color="#dc3545"), fillcolor="#dc3545"),
        decreasing=dict(line=dict(color="#28a745"), fillcolor="#28a745"),
        showlegend=False,
    ))

    # 现价线
    fig.add_hline(
        y=current_price,
        line_dash="dash",
        line_color="#ffc107",
        line_width=2,
        annotation=dict(
            text=f"现价 {current_price:.2f}",
            font=dict(size=12, color="#ffc107"),
            bgcolor="rgba(0,0,0,0.6)",
        ),
        annotation_position="bottom right",
    )

    # 支撑位 (绿色实线)
    for s in supports:
        strength = s.get("strength", 1)
        fig.add_hline(
            y=s["price"],
            line_dash="dot",
            line_color="#28a745",
            line_width=1 + strength * 0.3,
            opacity=0.4 + strength * 0.15,
            annotation=dict(
                text=f"S {s['price']}",
                font=dict(size=9, color="#28a745"),
            ),
            annotation_position="left",
        )

    # 压力位 (红色实线)
    for r in resistances:
        strength = r.get("strength", 1)
        fig.add_hline(
            y=r["price"],
            line_dash="dot",
            line_color="#dc3545",
            line_width=1 + strength * 0.3,
            opacity=0.4 + strength * 0.15,
            annotation=dict(
                text=f"R {r['price']}",
                font=dict(size=9, color="#dc3545"),
            ),
            annotation_position="left",
        )

    # 轴心价
    if sr.get("pivot"):
        fig.add_hline(
            y=sr["pivot"],
            line_dash="dash",
            line_color="#6c757d",
            line_width=1.5,
            annotation=dict(
                text=f"Pivot {sr['pivot']:.2f}",
                font=dict(size=10, color="#6c757d"),
            ),
        )

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#eee"),
        yaxis=dict(showgrid=True, gridcolor="#eee"),
    )
    st.plotly_chart(fig, use_container_width=True, key="sr_chart")

    # ── 表格详情 ──
    col_s, col_r = st.columns(2)

    with col_s:
        st.markdown("#### 🟢 支撑位")
        if supports:
            sup_rows = []
            for s in supports[:6]:
                dist_pct = round(
                    (current_price - s["price"]) / current_price * 100, 2
                )
                sup_rows.append({
                    "价格": f"{s['price']:.2f}",
                    "来源": s["label"],
                    "距现价": f"-{dist_pct}%",
                    "强度": "⭐" * s.get("strength", 1),
                })
            st.dataframe(
                pd.DataFrame(sup_rows), hide_index=True, use_container_width=True
            )
        else:
            st.info("暂无有效支撑位")

    with col_r:
        st.markdown("#### 🔴 压力位")
        if resistances:
            res_rows = []
            for r in resistances[:6]:
                dist_pct = round(
                    (r["price"] - current_price) / current_price * 100, 2
                )
                res_rows.append({
                    "价格": f"{r['price']:.2f}",
                    "来源": r["label"],
                    "距现价": f"+{dist_pct}%",
                    "强度": "⭐" * r.get("strength", 1),
                })
            st.dataframe(
                pd.DataFrame(res_rows), hide_index=True, use_container_width=True
            )
        else:
            st.info("暂无有效压力位")

    # ── 多周期高低点 ──
    st.markdown("---")
    st.markdown("**多周期高低点**")

    closes = kd["close"].values
    highs = kd["high"].values
    lows = kd["low"].values

    periods = [
        ("20日（月线）", 20),
        ("60日（季线）", 60),
        ("120日（半年线）", 120),
    ]

    mc1, mc2, mc3 = st.columns(3)
    for idx, (label, n) in enumerate(periods):
        col = [mc1, mc2, mc3][idx]
        if len(closes) >= n:
            h = float(highs[-n:].max())
            l = float(lows[-n:].min())
            ma_v = float(closes[-n:].mean())
            with col:
                st.markdown(f"""
                <div style="background:#f8f9fa;border-radius:10px;padding:12px;text-align:center;">
                    <div style="font-size:12px;color:#888;">{label}</div>
                    <div style="font-size:15px;margin-top:4px;">
                        <span style="color:#dc3545;">高 {h:.2f}</span>
                        &nbsp;
                        <span style="color:#28a745;">低 {l:.2f}</span>
                    </div>
                    <div style="font-size:12px;color:#17a2b8;margin-top:4px;">均价 {ma_v:.2f}</div>
                    <div style="font-size:11px;color:#666;margin-top:2px;">
                        振幅 {(h-l)/l*100:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
