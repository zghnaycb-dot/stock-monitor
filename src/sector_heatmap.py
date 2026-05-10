# -*- coding: utf-8 -*-
"""板块/行业热力图 - Plotly 可视化行业板块涨跌表现"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from enhanced_source import get_sector_performance


def render_sector_heatmap():
    """渲染板块热力图 Tab（行业涨跌全景图）"""
    st.markdown("#### 行业板块全景图")

    with st.spinner("加载板块数据..."):
        sectors = get_sector_performance()

    if not sectors:
        st.warning("板块数据暂不可用（请检查网络）")
        return

    df = pd.DataFrame(sectors)
    valid = [s for s in sectors if s.get("pct") is not None]

    # ── 涨幅 Top 20 + 跌幅 Bottom 10 ──
    by_pct = sorted(valid, key=lambda x: x.get("pct", 0) or 0, reverse=True)
    top_n = by_pct[:20]
    bottom_n = by_pct[-10:] if len(by_pct) > 20 else []
    combined = top_n + bottom_n

    pcts = [s.get("pct", 0) or 0 for s in combined]
    names = [s["name"] for s in combined]
    colors_bar = ["#dc3545" if p >= 0 else "#28a745" for p in pcts]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pcts,
        y=names,
        orientation="h",
        marker_color=colors_bar,
        text=[f"{p:+.2f}%" for p in pcts],
        textposition="outside",
        hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(400, len(combined) * 22),
        margin=dict(l=10, r=60, t=10, b=10),
        xaxis_title="涨跌幅 (%)",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key="sector_bar")

    # ── 板块热力图 Treemap (面积=成交额, 颜色=涨跌幅) ──
    st.markdown("**板块热力图** (面积=成交额, 颜色=涨跌幅)")

    treemap_data = []
    for s in valid:
        t = s.get("turnover")
        if t and t > 0:
            treemap_data.append(s)

    if treemap_data:
        df_tree = pd.DataFrame(treemap_data)
        fig2 = px.treemap(
            df_tree,
            path=["name"],
            values="turnover",
            color="pct",
            color_continuous_scale=["#28a745", "#f5f5f5", "#dc3545"],
            color_continuous_midpoint=0,
            hover_data={
                "pct": ":.2f%",
                "turnover": ":,.0f 万",
                "lead_stock": True,
                "main_flow": ":,.0f 万",
            },
        )
        fig2.update_traces(
            textinfo="label+text+value",
            texttemplate="%{label}<br>%{color:.1f}%",
            textfont=dict(size=11),
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=520)
        st.plotly_chart(fig2, use_container_width=True, key="sector_tree")

    # ── 板块领涨股 Top 15 ──
    st.markdown("**领涨龙头股 Top 15**")

    leaders = sorted(
        valid, key=lambda x: (x.get("lead_pct") or 0), reverse=True
    )[:15]
    lead_rows = []
    for s in leaders:
        lead_rows.append({
            "板块": s["name"],
            "涨跌幅": f"{(s.get('pct') or 0):+.2f}%",
            "领涨股": s.get("lead_stock", "—"),
            "领涨%": f"{(s.get('lead_pct') or 0):+.2f}%",
            "上涨比": f"{s.get('rise_ratio', 0)}%",
            "成交额(万)": f"{(s.get('turnover') or 0):,.0f}",
            "主力净流入": f"{(s.get('main_flow') or 0):+,.0f} 万",
        })
    st.dataframe(
        pd.DataFrame(lead_rows),
        hide_index=True,
        use_container_width=True,
        height=500,
    )
