"""Core data types and difficulty model (the Characteristica Universalis)."""

from .types import (
    Theorem,
    Proof,
    Conjecture,
    CandidateProof,
    VerificationResult,
    AlignmentReport,
    TierVerdict,
    ReadingReport,
    GateReport,
    CertifiedProof,
    DiscoveryResult,
)
from .difficulty import Difficulty, TIER_RUBRIC, TIER_ORDER

__all__ = [
    "Theorem",
    "Proof",
    "Conjecture",
    "CandidateProof",
    "VerificationResult",
    "AlignmentReport",
    "TierVerdict",
    "ReadingReport",
    "GateReport",
    "CertifiedProof",
    "DiscoveryResult",
    "Difficulty",
    "TIER_RUBRIC",
    "TIER_ORDER",
]
