# Module 06 — Build a simple eval in code

You will run the portfolio analysis skill agent against a 15-row gold-standard dataset and score it with two smoke tests and two LLM-as-judge scorers.

## What you'll see

The agent runs three steps per row:
1. Hardcoded SQL fetches transactions for a company in a date range
2. A Python script computes trading metrics over those rows
3. An LLM produces a written analysis from the metrics

Each step is traced as its own span. The scorers tell you whether the SQL ran, the Python ran, the analysis covered the right topics, and the analysis numbers are grounded in the Python output.

## Setup

```bash
cd ../  # repo root
pip install -r requirements.txt
export BRAINTRUST_API_KEY="..."
export OPENAI_API_KEY="..."        # or use proxy
```

(The CSVs in `data/` are pre-generated and committed — no build step.)

## Run

```bash
python module-06/eval_agent.py
```

Open the experiment URL in Braintrust. Inspect:
- Which rows scored well on `analysis_completeness`
- Which rows fail `analysis_groundedness` (hallucinated numbers)
- Which rows have a non-null `metadata.fetch_error` or `metadata.compute_error`

## Checkpoint

You should see 15 rows with four scores each in the Braintrust UI.

## Easter eggs to notice

- **Grokstad Mining** has no transactions in range — the analysis should say so
- **Aspen Energy** has one anomalous trade — the analysis should flag it
- **Horizon Materials** has only buys — the analysis should mention the unrealized position
- **"Old Name Corp"** isn't in the companies table — the agent reports it can't resolve
