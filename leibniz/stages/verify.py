"""
Stage: VERIFY — GATE 1 (Validity)
=================================
Formally type-checks a (theorem, proof) pair with the Lean client.
This is the only gate that can yield a machine certificate.
"""

from __future__ import annotations

from ..core.types import Theorem, Proof, VerificationResult
from ..formal.lean_client import LeanClient


def verify(theorem: Theorem, proof: Proof, lean: LeanClient) -> VerificationResult:
    """Run formal (Lean) verification. Returns a VerificationResult."""
    return lean.check(theorem, proof)
