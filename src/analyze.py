"""Isolated analysis step — the LLM call that turns metrics into narrative.

Used by module-06 and module-14 evals to test the analysis prompt in
isolation (no upstream tool calls per row, just one LLM call).
"""
from __future__ import annotations
import json
import os

import anthropic
import braintrust

from .prompts import ANALYSIS_BASELINE

MODEL = os.environ.get("EVAL_MODEL", "claude-haiku-4-5-20251001")

# Default user-message template — substitutes metrics into the prompt.
DEFAULT_USER_TEMPLATE = """Company: {company_name} ({ticker})
Date range: {start_date} to {end_date}

Precomputed metrics from the warehouse + script:
{metrics_json}

Write the analysis."""

_client = None
def _get_client():
    global _client
    if _client is None:
        if os.environ.get("USE_BRAINTRUST_PROXY"):
            _client = braintrust.wrap_anthropic(
                anthropic.Anthropic(
                    api_key=os.environ["BRAINTRUST_API_KEY"],
                    base_url="https://api.braintrust.dev/v1/proxy",
                )
            )
        else:
            _client = braintrust.wrap_anthropic(
                anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            )
    return _client


@braintrust.traced(name="analyze_metrics", type="task")
def analyze_metrics(ticker: str, start_date: str, end_date: str,
                    metrics: dict,
                    system_prompt: str | None = None,
                    user_template: str | None = None) -> str:
    """Single LLM call: metrics → written analysis."""
    span = braintrust.current_span()
    span.log(input={"ticker": ticker, "start_date": start_date, "end_date": end_date,
                    "metrics": metrics})

    sys_prompt = system_prompt or ANALYSIS_BASELINE
    template = user_template or DEFAULT_USER_TEMPLATE
    company_name = (metrics.get("company") or {}).get("name", ticker)

    user_msg = template.format(
        company_name=company_name,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        metrics_json=json.dumps(metrics, indent=2, default=str),
    )

    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=sys_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    span.log(output=text)
    return text
