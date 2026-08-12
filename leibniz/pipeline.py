"""
Pipeline Orchestrator
=====================
The top-level Leibniz engine. Wires a backend (LLM voice) and a Lean client
(formal verifier) to the five stages and exposes both modes:

    * Discovery  : Engine.discover / Engine.discover_and_verify
    * Review     : Engine.review   (3-gate: Validity -> Alignment -> Reading)

A process-wide default engine is available for convenience
(review(...), discover_and_verify(...)).
"""

from __future__ import annotations

from typing import List, Optional

from .config import EngineConfig, config as default_config
from .core.types import (
    Conjecture, CertifiedProof, DiscoveryResult,
    GateReport, Theorem, Proof,
)
from .llm.backend import BaseBackend, get_backend
from .formal.lean_client import LeanClient
from .stages import discover as _discover, prove as _prove, verify as _verify, align as _align, read as _read


class Engine:
    """The Leibniz engine: backend + formal verifier + the five stages."""

    def __init__(self, backend: Optional[BaseBackend] = None,
                 lean: Optional[LeanClient] = None,
                 cfg: Optional[EngineConfig] = None):
        self.cfg = cfg or default_config
        self.backend = backend or get_backend(self.cfg)
        self.lean = lean or LeanClient(self.cfg)

    # ---------- REVIEW MODE (3 gates) ----------

    def review(self, theorem: Theorem, proof: Proof) -> GateReport:
        """Run the full 3-gate review on a (theorem, proof) pair."""
        validity = _verify(theorem, proof, self.lean)
        alignment = _align(theorem, proof, self.backend)
        reading = _read(theorem, proof, self.backend)
        return GateReport(
            theorem=theorem, proof=proof,
            validity=validity, alignment=alignment, reading=reading,
        )

    # ---------- DISCOVERY MODE ----------

    def discover(self, seed: str, n: Optional[int] = None) -> List[Conjecture]:
        return _discover(seed, n or self.cfg.max_conjectures, self.backend)

    def discover_and_verify(self, seed: str, n: Optional[int] = None,
                            k: Optional[int] = None) -> DiscoveryResult:
        """Full Discover -> Prove -> Verify pipeline on a seed topic."""
        k = k or self.cfg.sample_k
        conjectures = self.discover(seed, n)
        certified: List[CertifiedProof] = []
        failed: List[Conjecture] = []

        for conj in conjectures:
            t = conj.theorem
            if not t.lean_statement:
                # Cannot formally verify a non-formal conjecture.
                failed.append(conj)
                continue
            candidates = _prove(t, k, self.backend)
            done = False
            for cand in candidates:
                res = self.lean.check(t, cand.proof)
                if res.passed is True:
                    certified.append(CertifiedProof(
                        theorem=t,
                        proof=cand.proof,
                        certificate=res.certificate or "(verified)",
                    ))
                    done = True
                    break
            if not done:
                failed.append(conj)

        return DiscoveryResult(
            seed=seed, conjectures=conjectures,
            certified=certified, failed=failed,
        )


# --- module-level default engine ---

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Return (creating if needed) the process-wide default Engine."""
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


# Convenience top-level functions
def review(theorem: Theorem, proof: Proof) -> GateReport:
    return get_engine().review(theorem, proof)


def discover_and_verify(seed: str, **kwargs) -> DiscoveryResult:
    return get_engine().discover_and_verify(seed, **kwargs)


def discover(seed: str, n: Optional[int] = None) -> List[Conjecture]:
    return get_engine().discover(seed, n)
