#!/usr/bin/env python
"""
SFT Formatting
==============
Converts corpus rows (statement/proof) into prompt–completion pairs for
supervised fine-tuning, and provides train/val splitting.

Schema in:  {"name","statement","proof","domain","difficulty"}
Schema out: {"prompt": str, "completion": str}
"""

from __future__ import annotations

import json
import os
import random
from typing import List, Tuple

PROMPT_TMPL = (
    "Complete the Lean 4 proof. Respond with ONLY the tactic block or proof "
    "term that follows `:= `.\n\n"
    "Statement:\n{statement}\n\nProof:\n"
)


def format_sft(row: dict) -> dict:
    """One SFT example: prompt asks for the proof; completion is the proof."""
    return {
        "prompt": PROMPT_TMPL.format(statement=row["statement"].strip()),
        "completion": (row.get("proof") or "").strip(),
    }


def load_corpus(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def filter_provable(rows: List[dict]) -> List[dict]:
    """Keep only rows that actually contain a proof (non-empty)."""
    return [r for r in rows if (r.get("proof") or "").strip()]


def train_val_split(rows: List[dict], val_fraction: float = 0.1,
                    seed: int = 42) -> Tuple[List[dict], List[dict]]:
    rows = list(rows)
    rng = random.Random(seed)
    rng.shuffle(rows)
    n_val = max(1, int(len(rows) * val_fraction)) if len(rows) > 1 else 0
    return rows[n_val:], rows[:n_val]


def to_hf_text(rows: List[dict]) -> List[str]:
    """Concatenated prompt+completion text for language-modeling trainers."""
    out = []
    for r in rows:
        ex = format_sft(r)
        out.append(ex["prompt"] + ex["completion"] + "\n")
    return out


if __name__ == "__main__":
    # Smoke test: works with zero heavy deps.
    here = os.path.dirname(os.path.abspath(__file__))
    rows = filter_provable(load_corpus(os.path.join(here, "bundled_sample.jsonl")))
    train, val = train_val_split(rows)
    print(f"provable rows: {len(rows)} | train: {len(train)} | val: {len(val)}")
    print("sample prompt:")
    print(format_sft(train[0])["prompt"])
    print("sample completion:", repr(format_sft(train[0])["completion"]))
