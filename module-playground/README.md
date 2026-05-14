# Module — Iterate in the Playground

You ran an eval in code (module 06) and walked the improvement loop (module 14). Now run the same idea in the Playground — same dataset, same scorer concept, but in a UI a PM or QA could drive without writing Python.

## What you'll do

1. **Seed two prompts into your project** — one generic, one with explicit failure-mode rules. Both pulled from the workshop code so the Playground gets the same prompts the evals use.
2. **Open a Playground**, add the Failure Modes dataset, drop in both prompts, attach a scorer.
3. **Run and compare.** See which rows each prompt wins on.

## Seed the prompts

```bash
python3 scripts/seed_playground_prompts.py
```

This pushes two named prompts into the project named in `$BRAINTRUST_PROJECT`:

- `analysis-baseline` — generic analyst, no failure-mode rules
- `analysis-improved` — adds explicit CRITICAL OUTPUT RULES for empty-result, unusually-large-trade, and accumulation-only cases

The user message in each prompt pulls `{{metadata.ticker}}`, `{{metadata.start_date}}`, `{{metadata.end_date}}`, and `{{metadata.metrics}}` from the dataset row — so the Playground feeds in the precomputed metrics automatically.

## Configure the Playground

1. In the project sidebar → **Playground → + New playground**
2. **Dataset**: select **Failure Modes**
3. **Prompts**: add **both** `analysis-baseline` and `analysis-improved`
4. **Scorer**: add `analysis_actionable` (the one you configured in module 12) — or any LLM-as-judge already in the project
5. **Run**

## Compare

The Playground shows side-by-side outputs per row and per prompt, plus the scorer column. Open the **Compare** view to see the score delta.

Expected pattern: the improved prompt wins or ties on most rows, with at least one row exposing a trade-off — the strict rules help in some cases and over-constrain in others.

## Discussion

- **Which rows did the improved prompt regress?** Read the judge rationale. Is it a real regression or judge noise?
- **What would you change in the prompt next?** Edit it directly in the Playground, re-run, watch the column move.
- **Who would use this?** A PM tuning copy. A QA validating a hypothesis. An analyst exploring failure modes without filing a ticket.

## Backtest against Gold Standard

You just iterated against a 6-row failure-mode dataset. The natural next question: do those tightened rules hold up on a broader test set?

1. With your improved prompt selected in the Playground, click **Run experiment**
2. Swap the dataset from **Failure Modes** to **Gold Standard** (15 rows)
3. Pick the scorer(s) you want (e.g., `analysis_actionable`, or pull in `analysis_completeness` / `analysis_groundedness` if available)
4. Run

This kicks off a full Braintrust experiment — same prompt you tuned in the Playground, now scored against the broader dataset. Open the experiment to see whether the failure-mode rules helped, hurt, or were neutral on normal cases.

The lesson: **Playground iteration → backtest experiment** is the real workflow. You explore in the UI, then validate against your gold dataset before shipping.

The bigger point: same eval primitives (dataset + prompt + scorer), no code.
