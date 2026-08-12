"""
Difficulty Model
================
The three graded tiers used by Gate 3 (Reading). Each tier is an escalating
level of human-style proof scrutiny, from surface checks to deep correctness.
"""

from enum import Enum


class Difficulty(str, Enum):
    """Graded difficulty tiers for proof reading (small -> hard)."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# A rubric describing what each tier scrutinises. Used by the reader stage
# (and surfaced in the UI / reports) so the meaning of each tier is explicit.
TIER_RUBRIC = {
    Difficulty.EASY: (
        "Surface & syntax: the proof is well-formed, names resolve, "
        "no obvious typos, and it terminates against the stated goal."
    ),
    Difficulty.MEDIUM: (
        "Logic flow: every tactic's preconditions hold, intermediate "
        "goals resolve in sequence, and there are no unjustified leaps."
    ),
    Difficulty.HARD: (
        "Deep correctness & faithfulness: the proof is valid, minimal, "
        "conceptually aligned with the theorem, and handles edge cases."
    ),
}

# Canonical order: small -> hard.
TIER_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]


def parse_difficulty(s: str) -> Difficulty:
    """Tolerantly parse a difficulty string into a Difficulty tier."""
    s = (s or "").strip().lower()
    for d in Difficulty:
        if d.value == s or s.startswith(d.value[:3]):
            return d
    # Default to MEDIUM when ambiguous.
    return Difficulty.MEDIUM
