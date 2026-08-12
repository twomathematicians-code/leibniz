#!/usr/bin/env python
"""
Leibniz Engine — local runner (JSON output)
===========================================
Runs the pipeline and emits machine-readable JSON, handy for piping into the
API or for quick introspection.

Usage:
    python leibniz/scripts/run_local.py discover --seed "primes" --n 5
    python leibniz/scripts/run_local.py review \
        --name t --stmt "theorem t : 2 + 2 = 4" --proof "by rfl"
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict


def main() -> None:
    p = argparse.ArgumentParser(description="Leibniz local runner (JSON output).")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="Run Discover -> Prove -> Verify.")
    d.add_argument("--seed", default="arithmetic")
    d.add_argument("--n", type=int, default=5)
    d.add_argument("--k", type=int, default=4)

    r = sub.add_parser("review", help="Run the 3-gate review on one theorem+proof.")
    r.add_argument("--name", required=True)
    r.add_argument("--stmt", "--statement", required=True, dest="stmt")
    r.add_argument("--proof", required=True, help="tactic block, e.g. 'by rfl'")
    r.add_argument("--informal", default="")
    r.add_argument("--domain", default="general")
    r.add_argument("--difficulty", default="medium")

    args = p.parse_args()
    engine = Engine()

    if args.cmd == "discover":
        res = engine.discover_and_verify(args.seed, n=args.n, k=args.k)
        print(json.dumps(to_dict(res), indent=2, ensure_ascii=False))
    elif args.cmd == "review":
        t = Theorem(args.name, args.informal, args.stmt, args.domain, args.difficulty)
        proof = Proof(lean_tactics=args.proof)
        rep = engine.review(t, proof)
        print(json.dumps(to_dict(rep), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
