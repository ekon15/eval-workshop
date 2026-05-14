"""Module 12 — Generate varied skill runs for online scoring.

Configure online scorers in the Braintrust UI BEFORE running this — fresh
logs will then be scored server-side as they land.
"""
from __future__ import annotations
import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import run_skill

random.seed(7)

TICKERS = ["VRTC", "NBLA", "TLKM", "HRZN", "ASPN", "KMRL",
           "FJDL", "OSLB", "CLVR", "GROK", "XXXX"]

DATE_RANGES = [
    ("2025-01-01", "2025-03-31"),
    ("2025-04-01", "2025-06-30"),
    ("2025-07-01", "2025-09-30"),
    ("2025-01-01", "2025-09-30"),
]


def main():
    print("Generating skill runs for online scoring...")
    for ticker in TICKERS:
        for start, end in random.sample(DATE_RANGES, 2):
            result = run_skill(ticker, start, end)
            print(f"  {ticker} [{start} → {end}] turns={result.turns} tools={[c['name'] for c in result.tool_calls]}")
    print("Done. Open the Logs view to see online scores attach.")


if __name__ == "__main__":
    main()
