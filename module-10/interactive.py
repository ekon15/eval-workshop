"""Module 10 — Run the skill agent interactively. Watch the trace tree.

Each invocation produces a multi-span trace:
    run_skill (root)
      |- anthropic.messages.create  (LLM turn 1: decides to call query_transactions)
      |- tool:query_transactions     (executes the data fetch)
      |- anthropic.messages.create  (LLM turn 2: decides to call run_compute_script)
      |- tool:run_compute_script     (subprocess: scripts/compute_metrics.py)
      |- anthropic.messages.create  (LLM turn 3: writes the analysis)
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import run_skill


SCENARIOS = [
    ("VRTC", "2025-01-01", "2025-09-30", "normal case"),
    ("GROK", "2025-01-01", "2025-09-30", "no transactions in range"),
    ("ASPN", "2025-04-01", "2025-04-30", "anomalous trade (100x quantity)"),
    ("HRZN", "2025-01-01", "2025-09-30", "accumulation only — no sells"),
    ("XXXX", "2025-01-01", "2025-09-30", "unknown ticker, empty result"),
]


def _print_menu():
    print("\nPick a scenario:")
    for i, (ticker, start, end, note) in enumerate(SCENARIOS, 1):
        print(f"  {i}. {ticker:<5} {start} → {end}   {note}")
    print("  c. custom (enter ticker + dates)")
    print("  q. quit")


def _custom():
    ticker = input("Ticker: ").strip().upper()
    start = input("Start date (YYYY-MM-DD): ").strip()
    end = input("End date (YYYY-MM-DD): ").strip()
    return ticker, start, end


def main():
    print("Portfolio analysis skill — interactive runner.")
    while True:
        _print_menu()
        choice = input("\n> ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return
        if choice == "c":
            ticker, start, end = _custom()
        elif choice.isdigit() and 1 <= int(choice) <= len(SCENARIOS):
            ticker, start, end, _ = SCENARIOS[int(choice) - 1]
        else:
            print(f"Unknown choice: {choice!r}")
            continue

        print(f"\nRunning skill: {ticker} {start} → {end}\n")
        result = run_skill(ticker, start, end)

        print(f"Turns: {result.turns}  Tools: {[c['name'] for c in result.tool_calls]}")
        if result.tool_errors:
            print(f"Tool errors: {result.tool_errors}")
        print("\nAnalysis:")
        print(result.analysis)
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
