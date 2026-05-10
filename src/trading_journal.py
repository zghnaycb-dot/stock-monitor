"""
交易记录管理器
存储、查询、分析个人交易记录
"""
import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
import pandas as pd

# ── 文件路径 ────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_TRADE_FILE = os.path.join(os.path.dirname(_DIR), "trades.json")


# ══════════════════════════════════════════════════════════
#  数据持久化
# ══════════════════════════════════════════════════════════

def _load_trades() -> List[Dict]:
    """从 JSON 文件加载交易记录"""
    if not os.path.exists(_TRADE_FILE):
        return []
    try:
        with open(_TRADE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_trades(trades: List[Dict]) -> bool:
    """保存交易记录到 JSON 文件"""
    try:
        with open(_TRADE_FILE, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存交易记录失败: {e}")
        return False


# ══════════════════════════════════════════════════════════
#  CRUD 操作
# ══════════════════════════════════════════════════════════

def get_trades(code: str = None, trade_type: str = None) -> List[Dict]:
    """
    获取交易记录
    
    Args:
        code: 过滤指定股票代码
        trade_type: 过滤类型 "buy" 或 "sell"
    
    Returns:
        交易记录列表，按日期倒序
    """
    trades = _load_trades()
    if code:
        trades = [t for t in trades if t.get("code") == code]
    if trade_type:
        trades = [t for t in trades if t.get("type") == trade_type]
    trades.sort(key=lambda x: x.get("date", ""), reverse=True)
    return trades


def add_trade(
    code: str,
    name: str,
    trade_type: str,
    price: float,
    quantity: int,
    trade_date: str = None,
    notes: str = "",
) -> Dict:
    """
    添加一笔交易记录
    
    Args:
        code: 股票代码，如 "600519"
        name: 股票名称
        trade_type: "buy" 或 "sell"
        price: 成交价格
        quantity: 成交数量（正数）
        trade_date: 交易日期，格式 "YYYY-MM-DD"，默认今天
        notes: 备注
    
    Returns:
        新增的交易记录
    """
    if not trade_date:
        trade_date = date.today().strftime("%Y-%m-%d")
    
    trades = _load_trades()
    trade_id = f"{trade_date}_{code}_{trade_type}_{len(trades) + 1}"
    
    trade = {
        "id": trade_id,
        "code": code.strip().zfill(6),
        "name": name,
        "type": trade_type,           # "buy" 或 "sell"
        "price": float(price),
        "quantity": int(quantity),
        "date": trade_date,
        "amount": round(float(price) * int(quantity), 2),
        "notes": notes,
        "created_at": datetime.now().isoformat(),
    }
    
    trades.append(trade)
    if _save_trades(trades):
        return trade
    return {}


def delete_trade(trade_id: str) -> bool:
    """删除指定交易记录"""
    trades = _load_trades()
    before = len(trades)
    trades = [t for t in trades if t.get("id") != trade_id]
    if len(trades) < before:
        return _save_trades(trades)
    return False


def update_trade(trade_id: str, updates: Dict) -> bool:
    """更新指定交易记录"""
    trades = _load_trades()
    for i, t in enumerate(trades):
        if t.get("id") == trade_id:
            trades[i].update(updates)
            return _save_trades(trades)
    return False


# ══════════════════════════════════════════════════════════
#  持仓分析
# ══════════════════════════════════════════════════════════

def get_positions() -> List[Dict]:
    """
    计算当前持仓
    买入 - 卖出 = 剩余持仓
    
    Returns:
        持仓列表，每只股票: {code, name, shares, avg_buy_price, total_cost}
    """
    trades = _load_trades()
    positions: Dict[str, Dict] = {}
    
    for t in trades:
        code = t.get("code")
        if code not in positions:
            positions[code] = {
                "code": code,
                "name": t.get("name", code),
                "shares": 0,
                "total_cost": 0.0,
                "buy_count": 0,
                "sell_count": 0,
            }
        
        p = positions[code]
        qty = int(t.get("quantity", 0))
        price = float(t.get("price", 0))
        
        if t.get("type") == "buy":
            p["total_cost"] += qty * price
            p["shares"] += qty
            p["buy_count"] += 1
        elif t.get("type") == "sell":
            p["shares"] -= qty
            p["sell_count"] += 1
    
    # 只返回剩余持仓（shares > 0）
    result = []
    for code, p in positions.items():
        if p["shares"] > 0:
            p["avg_price"] = round(p["total_cost"] / p["shares"], 3)
            result.append(p)
    
    result.sort(key=lambda x: x.get("total_cost", 0), reverse=True)
    return result


# ══════════════════════════════════════════════════════════
#  账户汇总
# ══════════════════════════════════════════════════════════

def get_account_summary(current_prices: Dict[str, float] = None) -> Dict:
    """
    账户整体汇总
    
    Args:
        current_prices: {code: current_price}，用于计算浮动盈亏
    
    Returns:
        汇总字典
    """
    trades = _load_trades()
    if not trades:
        return _empty_summary()
    
    buys = [t for t in trades if t.get("type") == "buy"]
    sells = [t for t in trades if t.get("type") == "sell"]
    
    # 入金总额
    total_in = sum(t.get("amount", 0) for t in buys)
    # 出金总额
    total_out = sum(t.get("amount", 0) for t in sells)
    
    # 已实现盈亏（卖出收入 - 对应买入成本，这里简化计算）
    # 简化：total_out - (与卖出配对的买入平均成本 * 卖出数量)
    realized_pnl = total_out - sum(t.get("amount", 0) for t in sells)
    
    # 按股票配对计算已实现盈亏
    realized_pnl = _calc_realized_pnl(trades)
    
    # 浮动盈亏
    positions = get_positions()
    unrealized_pnl = 0.0
    if current_prices:
        for pos in positions:
            cur = current_prices.get(pos["code"])
            if cur:
                cur_value = cur * pos["shares"]
                cost = pos["total_cost"]
                unrealized_pnl += cur_value - cost
    
    total_pnl = realized_pnl + unrealized_pnl
    
    # 交易次数
    trade_count = len(trades)
    buy_count = len(buys)
    sell_count = len(sells)
    
    # 胜率（盈利交易次数 / 总平仓次数）
    closed_trades = _get_closed_trades(trades)
    win_count = sum(1 for t in closed_trades if t.get("realized_pnl", 0) > 0)
    win_rate = round(win_count / len(closed_trades) * 100, 1) if closed_trades else 0
    
    return {
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "trade_count": trade_count,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "position_count": len(positions),
        "win_count": win_count,
        "win_rate": win_rate,
        "closed_trades": len(closed_trades),
    }


def _calc_realized_pnl(trades: List[Dict]) -> float:
    """计算已实现盈亏（按FIFO配对）"""
    positions_fifo: Dict[str, List] = {}
    realized = 0.0
    
    # 按日期排序（先进先出）
    sorted_trades = sorted(trades, key=lambda x: x.get("date", ""))
    
    for t in sorted_trades:
        code = t.get("code")
        if code not in positions_fifo:
            positions_fifo[code] = []  # [(price, quantity), ...]
        
        qty = int(t.get("quantity", 0))
        price = float(t.get("price", 0))
        
        if t.get("type") == "buy":
            positions_fifo[code].append({"price": price, "qty": qty})
        elif t.get("type") == "sell":
            remaining = qty
            while remaining > 0 and positions_fifo[code]:
                lot = positions_fifo[code][0]
                if lot["qty"] <= remaining:
                    realized += (price - lot["price"]) * lot["qty"]
                    remaining -= lot["qty"]
                    positions_fifo[code].pop(0)
                else:
                    realized += (price - lot["price"]) * remaining
                    lot["qty"] -= remaining
                    remaining = 0
    
    return round(realized, 2)


def _get_closed_trades(trades: List[Dict]) -> List[Dict]:
    """获取已平仓的交易对"""
    positions_fifo: Dict[str, List] = {}
    closed = []
    
    sorted_trades = sorted(trades, key=lambda x: x.get("date", ""))
    
    for t in sorted_trades:
        code = t.get("code")
        if code not in positions_fifo:
            positions_fifo[code] = []
        
        qty = int(t.get("quantity", 0))
        price = float(t.get("price", 0))
        
        if t.get("type") == "buy":
            positions_fifo[code].append({"price": price, "qty": qty})
        elif t.get("type") == "sell":
            remaining = qty
            while remaining > 0 and positions_fifo[code]:
                lot = positions_fifo[code][0]
                pnl = (price - lot["price"]) * min(lot["qty"], remaining)
                if lot["qty"] <= remaining:
                    remaining -= lot["qty"]
                    positions_fifo[code].pop(0)
                else:
                    lot["qty"] -= remaining
                    remaining = 0
                closed.append({"code": code, "realized_pnl": pnl})
    
    return closed


def _empty_summary() -> Dict:
    return {
        "total_in": 0, "total_out": 0, "realized_pnl": 0,
        "unrealized_pnl": 0, "total_pnl": 0,
        "trade_count": 0, "buy_count": 0, "sell_count": 0,
        "position_count": 0, "win_count": 0, "win_rate": 0, "closed_trades": 0,
    }


# ══════════════════════════════════════════════════════════
#  交易历史 DataFrame
# ══════════════════════════════════════════════════════════

def get_trades_df(code: str = None) -> pd.DataFrame:
    """获取交易记录 DataFrame（用于表格展示）"""
    trades = get_trades(code=code)
    if not trades:
        return pd.DataFrame()
    
    rows = []
    for t in trades:
        rows.append({
            "ID": t.get("id", ""),
            "日期": t.get("date", ""),
            "代码": t.get("code", ""),
            "名称": t.get("name", ""),
            "方向": "买入" if t.get("type") == "buy" else "卖出",
            "价格": t.get("price", 0),
            "数量": t.get("quantity", 0),
            "金额": t.get("amount", 0),
            "备注": t.get("notes", ""),
        })
    
    return pd.DataFrame(rows)


def get_positions_df() -> pd.DataFrame:
    """获取持仓 DataFrame"""
    positions = get_positions()
    if not positions:
        return pd.DataFrame()
    
    rows = []
    for p in positions:
        rows.append({
            "代码": p.get("code", ""),
            "名称": p.get("name", ""),
            "持仓": p.get("shares", 0),
            "均价": p.get("avg_price", 0),
            "成本": p.get("total_cost", 0),
            "买入次数": p.get("buy_count", 0),
            "卖出次数": p.get("sell_count", 0),
        })
    
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════
#  格式化工具
# ══════════════════════════════════════════════════════════

def format_pnl(amount: float) -> str:
    """格式化盈亏金额，带颜色标记"""
    if amount > 0:
        return f"+{amount:.2f}"
    return f"{amount:.2f}"


def format_pct(current: float, cost: float) -> str:
    """计算收益率百分比"""
    if cost == 0:
        return "0%"
    pct = (current - cost) / cost * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.2f}%"
