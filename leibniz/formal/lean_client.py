"""
Lean Client — the formal verifier behind Gate 1 (Validity)
==========================================================
Detects a Lean 4 toolchain on PATH and type-checks candidate proofs. When no
toolchain is present, it falls back to a clearly-labelled PROVISIONAL heuristic
(based on the encyclopedia's known-good proofs) so the pipeline remains
demonstrable end-to-end — but a provisional result is NEVER reported as a real
formal certificate.

Real verification:
    `lean <tempfile>` — exit 0 with no errors => certified.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Optional

from ..config import EngineConfig, config as default_config
from ..core.types import Theorem, Proof, VerificationResult


class LeanClient:
    """Type-check Theorem/Proof pairs with a local Lean 4 toolchain."""

    def __init__(self, cfg: Optional[EngineConfig] = None):
        self.cfg = cfg or default_config
        self._lean = shutil.which(self.cfg.lean_cmd)
        self._lake = shutil.which(self.cfg.lake_cmd)
        self.available = bool(self._lean)

    # ------------------------------------------------------------------

    def check(self, theorem: Theorem, proof: Proof) -> VerificationResult:
        from . import snippets
        source = snippets.wrap_module(theorem, proof)
        if not source:
            return VerificationResult(
                passed=None,
                error="No formal Lean statement/proof provided.",
                lean_available=self.available,
            )
        if not self.available:
            return self._provisional(theorem, proof)
        return self._compile(source)

    # --- real Lean compilation ----------------------------------------

    def _compile(self, source: str) -> VerificationResult:
        start = time.time()
        fd, path = tempfile.mkstemp(suffix=".lean", prefix="leibniz_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(source)
            try:
                proc = subprocess.run(
                    [self._lean, path],
                    capture_output=True,
                    text=True,
                    timeout=self.cfg.lean_timeout_s,
                )
            except subprocess.TimeoutExpired:
                return VerificationResult(
                    passed=None,
                    error=f"Lean timed out after {self.cfg.lean_timeout_s}s.",
                    lean_available=True,
                    elapsed_ms=(time.time() - start) * 1000,
                )
            elapsed = (time.time() - start) * 1000
            if proc.returncode == 0:
                return VerificationResult(
                    passed=True,
                    certificate="lean:exit0 (compiled clean)",
                    lean_available=True,
                    formal=True,
                    elapsed_ms=elapsed,
                )
            err = (proc.stderr or proc.stdout or "").strip() or f"lean exit {proc.returncode}"
            return VerificationResult(
                passed=False,
                error=_first_error(err),
                lean_available=True,
                elapsed_ms=elapsed,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    # --- provisional fallback (no toolchain) --------------------------

    def _provisional(self, theorem: Theorem, proof: Proof) -> VerificationResult:
        """NON-formal heuristic: only 'passes' when the proof reproduces a
        known-good encyclopedia proof. Always clearly labelled as provisional."""
        from ..encyclopedia.lookup import default as _default_enc
        enc = _default_enc()
        entry = enc.get(theorem.name)
        known_good = (entry or {}).get("lean_proof", "").strip()
        tac = (proof.lean_tactics or "").strip()
        if known_good and tac == known_good:
            return VerificationResult(
                passed=True,
                certificate=(
                    "PROVISIONAL:pattern-match (NOT a formal Lean certificate — "
                    "install elan/Lean for real verification)"
                ),
                lean_available=False,
                formal=False,
            )
        return VerificationResult(
            passed=None,
            error=(
                "Lean toolchain not installed; could not formally verify "
                "(and no provisional pattern match)."
            ),
            lean_available=False,
        )


def _first_error(err: str) -> str:
    """Trim a Lean error dump to its first meaningful line(s)."""
    # Lean errors typically begin with `<path>:<l>:<c>: error:` or `error:`.
    for line in err.splitlines():
        if "error:" in line or "unknown identifier" in line or "tactic failed" in line:
            return line.strip()[:300]
    return err[:300]
