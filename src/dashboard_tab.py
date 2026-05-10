# -*- coding: utf-8 -*-
"""
📊 交易业务数据看板
嵌入到 stock-monitor/app.py 的 Tab 页面

使用方法：
  在 app.py 的 tab 定义区域添加：
    from src.dashboard_tab import render_dashboard_tab
    ...
    tab1, tab2, tab3, tab4 = st.tabs(["📊 行情监控", "📋 技术分析", "💰 交易看板", "🤖 AI分析"])
    with tab3:
        render_dashboard_tab()

  需要在 app.py 顶部添加导入：
    from src.dashboard_tab import render_dashboard_tab
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime, date
from typing import List, Dict, Optional

# data_source 在同目录 src/ 下
from data_source import get_realtime_quotes

# ── 数据路径 ────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_TRADE_FILE = os.path.join(os.path.dirname(_DIR), "trades.json")


# ══════════════════════════════════════════════════════════
#  数据加载
# ══════════════════════════════════════════════════════════

def _load_trades() -> List[Dict]:
    if not os.path.exists(_TRADE_FILE):
        return []
    try:
        with open(_TRADE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ══════════════════════════════════════════════════════════
#  持仓计算
# ══════════════════════════════════════════════════════════

def _calc_positions(trades: List[Dict]) -> List[Dict]:
    """计算当前持仓：买入-卖出"""
    positions: Dict[str, Dict] = {}
    for t in trades:
        code = t.get("code", "")
        name = t.get("name", code)
        t_type = t.get("type", "")
        price = float(t.get("price", 0))
        qty = int(t.get("quantity", 0))
        if t_type == "buy":
            if code not in positions:
                positions[code] = {"code": code, "name": name, "shares": 0, "total_cost": 0.0, "buy_count": 0, "sell_count": 0}
            positions[code]["shares"] += qty
            positions[code]["total_cost"] += price * qty
        elif t_type == "sell":
            if code in positions:
                # 先进先出简化：按平均成本计算
                avg = positions[code]["total_cost"] / positions[code]["shares"] if positions[code]["shares"] > 0 else 0
                positions[code]["shares"] -= qty
                positions[code]["total_cost"] = avg * positions[code]["shares"]
                positions[code]["sell_count"] = positions[code].get("sell_count", 0) + 1

    result = []
    for code, pos in positions.items():
        if pos["shares"] > 0:
            pos["avg_price"] = pos["total_cost"] / pos["shares"]
            result.append(pos)
    return result


# ══════════════════════════════════════════════════════════
#  盈亏统计
# ══════════════════════════════════════════════════════════

def _calc_stats(trades: List[Dict], positions: List[Dict], live_quotes: List[Dict]) -> Dict:
    """计算整体盈亏统计"""
    quote_map = {q["code"]: q for q in live_quotes}

    # 累计买入/卖出
    total_buy = sum(t["amount"] for t in trades if t.get("type") == "buy")
    total_sell = sum(t["amount"] for t in trades if t.get("type") == "sell")
    net_invest = total_buy - total_sell  # 净投入

    # 持仓市值 & 浮动盈亏
    pos_value = 0.0
    pos_cost = 0.0
    unreal_pnl = 0.0
    for pos in positions:
        code = pos["code"]
        shares = pos["shares"]
        avg_cost = pos["avg_price"]
        live = quote_map.get(code, {})
        cur_price = live.get("current", avg_cost)
        cur_val = cur_price * shares
        pos_value += cur_val
        pos_cost += avg_cost * shares
        unreal_pnl += cur_val - avg_cost * shares

    # 已实现盈亏（用卖出金额 - 买入成本粗算）
    realized_pnl = total_sell - total_buy + pos_cost  # 简化
    total_pnl = unreal_pnl + realized_pnl
    # 更准确：卖出的股 * (卖价 - 买均价)
    # 简化版：已实现 = 累计卖出 - 对应买入成本
    # 我们用：每笔卖出 - 当时持仓均价的成本
    buy_total_for_sold = 0.0
    sell_amounts = [t for t in trades if t.get("type") == "sell"]
    # 简化：用 total_sell - (已持仓平均成本 * 卖出股数)
    realized_pnl = 0.0  # 留空，已实现需要逐笔配对

    return {
        "total_buy": total_buy,
        "total_sell": total_sell,
        "net_invest": net_invest,
        "pos_value": pos_value,
        "pos_cost": pos_cost,
        "unreal_pnl": unreal_pnl,
        "unreal_pnl_pct": (unreal_pnl / pos_cost * 100) if pos_cost > 0 else 0.0,
        "total_trades": len(trades),
        "buy_count": len([t for t in trades if t.get("type") == "buy"]),
        "sell_count": len([t for t in trades if t.get("type") == "sell"]),
        "positions_count": len(positions),
    }


# ══════════════════════════════════════════════════════════
#  格式化工具
# ══════════════════════════════════════════════════════════

def pnl_color(v: float) -> str:
    if v > 0:   return "#e63946"   # 红涨
    if v < 0:   return "#2a9d8f"   # 绿跌
    return "#888"

def pnl_str(v: float, prefix="", suffix="") -> str:
    color = pnl_color(v)
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "—")
    return f'<span style="color:{color};font-weight:700">{prefix}{arrow}{abs(v):,.2f}{suffix}</span>'

def kpi_card(label: str, value: str, sub: str = "", color: str = "#333") -> str:
    return f"""
    <div style="background:#fff;border-radius:12px;padding:20px 24px;border:1px solid #eee;min-width:160px;">
        <div style="font-size:0.8rem;color:#888;margin-bottom:8px;">{label}</div>
        <div style="font-size:1.5rem;font-weight:700;color:{color};margin-bottom:4px;">{value}</div>
        <div style="font-size:0.75rem;color:#aaa;">{sub}</div>
    </div>
    """


# ══════════════════════════════════════════════════════════
#  交易记录统计
# ══════════════════════════════════════════════════════════

def _trade_summary_by_month(trades: List[Dict]) -> pd.DataFrame:
    """按月统计交易"""
    rows = []
    for t in trades:
        try:
            ym = t.get("date", "")[:7]  # "YYYY-MM"
        except Exception:
            ym = "未知"
        rows.append({
            "月份": ym,
            "方向": "买入" if t.get("type") == "buy" else "卖出",
            "金额": t.get("amount", 0),
            "股数": t.get("quantity", 0),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.groupby(["月份", "方向"], as_index=False).sum()


# ══════════════════════════════════════════════════════════
#  主渲染函数
# ══════════════════════════════════════════════════════════

def render_dashboard_tab():
    st.markdown("## 💰 交易看板")

    # ── 数据加载 ─────────────────────────────────────────
    trades = _load_trades()
    if not trades:
        st.info("暂无交易记录，请在「交易记录」页面添加")
        st.stop()

    positions = _calc_positions(trades)

    # 获取持仓实时行情
    pos_codes = [p["code"] for p in positions]
    live_quotes = get_realtime_quotes(pos_codes) if pos_codes else []
    quote_map = {q["code"]: q for q in live_quotes}

    stats = _calc_stats(trades, positions, live_quotes)

    # ── KPI 概览 ─────────────────────────────────────────
    st.markdown("### 📌 账户概览")

    unreal_color = pnl_color(stats["unreal_pnl"])
    unreal_pct = stats.get("unreal_pnl_pct", 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(kpi_card(
            "📥 累计买入",
            f"¥{stats['total_buy']:,.0f}",
            f"共 {stats['buy_count']} 笔买入"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(kpi_card(
            "📤 累计卖出",
            f"¥{stats['total_sell']:,.0f}",
            f"共 {stats['sell_count']} 笔卖出"
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(kpi_card(
            "💼 当前持仓市值",
            f"¥{stats['pos_value']:,.0f}",
            f"成本 ¥{stats['pos_cost']:,.0f}"
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(kpi_card(
            "📈 浮动盈亏",
            f"{'▲' if stats['unreal_pnl']>0 else '▼' if stats['unreal_pnl']<0 else '—'} ¥{abs(stats['unreal_pnl']):,.0f}",
            f"{unreal_pct:+.2f}%" if unreal_pct != 0 else "—",
            color=unreal_color
        ), unsafe_allow_html=True)

    st.markdown("---")

    # ── 持仓明细 ─────────────────────────────────────────
    st.markdown("### 💼 持仓明细")

    if positions:
        pos_rows = []
        for p in positions:
            code = p["code"]
            live = quote_map.get(code, {})
            cur_price = live.get("current", p["avg_price"])
            pct = live.get("pct", 0)
            pos_value = cur_price * p["shares"]
            cost = p["avg_price"] * p["shares"]
            pnl = pos_value - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0

            pos_rows.append({
                "股票名称": p["name"],
                "代码": code,
                "持仓数量": p["shares"],
                "成本价": f"{p['avg_price']:.3f}",
                "现价": f"{cur_price:.3f}",
                "持仓市值": f"¥{pos_value:,.0f}",
                "成本总额": f"¥{cost:,.0f}",
                "浮动盈亏": f"{'+' if pnl>=0 else ''}{pnl:,.0f}",
                "盈亏%": pct,
                "今日涨跌%": pct,
                "盈亏颜色": pnl_color(pnl),
            })

        pos_df = pd.DataFrame(pos_rows)

        # 用 HTML 表格展示持仓（含颜色）
        html = '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        headers = ["股票名称", "代码", "持仓数量", "成本价", "现价", "持仓市值", "成本总额", "浮动盈亏", "盈亏%", "今日涨跌%"]
        html += "<thead><tr>"
        for h in headers:
            html += f'<th style="text-align:center;padding:10px 12px;background:#f8f9fa;border-bottom:2px solid #dee2e6;color:#495057;white-space:nowrap;">{h}</th>'
        html += "</tr></thead><tbody>"

        for _, row in pos_df.iterrows():
            pnl_c = row["盈亏颜色"]
            pct_v = row["盈亏%"]
            pct_str_val = f"+{pct_v:.2f}%" if pct_v > 0 else f"{pct_v:.2f}%"
            day_pct = row["今日涨跌%"]
            day_str = f"+{day_pct:.2f}%" if day_pct > 0 else f"{day_pct:.2f}%"

            html += "<tr>"
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;font-weight:600;">{row["股票名称"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666;">{row["代码"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">{row["持仓数量"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">{row["成本价"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">{row["现价"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;font-weight:600;">{row["持仓市值"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">{row["成本总额"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;color:{pnl_c};font-weight:700;">{row["浮动盈亏"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;color:{pnl_c};font-weight:700;">{pct_str_val}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;color:{pnl_color(day_pct)};font-weight:600;">{day_str}</td>'
            html += "</tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("当前无持仓")

    st.markdown("---")

    # ── 交易记录 ─────────────────────────────────────────
    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        st.markdown("### 📋 交易记录")
    with col_f2:
        filter_code = st.selectbox("筛选股票", ["全部"] + list({t.get("code"): t.get("name", t["code"]) for t in trades}.items()), label_visibility="collapsed")

    filtered_trades = trades
    if filter_code != "全部":
        filtered_trades = [t for t in trades if t.get("code") == filter_code]

    trade_rows = []
    for t in filtered_trades:
        trade_rows.append({
            "日期": t.get("date", ""),
            "股票名称": t.get("name", t.get("code", "—")),
            "代码": t.get("code", "—"),
            "方向": "买入" if t.get("type") == "buy" else "卖出",
            "价格": f"¥{t.get('price', 0):.3f}",
            "数量": t.get("quantity", 0),
            "金额": f"¥{t.get('amount', 0):,.2f}",
            "备注": t.get("notes", ""),
        })

    if trade_rows:
        trade_df = pd.DataFrame(trade_rows)
        st.dataframe(
            trade_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("暂无交易记录")

    # ── 月度统计 ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📅 月度交易统计")

    if len(trades) > 0:
        # 按月汇总
        monthly = {}
        for t in trades:
            ym = t.get("date", "Unknown")[:7]
            if ym not in monthly:
                monthly[ym] = {"买入金额": 0.0, "卖出金额": 0.0, "买入笔数": 0, "卖出笔数": 0, "买入股数": 0, "卖出股数": 0}
            if t.get("type") == "buy":
                monthly[ym]["买入金额"] += t.get("amount", 0)
                monthly[ym]["买入笔数"] += 1
                monthly[ym]["买入股数"] += t.get("quantity", 0)
            else:
                monthly[ym]["卖出金额"] += t.get("amount", 0)
                monthly[ym]["卖出笔数"] += 1
                monthly[ym]["卖出股数"] += t.get("quantity", 0)

        month_rows = []
        for ym in sorted(monthly.keys(), reverse=True):
            m = monthly[ym]
            month_rows.append({
                "月份": ym,
                "买入笔数": m["买入笔数"],
                "买入金额": f"¥{m['买入金额']:,.0f}",
                "买入股数": m["买入股数"],
                "卖出笔数": m["卖出笔数"],
                "卖出金额": f"¥{m['卖出金额']:,.0f}",
                "卖出股数": m["卖出股数"],
                "净流入": f"{'+' if (m['买入金额']-m['卖出金额'])>=0 else ''}{m['买入金额']-m['卖出金额']:,.0f}",
            })
        month_df = pd.DataFrame(month_rows)
        st.dataframe(month_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无数据")

    # ── 股票交易明细 ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 股票盈亏明细")

    # 汇总每只股票的交易情况
    stock_summary: Dict[str, Dict] = {}
    for t in trades:
        code = t.get("code", "")
        name = t.get("name", code)
        if code not in stock_summary:
            stock_summary[code] = {
                "name": name, "buy_count": 0, "sell_count": 0,
                "buy_amount": 0.0, "sell_amount": 0.0,
                "buy_shares": 0, "sell_shares": 0,
            }
        if t.get("type") == "buy":
            stock_summary[code]["buy_count"] += 1
            stock_summary[code]["buy_amount"] += t.get("amount", 0)
            stock_summary[code]["buy_shares"] += t.get("quantity", 0)
        else:
            stock_summary[code]["sell_count"] += 1
            stock_summary[code]["sell_amount"] += t.get("amount", 0)
            stock_summary[code]["sell_shares"] += t.get("quantity", 0)

    sum_rows_clean = []
    for code, s in stock_summary.items():
        live = quote_map.get(code, {})
        cur_price = live.get("current", 0)
        remaining = s["buy_shares"] - s["sell_shares"]
        avg_buy_cost = s["buy_amount"] / s["buy_shares"] if s["buy_shares"] > 0 else 0
        realized = s["sell_amount"] - avg_buy_cost * s["sell_shares"]
        unreal = (cur_price - avg_buy_cost) * remaining if remaining > 0 else 0
        total_pnl = realized + unreal

        sum_rows_clean.append({
            "name": s["name"],
            "code": code,
            "buy_count": s["buy_count"],
            "buy_amount": s["buy_amount"],
            "sell_amount": s["sell_amount"],
            "remaining": remaining,
            "realized": realized,
            "unreal": unreal,
            "total_pnl": total_pnl,
            "real_c": pnl_color(realized),
            "unreal_c": pnl_color(unreal),
            "total_c": pnl_color(total_pnl),
        })

    if sum_rows_clean:
        html = '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
        headers = ["股票名称", "代码", "买入笔数", "买入总额", "卖出总额", "剩余持仓", "已实现盈亏", "浮动盈亏", "总盈亏"]
        html += "<thead><tr>"
        for h in headers:
            html += f'<th style="text-align:center;padding:10px 12px;background:#f8f9fa;border-bottom:2px solid #dee2e6;color:#495057;">{h}</th>'
        html += "</tr></thead><tbody>"
        for r in sum_rows_clean:
            buy_str = f"¥{r['buy_amount']:,.0f}"
            sell_str = f"¥{r['sell_amount']:,.0f}"
            real_str = f"{'+' if r['realized']>=0 else ''}{r['realized']:,.0f}"
            unreal_str = f"{'+' if r['unreal']>=0 else ''}{r['unreal']:,.0f}"
            total_str = f"{'+' if r['total_pnl']>=0 else ''}{r['total_pnl']:,.0f}"
            html += "<tr>"
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;font-weight:600;">{r["name"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;color:#666;">{r["code"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">{r["buy_count"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">{buy_str}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">{sell_str}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">{r["remaining"]}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;color:{r["real_c"]};font-weight:600;">{real_str}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;color:{r["unreal_c"]};font-weight:600;">{unreal_str}</td>'
            html += f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;color:{r["total_c"]};font-weight:700;">{total_str}</td>'
            html += "</tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("暂无数据")

    st.caption(f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  共 {stats['total_trades']} 笔交易  |  {stats['positions_count']} 只持仓")
