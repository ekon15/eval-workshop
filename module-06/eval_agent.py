"""Module 06 — Code eval targeting the analysis step.

The dataset rows already contain precomputed metrics in metadata. Each eval
row makes exactly ONE LLM call (the analysis), so the eval is fast,
deterministic, and isolates the prompt as the variable being tested.

Usage:
    python module-06/eval_agent.py

Pre-req: upload data/gold_standard.csv as a Braintrust dataset named
'gold-standard' in your project.
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


def analysis_completeness(input, output, expected, **_):
    return _judge(
        f"""Score how completely this analysis covers the expected topics. Apply STRICT criteria — generic mentions count as PARTIAL, not COMPLETE.

Pick exactly ONE of:
  - COMPLETE (1.0): the analysis explicitly cites EACH expected topic with specific figures from the metrics — no vague paraphrasing, no skipped topics, no editorial filler
  - PARTIAL  (0.5): touches the expected topics but is vague, paraphrases without specifics, omits one topic, or pads with speculation
  - MISSING  (0.0): misses two or more expected topics entirely

Query: {input}
Expected coverage: {expected}
Analysis: {output}""",
        "analysis_completeness",
    )


def analysis_groundedness(input, output, expected, metadata=None, **_):
    md = _ensure_dict(metadata)
    metrics_json = json.dumps(md.get("metrics", {}), default=str)
    return _judge(
        f"""Score whether every numeric or quantitative claim in the analysis is grounded VERBATIM in the metrics. Apply VERY STRICT criteria.

Pick exactly ONE of:

  - GROUNDED  (1.0): every figure appears in the metrics with identical units, precision, and formatting:
      * "21800000" stays "21,800,000" or "$21,800,000" — NOT "$21.8M" or "$21.8 million"
      * Dates stay in the ISO form they appear in the metrics — NOT "April 15" or "mid-April"
      * No percentages computed by the analysis that aren't in the metrics
      * No qualitative substitutions for numbers ("substantial", "significant", "modest", "a large")

  - PARTIAL   (0.5): figures match in essence but are reformatted or characterized — for example:
      * Abbreviated currency ($21.8M, $21.8 million, ~$22M)
      * Reformatted dates (April 15, mid-April, April 2025)
      * Computed percentages or ratios not present in the metrics
      * Vague quantifiers ("substantial", "significant", "large", "small") replacing exact figures
      * Trivial rounding (e.g., 21,847,392 → 21.8M)

  - FABRICATED (0.0): cites figures not in the metrics, or contradicts the metrics

Metrics: {metrics_json}
Analysis: {output}""",
        "analysis_groundedness",
    )


def _ensure_dict(md):
    """Metadata comes back parsed when the dataset column was named 'metadata'.
    If it's still a JSON string (e.g. legacy upload), parse it."""
    if md is None:
        return {}
    if isinstance(md, str):
        try:
            return json.loads(md)
        except Exception:
            return {}
    return md


def task(input_str, hooks=None):
    """Pull metrics from the dataset row's metadata, call the analysis LLM."""
    md = _ensure_dict(hooks.metadata if (hooks is not None and hasattr(hooks, "metadata")) else None)
    return analyze_metrics(
        md.get("ticker", ""),
        md.get("start_date", ""),
        md.get("end_date", ""),
        md.get("metrics", {}),
    )


Eval(
    PROJECT,
    data=load_or_die("Gold Standard"),
    task=task,
    scores=[analysis_completeness, analysis_groundedness],
    experiment_name="module-06-baseline",
)
