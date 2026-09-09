"""Build a Mathematics in Lean (MiL)-aligned SFT corpus.

Extracts theorem statement -> proof pairs from the encyclopedia's MiL-sourced
entries plus the bundled core pairs, in the same JSONL schema used by
training/data/format.py.  MiL (Avigad & Massot) is CC BY 4.0 — attribution is
preserved in each row's source field.

Usage:
    python scripts/build_mil_corpus.py [--out path]
"""

from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main() -> None:
    p = argparse.ArgumentParser(description="Build a MiL-aligned SFT corpus.")
    p.add_argument("--out", default=os.path.join(HERE, "mil_corpus.jsonl"))
    args = p.parse_args()

    with open(os.path.join(ROOT, "leibniz", "encyclopedia", "data.json"),
              encoding="utf-8") as f:
        enc = json.load(f)

    rows = []
    for e in enc["entries"]:
        source = e.get("source", "")
        if "Mathematics in Lean" not in source:
            continue
        # only include entries whose statements are Lean-parseable-ish
        stmt = e.get("lean_statement", "")
        if not stmt or not stmt.startswith("theorem"):
            continue
        rows.append({
            "name": e["name"],
            "statement": stmt,
            "proof": e.get("lean_proof", ""),   # empty = proof-generation target
            "domain": e.get("domain", "general"),
            "difficulty": e.get("difficulty", "medium"),
            "source": source,
        })

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with_proof = sum(1 for r in rows if r["proof"].strip())
    print(f"[mil_corpus] wrote {len(rows)} rows -> {args.out}")
    print(f"  ({with_proof} with proofs, {len(rows) - with_proof} as "
          f"proof-generation targets)")
    print("  Attribution: Mathematics in Lean, Avigad & Massot (CC BY 4.0)")


if __name__ == "__main__":
    main()
