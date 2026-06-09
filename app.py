# -*- coding: utf-8 -*-
"""
A股/港股 股票监控分析系统 v3 (Clean)
自选股管理 + 实时行情 + 技术分析 + 智能信号 + AI分析

启动：
    cd stock-monitor
    streamlit run app.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import pandas as pd
from datetime import datetime, date
import streamlit.components.v1 as components
from typing import Dict, List, Optional
from datetime import datetime

# ── 自选股持久化文件路径 ──────────────────────────────────
_WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")

def _load_watchlist() -> list:
    """从文件加载自选股列表，文件不存在或损坏时返回默认列表"""
    if os.path.exists(_WATCHLIST_FILE):
        try:
            with open(_WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and all(isinstance(x, str) for x in data):
                    return data
        except (json.JSONDecodeError, IOError):
            pass
    # 默认列表
    return ["000001", "600519", "000858", "601318", "600036"]

def _save_watchlist(codes: list):
    """保存自选股列表到文件"""
    try:
        with open(_WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(codes, f, ensure_ascii=False, indent=2)
    except IOError as e:
        st.error(f"保存自选股失败: {e}")

def _get_watchlist() -> list:
    """从 session_state 读取，自选股第一次加载时从文件恢复"""
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = _load_watchlist()
    return st.session_state["watchlist"]

def _add_to_watchlist(code: str):
    """添加股票到自选股并保存"""
    wl = _get_watchlist()
    c = code.strip().zfill(6)
    if c not in wl:
        wl.append(c)
        st.session_state["watchlist"] = wl
        _save_watchlist(wl)
        return True
    return False

def _remove_from_watchlist(code: str):
    """从自选股删除并保存"""
    wl = _get_watchlist()
    if code in wl:
        wl.remove(code)
        st.session_state["watchlist"] = wl
        _save_watchlist(wl)
        return True
    return False

import config
from data_source import (
    get_realtime_quotes,
    get_technical_indicators,
    get_background_info,
    get_market_top,
    get_stock_news,
    generate_signals,
    generate_dayt_suggestion,
)
try:
    from data_source import get_manager as _get_source_mgr
    _source_mgr = _get_source_mgr()
    HAS_MULTI_SOURCE = True
except Exception:
    HAS_MULTI_SOURCE = False
    _source_mgr = None
from ai_client import get_ai_client
from enhanced_source import get_capital_flow, get_sector_performance, get_market_breadth, calc_support_resistance
from kline_chart import render_kline_chart, render_compare_chart
from backtest import render_backtest_tab
from alerts import load_alerts, check_alerts, add_alert, delete_alert, render_alerts_sidebar
from stock_compare import render_compare_tab
from sector_heatmap import render_sector_heatmap
from market_sentiment import render_market_sentiment
from support_resistance import render_support_resistance_tab
from divergence import render_divergence_tab

# ── 页面设置 ───────────────────────────────────────────────
st.set_page_config(
    page_title="📈 股票监控",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
    * { font-family: 'Noto Sans SC', 'Microsoft YaHei', 'Segoe UI', sans-serif !important; }
    .up   { color:#e63946; font-weight:700; }   /* 上涨=红 */
    .down { color:#2a9d8f; font-weight:700; }   /* 下跌=绿 */
    .flat { color:#888; }
    .mkt-badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.72rem; font-weight:700; }
    .mkt-a   { background:#e63946; color:white; }
    .mkt-hk  { background:#2a9d8f; color:white; }
    .card { background:#f8f9fa; border-radius:12px; padding:16px; margin:6px 0; border:1px solid #eee; }
    .signal-buy   { background:#d4edda; border-left:5px solid #28a745; padding:10px 14px; border-radius:4px; margin:6px 0; }
    .signal-sell  { background:#f8d7da; border-left:5px solid #dc3545; padding:10px 14px; border-radius:4px; margin:6px 0; }
    .signal-hold  { background:#fff3cd; border-left:5px solid #ffc107; padding:10px 14px; border-radius:4px; margin:6px 0; }
    footer { visibility:hidden; }
    .ai-box { background:#f8f9fa; border-radius:12px; padding:18px; border:1px solid #dee2e6; }
    .stTabs [data-baseweb="tab-list"] { gap:4px; }
    div[data-testid="stHorizontalBlock"] { gap:8px; }
</style>
""", unsafe_allow_html=True)


# ── 辅助函数 ──────────────────────────────────────────────

def color_pct(v):
    """涨跌颜色：A股红涨绿跌"""
    if v is None: return "#888"
    return "#e63946" if v > 0 else ("#2a9d8f" if v < 0 else "#888")

def pct_str(v):
    if v is None: return "—"
    return f"+{v:.2f}%" if v > 0 else f"{v:.2f}%"

