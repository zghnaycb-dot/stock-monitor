# -*- coding: utf-8 -*-
"""Price alert system - set and monitor price alerts"""

import json
import os
import streamlit as st
from typing import List, Dict
from datetime import datetime

ALERTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alerts.json")


def load_alerts() -> List[Dict]:
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_alerts(alerts: List[Dict]):
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def add_alert(code: str, name: str, alert_type: str, value: float) -> Dict:
    alerts = load_alerts()
    alert = {
        "id": f"{code}_{alert_type}_{int(datetime.now().timestamp())}",
        "code": code,
        "name": name,
        "type": alert_type,
        "value": value,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "triggered": False,
    }
    alerts.append(alert)
    save_alerts(alerts)
    return alert


def delete_alert(alert_id: str):
    alerts = load_alerts()
    alerts = [a for a in alerts if a["id"] != alert_id]
    save_alerts(alerts)


def check_alerts(quotes: List[Dict]) -> List[Dict]:
    """Check alerts against current prices. Returns list of triggered alerts."""
    alerts = load_alerts()
    triggered = []
    modified = False
    for alert in alerts:
        if alert.get("triggered"):
            continue
        quote = next((q for q in quotes if q.get("code") == alert["code"]), None)
        if not quote:
            continue
        current = quote.get("price", 0)
        trigger = False
        pct = quote.get("change_pct", 0)
        if alert["type"] == "price_above" and current >= alert["value"]:
            trigger = True
        elif alert["type"] == "price_below" and current <= alert["value"]:
            trigger = True
        elif alert["type"] == "pct_above" and pct >= alert["value"]:
            trigger = True
        elif alert["type"] == "pct_below" and pct <= alert["value"]:
            trigger = True
        if trigger:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            alert["current"] = current
            triggered.append(alert)
            modified = True
    if modified:
        save_alerts(alerts)
    return triggered


def render_alerts_sidebar(quotes: List[Dict]) -> None:
    """Render alert management UI in sidebar"""
    st.markdown("---")
    st.markdown("### [ALERT] Price Alert")

    alerts = load_alerts()
    active = [a for a in alerts if not a.get("triggered")]
    triggered_alerts = [a for a in alerts if a.get("triggered")]

    # Show triggered alerts
    if triggered_alerts:
        st.markdown("**Triggered:**")
        for a in triggered_alerts[:3]:
            type_label = {
                "price_above": "Price Break Above",
                "price_below": "Price Break Below",
                "pct_above": "Gain Exceeds",
                "pct_below": "Loss Exceeds",
            }
            st.warning(f"{a['name']} {type_label.get(a['type'], a['type'])} {a['value']}")

    st.markdown(f"Active alerts: {len(active)}")

    # Add new alert
    with st.expander("+Add Alert", expanded=False):
        alert_type = st.selectbox(
            "Alert Type",
            ["price_above", "price_below", "pct_above", "pct_below"],
            format_func=lambda x: {
                "price_above": "Price Break Above",
                "price_below": "Price Break Below",
                "pct_above": "Gain Exceeds (%)",
                "pct_below": "Loss Exceeds (%)",
            }.get(x, x),
            key="alert_type",
            label_visibility="collapsed",
        )
        if "pct" in alert_type:
            alert_val = st.number_input("Threshold (%):", value=5.0, step=0.5, key="alert_pct_val")
        else:
            alert_val = st.number_input("Threshold (Price):", value=10.0, step=0.01, key="alert_price_val")

        alert_stock = st.selectbox(
            "Monitor Stock",
            [q.get("name", q.get("code", "")) for q in quotes] if quotes else ["No data"],
            key="alert_stock",
        )
        if st.button("Add Alert", key="add_alert_btn"):
            q = next((q for q in quotes if q.get("name") == alert_stock or q.get("code") == alert_stock), None)
            if q:
                add_alert(q["code"], q.get("name", q["code"]), alert_type, alert_val)
                st.success("Alert set!")
                st.rerun()

    # List active alerts
    if active:
        for a in active[:5]:
            type_str = {
                "price_above": f"Price > {a['value']}",
                "price_below": f"Price < {a['value']}",
                "pct_above": f"Gain > {a['value']}%",
                "pct_below": f"Loss > {a['value']}%",
            }.get(a["type"], a["type"])
            col_a, col_d = st.columns([4, 1])
            with col_a:
                st.caption(f"{a['name']} - {type_str}")
            with col_d:
                if st.button("Del", key=f"del_alert_{a['id']}"):
                    delete_alert(a["id"])
                    st.rerun()
    else:
        st.caption("No active alerts")
