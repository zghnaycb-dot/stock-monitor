# -*- coding: utf-8 -*-
"""市场情绪指标 - 涨跌家数、市场宽度、情绪仪表盘"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from enhanced_source import get_market_breadth


def render_market_sentiment():
    """渲染市场情绪 Tab（全景市场温度计）"""
    st.markdown("#### 市场情绪 & 市场宽度")

    with st.spinner("分析全市场数据..."):
        breadth = get_market_breadth()

    if not breadth:
        st.warning("市场数据暂不可用（请检查网络）")
        return

    # ═══ KPI 概览 ═══
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("上涨", breadth["up"])
    k2.metric("下跌", breadth["down"], delta_color="inverse")
    k3.metric("平盘", breadth["flat"])
    k4.metric("涨停", breadth["limit_up"])
    k5.metric("跌停", breadth["limit_down"], delta_color="inverse")
    k6.metric("上涨占比", f"{breadth['up_pct']}%")

    # ═══ 情绪仪表盘 ═══
    sentiment_color_map = {
        "🔥 亢奋": "#dc3545",
        "☀️ 偏暖": "#ff914d",
        "😐 中性": "#ffc107",
        "🌧️ 偏冷": "#4ecdc4",
        "❄️ 恐慌": "#28a745",
    }
    s_color = sentiment_color_map.get(breadth["sentiment"], "#888")

    c_left, c_right = st.columns([3, 2])

    with c_left:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=breadth["up_pct"],
            number={"suffix": "%", "font": {"size": 40}},
            title={"text": f"市场情绪温度计<br><span style='font-size:14px;color:{s_color};'>{breadth['sentiment']} — {breadth['sdesc']}</span>"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#666"},
                "bar": {"color": s_color, "thickness": 0.25},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#ddd",
                "steps": [
                    {"range": [0, 20], "color": "rgba(40,167,69,0.25)"},
                    {"range": [20, 40], "color": "rgba(78,205,196,0.25)"},
                    {"range": [40, 60], "color": "rgba(255,193,7,0.25)"},
                    {"range": [60, 80], "color": "rgba(255,145,77,0.25)"},
                    {"range": [80, 100], "color": "rgba(220,53,69,0.25)"},
                ],
            },
        ))
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True, key="sentiment_gauge")

    with c_right:
        # 涨跌饼图
        labels = ["上涨", "下跌", "平盘"]
        values = [breadth["up"], breadth["down"], breadth["flat"]]
        pie_colors = ["#dc3545", "#28a745", "#ccc"]

        fig2 = go.Figure(go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=pie_colors),
            textinfo="label+percent",
            hole=0.45,
            sort=False,
        ))
        fig2.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True, key="sentiment_pie")

        # 情绪卡片
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, {s_color}22, #f8f9fa);
                    border-radius:12px; padding:16px; text-align:center;
                    border:1px solid {s_color}44;">
            <div style="font-size:36px;font-weight:800;color:{s_color};">{breadth['up_pct']}%</div>
            <div style="font-size:13px;color:#666;margin-top:4px;">上涨占比</div>
            <div style="margin-top:12px;font-size:14px;line-height:1.8;">
                <b>涨停</b> {breadth['limit_up']} &nbsp;|&nbsp;
                <b>跌停</b> {breadth['limit_down']}
            </div>
            <div style="margin-top:10px;padding:8px;background:white;border-radius:6px;
                        font-size:12px;color:#555;line-height:1.5;">
                {breadth['sdesc']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ═══ 市场结构分析 ═══
    st.markdown("---")
    st.markdown("**市场结构分析**")

    c1, c2, c3 = st.columns(3)

    with c1:
        up_pct = breadth["up_pct"]
        if up_pct >= 60:
            trend_icon, trend_text = "📈 强势", "多头主导，积极布局"
        elif up_pct >= 40:
            trend_icon, trend_text = "↗️ 偏强", "震荡偏多，精选个股"
        elif up_pct >= 25:
            trend_icon, trend_text = "↔️ 平衡", "方向不明，等待信号"
        elif up_pct >= 15:
            trend_icon, trend_text = "↘️ 偏弱", "空头占优，控制仓位"
        else:
            trend_icon, trend_text = "📉 弱势", "恐慌情绪，防御为主"

        st.metric("趋势判断", trend_icon, delta=trend_text, delta_color="off")
        st.caption(f"上涨 {breadth['up']} / 下跌 {breadth['down']} / 平盘 {breadth['flat']}")

    with c2:
        lu_ld_ratio = "—"
        if breadth["limit_down"] > 0:
            r = breadth["limit_up"] / breadth["limit_down"]
            lu_ld_ratio = f"{r:.1f}x"
        elif breadth["limit_up"] > 0:
            lu_ld_ratio = "涨停碾压"
        st.metric("涨停/跌停比", lu_ld_ratio)

    with c3:
        adv_decline = 0
        if breadth["down"] > 0:
            adv_decline = round(breadth["up"] / breadth["down"], 2)
        elif breadth["up"] > 0:
            adv_decline = 999
        st.metric("腾落比", f"{adv_decline}x" if adv_decline != 999 else "∞",
                  delta="偏多" if adv_decline > 1 else ("偏空" if adv_decline < 1 else "均衡"),
                  delta_color="off")
