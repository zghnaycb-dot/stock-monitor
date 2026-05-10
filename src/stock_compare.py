# -*- coding: utf-8 -*-
"""Stock comparison tool - compare two stocks side by side"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


def render_compare_tab(
    quotes: List[Dict],
    get_tech_fn,
    get_bg_fn,
    get_hist_fn,
) -> None:
    """Render stock comparison tab"""
    if len(quotes) < 2:
        st.info("至少需要 2 只自选股才能对比")
        return

    st.markdown("### 📊 股票对比")

    col_a, col_b = st.columns(2)

    stock_opts = [f"{q.get('name', q['code'])} ({q['code']})" for q in quotes]

    with col_a:
        sel_a = st.selectbox("股票 A", stock_opts, key="cmp_a")
    with col_b:
        # Default to second stock
        default_idx = 1 if len(stock_opts) > 1 else 0
        sel_b = st.selectbox("股票 B", stock_opts, key="cmp_b", index=default_idx)

    code_a = sel_a.split("(")[-1].rstrip(")")
    code_b = sel_b.split("(")[-1].rstrip(")")
    name_a = sel_a.split(" (")[0]
    name_b = sel_b.split(" (")[0]

    if code_a == code_b:
        st.warning("请选择不同的两只股票")
        return

    # 获取行情
    q_a = next((q for q in quotes if q["code"] == code_a), {})
    q_b = next((q for q in quotes if q["code"] == code_b), {})

    # ── 指标对比 ──
    st.markdown("#### 关键指标对比")
    c1, c2, c3, c4, c5 = st.columns(5)

    metrics = [
        ("现价", lambda q: f"{q.get('current','---'):.2f}" if q.get("current") else "---"),
        ("涨跌幅", lambda q: f"{q.get('pct','---'):+.2f}%" if q.get("pct") is not None else "---"),
        ("涨跌额", lambda q: f"{q.get('change','---'):+.2f}" if q.get("change") is not None else "---"),
        ("今开", lambda q: f"{q.get('open','---'):.2f}" if q.get("open") else "---"),
        ("成交量", lambda q: f"{q.get('vol','---'):.0f}" if q.get("vol") else "---"),
    ]

    for col, (label, fn) in zip([c1, c2, c3, c4, c5], metrics):
        with col:
            st.caption(f"**{label}**")
            st.markdown(f"<span style='color:#dc3545'>{name_a}: {fn(q_a)}</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#4d96ff'>{name_b}: {fn(q_b)}</span>", unsafe_allow_html=True)

    # ── 技术指标对比 ──
    st.markdown("#### 技术指标对比")
    tech_a = get_tech_fn(code_a)
    tech_b = get_tech_fn(code_b)

    if tech_a and tech_b:
        t1, t2, t3, t4 = st.columns(4)

        # RSI
        rsi_a = tech_a.get("rsi", {}).get("14")
        rsi_b = tech_b.get("rsi", {}).get("14")
        with t1:
            st.metric(f"RSI(14) - {name_a}", f"{rsi_a:.2f}" if rsi_a else "---")
            st.metric(f"RSI(14) - {name_b}", f"{rsi_b:.2f}" if rsi_b else "---")

        # MACD
        macd_a = tech_a.get("macd", {})
        macd_b = tech_b.get("macd", {})
        with t2:
            st.metric(f"MACD - {name_a}",
                      f"{macd_a.get('DIF','---'):.4f}" if macd_a.get("DIF") else "---",
                      delta=macd_a.get("cross", ""))
            st.metric(f"MACD - {name_b}",
                      f"{macd_b.get('DIF','---'):.4f}" if macd_b.get("DIF") else "---",
                      delta=macd_b.get("cross", ""))

        # KDJ
        kdj_a = tech_a.get("kdj", {})
        kdj_b = tech_b.get("kdj", {})
        with t3:
            st.metric(f"KDJ-K - {name_a}", f"{kdj_a.get('K','---'):.2f}" if kdj_a.get("K") else "---")
            st.metric(f"KDJ-K - {name_b}", f"{kdj_b.get('K','---'):.2f}" if kdj_b.get("K") else "---")

        # BOLL
        boll_a = tech_a.get("boll", {})
        boll_b = tech_b.get("boll", {})
        with t4:
            st.metric(f"BOLL位置 - {name_a}",
                      f"{boll_a.get('pos_pct','---'):.0f}%" if boll_a.get("pos_pct") else "---")
            st.metric(f"BOLL位置 - {name_b}",
                      f"{boll_b.get('pos_pct','---'):.0f}%" if boll_b.get("pos_pct") else "---")

    # ── 归一化走势对比图 ──
    st.markdown("#### 走势叠加对比 (标准化 基期=100)")
    try:
        from kline_chart import render_compare_chart
        hist_a = get_hist_fn(code_a)
        hist_b = get_hist_fn(code_b)
        if not hist_a.empty and not hist_b.empty:
            render_compare_chart(hist_a, name_a, hist_b, name_b, days=120)
    except Exception as e:
        st.warning(f"生成对比图失败: {e}")
