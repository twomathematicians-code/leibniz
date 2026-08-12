#!/usr/bin/env python
"""
Leibniz Engine — one-shot demo (both modes)
===========================================
Runs the full pipeline with the StubBackend (no GPU/network/Lean required):

    1. DISCOVERY: seed -> conjectures -> candidate proofs -> (provisional) certificates
    2. REVIEW:    a sample theorem+proof through the 3 gates

Usage:
    python leibniz/scripts/demo.py
    python leibniz/scripts/demo.py --seed "prime numbers"
"""

from __future__ import annotations

import argparse
import os
import sys

# Make `leibniz` importable whether run as a script or installed.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof
from leibniz.core.types import to_json


def _box(title: str) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n{title}\n{bar}")


def demo_discovery(engine: Engine, seed: str) -> None:
    _box(f"DISCOVERY MODE  —  seed: {seed!r}")
    result = engine.discover_and_verify(seed)
    print(f"Conjectures generated: {len(result.conjectures)}")
    print(f"Certified/provisional: {len(result.certified)}   "
          f"Unproven: {len(result.failed)}   "
          f"Success: {result.success_rate:.0%}")
    print("-" * 70)
    for cp in result.certified:
        formal = "FORMAL ✓" if "(compiled clean)" in (cp.certificate or "") else "PROVISIONAL"
        print(f"  ✓ [{formal}] {cp.theorem.name}  ({cp.theorem.domain})")
        print(f"      {cp.theorem.lean_statement} := {cp.proof.lean_tactics}")
    for c in result.failed:
        print(f"  ✗ {c.theorem.name}  ({c.theorem.domain}) — no passing proof found")


def demo_review(engine: Engine) -> None:
    _box("REVIEW MODE  —  3-gate proof review")
    theorem = Theorem(
        name="add_comm_nat",
        informal="Addition of natural numbers is commutative: a + b = b + a.",
        lean_statement="theorem add_comm_nat (a b : Nat) : a + b = b + a",
        domain="algebra",
        difficulty="medium",
        keywords=["addition", "commutativity", "algebra"],
    )
    proof = Proof(lean_tactics="by rw [Nat.add_comm]", informal="Rewrite using commutativity of addition.")
    report = engine.review(theorem, proof)

    print(f"Theorem: {theorem.name} — {theorem.informal}")
    print(f"Proof:   {theorem.lean_statement} := {proof.lean_tactics}\n")

    v = report.validity
    if v.passed is True and v.formal:
        tag = "FORMALLY CERTIFIED ✓"
    elif v.passed is True:
        tag = f"provisional (non-formal): {v.certificate}"
    elif v.passed is None:
        tag = f"skipped — {v.error}"
    else:
        tag = f"REJECTED ✗ — {v.error}"
    print(f"  GATE 1 — VALIDITY:    {tag}")

    a = report.alignment
    print(f"  GATE 2 — ALIGNMENT:   score={a.score:.2f}  "
          f"matched={a.matched_concepts}  missing={a.missing_concepts}")

    print(f"  GATE 3 — READING:     overall={report.reading.overall_verdict}")
    for tv in report.reading.tiers:
        print(f"      [{tv.tier.value:6}] {tv.verdict:4} — {tv.comments[0] if tv.comments else ''}")

    print(f"\n  => OVERALL: {'PASS ✓' if report.overall_pass else 'ATTENTION'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Leibniz engine demo.")
    parser.add_argument("--seed", default="arithmetic and primes",
                        help="seed topic for the discovery pipeline")
    args = parser.parse_args()

    engine = Engine()
    print(f"Leibniz engine ready. backend={engine.backend.name}  lean_available={engine.lean.available}")
    demo_discovery(engine, args.seed)
    demo_review(engine)
    print("\n(Dump full review as JSON? pass --json in a future flag; see run_local.py)\n")


if __name__ == "__main__":
    main()
