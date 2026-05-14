"""Defensive dataset loader.

`init_dataset(name=...)` silently creates a new empty dataset if no existing
one matches the name. That's a footgun in a workshop where 50 attendees
each upload a CSV via the UI — any naming drift becomes a silent zero-row
experiment.

`load_or_die` fetches the dataset and bails with a clear error if it's
empty, pointing attendees at the most likely cause.
"""
from __future__ import annotations
from braintrust import init_dataset

from .agent import PROJECT


def load_or_die(name: str):
    """Return a Braintrust dataset by exact name. Exit with a helpful message if empty."""
    ds = init_dataset(project=PROJECT, name=name)
    rows = list(ds.fetch())
    if not rows:
        expected_csv = name.lower().replace(" ", "_") + ".csv"
        raise SystemExit(
            f"\nDataset '{name}' has 0 rows in project '{PROJECT}'.\n"
            f"Check the Braintrust UI Datasets tab — the dataset must be named exactly '{name}' "
            f"(case and spaces matter). Upload data/{expected_csv} if you haven't, or rename "
            f"your existing dataset to '{name}' to match.\n"
        )
    return ds