def mkt_tag(mkt):
    if mkt == "HK":
        return '<span class="mkt-badge mkt-hk">港股</span>'
    return '<span class="mkt-badge mkt-a">A股</span>'

def score_color(s):
    if s >= 50: return "#28a745"
    if s >= 20: return "#6cbf7a"
    if s >= -20: return "#ffc107"
    if s >= -50: return "#fd7e14"
    return "#dc3545"

def make_html_table(df, pct_col="Change%", pct_cols=None):
    """
    将 DataFrame 渲染为带颜色的 HTML 表格
    pct_col: 要着色的列名（填 None 则整行着色）
    """
    html = '<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">'

    # 表头
    html += "<thead><tr>"
    for col in df.columns:
        html += f'<th style="text-align:left;padding:8px 12px;background:#f1f3f5;border-bottom:2px solid #dee2e6;color:#495057;">{col}</th>'
    html += "</tr></thead>"

    # 数据行
    html += "<tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]
            # 判断是否是百分比列
            is_pct = (pct_cols and col in pct_cols) or (pct_col and col == pct_col)
            if is_pct and isinstance(val, (int, float)):
                color = color_pct(val)
                html += f'<td style="padding:8px 12px;border-bottom:1px solid #eee;color:{color};font-weight:600;">{pct_str(val)}</td>'
            elif isinstance(val, (int, float)):
                html += f'<td style="padding:8px 12px;border-bottom:1px solid #eee;">{val:.2f}</td>'
            else:
                html += f'<td style="padding:8px 12px;border-bottom:1px solid #eee;">{val}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html


# ── 缓存 ─────────────────────────────────────────────────

@st.cache_data(ttl=30)
def cached_quotes(codes):
    return get_realtime_quotes(codes)

@st.cache_data(ttl=300)
def cached_tech(code):
    return get_technical_indicators(code)

@st.cache_data(ttl=3600)
def cached_bg(code):
    return get_background_info(code)


# ══════════════════════════════════════════════════════════
#  侧边栏：自选股管理
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⭐ 自选股管理")
    st.caption("⚡ Pro — 8大功能模块")

    # 当前自选股行情预览（从持久化文件读取）
    favs = _get_watchlist()
    fav_quotes = cached_quotes(favs) if favs else []
    render_alerts_sidebar(fav_quotes if fav_quotes else [])

    if fav_quotes:
        st.markdown("**实时行情预览**")
        preview_rows = []
        for q in fav_quotes:
            pct = q.get("pct")
            current = q.get("current")
            preview_rows.append({
                "Name": q.get("name", q["code"]),
                "Price": f"{current:.2f}" if current else "—",
                "Change%": pct,
            })
        preview_df = pd.DataFrame(preview_rows)
        st.markdown(
            make_html_table(preview_df, pct_col="Change%"),
            unsafe_allow_html=True,
        )
        st.caption(f"共 {len(fav_quotes)} 只 | 自动刷新 30s | 数据持久化 ✅")
    else:
        st.info("暂无自选股，请添加")

    st.markdown("---")

    # 添加股票
    st.markdown("### ➕ 添加股票")
    new_code = st.text_input(
        "股票代码",
        placeholder="例如：000001",
        label_visibility="collapsed",
        key="add_code_input",
    )
    col_btns = st.columns(2)
    with col_btns[0]:
        if st.button("添加", use_container_width=True, key="add_btn"):
            c = new_code.strip().zfill(6)
            if c.isdigit() and len(c) == 6:
                added = _add_to_watchlist(c)
                if added:
                    st.rerun()
                else:
                    st.warning("已在自选列表中")
            else:
                st.error("请输入6位股票代码")

    with col_btns[1]:
        if st.button("📋 常用A股", use_container_width=True):
            defaults = ["000001", "600519", "000858", "601318", "600036"]
            for c in defaults:
                _add_to_watchlist(c)
            st.rerun()

    # 快捷添加港股
    with st.expander("➕ 快捷添加港股"):
        hk_stocks = [("00700", "腾讯控股"), ("09988", "阿里巴巴"), ("03690", "美团"),
                     ("01810", "小米集团"), ("09618", "京东健康")]
        for code, name in hk_stocks:
            col_hk = st.columns([1, 2])
            with col_hk[0]:
                st.caption(f"{code}")
            with col_hk[1]:
                if st.button(f"+ {name}", key=f"hk_{code}", use_container_width=True):
                    _add_to_watchlist(code)
                    st.rerun()

    # 删除股票
    st.markdown("---")
    st.markdown("### 🗑️ 删除股票")
    if favs:
        remove_options = [""] + favs
        rem = st.selectbox("选择要删除的股票", remove_options, label_visibility="collapsed", key="rem_select")
        if rem and st.button("删除", key="del_btn"):
            _remove_from_watchlist(rem)
            st.rerun()
    else:
        st.caption("暂无自选股")

    st.markdown("---")
    show_news  = st.checkbox("📰 财经新闻", value=True)
    auto_refresh = st.checkbox("🔄 自动刷新 (30s)", value=False)
    if auto_refresh:
        sec = st.slider("间隔(秒)", 5, 120, 30, 5, label_visibility="collapsed")
        st.components.v1.html(f'<script>setTimeout(function(){{window.parent.location.reload();}}, {sec*1000});</script>', height=0)

    st.markdown("---")
    st.caption(f"更新时间：{datetime.now().strftime('%H:%M:%S')}")


