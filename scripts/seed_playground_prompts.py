"""Seed two named prompts into your existing workshop project.

After running this, open the Playground in the BT UI, select the Failure
Modes dataset, and pick `analysis-baseline` or `analysis-improved` from
the prompt library instead of pasting multi-line system prompts by hand.

This script does NOT create the project — it expects it to exist already.

Required env:
    BRAINTRUST_API_KEY   your Braintrust API key
    BRAINTRUST_PROJECT   the existing project name (per-attendee)

Usage:
    python3 scripts/seed_playground_prompts.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import braintrust
from src.prompts import ANALYSIS_BASELINE

API_BASE = "https://api.braintrust.dev"
# Use the base model name (no date suffix). The date-suffixed variant can
# get routed to a custom AI provider in some orgs; the base name resolves
# cleanly through the default Anthropic provider for every attendee.
MODEL = "claude-haiku-4-5"


def _require_env(key: str) -> str:
    v = os.environ.get(key)
    if not v:
        raise SystemExit(f"Missing required env var: {key}")
    return v


def _verify_project_exists(api_key: str, project_name: str) -> None:
    """GET the project by name. Raise loudly if it doesn't exist."""
    url = f"{API_BASE}/v1/project?project_name={urllib.parse.quote(project_name)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req) as r:
        body = json.loads(r.read())
    if not body.get("objects"):
        raise SystemExit(
            f"Project '{project_name}' not found in Braintrust.\n"
            f"Create the project in the UI first, then re-run this script."
        )


def _load_improved_system() -> str:
    """Pull IMPROVED_SYSTEM out of eval_improved.py without executing its Eval()."""
    text = (ROOT / "module-14" / "eval_improved.py").read_text()
    m = re.search(r'IMPROVED_SYSTEM = """(.+?)"""', text, re.DOTALL)
    if not m:
        raise RuntimeError("Could not locate IMPROVED_SYSTEM in module-14/eval_improved.py")
    return m.group(1)


# User message template — pulls from the dataset row's metadata column using
# Braintrust playground Mustache substitution.
USER_TEMPLATE = """Company: {{metadata.ticker}}
Date range: {{metadata.start_date}} to {{metadata.end_date}}

Precomputed metrics from the warehouse + script:
{{metadata.metrics}}

Write the analysis."""


def main():
    api_key = _require_env("BRAINTRUST_API_KEY")
    project_name = _require_env("BRAINTRUST_PROJECT")

    _verify_project_exists(api_key, project_name)
    improved_system = _load_improved_system()

    # Project confirmed to exist. The SDK builder gets a handle to it; no
    # creation happens because the project is already present server-side.
    project = braintrust.projects.create(name=project_name)

    project.prompts.create(
        name="analysis-baseline",
        slug="analysis-baseline",
        description="Generic analyst prompt with no failure-mode rules. Mirrors module 06/14 baseline.",
        messages=[
            {"role": "system", "content": ANALYSIS_BASELINE},
            {"role": "user", "content": USER_TEMPLATE},
        ],
        model=MODEL,
        params={"max_tokens": 1024},
        if_exists="replace",
    )

    project.prompts.create(
        name="analysis-improved",
        slug="analysis-improved",
        description="Adds explicit CRITICAL OUTPUT RULES for each failure mode. Mirrors module 14 improved.",
        messages=[
            {"role": "system", "content": improved_system},
            {"role": "user", "content": USER_TEMPLATE},
        ],
        model=MODEL,
        params={"max_tokens": 1024},
        if_exists="replace",
    )

    project.publish()
    print(f"Seeded prompts into project '{project_name}':")
    print("  - analysis-baseline")
    print("  - analysis-improved")


if __name__ == "__main__":
    main()
