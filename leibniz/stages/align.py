"""
Stage: ALIGN — GATE 2 (Conceptual alignment)
============================================
Scores how well a proof's concepts match the theorem's expected concepts.
"""

from __future__ import annotations

from ..core.types import AlignmentReport, Theorem, Proof
from ..llm.backend import BaseBackend


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def align(theorem: Theorem, proof: Proof, backend: BaseBackend) -> AlignmentReport:
    """Produce a 0..1 conceptual-alignment report via the backend."""
    d = backend.align(theorem, proof)
    return AlignmentReport(
        score=_clamp01(d.get("score", 0.0)),
        matched_concepts=list(d.get("matched_concepts", [])),
        missing_concepts=list(d.get("missing_concepts", [])),
        rationale=str(d.get("rationale", "")),
    )
