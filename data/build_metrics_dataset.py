"""Build the metrics-enriched datasets used by module-06 and module-14.

For each row in the gold-standard / failure-modes input list, we run the
deterministic upstream steps (query_transactions + run_compute_script) and
capture the resulting metrics. The metrics get written into the dataset CSV
so the eval can target just the analysis step.

Output CSVs:
  data/gold_standard.csv       — for module-06
  data/failure_modes.csv       — for module-14

These are the canonical dataset files to upload via the Braintrust UI.

Run once after changing the upstream tools or the seed lists:
    python data/build_metrics_dataset.py
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools import query_transactions, run_compute_script

HERE = Path(__file__).parent

GOLD_STANDARD = [
    ("VRTC", "2025-01-01", "2025-09-30",
     "cover net position, average buy and sell prices, realized PnL"),
    ("NBLA", "2025-01-01", "2025-09-30",
     "cover net position and realized PnL"),
    ("TLKM", "2025-01-01", "2025-09-30",
     "cover net position and realized PnL"),
    ("HRZN", "2025-01-01", "2025-09-30",
     "note that position was accumulated only — no sells"),
    ("ASPN", "2025-04-01", "2025-04-30",
     "must flag the unusually large trade as an anomaly"),
    ("ASPN", "2025-01-01", "2025-09-30",
     "must flag the unusually large trade"),
    ("KMRL", "2025-01-01", "2025-09-30", "summarize net position and PnL"),
    ("FJDL", "2025-01-01", "2025-09-30", "summarize net position and PnL"),
    ("OSLB", "2025-01-01", "2025-09-30", "summarize net position and PnL"),
    ("CLVR", "2025-01-01", "2025-09-30", "summarize net position and PnL"),
    ("GROK", "2025-01-01", "2025-09-30",
     "must state there were no transactions in the range"),
    ("XXXX", "2025-01-01", "2025-09-30",
     "must state there were no transactions for this ticker"),
    ("VRTC", "2025-01-01", "2025-02-28",
     "narrow window — smaller transaction count"),
    ("NBLA", "2025-06-01", "2025-09-30", "second-half-only window for NBLA"),
    ("HRZN", "2025-07-01", "2025-09-30", "Q3 window — accumulation only"),
]

FAILURE_MODES = [
    ("GROK", "2025-01-01", "2025-09-30",
     "must explicitly state no transactions in the range"),
    ("XXXX", "2025-01-01", "2025-09-30",
     "must explicitly state no transactions for this ticker"),
    ("ASPN", "2025-04-01", "2025-04-30",
     "must flag the unusually large trade"),
    ("ASPN", "2025-01-01", "2025-09-30",
     "must flag the unusually large trade"),
    ("HRZN", "2025-01-01", "2025-09-30",
     "must mention accumulation only / no sells"),
    ("HRZN", "2025-07-01", "2025-09-30",
     "must mention accumulation only / no sells"),
]


def build_row(ticker: str, start: str, end: str, expected: str) -> dict:
    """Run the upstream tool steps and return a flat dataset row.

    Metadata is collapsed into a single JSON column so the Braintrust UI
    upload only requires moving one field (instead of four) into the
    Metadata section.
    """
    rows = query_transactions(ticker, start, end)
    metrics = run_compute_script(rows, ticker)
    metadata = {
        "ticker": ticker,
        "start_date": start,
        "end_date": end,
        "metrics": metrics,
    }
    return {
        "input": f"Analyze portfolio transactions for ticker {ticker} from {start} to {end}.",
        "expected": expected,
        "metadata": json.dumps(metadata, default=str, separators=(",", ":")),
    }


def write_csv(path: Path, rows: list[dict]) -> int:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    gold = [build_row(*r) for r in GOLD_STANDARD]
    n = write_csv(HERE / "gold_standard.csv", gold)
    print(f"Wrote {n} rows → data/gold_standard.csv")

    failure = [build_row(*r) for r in FAILURE_MODES]
    m = write_csv(HERE / "failure_modes.csv", failure)
    print(f"Wrote {m} rows → data/failure_modes.csv")


if __name__ == "__main__":
    main()
