"""Tool implementations exposed to the agent.

The agent calls these via Anthropic tool use. Each tool is a small, traced
operation that mirrors what a production skill would actually do.

  query_transactions   — mocks a Snowflake MCP call. Reads transactions.csv,
                          filters by ticker + date range.
  run_compute_script   — invokes scripts/compute_metrics.py via subprocess
                          (the 'bash' tool pattern). Passes transactions
                          via stdin as JSON.
"""
from __future__ import annotations
import csv
import json
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
TRANSACTIONS_CSV = DATA_DIR / "transactions.csv"


def query_transactions(ticker: str, start_date: str, end_date: str) -> list[dict]:
    """Filter transactions.csv by ticker + ISO date range."""
    rows: list[dict] = []
    with TRANSACTIONS_CSV.open() as f:
        for r in csv.DictReader(f):
            if r["ticker"] != ticker:
                continue
            if not (start_date <= r["trade_date"] <= end_date):
                continue
            rows.append({
                "id": int(r["id"]),
                "ticker": r["ticker"],
                "trade_date": r["trade_date"],
                "side": r["side"],
                "quantity": int(r["quantity"]),
                "price_per_share": float(r["price_per_share"]),
                "portfolio_id": r["portfolio_id"],
            })
    rows.sort(key=lambda x: x["trade_date"])
    return rows


def run_compute_script(transactions: list[dict], ticker: str) -> dict:
    """Invoke scripts/compute_metrics.py via subprocess. Passes JSON via stdin.

    Returns the parsed JSON metrics. Raises RuntimeError on script failure.
    """
    payload = json.dumps({"transactions": transactions, "ticker": ticker})
    result = subprocess.run(
        ["python3", str(SCRIPTS_DIR / "compute_metrics.py")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"compute_metrics.py failed: {result.stderr}")
    return json.loads(result.stdout)
