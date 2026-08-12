"""
Stage: DISCOVER (conjecture generation)
=======================================
The first stage of the discovery pipeline. Asks the backend to propose
conjectures from a seed topic and shapes them into Conjecture objects.
"""

from __future__ import annotations

from typing import List

from ..core.types import Conjecture, Theorem
from ..core.difficulty import parse_difficulty
from ..llm.backend import BaseBackend


def discover(seed: str, n: int, backend: BaseBackend) -> List[Conjecture]:
    """Generate up to `n` conjectures related to `seed` using `backend`."""
    raw = backend.discover(seed, n)
    out: List[Conjecture] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        theorem = Theorem(
            name=str(r.get("name") or f"conjecture_{len(out)}"),
            informal=str(r.get("informal") or ""),
            lean_statement=(str(r["lean_statement"]) if r.get("lean_statement") else None),
            domain=str(r.get("domain") or "general"),
            difficulty=parse_difficulty(str(r.get("difficulty") or "medium")),
            keywords=list(r.get("keywords") or []),
        )
        out.append(Conjecture(theorem=theorem, rationale=str(r.get("rationale") or "")))
    return out
