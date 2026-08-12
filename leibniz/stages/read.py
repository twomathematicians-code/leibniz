"""
Stage: READ — GATE 3 (Graded proof reading)
==========================================
Runs the backend as a human-style reviewer at each difficulty tier
(easy -> medium -> hard) and aggregates the verdicts.
"""

from __future__ import annotations

from typing import List

from ..core.types import ReadingReport, Theorem, Proof, TierVerdict
from ..core.difficulty import Difficulty, TIER_ORDER
from ..llm.backend import BaseBackend


def read(theorem: Theorem, proof: Proof, backend: BaseBackend,
         tiers: List[Difficulty] = None) -> ReadingReport:
    """Grade a proof across difficulty tiers; return an aggregate report."""
    tiers = tiers if tiers is not None else list(TIER_ORDER)
    tier_verdicts: List[TierVerdict] = []
    for tier in tiers:
        d = backend.read_tier(theorem, proof, tier)
        verdict = str(d.get("verdict", "warn")).lower()
        if verdict not in ("pass", "warn", "fail"):
            verdict = "warn"
        tier_verdicts.append(TierVerdict(
            tier=tier,
            verdict=verdict,
            comments=[str(c) for c in d.get("comments", [])],
        ))

    if all(tv.verdict == "pass" for tv in tier_verdicts):
        overall = "pass"
    elif any(tv.verdict == "fail" for tv in tier_verdicts):
        overall = "fail"
    else:
        overall = "warn"

    return ReadingReport(tiers=tier_verdicts, overall_verdict=overall)
