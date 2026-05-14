#!/usr/bin/env python3
"""Compute trading metrics from a JSON payload via stdin.

Modeled on the Claude Skills pattern: a script that lives in a skill's
`scripts/` folder and is invoked by the agent via a bash tool call.

Input (stdin, JSON):
    {"transactions": [...], "ticker": "VRTC"}

Output (stdout, JSON):
    {"company": {...}, "transaction_count": N, "net_shares": ..., ...}
"""
from __future__ import annotations
import csv
import json
import statistics
import sys
from pathlib import Path

COMPANIES_CSV = Path(__file__).parent.parent / "data" / "companies.csv"


def compute(transactions: list[dict], ticker: str | None) -> dict:
    company_meta: dict | None = None
    if ticker:
        with COMPANIES_CSV.open() as f:
            for row in csv.DictReader(f):
                if row["ticker"] == ticker:
                    company_meta = row
                    break

    if not transactions:
        return {
            "company": company_meta,
            "transaction_count": 0,
            "total_bought_shares": 0,
            "total_sold_shares": 0,
            "net_shares": 0,
            "avg_buy_price": None,
            "avg_sell_price": None,
            "total_invested": 0.0,
            "total_divested": 0.0,
            "realized_pnl": 0.0,
            "largest_single_trade_value": 0.0,
            "anomalies": ["no transactions in range"],
        }

    buys = [t for t in transactions if t["side"] == "BUY"]
    sells = [t for t in transactions if t["side"] == "SELL"]

    total_bought = sum(t["quantity"] for t in buys)
    total_sold = sum(t["quantity"] for t in sells)
    total_invested = sum(t["quantity"] * t["price_per_share"] for t in buys)
    total_divested = sum(t["quantity"] * t["price_per_share"] for t in sells)

    avg_buy = (total_invested / total_bought) if total_bought else None
    avg_sell = (total_divested / total_sold) if total_sold else None

    realized_pnl = 0.0
    if avg_buy is not None and total_sold:
        realized_pnl = (avg_sell - avg_buy) * total_sold

    trade_values = [t["quantity"] * t["price_per_share"] for t in transactions]
    largest = max(trade_values)

    anomalies = []
    median_val = statistics.median(trade_values) if len(trade_values) >= 3 else None
    for t in transactions:
        val = t["quantity"] * t["price_per_share"]
        is_relative_outlier = median_val is not None and val > median_val * 5
        is_absolute_outlier = val > 5_000_000  # $5M+ single trade is unusual at this scale
        if is_relative_outlier or is_absolute_outlier:
            anomalies.append(
                f"unusually large {t['side']} on {t['trade_date']}: "
                f"{t['quantity']:,} shares @ ${t['price_per_share']:.2f} "
                f"= ${val:,.0f}"
            )

    if total_sold == 0:
        anomalies.append("no sells in range — full position still held")

    return {
        "company": company_meta,
        "transaction_count": len(transactions),
        "total_bought_shares": total_bought,
        "total_sold_shares": total_sold,
        "net_shares": total_bought - total_sold,
        "avg_buy_price": round(avg_buy, 2) if avg_buy else None,
        "avg_sell_price": round(avg_sell, 2) if avg_sell else None,
        "total_invested": round(total_invested, 2),
        "total_divested": round(total_divested, 2),
        "realized_pnl": round(realized_pnl, 2),
        "largest_single_trade_value": round(largest, 2),
        "anomalies": anomalies,
    }


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    result = compute(payload["transactions"], payload.get("ticker"))
    json.dump(result, sys.stdout, default=str)
