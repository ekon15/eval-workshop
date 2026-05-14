"""One-time generator for the synthetic workshop data.

Writes:
  data/companies.csv      — ticker, name, sector, country, status
  data/transactions.csv   — id, ticker, trade_date, side, quantity, price_per_share, portfolio_id

The CSVs are the canonical source of truth — committed alongside the repo.
Re-run this only if you want to regenerate them.
"""
from __future__ import annotations
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

HERE = Path(__file__).parent

COMPANIES = [
    # ticker, name, sector, country, status
    ("VRTC", "Vertica Industries",   "Industrials",    "US", "active"),
    ("NBLA", "Nubela Corp",          "Technology",     "US", "renamed_from_old_name_corp"),
    ("TLKM", "TeleKom Holdings",     "Communications", "DE", "active"),
    ("HRZN", "Horizon Materials",    "Materials",      "NO", "active"),
    ("ASPN", "Aspen Energy",         "Energy",         "NO", "active"),
    ("KMRL", "Kameral Pharma",       "Healthcare",     "CH", "active"),
    ("FJDL", "Fjordal Banking",      "Financials",     "NO", "active"),
    ("OSLB", "Oslo Beverages",       "Consumer",       "NO", "active"),
    ("CLVR", "Clavier Software",     "Technology",     "FR", "active"),
    ("GROK", "Grokstad Mining",      "Materials",      "NO", "active"),  # easter egg: no transactions
]


def main():
    with (HERE / "companies.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "sector", "country", "status"])
        w.writerows(COMPANIES)

    transactions: list[tuple] = []
    start = date(2025, 1, 1)
    next_id = 1

    for ticker, *_ in COMPANIES:
        if ticker == "GROK":
            continue   # easter egg 1: no transactions
        n = random.randint(8, 20)
        for _ in range(n):
            trade_date = start + timedelta(days=random.randint(0, 270))
            side = "BUY" if ticker == "HRZN" else random.choice(["BUY", "SELL"])  # easter egg 2
            quantity = random.choice([100, 250, 500, 1000, 2500])
            price = round(random.uniform(45.0, 280.0), 2)
            transactions.append((next_id, ticker, trade_date.isoformat(), side, quantity, price, "PORT-001"))
            next_id += 1

    # easter egg 3: one anomalous ASPN trade (off by 100x in quantity)
    transactions.append((next_id, "ASPN", "2025-04-15", "BUY", 250000, 87.50, "PORT-001"))
    transactions.sort(key=lambda r: (r[1], r[2]))  # sort by ticker, date

    with (HERE / "transactions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "ticker", "trade_date", "side", "quantity", "price_per_share", "portfolio_id"])
        w.writerows(transactions)

    print(f"Wrote {len(COMPANIES)} companies and {len(transactions)} transactions.")


if __name__ == "__main__":
    main()
