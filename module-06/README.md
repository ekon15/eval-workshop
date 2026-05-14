# Module 06 — Build a simple eval in code

Run an eval against the `Gold Standard` dataset and score 15 rows with two LLM-as-judge scorers.

## What you'll see

Each dataset row already contains the precomputed metrics in metadata (the SQL fetch and Python compute have been pre-run). The eval makes a single LLM call per row — the analysis step — and scores the result.

Two scorers, both discrete categorical (COMPLETE / PARTIAL / MISSING):

- `analysis_completeness` — does the analysis cover position direction, capital, PnL, anomalies?
- `analysis_groundedness` — are the numbers cited in the analysis traceable to the metrics?

## Run

```bash
python3 module-06/eval_agent.py
```

Open the experiment URL in Braintrust. Inspect:

- Rows that scored 1.0 on both scorers — clean
- Rows that scored 0.5 on `analysis_groundedness` — analysis fabricated or rounded sloppily
- Rows that scored 0.5 or 0.0 on `analysis_completeness` — analysis missed required topics

## Checkpoint

15 rows scored. Click into a failing row and read the judge's `reason` — that's the signal you'd act on in the improvement loop (module 14).

## Built-in failure modes to notice

- **GROK** — zero transactions in range; analysis should state so
- **ASPN** — one anomalous trade (~$21.8M); analysis should flag it
- **HRZN** — only buys, no sells; analysis should note accumulation
- **XXXX** — unknown ticker; analysis should state no transactions found
