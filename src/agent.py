"""Multi-turn tool-using portfolio analysis skill agent.

Built on Anthropic tool use. The agent loop:

    LLM turn 1:  emits tool_use -> query_transactions(ticker, start, end)
    Tool:        returns rows from transactions.csv
    LLM turn 2:  emits tool_use -> run_compute_script(transactions, ticker)
    Tool:        subprocess invokes scripts/compute_metrics.py
    LLM turn N:  produces the written analysis (no more tool_use)

Tracing uses explicit start_span context managers so the trace tree is:

    run_skill (root)
      |- llm_turn_1
      |- tool:query_transactions
      |- llm_turn_2
      |- tool:run_compute_script
      |- llm_turn_3   (writes the analysis)

Each span's input/output is set explicitly to plain strings/dicts so the UI
shows clean values instead of raw Anthropic content blocks.
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

_logger = braintrust.init_logger(project=PROJECT)

_client = None
def get_client():
    global _client
    if _client is None:
        if os.environ.get("USE_BRAINTRUST_PROXY"):
            _client = anthropic.Anthropic(
                api_key=os.environ["BRAINTRUST_API_KEY"],
                base_url="https://api.braintrust.dev/v1/proxy",
            )
        else:
            _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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


def _block_to_dict(block):
    """Flatten an Anthropic response block to a plain dict for logging."""
    t = getattr(block, "type", None)
    if t == "text":
        return {"type": "text", "text": block.text}
    if t == "tool_use":
        return {"type": "tool_use", "name": block.name, "input": block.input}
    return {"type": t, "repr": str(block)}


def _summarize_messages(messages):
    """Flat, readable view of the conversation so far for span input."""
    out = []
    for m in messages:
        role = m["role"]
        c = m["content"]
        if isinstance(c, str):
            out.append({"role": role, "text": c})
        elif isinstance(c, list):
            parts = []
            for block in c:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        body = block.get("content", "")
                        if isinstance(body, str) and len(body) > 400:
                            body = body[:400] + "...[truncated]"
                        parts.append({"type": "tool_result", "content": body,
                                      "is_error": block.get("is_error", False)})
                    else:
                        parts.append(block)
                else:
                    parts.append(_block_to_dict(block))
            out.append({"role": role, "blocks": parts})
    return out


def _execute_tool(name: str, args: dict):
    if name == "query_transactions":
        with braintrust.start_span(name="tool:query_transactions", type="tool") as span:
            r = query_transactions(args["ticker"], args["start_date"], args["end_date"])
            span.log(input=args, output={"row_count": len(r), "rows": r})
            return r
    if name == "run_compute_script":
        with braintrust.start_span(name="tool:run_compute_script", type="tool") as span:
            r = run_compute_script(args["transactions"], args["ticker"])
            span.log(
                input={"transaction_count": len(args["transactions"]), "ticker": args["ticker"]},
                output=r,
            )
            return r
    raise ValueError(f"unknown tool: {name}")


def run_skill(ticker: str, start_date: str, end_date: str,
              system_prompt: str | None = None) -> AgentResult:
    """Run the skill end-to-end. Returns AgentResult with analysis + tool trace."""
    system = system_prompt or SKILL_SYSTEM
    user_msg = f"Analyze portfolio transactions for ticker {ticker} from {start_date} to {end_date}."
    messages: list[dict] = [{"role": "user", "content": user_msg}]

    client = get_client()
    tool_calls: list[dict] = []
    tool_errors: list[str] = []
    final_text = ""
    stop_reason = ""

    with _logger.start_span(name="run_skill", type="task") as root:
        root.log(input=user_msg)

        for turn_idx in range(1, MAX_TURNS + 1):
            with braintrust.start_span(name=f"llm_turn_{turn_idx}", type="llm") as llm_span:
                resp = client.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                )
                stop_reason = resp.stop_reason or ""
                resp_blocks = [_block_to_dict(b) for b in resp.content]
                llm_span.log(
                    input={"messages": _summarize_messages(messages), "system": system[:300] + ("..." if len(system) > 300 else "")},
                    output=resp_blocks,
                    metadata={
                        "model": MODEL,
                        "stop_reason": stop_reason,
                        "input_tokens": getattr(resp.usage, "input_tokens", None),
                        "output_tokens": getattr(resp.usage, "output_tokens", None),
                    },
                )

            if stop_reason != "tool_use":
                for block in resp.content:
                    if getattr(block, "type", None) == "text":
                        final_text = block.text
                break

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

        root.log(
            output=final_text,
            metadata={
                "tool_call_count": len(tool_calls),
                "tools_used": [c["name"] for c in tool_calls],
                "stop_reason": stop_reason,
                "tool_errors": tool_errors,
            },
        )

    braintrust.flush()

    return AgentResult(
        analysis=final_text,
        tool_calls=tool_calls,
        turns=len(messages),
        stopped_for=stop_reason,
        tool_errors=tool_errors,
    )
