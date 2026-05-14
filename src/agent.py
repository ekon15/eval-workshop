"""Multi-turn tool-using portfolio analysis skill agent.

Built on Anthropic tool use. The agent loop:

    LLM turn 1:  emits tool_use → query_transactions(ticker, start, end)
    Tool:        returns rows from transactions.csv
    LLM turn 2:  emits tool_use → run_compute_script(transactions, ticker)
    Tool:        subprocess invokes scripts/compute_metrics.py
    LLM turn N:  produces the written analysis (no more tool_use)

Each LLM turn and each tool execution is its own Braintrust span under the
root `run_skill` span. The trace tree looks like a real agentic workflow.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field

import anthropic
import braintrust

from .tools import query_transactions, run_compute_script
from .prompts import SKILL_SYSTEM

PROJECT = os.environ.get("BRAINTRUST_PROJECT", "eval-workshop")
MODEL = os.environ.get("EVAL_MODEL", "claude-haiku-4-5-20251001")
MAX_TURNS = 6

braintrust.init_logger(project=PROJECT)

_client = None
def get_client():
    global _client
    if _client is None:
        # Default: hit Anthropic directly. Braintrust still traces via wrap_anthropic.
        # Opt-in proxy: set USE_BRAINTRUST_PROXY=1 to route model calls through
        # the Braintrust proxy (gives caching + cost tracking).
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


TOOLS = [
    {
        "name": "query_transactions",
        "description": (
            "Fetch portfolio transactions for a given ticker over a date range. "
            "Returns a list of transaction rows (id, ticker, trade_date, side, "
            "quantity, price_per_share, portfolio_id). In production this would "
            "be a SQL query against the data warehouse."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
                "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
            "required": ["ticker", "start_date", "end_date"],
        },
    },
    {
        "name": "run_compute_script",
        "description": (
            "Execute scripts/compute_metrics.py to compute trading metrics over "
            "the transactions. Returns totals, averages, realized PnL, and "
            "anomaly flags."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "description": "List of transactions from query_transactions",
                    "items": {"type": "object"},
                },
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["transactions", "ticker"],
        },
    },
]


@dataclass
class AgentResult:
    analysis: str
    tool_calls: list[dict] = field(default_factory=list)
    turns: int = 0
    stopped_for: str = ""
    tool_errors: list[str] = field(default_factory=list)


def _execute_tool(name: str, args: dict):
    if name == "query_transactions":
        @braintrust.traced(name="tool:query_transactions", type="tool")
        def _t():
            r = query_transactions(args["ticker"], args["start_date"], args["end_date"])
            braintrust.current_span().log(input=args, output={"row_count": len(r), "rows": r})
            return r
        return _t()
    if name == "run_compute_script":
        @braintrust.traced(name="tool:run_compute_script", type="tool")
        def _t():
            r = run_compute_script(args["transactions"], args["ticker"])
            braintrust.current_span().log(
                input={"transaction_count": len(args["transactions"]), "ticker": args["ticker"]},
                output=r,
            )
            return r
        return _t()
    raise ValueError(f"unknown tool: {name}")


@braintrust.traced(name="run_skill")
def run_skill(ticker: str, start_date: str, end_date: str,
              system_prompt: str | None = None) -> AgentResult:
    """Run the skill end-to-end. Returns AgentResult with analysis + tool trace."""
    span = braintrust.current_span()
    span.log(input={"ticker": ticker, "start_date": start_date, "end_date": end_date})

    system = system_prompt or SKILL_SYSTEM
    user_msg = f"Analyze portfolio transactions for ticker {ticker} from {start_date} to {end_date}."
    messages: list[dict] = [{"role": "user", "content": user_msg}]

    client = get_client()
    tool_calls: list[dict] = []
    tool_errors: list[str] = []
    final_text = ""
    stop_reason = ""

    for _ in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        stop_reason = resp.stop_reason or ""

        if stop_reason != "tool_use":
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    final_text = block.text
            break

        # Append assistant turn with the tool_use blocks
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            tool_calls.append({"name": block.name, "input": block.input})
            try:
                result = _execute_tool(block.name, block.input)
                content = json.dumps(result, default=str)
                is_error = False
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                tool_errors.append(f"{block.name}: {err}")
                content = json.dumps({"error": err})
                is_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    span.log(
        output=final_text,
        metadata={
            "tool_call_count": len(tool_calls),
            "tools_used": [c["name"] for c in tool_calls],
            "stop_reason": stop_reason,
            "tool_errors": tool_errors,
        },
    )

    # Force span finalization so the trace tree is fully populated in the UI
    # before the caller checks it. Without this, late spans can show as
    # "in progress" if the SDK batches the flush.
    braintrust.flush()

    return AgentResult(
        analysis=final_text,
        tool_calls=tool_calls,
        turns=len(messages),
        stopped_for=stop_reason,
        tool_errors=tool_errors,
    )
