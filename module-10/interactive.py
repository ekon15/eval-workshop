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


def main():
    print("Portfolio analysis skill — interactive runner.")
    print("Enter a ticker, then a start and end date (YYYY-MM-DD).")
    print("Type 'quit' to exit.\n")

    while True:
        ticker = input("Ticker: ").strip().upper()
        if ticker.lower() in ("quit", "exit", "q"):
            return
        start = input("Start date (YYYY-MM-DD): ").strip()
        end = input("End date (YYYY-MM-DD): ").strip()

        print("\nRunning skill...\n")
        result = run_skill(ticker, start, end)

        print(f"Turns: {result.turns}")
        print(f"Tools used: {[c['name'] for c in result.tool_calls]}")
        if result.tool_errors:
            print(f"Tool errors: {result.tool_errors}")
        print("\nAnalysis:")
        print(result.analysis)
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
