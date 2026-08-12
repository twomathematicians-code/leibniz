"""
Leibniz — A Universal Calculator for Truth
==========================================

A three-stage LLM-driven mathematical discovery and proof-checking engine,
realizing Leibniz's vision with modern tools (Lean 4 + Mathlib + LLMs).

Three pillars (Leibniz, ~1666):
    * Characteristica Universalis  -> leibniz.core.types      (the formal language)
    * Encyclopedia                  -> leibniz.encyclopedia   (verified thoughts)
    * Calculus Ratiocinator         -> leibniz.llm + stages   (the engine of reason)

Two modes:
    * Discovery  : Discover -> Prove -> Verify   (conjecture -> proof -> Lean certificate)
    * Review     : Validity -> Alignment -> Reading  (3-gate proof review)

The whole package runs with ZERO heavy dependencies via StubBackend.
Set LEIBNIZ_BACKEND=hf (or =remote) to plug in a real model.
"""

from .core.types import (
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
from .core.difficulty import Difficulty
from .config import EngineConfig, load_config, config

__version__ = "0.1.0"

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
    "EngineConfig",
    "load_config",
    "config",
    "__version__",
]
