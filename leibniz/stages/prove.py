"""
Stage: PROVE (candidate-proof generation)
=========================================
The second stage of the discovery pipeline. Produces k candidate proofs
(tactic blocks) for a theorem, tagged with their source backend.
"""

from __future__ import annotations

from typing import List

from ..core.types import CandidateProof, Proof, Theorem
from ..llm.backend import BaseBackend


def prove(theorem: Theorem, k: int, backend: BaseBackend) -> List[CandidateProof]:
    """Generate up to `k` candidate proofs for `theorem`."""
    tactics = backend.prove(theorem, k)
    out: List[CandidateProof] = []
    for tac in tactics:
        if not (tac or "").strip():
            continue
        out.append(CandidateProof(
            proof=Proof(lean_tactics=tac.strip(), author=backend.name),
            source=backend.name,
        ))
    return out
