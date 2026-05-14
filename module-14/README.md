# Module 14 — The improvement loop

You'll spot a failure pattern in the baseline, propose a prompt change, rerun, and verify in the eval.

## Dataset

Both runs evaluate against the **Failure Modes** dataset (6 rows) — not Gold Standard. Each row is one of the engineered failure modes the analysis step should handle:

- empty result (no transactions in range)
- anomaly (unusually large trade)
- accumulation only (buys but no sells)
- unresolved company (unknown ticker)

This is deliberately a tiny, focused dataset — the point is to see the improvement loop, not to grind statistics.

## What you'll do

1. **Run the baseline.** Uses the default `ANALYSIS_BASELINE` prompt from `src/prompts.py` — a generic "junior analyst" prompt with no explicit failure-mode rules.
2. **Open the experiment** in Braintrust. Inspect rows that scored < 1.0 on `handled_correctly`. Read the judge's rationale.
3. **Run the improved version.** Same task, same dataset, same scorer — only the system prompt changes. The improved prompt (`IMPROVED_SYSTEM` in `eval_improved.py`) adds explicit `CRITICAL OUTPUT RULES` for each failure mode:
    - `transaction_count == 0` → exact one-line output, no speculation
    - `anomalies` includes "unusually large" → must cite date and dollar amount
    - `anomalies` includes "no sells in range" → must note position is still held
4. **Compare experiments side-by-side.** Did the metric move?

## Run

```bash
python3 module-14/eval_baseline.py     # produces module-14-baseline
python3 module-14/eval_improved.py     # produces module-14-improved
```

## Checkpoint

Two experiments visible in the project. Pick "Compare experiments" → select baseline + improved → look at the `handled_correctly` score delta per row.

## Discussion

Expected behavior: the improved prompt should lift `handled_correctly` on the empty-result, accumulation-only, and unresolved-company rows. The anomaly row may or may not improve — sometimes a prompt change isn't the right lever (the analyst may need access to a richer anomaly flag from the Python step). That's the lesson: the eval tells you whether your hypothesis worked, and the failing rows tell you what to try next.