# ══════════════════════════════════════════════════════════
#  主界面
# ══════════════════════════════════════════════════════════

st.markdown("## 📈 股票监控分析系统")

# 刷新按钮
col_header = st.columns([1, 6, 1])
with col_header[0]:
    st.markdown(f"**{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
with col_header[2]:
    if st.button("🔄 刷新数据"):
        st.rerun()

# ── 自选股实时行情表格 ───────────────────────────────────
st.markdown("### 📊 自选股实时行情")

codes = _get_watchlist()
quotes = cached_quotes(codes) if codes else []

if quotes:
    rows = []
    for q in quotes:
        pct = q.get("pct")
        rows.append({
            "Market": q.get("market", "A"),
            "Name": q.get("name", q["code"]),
            "Code": q["code"],
            "Price": q.get("current"),
            "Change%": pct,
            "Change": q.get("change"),
            "Open": q.get("open"),
            "High": q.get("high"),
            "Low": q.get("low"),
            "PrevClose": q.get("prev_close"),
            "Vol": q.get("vol"),
            "Amount": q.get("amount"),
        })

    df = pd.DataFrame(rows)

    # 显示表格：市场、名称、现价、涨跌幅、成交量、成交额
    disp = pd.DataFrame({
        "市场": ["港股" if r.get("market") == "HK" else "A股" for r in rows],
        "名称": [r["Name"] for r in rows],
        "代码": [r["Code"] for r in rows],
        "现价": [f"{r['Price']:.2f}" if r.get("Price") else "—" for r in rows],
        "涨跌幅": [r["Change%"] for r in rows],
        "涨跌额": [f"{r['Change']:.2f}" if r.get("Change") else "—" for r in rows],
        "今开": [f"{r['Open']:.2f}" if r.get("Open") else "—" for r in rows],
        "最高": [f"{r['High']:.2f}" if r.get("High") else "—" for r in rows],
        "最低": [f"{r['Low']:.2f}" if r.get("Low") else "—" for r in rows],
        "昨收": [f"{r['PrevClose']:.2f}" if r.get("PrevClose") else "—" for r in rows],
    })

    st.markdown(
        make_html_table(disp, pct_col="涨跌幅"),
        unsafe_allow_html=True,
    )
else:
    st.info("自选股列表为空，请在侧边栏添加股票代码")

# ── 涨跌榜（折叠）───────────────────────────────────────
with st.expander("📈 A股涨跌榜", expanded=False):
    market_col1, market_col2 = st.columns(2)

    with market_col1:
        mkt_type = st.radio("选择榜单", ["涨幅榜", "跌幅榜", "成交额"],
                             label_visibility="collapsed", horizontal=True)

    if mkt_type == "涨幅榜":
        st.markdown("**涨幅 Top 15**")
        data = get_market_top(market="gainers", limit=15)
    elif mkt_type == "跌幅榜":
        st.markdown("**跌幅 Top 15**")
        data = get_market_top(market="losers", limit=15)
    else:
        st.markdown("**成交额 Top 15**")
        data = get_market_top(market="turnover", limit=15)

    if data:
        mkt_rows = []
        for r in data:
            pct = r.get("pct")
            amount = r.get("amount")
            mkt_rows.append({
                "名称": r.get("name", r.get("code", "—")),
                "代码": r.get("code", "—"),
                "现价": f"{r.get('price', '—'):.2f}" if r.get("price") else "—",
                "涨跌幅": pct,
                "成交额(万)": f"{amount/10000:.0f}" if amount else "—",
                "换手率(%)": f"{r.get('turnover', 0):.2f}" if r.get("turnover") else "—",
            })
        mkt_df = pd.DataFrame(mkt_rows)
        st.markdown(
            make_html_table(mkt_df, pct_col="涨跌幅"),
            unsafe_allow_html=True,
        )
    else:
        st.warning("暂无数据，请检查网络连接")

# ── 数据源状态 ──────────────────────────────────────────
if HAS_MULTI_SOURCE and _source_mgr:
    with st.expander("📊 数据源状态", expanded=False):
        report = _source_mgr.get_health_report()
        src_cols = st.columns(len(report))
        for i, (name, status) in enumerate(report.items()):
            with src_cols[i]:
                ok = status.get("ok", False)
                if ok:
                    st.markdown(f"**{name}** \n\n ✅ 在线")
                else:
                    st.markdown(f"**{name}** \n\n ❌ 离线")

# ── 个股详情分析 ─────────────────────────────────────────
if quotes:
    st.markdown("---")
    st.markdown("### 🔍 个股深度分析")

    # 选股下拉框
    sel_name = st.selectbox(
        "选择要分析的自选股",
        options=[q.get("name", q["code"]) for q in quotes],
        label_visibility="collapsed",
    )
    sel_q = next((q for q in quotes if q.get("name", q["code"]) == sel_name), quotes[0])
    sel_code = sel_q["code"]

    # 关键指标横排
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    pct = sel_q.get("pct")
    with c1:
        st.metric("现价", f"{sel_q.get('current','—'):.2f}" if sel_q.get("current") else "—",
                  delta=pct_str(pct) if pct else None)
    with c2:
        st.metric("涨跌额", f"{sel_q.get('change','—'):.2f}" if sel_q.get("change") else "—")
    with c3:
        st.metric("今开", f"{sel_q.get('open','—'):.2f}" if sel_q.get("open") else "—")
    with c4:
        st.metric("最高", f"{sel_q.get('high','—'):.2f}" if sel_q.get("high") else "—")
    with c5:
        st.metric("最低", f"{sel_q.get('low','—'):.2f}" if sel_q.get("low") else "—")
    with c6:
        st.metric("昨收", f"{sel_q.get('prev_close','—'):.2f}" if sel_q.get("prev_close") else "—")


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 市场情绪 + 板块热力图
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with st.expander("🔥 市场情绪 & 板块热力图", expanded=False):
        col_br, col_sc = st.columns(2)
        with col_br:
            st.markdown("##### 市场宽度")
            breadth = get_market_breadth()
            if breadth:
                up_pct = breadth["up_pct"]
                b1,b2,b3,b4 = st.columns(4)
                b1.metric("上涨", f"{breadth['up']}", delta=f"{up_pct}%")
                b2.metric("下跌", f"{breadth['down']}")
                b3.metric("涨停", f"{breadth['limit_up']}")
                b4.metric("跌停", f"{breadth['limit_down']}")
                dn = 100 - up_pct
                bar_html = (f'<div style="display:flex; height:20px; border-radius:8px; overflow:hidden; margin:8px 0;">'
                            f'<div style="background:#dc3545; width:{up_pct:.0f}%; display:flex; align-items:center; justify-content:center; color:white; font-size:0.7rem;">涨 {up_pct:.0f}%</div>'
                            f'<div style="background:#28a745; width:{dn:.0f}%; display:flex; align-items:center; justify-content:center; color:white; font-size:0.7rem;">跌 {dn:.0f}%</div>'
                            f'</div>')
                st.markdown(bar_html, unsafe_allow_html=True)
                st.markdown(f"**{breadth['sentiment']}** — {breadth['sdesc']}")
            else:
                st.caption("数据加载中...")
        with col_sc:
            st.markdown("##### 行业板块 Top")
            sectors = get_sector_performance()
            if sectors:
                top5, bot5 = sectors[:5], sectors[-5:]
                ttab, btab = st.tabs(["🔥 涨幅榜", "❄️ 跌幅榜"])
                with ttab:
                    for s in top5:
                        st.markdown(f"<span style='color:#dc3545'>▲{s['pct']:+.2f}%</span> **{s['name']}** <small style='color:#888'>({s.get('lead_stock','')})</small>", unsafe_allow_html=True)
                with btab:
                    for s in bot5:
                        st.markdown(f"<span style='color:#28a745'>▼{s['pct']:+.2f}%</span> **{s['name']}** <small style='color:#888'>({s.get('lead_stock','')})</small>", unsafe_allow_html=True)
            else:
                st.caption("数据加载中...")

    # Tab 切换
    tab_kline, tab_tech, tab_signal, tab_fund, tab_ai, tab_compare, tab_backtest, tab_sr, tab_sector, tab_sentiment, tab_div = st.tabs(
        ["📊 K线图", "📈 技术指标", "💡 智能信号", "📋 基本面", "🤖 AI分析", "🔄 股票对比", "📊 策略回测", "🎯 支撑/压力", "🏭 板块热力", "🌡️ 市场情绪", "🔍 背离/分型"]
    )

    # ── K线图 Tab ─────────────────────────────────────────
    with tab_kline:
        st.markdown("#### 当前行情总览")
        with st.spinner("加载历史数据..."):
            tech = cached_tech(sel_code)

        if tech and tech.get("ma"):
            ma = tech["ma"]
            st.markdown("**移动平均线 (MA)**")
            cm = st.columns(4)
            ma_vals = [
                ("MA5",  ma.get("MA5")),
                ("MA10", ma.get("MA10")),
                ("MA20", ma.get("MA20")),
                ("MA60", ma.get("MA60")),
            ]
            for i, (k, v) in enumerate(ma_vals):
                with cm[i]:
                    st.metric(k, f"{v:.3f}" if v else "—")
            # MA 排列状态
            cross = ma.get("cross", "")
            if "BULLISH" in str(cross):
                st.success(f"✅ MA多头排列：{cross}")
            elif "BEARISH" in str(cross):
                st.error(f"🔴 MA空头排列：{cross}")
            else:
                st.warning(f"⚠️ {cross}")

        if tech and tech.get("boll"):
            boll = tech["boll"]
            st.markdown("**布林带 (BOLL)**")
            cb = st.columns(4)
            with cb[0]: st.metric("上轨", f"{boll.get('upper','—'):.3f}" if boll.get("upper") else "—")
            with cb[1]: st.metric("中轨", f"{boll.get("mid","—"):.3f}" if boll.get("mid") else "—")
            with cb[2]: st.metric("下轨", f"{boll.get('lower','—'):.3f}" if boll.get("lower") else "—")
            with cb[3]: st.metric("现价位置", f"{boll.get('pos_pct','—'):.0f}%" if boll.get("pos_pct") else "—")

        if not tech:
            st.warning("历史数据加载失败，请检查股票代码或网络")

    # ── 技术指标 Tab ──────────────────────────────────
    with tab_tech:
        with st.spinner("计算技术指标..."):
            tech = cached_tech(sel_code)

        if not tech:
            st.warning("技术指标数据不可用")
        else:
            # ── 支撑/压力位 ──
            from data_source import get_historical_kline as _kline_sr
            kd = _kline_sr(sel_code, days=120)
            if not kd.empty:
                sr = calc_support_resistance(kd, sel_q.get("current"))
                if sr.get("supports") or sr.get("resistances"):
                    st.markdown("**🎯 支撑/压力位**")
                    s1,s2 = st.columns(2)
                    with s1:
                        for s in sr.get("supports", [])[:3]:
                            d = round((sel_q.get("current",0)-s['price'])/sel_q.get("current",1)*100, 1)
                            st.markdown(f"🟢 **{s['price']}** ({s['label']}) — -{d:.1f}%")
                    with s2:
                        for r in sr.get("resistances", [])[:3]:
                            d = round((r['price']-sel_q.get("current",0))/sel_q.get("current",1)*100, 1)
                            st.markdown(f"🔴 **{r['price']}** ({r['label']}) — +{d:.1f}%")
                    if sr.get("pivot"):
                        st.caption(f"📍 Pivot: {sr['pivot']}")

            # RSI
            if tech.get("rsi"):
                rsi = tech["rsi"]
                st.markdown("**RSI 相对强弱指数**")
                cr = st.columns(3)
                rsi_data = [
                    ("RSI(6)",  rsi.get("6")),
                    ("RSI(14)", rsi.get("14")),
                    ("RSI(26)", rsi.get("26")),
                ]
                for i, (k, v) in enumerate(rsi_data):
                    with cr[i]:
                        tip = ""
                        if v:
                            if v < 30: tip = "超卖 🟢"
                            elif v > 70: tip = "超买 🔴"
                            elif v > 50: tip = "偏强 📈"
                            else: tip = "偏弱 📉"
                        st.metric(k, f"{v:.2f}" if v else "—", delta=tip)

            # RSI 刻度条
                v14 = rsi.get("14")
                if v14:
                    pos = max(0, min(100, v14))
                    bar = f"""
                    <div style="display:flex; height:14px; border-radius:7px; overflow:hidden; margin-top:8px;">
                        <div style="background:#28a745; width:30%;"></div>
                        <div style="background:#17a2b8; width:20%;"></div>
                        <div style="background:#ffc107; width:20%;"></div>
                        <div style="background:#dc3545; width:30%;"></div>
                    </div>
                    <div style="position:relative; height:4px; margin-top:-10px;">
                        <div style="position:absolute; background:#333; width:3px; height:18px; left:{pos:.0f}%; top:-2px; border-radius:2px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#888; margin-top:4px;">
                        <span>0 (超卖)</span><span>50</span><span>100 (超买)</span>
                    </div>
                    """
                    st.markdown(bar, unsafe_allow_html=True)

            # MACD
            if tech.get("macd"):
                macd = tech["macd"]
                st.markdown("**MACD 指数平滑异同移动平均线**")
                cm = st.columns(4)
                with cm[0]: st.metric("DIF", f"{macd.get('DIF','—'):.4f}" if macd.get("DIF") else "—")
                with cm[1]: st.metric("DEA", f"{macd.get('DEA','—'):.4f}" if macd.get("DEA") else "—")
                with cm[2]: st.metric("MACD柱", f"{macd.get('BAR','—'):.4f}" if macd.get("BAR") else "—")
                mc = macd.get("cross", "")
                mc_color = "🟢 金叉" if "Golden" in str(mc) else ("🔴 死叉" if "Death" in str(mc) else "⚠️ 中性")
                with cm[3]: st.metric("状态", mc_color)

            # KDJ
            if tech.get("kdj"):
                kdj = tech["kdj"]
                st.markdown("**KDJ 随机指标**")
                ck = st.columns(4)
                kdj_data = [("K", kdj.get("K")), ("D", kdj.get("D")), ("J", kdj.get("J"))]
                for i, (k, v) in enumerate(kdj_data):
                    with ck[i]:
                        tip = ""
                        if v:
                            if v < 20: tip = "超卖"
                            elif v > 80: tip = "超买"
                        st.metric(k, f"{v:.2f}" if v else "—", delta=tip)
                with ck[3]:
                    trend = kdj.get("K") and kdj.get("D")
                    st.metric("K>D", "✅ 是" if (trend and kdj.get("K", 0) > kdj.get("D", 0)) else "❌ 否")

            # 成交量
            if tech.get("volume"):
                vol = tech["volume"]
                st.markdown("**成交量分析**")
                cv = st.columns(3)
                with cv[0]: st.metric("量比", f"{vol.get('ratio','—'):.2f}x" if vol.get("ratio") else "—")
                with cv[1]: st.metric("5日均量", f"{vol.get('avg_5d','—'):.0f}" if vol.get("avg_5d") else "—")
                with cv[2]:
                    ratio = vol.get("ratio")
                    tip = "放量 📈" if (ratio and ratio > 1.5) else ("缩量 📉" if (ratio and ratio < 0.7) else "正常")
                    st.metric("量能判断", tip)

    # ── 智能信号 Tab ──────────────────────────────────
    with tab_signal:
        with st.spinner("生成智能信号..."):
            tech = cached_tech(sel_code)
            signals = generate_signals(tech) if tech else {}
            dayt = generate_dayt_suggestion(tech, sel_q) if tech else {}

        if signals:
            score    = signals.get("score", 0)
            rec      = signals.get("recommendation", "数据不足")
            summary  = signals.get("summary", "")

            # 综合评分仪表
            bar_pct = (score + 100) / 2
            rec_colors = {"STRONG BUY": "#28a745", "BUY": "#6cbf7a", "HOLD": "#ffc107",
                          "SELL": "#fd7e14", "STRONG SELL": "#dc3545"}
            rc = rec_colors.get(rec, "#888")
            gauge = f"""
            <div style="text-align:center; background:#f8f9fa; border-radius:12px; padding:20px; margin:10px 0;">
                <div style="font-size:3.5rem; font-weight:700; color:{rc};">{score}</div>
                <div style="font-size:1.4rem; font-weight:700; color:{rc}; margin:6px 0;">{rec}</div>
                <div style="font-size:0.9rem; color:#666; margin-bottom:12px;">{summary}</div>
                <div style="background:#e9ecef; border-radius:6px; height:12px; overflow:hidden;">
                    <div style="background:{rc}; width:{bar_pct:.0f}%; height:100%; border-radius:6px; transition:width 0.5s;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#888; margin-top:4px;">
                    <span>-100 强烈卖出</span><span>0 观望</span><span>+100 强烈买入</span>
                </div>
            </div>
            """
            st.markdown(gauge, unsafe_allow_html=True)

            # 资金流向
            cap = get_capital_flow(sel_code)
            if cap:
                st.markdown("**💰 资金流向（万元）**")
                f1,f2,f3,f4,f5 = st.columns(5)
                f1.metric("主力净流入", f"{cap['main_net']:.0f}", delta=f"{cap['main_net']:+.0f}")
                f2.metric("超大单", f"{cap['super_large']:.0f}", delta=f"{cap['super_large']:+.0f}")
                f3.metric("大单", f"{cap['large']:.0f}", delta=f"{cap['large']:+.0f}")
                f4.metric("中单", f"{cap['medium']:.0f}", delta=f"{cap['medium']:+.0f}")
                f5.metric("小单", f"{cap['small']:.0f}", delta=f"{cap['small']:+.0f}")
                st.markdown(f'<span style="color:{cap["status_color"]}; font-weight:700;">{cap["status"]}</span>', unsafe_allow_html=True)

            st.markdown("---")

            # ══════════════════════════════════════════════
            # 买卖建议（价位）
            # ══════════════════════════════════════════════
            price_sug = signals.get("price_suggestion", {})
            if price_sug:
                st.markdown("### 💰 买卖价位建议")
                action = price_sug.get("action", "观望")
                detail = price_sug.get("detail", "")
                buy_levels = price_sug.get("buy_levels", [])
                sell_levels = price_sug.get("sell_levels", [])

                # 操作建议
                action_color = "#28a745" if "买" in action else ("#dc3545" if "卖" in action else "#ffc107")
                st.markdown(
                    f'<div style="background:{action_color}; color:white; padding:12px 20px; border-radius:8px; font-size:1.2rem; font-weight:700; text-align:center;">{action}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(detail)

                # 买入价位
                col_bl, col_sl = st.columns(2)
                with col_bl:
                    st.markdown("**🟢 建议买入价位**")
                    if buy_levels:
                        for lvl in buy_levels:
                            st.markdown(f"- **{lvl['price']}** — {lvl['reason']} ({lvl['strength']}支撑)")
                    else:
                        st.caption("暂无明确买入点")

                # 卖出价位
                with col_sl:
                    st.markdown("**🔴 建议卖出价位**")
                    if sell_levels:
                        for lvl in sell_levels:
                            st.markdown(f"- **{lvl['price']}** — {lvl['reason']} ({lvl['strength']}压力)")
                    else:
                        st.caption("暂无明确卖出点")

                # 止损止盈
                stop_loss = price_sug.get("stop_loss")
                take_profit = price_sug.get("take_profit")
                if stop_loss or take_profit:
                    st.markdown("---")
                    col_sl_tp = st.columns(2)
                    with col_sl_tp[0]:
                        if stop_loss:
                            st.metric("🛡️ 止损价", f"{stop_loss}", delta="-5%")
                    with col_sl_tp[1]:
                        if take_profit:
                            st.metric("🎯 止盈价", f"{take_profit}", delta="+10%")

                st.markdown("---")

            # ══════════════════════════════════════════════
            # 做T建议
            # ══════════════════════════════════════════════
            if dayt and dayt.get("available"):
                st.markdown("### 🔄 做T建议（日内高抛低吸）")

                dayt_action = dayt.get("action", "")
                dayt_type = dayt.get("action_type", "HOLD")
                trend_score = dayt.get("trend_score", 0)
                buy_p = dayt.get("buy_price")
                buy_r = dayt.get("buy_reason", "")
                sell_p = dayt.get("sell_price")
                sell_r = dayt.get("sell_reason", "")
                profit_pct = dayt.get("profit_pct")

                # 做T操作建议
                dayt_colors = {
                    "BUY_T": "#28a745",
                    "SELL_T": "#fd7e14",
                    "LIGHT_BUY": "#6cbf7a",
                    "LIGHT_SELL": "#ffc107",
                    "HOLD": "#6c757d",
                }
                dc = dayt_colors.get(dayt_type, "#6c757d")
                st.markdown(
                    f'<div style="background:{dc}; color:white; padding:12px 20px; border-radius:8px; font-size:1.2rem; font-weight:700; text-align:center;">{dayt_action}</div>',
                    unsafe_allow_html=True,
                )

                # 做T价位
                col_buy_t, col_sell_t = st.columns(2)
                with col_buy_t:
                    if buy_p:
                        st.metric("📍 建议低吸价", f"{buy_p}", delta=buy_r)
                with col_sell_t:
                    if sell_p:
                        st.metric("📍 建议高抛价", f"{sell_p}", delta=sell_r)

                # 预期收益
                if profit_pct:
                    st.metric("📊 预期T收益", f"{profit_pct}%", delta="理论空间")

                # 做T信号明细
                dayt_signals = dayt.get("signals", {})
                if any(dayt_signals.values()):
                    st.markdown("**信号明细：**")
                    sig_cols = st.columns(3)
                    if dayt_signals.get("kdj"):
                        with sig_cols[0]:
                            st.caption(f"KDJ: {dayt_signals['kdj']}")
                    if dayt_signals.get("rsi"):
                        with sig_cols[1]:
                            st.caption(f"RSI: {dayt_signals['rsi']}")
                    if dayt_signals.get("boll"):
                        with sig_cols[2]:
                            st.caption(f"BOLL: {dayt_signals['boll']}")

                # 做T提示
                tips = dayt.get("tips", [])
                if tips:
                    st.markdown("**💡 做T提示：**")
                    for tip in tips:
                        st.markdown(f"- {tip}")

                st.markdown("---")

            # 详细信号列表
            sig_list = signals.get("signals", [])
            if sig_list:
                st.markdown("### 📊 详细信号分解")
                buy_sigs  = [s for s in sig_list if s["signal"] == "BUY"]
                sell_sigs = [s for s in sig_list if s["signal"] == "SELL"]
                hold_sigs = [s for s in sig_list if s["signal"] not in ("BUY", "SELL")]

                col_b, col_s = st.columns(2)
                with col_b:
                    st.markdown(f"**🟢 买入信号 ({len(buy_sigs)})**")
                    for s in buy_sigs:
                        st.markdown(
                            f'<div class="signal-buy">✅ {s["indicator"]} — {s["text"]} (权重:{s["weight"]})</div>',
                            unsafe_allow_html=True,
                        )
                with col_s:
                    st.markdown(f"**🔴 卖出信号 ({len(sell_sigs)})**")
                    for s in sell_sigs:
                        st.markdown(
                            f'<div class="signal-sell">⚠️ {s["indicator"]} — {s["text"]} (权重:{s["weight"]})</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info("暂无明确信号，请等待数据更新")
        else:
            st.warning("信号分析数据不可用，请检查股票代码")

    # ── 基本面 Tab ────────────────────────────────────
    with tab_fund:
        with st.spinner("加载基本面数据..."):
            bg = cached_bg(sel_code)

        if bg:
            if bg.get("industry"):
                st.markdown(f"**所属行业：** {bg['industry']}")

            if bg.get("financial"):
                fin = bg["financial"]
                st.markdown("**财务指标**")
                cf = st.columns(3)
                fin_data = [
                    ("ROE 净资产收益率", fin.get("ROE"), "%"),
                    ("毛利率", fin.get("gross_margin"), "%"),
                    ("负债率", fin.get("debt_ratio"), "%"),
                ]
                for i, (k, v, u) in enumerate(fin_data):
                    with cf[i]:
                        val = f"{v:.2f}{u}" if v else "—"
                        st.metric(k, val)

            if bg.get("total_shares"):
                st.markdown(f"**总股本：** {bg['total_shares']}")
            if bg.get("float_shares"):
                st.markdown(f"**流通股本：** {bg['float_shares']}")
        else:
            st.info("基本面数据暂不可用（部分股票可能不支持）")

    # ── 股票对比 Tab ─────────────────────────────────────
    with tab_compare:
        render_compare_tab(
            quotes,
            get_tech_fn=cached_tech,
            get_bg_fn=cached_bg,
            get_hist_fn=lambda c: __import__('data_source', fromlist=['get_historical_kline']).get_historical_kline(c, days=120),
        )

    # ── 策略回测 Tab ─────────────────────────────────────
    with tab_backtest:
        from data_source import get_historical_kline as _bt_hist
        bt = _bt_hist(sel_code, days=500)
        if not bt.empty:
            render_backtest_tab(bt, sel_name)

    # ── AI分析 Tab
    with tab_ai:
            # 检查 API Key
            has_key = any(
                getattr(config, k, "") and not getattr(config, k, "").startswith("YOUR_")
                for k in ["ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "SILICONFLOW_API_KEY"]
            )
            if not has_key:
                st.warning("⚠️ AI未配置。请在 `src/config.py` 中填入 API Key")
                st.markdown("""
                **推荐配置智谱 API（免费额度）：**
                1. 访问 https://open.bigmodel.cn 注册
                2. 获取 API Key
                3. 写入 `src/config.py` → `ZHIPU_API_KEY = "你的KEY"`
                """)
            else:
                with st.spinner("🤖 AI分析中，请稍候（10-30秒）..."):
                    try:
                        ai = get_ai_client()
                        tech_s  = cached_tech(sel_code)
                        bg_s    = cached_bg(sel_code)
                        sigs    = generate_signals(tech_s) if tech_s else {}
                        analysis = ai.analyze_stock(sel_code, sel_name, sel_q, bg_s, tech_s)
                        st.markdown(
                            f'<div class="ai-box">{analysis}</div>',
                            unsafe_allow_html=True,
                        )
                    except Exception as e:
                        st.error(f"AI分析出错：{str(e)}")

# ── 支撑/压力位 Tab ──────────────────────────────
with tab_sr:
    render_support_resistance_tab(sel_code, sel_q.get("current", 0))

# ── 板块热力 Tab ─────────────────────────────────
with tab_sector:
    render_sector_heatmap()

# ── 市场情绪 Tab ─────────────────────────────────
with tab_sentiment:
    render_market_sentiment()

# ── 背离/分型 Tab ────────────────────────────────
with tab_div:
    render_divergence_tab(sel_code, sel_name, sel_q.get("current", 0))

# ── 财经新闻 ─────────────────────────────────────────────
if show_news:
    st.markdown("---")
    st.markdown("### 📰 财经资讯")
    with st.spinner("加载新闻..."):
        news = get_stock_news(8)
    if news:
        for item in news:
            col_t, col_n = st.columns([1, 5])
            with col_t:
                st.caption(item.get("time", ""))
            with col_n:
                st.markdown(f"**{item.get('title', '—')}** — {item.get('source', '')}")
    else:
        st.info("暂无新闻数据")

# ── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ 免责声明：本工具仅供学习参考，不构成投资建议。股市有风险，入市需谨慎。")
