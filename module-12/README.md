# Module 12 — Online scoring

Configure an LLM-as-judge scorer in the Braintrust UI that runs automatically on every new `run_skill` log. No code change required after setup.

## Prerequisites

- `eval-workshop` project exists (or your override via `BRAINTRUST_PROJECT`)
- At least one prior `run_skill` log in the project (run module-10 once if not)

## Configure the online scorer in the UI

1. Open your project → **Configuration → Online scoring** (or **Scorers**, depending on UI version)
2. **Create the scorer** in Library/Prompts:
   - **Name**: `analysis_completeness`
   - **Type**: LLM-as-judge
   - **Model**: `claude-haiku-4-5` (cheap and fast — fine for a 3-bucket discrete judge)
   - **Prompt template**:

   ```
   Score this portfolio trading analysis. Pick exactly ONE of:
     - COMPLETE: mentions position direction, capital deployed and divested, realized PnL, AND any anomalies surfaced by the metrics
     - PARTIAL: covers some required topics but is vague or misses one or two
     - MISSING: misses most required topics or fabricates

   Analysis:
   {{output}}

   Respond with just the label.
   ```

3. In the **Choice Scores** section of the scorer config, map each label to a numeric score:

   | Choice    | Score |
   |-----------|-------|
   | COMPLETE  | 1.0   |
   | PARTIAL   | 0.5   |
   | MISSING   | 0.0   |

4. Save the scorer.

5. **Create the automation rule** that applies the scorer to incoming logs:
   - **Name**: `analysis_completeness` — match the scorer name exactly. BT creates a UI column per rule AND per scorer; matching names collapses them into one column instead of two near-duplicates.
   - **Scorer**: `analysis_completeness` (from step 1-4)
   - **Filter** (BTQL): `is_root` — scores only the root `run_skill` span of each trace, not the intermediate LLM/tool sub-spans
   - **Sampling**: 100% (workshop — score every log)

6. Save the rule.

## Run

```bash
python3 module-12/generate_runs.py
```

This fires ~22 skill invocations across the full ticker set. As each log lands, the online scorer picks it up server-side.

## Checkpoint

Open the **Logs** tab. New traces should have `analysis_completeness` score attached within a few seconds of arrival. If you don't see scores, check the scorer rule is active and the filter matches `run_skill`.

## What's NOT scored online

- **Groundedness** (does the analysis fabricate numbers?) lives offline in module-06 because it needs access to the metrics (in the `tool:run_compute_script` child span). Easier to compute against a curated dataset than across spans in real time.
