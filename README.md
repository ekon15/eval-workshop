# Eval Workshop — Hands-on

A multi-turn tool-using skill agent for the eval workshop, with four modules that walk the eval flywheel.

## The agent

Anthropic tool-use loop. Input: a ticker + a date range.

```
run_skill (root)
  ├── anthropic.messages.create   LLM turn 1 — decides to call query_transactions
  ├── tool:query_transactions      data fetch (mocks Snowflake MCP, reads CSV)
  ├── anthropic.messages.create   LLM turn 2 — decides to call run_compute_script
  ├── tool:run_compute_script      subprocess → scripts/compute_metrics.py
  └── anthropic.messages.create   LLM turn 3 — writes the analysis
```

The agent mirrors the Claude Skills shape (instructions + tool calls + `scripts/` directory). In production the data-fetch step is a Snowflake MCP call; here it's a CSV read so the workshop has zero connectivity.

## Setup

```bash
# Clone
git clone https://github.com/ekon15/eval-workshop
cd eval-workshop

# Virtual env
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# API keys (export in your shell or use a .env loader)
export BRAINTRUST_API_KEY="..."
export ANTHROPIC_API_KEY="..."

# Verify
python3 -c "import braintrust, anthropic; print('OK')"
```

> Note: `pip install braintrust` also installs a `bt` CLI binary. This workshop uses the Python SDK throughout — the CLI is not required and not used in any module.

In the Braintrust UI for your project, upload the two datasets via **Datasets → New Dataset**. The UI auto-names them based on the filename — accept the defaults:

  - `Gold Standard` ← `data/gold_standard.csv`
  - `Failure Modes` ← `data/failure_modes.csv`

Other CSVs (`companies.csv`, `transactions.csv`) are the agent's data source — they stay local and don't need to be uploaded.

## Walk through the modules in this order

Tick each one off as you go. Each module has its own README with the detail.

- [ ] **1. Module 06 — Code eval.** See `module-06/README.md`
- [ ] **2. Module 10 — Multi-step agent + tracing.** See `module-10/README.md`
- [ ] **3. Module 12 — Online scoring.** See `module-12/README.md`
- [ ] **4. Module 14 — Improvement loop.** See `module-14/README.md`

## Why the modules split offline vs online

Modules 06 and 14 isolate the analysis step (single LLM call per row, metrics pre-computed in dataset metadata). Modules 10 and 12 run the full multi-turn tool-using agent. This split keeps offline evals fast and deterministic while still demonstrating the agentic loop end-to-end.

To rebuild the metrics-enriched CSVs (e.g., after editing the seed lists or upstream tools):

```bash
python data/build_metrics_dataset.py
```

## Built-in failure modes

Wired into the data so attendees have real failures to investigate. Surface across modules 06 / 10 / 14:

- **GROK** — zero transactions in any range
- **ASPN** — one trade off by 100x in quantity (≈ $21.8M)
- **HRZN** — only buys, no sells
- **XXXX** — unknown ticker; query returns empty

## Project

Traces land in the Braintrust project `eval-workshop` (override via `BRAINTRUST_PROJECT`).
