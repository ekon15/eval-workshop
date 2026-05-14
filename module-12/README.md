# Module 12 — Online scoring

Configure an LLM-as-judge scorer in the Braintrust UI that runs automatically on every new `run_skill` log. No code change required after setup.

The online scorer here measures a **different dimension** than the offline scorers in module 06. Offline scorers (completeness, groundedness) test the analysis against a curated dataset. Online scorers run on prod traffic and ask different questions — here, *is this analysis actionable?*

## Prerequisites

- `eval-workshop` project exists (or your override via `BRAINTRUST_PROJECT`)
- At least one prior `run_skill` log in the project (run module-10 once if not)

## Configure the online scorer in the UI

1. Open your project → **Configuration → Online scoring** (or **Scorers**, depending on UI version)
2. **Create the scorer** in Library/Prompts:
   - **Name**: `analysis_actionable`
   - **Type**: LLM-as-judge
   - **Model**: `claude-haiku-4-5` (cheap and fast — fine for a 3-bucket discrete judge)
   - **Prompt template**:

   ```
   Score this portfolio trading analysis for whether it actionably informs the next decision. Pick exactly ONE of:
     - ACTIONABLE: states a clear position picture (held / accumulated / closed) AND surfaces what to watch next (anomalies, risk, sizing)
     - PARTIAL: covers the position but doesn't surface anomalies, risks, or next steps
     - NOT_ACTIONABLE: vague, hedges, or repeats inputs without analytical signal

   Analysis:
   {{output}}

   Respond with just the label.
   ```

3. In the **Choice Scores** section of the scorer config, map each label to a numeric score:

   | Choice          | Score |
   |-----------------|-------|
   | ACTIONABLE      | 1.0   |
   | PARTIAL         | 0.5   |
   | NOT_ACTIONABLE  | 0.0   |

4. Save the scorer.

5. **Create the automation rule** that applies the scorer to incoming logs:
   - **Name**: `analysis_actionable` — match the scorer name exactly. BT creates a UI column per rule AND per scorer; matching names collapses them into one column instead of two near-duplicates.
   - **Scorer**: `analysis_actionable` (from step 1-4)
   - **Filter** (BTQL): `is_root` — scores only the root `run_skill` span of each trace, not the intermediate LLM/tool sub-spans
   - **Sampling**: 100% (workshop — score every log)

6. Save the rule.

## Run

```bash
python3 module-12/generate_runs.py
```

This fires ~22 skill invocations across the full ticker set. As each log lands, the online scorer picks it up server-side.

## Checkpoint

Open the **Logs** tab. New traces should have `analysis_actionable` attached within a few seconds of arrival. If you don't see scores, check the scorer rule is active and the filter matches `run_skill`.

## Why a different scorer than module 06

| Where | Scorer | What it tests |
|---|---|---|
| Module 06 (code) | `analysis_completeness` + `analysis_groundedness` | Did the analysis cover all required topics, and are the numbers grounded in the metrics? |
| Module 12 (UI) | `analysis_actionable` | Is the analysis useful for making a decision? |

Same logical surface (the analysis text), three different lenses. Offline scorers stay in code where you control the dataset and rerun deterministically. Online scorers live in the UI so PM/QA can tweak them without a deploy.
