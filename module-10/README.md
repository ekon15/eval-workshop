# Module 10 — Multi-step tool-using agent with tracing

Run the skill agent interactively. Watch the multi-turn agentic loop play out in the Braintrust trace tree.

## What you'll see

Each invocation produces this kind of trace:

```
run_skill (root)
  ├── anthropic.messages.create   LLM turn 1 — emits tool_use: query_transactions
  ├── tool:query_transactions     fetched rows
  ├── anthropic.messages.create   LLM turn 2 — emits tool_use: run_compute_script
  ├── tool:run_compute_script     subprocess output: metrics
  └── anthropic.messages.create   LLM turn 3 — final analysis text
```

Click into each LLM call to see the messages sent (including the tool definitions and prior tool results). Click into each tool span to see the inputs and outputs.

## Run

```bash
python3 module-10/interactive.py
```

Try at least 5 invocations. Suggested inputs to surface the built-in failure modes:

| Ticker | Start       | End         | Look for |
|--------|-------------|-------------|----------|
| VRTC   | 2025-01-01  | 2025-09-30  | normal case |
| GROK   | 2025-01-01  | 2025-09-30  | no transactions in range |
| ASPN   | 2025-04-01  | 2025-04-30  | anomalous trade |
| HRZN   | 2025-01-01  | 2025-09-30  | accumulation only |
| XXXX   | 2025-01-01  | 2025-09-30  | unknown ticker, empty result |

## Checkpoint

Open the project's Logs view. Find your runs. The root `run_skill` span should have `input` and `output` populated, and you should see the alternating LLM-turn / tool spans inside.
