# Module 14 — The improvement loop

You'll spot a failure pattern in the baseline, propose a prompt change, rerun, and verify in the eval.

## What you'll do

1. **Run the baseline.** The dataset is six rows focused on the failure modes the agent should handle (empty result, anomaly, accumulation-only, unresolved company).
2. **Open the experiment** in Braintrust. Inspect rows that scored < 1.0 on `handled_correctly`. Read the judge's rationale.
3. **Run the improved version.** The system prompt has been rewritten to give explicit rules for each failure mode.
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
