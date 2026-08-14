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
from .stages import formalize as _formalize, FormalizationResult


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

    # ---------- FORMALIZE (NL → Lean) ----------

    def formalize(self, informal: str) -> "FormalizationResult":
        """Translate an informal mathematical statement into a candidate Lean 4 statement.

        Recognition-first: matches against the encyclopedia; falls back to the
        LLM backend for novel statements. Returns a FormalizationResult."""
        return _formalize(informal, backend=self.backend)

    def formalize_and_review(self, informal: str) -> GateReport:
        """One-shot: informal statement → formal Lean statement → 3-gate review.

        If formalization fails to produce a statement, returns a GateReport with
        Gate 1 skipped and a note in the validity error."""
        result = self.formalize(informal)
        if not result.lean_statement:
            t = Theorem(name=result.matched_entry or "unformalized",
                        informal=informal, lean_statement=None, domain="general")
            from .core.types import VerificationResult
            rep = self.review(t, Proof(lean_tactics=None))
            rep.validity = VerificationResult(
                passed=None,
                error=f"Autoformalization failed: {result.notes}",
                lean_available=self.lean.available,
            )
            return rep
        t = Theorem(
            name=result.matched_entry or "formalized",
            informal=informal,
            lean_statement=result.lean_statement,
            domain="linear_algebra",
        )
        rep = self.review(t, Proof(lean_tactics=None))
        # Attach formalization provenance to the alignment rationale.
        rep.alignment.rationale = (
            f"[formalized via {result.source}, confidence {result.confidence:.2f}] "
            + rep.alignment.rationale
        )
        return rep

    # ---------- COMPUTE (symbolic, Wolfram-Alpha-style) ----------

    def compute(self, query: str, intent: Optional[str] = None):
        """Symbolically compute a result from a natural-language / symbolic query.

        Backed by SymPy: solve, differentiate, integrate, limit, series,
        simplify, factor, expand, and matrix operations. Returns a
        ComputeResult (exact answer + step-by-step)."""
        from .compute.engine import compute as _compute
        return _compute(query, intent=intent)

    # ---------- NONCOMMUTATIVE ANALYSIS (SU(2) cell) ----------

    def su2_analysis(self, l_max: int = 2) -> dict:
        """Exact symbolic harmonic analysis on SU(2) up to rank l_max.

        Computes Wigner d-matrices, Weyl characters, fusion rules, and runs
        the machine verification of Peter–Weyl orthogonality (exact, via the
        Beta-function reduction — no floating point)."""
        from .groups.su2 import su2_report
        return su2_report(l_max)


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


def formalize(informal: str) -> "FormalizationResult":
    return get_engine().formalize(informal)


def formalize_and_review(informal: str) -> GateReport:
    return get_engine().formalize_and_review(informal)


def compute(query: str, intent: Optional[str] = None):
    return get_engine().compute(query, intent=intent)


def su2_analysis(l_max: int = 2) -> dict:
    return get_engine().su2_analysis(l_max)
