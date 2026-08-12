#!/usr/bin/env python
"""
Corpus Builder
==============
Assembles a supervised fine-tuning (SFT) corpus of Lean 4 statement→proof pairs
in a uniform JSONL schema:

    {"name": str, "statement": str, "proof": str, "domain": str, "difficulty": str}

Sources:
    * bundled (default)  — ships ~30 hand-written, core-compilable pairs.
    * minif2f             — the miniF2F benchmark (via HuggingFace datasets), if available.
    * proofnet            — the ProofNet benchmark (via HuggingFace datasets), if available.

The bundled source guarantees `format.py` and `eval.py --stub` run out-of-the-box
with NO network and NO heavy dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "bundled_sample.jsonl")


def load_bundled() -> List[dict]:
    with open(BUNDLED, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_minif2f() -> List[dict]:  # pragma: no cover - needs network
    from datasets import load_dataset  # type: ignore
    out: List[dict] = []
    for split in ("validation", "test"):
        try:
            ds = load_dataset("casper-hansen/miniF2F-lean", split=split)
        except Exception as exc:
            print(f"[minif2f] {split} unavailable: {exc}", file=sys.stderr)
            continue
        for row in ds:
            out.append({
                "name": str(row.get("name", "")),
                "statement": str(row.get("formal_statement", row.get("lean", ""))),
                "proof": "",  # miniF2F is a benchmark; proofs are withheld
                "domain": "minif2f",
                "difficulty": "hard",
            })
    return out


def load_proofnet() -> List[dict]:  # pragma: no cover - needs network
    from datasets import load_dataset  # type: ignore
    out: List[dict] = []
    try:
        ds = load_dataset("zhangir-azarov/proofnet", split="test")
    except Exception as exc:
        print(f"[proofnet] unavailable: {exc}", file=sys.stderr)
        return out
    for row in ds:
        out.append({
            "name": str(row.get("name", "")),
            "statement": str(row.get("lean_statement", row.get("formal_statement", ""))),
            "proof": "",
            "domain": "proofnet",
            "difficulty": "hard",
        })
    return out


SOURCES = {"bundled": load_bundled, "minif2f": load_minif2f, "proofnet": load_proofnet}


def build(source: str = "bundled") -> List[dict]:
    if source not in SOURCES:
        raise ValueError(f"Unknown source '{source}'. Choose from {list(SOURCES)}.")
    return SOURCES[source]()


def write_jsonl(rows: List[dict], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[build_corpus] wrote {len(rows)} rows -> {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Build the Leibniz SFT corpus.")
    p.add_argument("--source", default="bundled", choices=list(SOURCES))
    p.add_argument("--out", default=os.path.join(HERE, "corpus.jsonl"))
    args = p.parse_args()
    rows = build(args.source)
    write_jsonl(rows, args.out)


if __name__ == "__main__":
    main()
