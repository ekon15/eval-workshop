"""Module 14 — Improved eval. Same dataset; modified system prompt with
explicit rules for each failure mode.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from braintrust import Eval
from src.agent import PROJECT
from src.analyze import analyze_metrics
from src.datasets import load_or_die

IMPROVED_SYSTEM = """You are a portfolio trading analysis skill.

You receive precomputed metrics from the warehouse + script. Write a 3-5 sentence analysis.

CRITICAL OUTPUT RULES:

  - If `transaction_count` is 0, your ENTIRE output must be:
    "No transactions were found for <ticker> in the range <start> to <end>." and stop.

  - If `anomalies` includes an "unusually large" entry, you MUST mention it explicitly with the date and dollar amount.

  - If `anomalies` includes "no sells in range — full position still held", you MUST note that the position was accumulated and is still held.

  - Otherwise: cover net position, capital deployed/divested, realized PnL, and any anomalies.

  - Ground every figure in the metrics provided. Do not invent numbers.
"""

judge = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _judge(prompt: str, name: str):
    resp = judge.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt + "\n\nRespond as JSON: {\"score\": <0|0.5|1>, \"reason\": \"<one line>\"}"}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(text)
        return {"name": name, "score": float(parsed["score"]),
                "metadata": {"reason": parsed.get("reason", "")}}
    except Exception as e:
        return {"name": name, "score": 0,
                "metadata": {"reason": f"judge error: {e}; raw: {text[:200]}"}}


def handled_correctly(input, output, expected, **_):
    return _judge(
        f"""Score whether the analysis precisely handled the failure mode. Apply STRICT criteria — vague handling counts as PARTIAL, not HANDLED.

Pick exactly ONE of:

  - HANDLED (1.0): the analysis precisely matches the requirement:
      * For "no transactions" cases: states no transactions were found and does NOT speculate about market conditions, strategy, or future activity. Sticks to the fact.
      * For "unusually large trade" cases: explicitly cites BOTH the specific dollar amount AND the trade date. Not just "a large trade".
      * For "accumulation only" cases: explicitly states the position is still held / not monetized — not just that there were buys.

  - PARTIAL (0.5): touches the topic but adds speculation, lacks the required specifics, or paraphrases without the precise framing.

  - MISSED (0.0): doesn't address the failure mode at all, or fabricates.

Query: {input}
Required behavior: {expected}
Analysis: {output}""",
        "handled_correctly",
    )


def _ensure_dict(md):
    if md is None:
        return {}
    if isinstance(md, str):
        try:
            return json.loads(md)
        except Exception:
            return {}
    return md


def task(input_str, hooks=None):
    md = _ensure_dict(hooks.metadata if (hooks is not None and hasattr(hooks, "metadata")) else None)
    return analyze_metrics(
        md.get("ticker", ""),
        md.get("start_date", ""),
        md.get("end_date", ""),
        md.get("metrics", {}),
        system_prompt=IMPROVED_SYSTEM,
    )


Eval(
    PROJECT,
    data=load_or_die("Failure Modes"),
    task=task,
    scores=[handled_correctly],
    experiment_name="module-14-improved",
)
