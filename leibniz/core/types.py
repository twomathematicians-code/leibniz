"""
Core Data Types — the Characteristica Universalis
=================================================
The formal language of the Leibniz engine: dataclasses representing theorems,
proofs, conjectures, and the results of each verification stage.

Design goals:
    * Simple, serializable (dataclasses + to_dict/from_dict) so the whole
      pipeline runs with zero heavy dependencies.
    * Optional `lean_statement` / `lean_tactics` everywhere — the engine works
      on natural-language mathematics too, and becomes *formal* when Lean
      statements are provided.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .difficulty import Difficulty, parse_difficulty


# ----------------------------------------------------------------------------
# §1. The language: theorems and proofs
# ----------------------------------------------------------------------------

@dataclass
class Theorem:
    """A mathematical statement, optionally with a formal Lean counterpart."""
    name: str                                   # e.g. "infinitude_of_primes"
    informal: str                               # natural-language statement
    lean_statement: Optional[str] = None        # e.g.  "theorem t : ∀ n, ..."  (no proof)
    domain: str = "general"                     # e.g. "number_theory"
    difficulty: Difficulty = Difficulty.MEDIUM
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Coerce string difficulty -> enum (tolerant of JSON round-trips).
        if not isinstance(self.difficulty, Difficulty):
            self.difficulty = parse_difficulty(str(self.difficulty))


@dataclass
class Proof:
    """A candidate proof, optionally formal (Lean tactics / proof term)."""
    lean_tactics: Optional[str] = None          # the `by ...` block or proof term
    informal: Optional[str] = None              # natural-language sketch
    author: str = "engine"                      # stub | hf | remote | <user>


@dataclass
class CandidateProof:
    """A proof emitted by the Prove stage, tagged with its source."""
    proof: Proof
    source: str = "stub"                        # stub | hf | remote


# ----------------------------------------------------------------------------
# §2. Stage results
# ----------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """GATE 1 — Validity. The output of formal (Lean) compilation.

    `passed is None` means verification was *skipped* (e.g. no Lean toolchain
    or no formal statement). `passed is True` means a machine certificate
    exists; `passed is False` means the proof was rejected.
    """
    passed: Optional[bool] = None
    certificate: Optional[str] = None           # human-readable certificate / hash
    error: Optional[str] = None                 # compiler error / skip reason
    lean_available: bool = True                 # False if the Lean toolchain was missing
    formal: bool = False                        # True ONLY when Lean actually compiled the proof
    elapsed_ms: float = 0.0


@dataclass
class AlignmentReport:
    """GATE 2 — Conceptual alignment. How well the proof matches the theorem's concepts."""
    score: float = 0.0                          # 0.0 .. 1.0
    matched_concepts: List[str] = field(default_factory=list)
    missing_concepts: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class TierVerdict:
    """A single tier's verdict within the graded reading gate."""
    tier: Difficulty = Difficulty.MEDIUM
    verdict: str = "warn"                       # pass | warn | fail
    comments: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.tier, Difficulty):
            self.tier = parse_difficulty(str(self.tier))


@dataclass
class ReadingReport:
    """GATE 3 — Graded reading. One verdict per difficulty tier (easy -> hard)."""
    tiers: List[TierVerdict] = field(default_factory=list)
    overall_verdict: str = "warn"               # pass | warn | fail


@dataclass
class GateReport:
    """Full 3-gate review of a (theorem, proof) pair."""
    theorem: Theorem
    proof: Proof
    validity: VerificationResult = field(default_factory=VerificationResult)
    alignment: AlignmentReport = field(default_factory=AlignmentReport)
    reading: ReadingReport = field(default_factory=ReadingReport)

    @property
    def overall_pass(self) -> bool:
        """A proof passes overall iff it is formally valid (or verification was
        skipped) AND alignment is acceptable AND no tier hard-fails."""
        validity_ok = self.validity.passed in (True, None)
        alignment_ok = self.alignment.score >= 0.5
        reading_ok = self.reading.overall_verdict != "fail"
        return bool(validity_ok and alignment_ok and reading_ok)


# ----------------------------------------------------------------------------
# §3. Discovery results
# ----------------------------------------------------------------------------

@dataclass
class Conjecture:
    """A theorem proposed by the Discover stage, with a rationale."""
    theorem: Theorem
    rationale: str = ""


@dataclass
class CertifiedProof:
    """A theorem + proof that passed formal verification."""
    theorem: Theorem
    proof: Proof
    certificate: str


@dataclass
class DiscoveryResult:
    """Output of the full Discover -> Prove -> Verify pipeline."""
    seed: str
    conjectures: List[Conjecture] = field(default_factory=list)
    certified: List[CertifiedProof] = field(default_factory=list)
    failed: List[Conjecture] = field(default_factory=list)  # no passing proof found

    @property
    def success_rate(self) -> float:
        total = len(self.conjectures)
        if total == 0:
            return 0.0
        return len(self.certified) / total


# ----------------------------------------------------------------------------
# §4. Serialization helpers
# ----------------------------------------------------------------------------

def to_dict(obj: Any) -> Dict[str, Any]:
    """Recursively convert a dataclass (with enums) into a JSON-safe dict."""
    d = asdict(obj)
    _stringify_enums(d)
    _include_properties(d, obj)
    return d


def _include_properties(d: Dict[str, Any], obj: Any) -> None:
    """Add computed @property values that are useful in serialized output."""
    if isinstance(obj, GateReport):
        d["overall_pass"] = obj.overall_pass
    elif isinstance(obj, DiscoveryResult):
        d["success_rate"] = obj.success_rate


def _stringify_enums(d: Any) -> None:
    """In-place: convert Difficulty enum values to their string form."""
    if isinstance(d, dict):
        for k, v in list(d.items()):
            if isinstance(v, Difficulty):
                d[k] = v.value
            else:
                _stringify_enums(v)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if isinstance(v, Difficulty):
                d[i] = v.value
            else:
                _stringify_enums(v)


def to_json(obj: Any, indent: int = 2) -> str:
    """Serialize a dataclass instance to a JSON string."""
    import json
    return json.dumps(to_dict(obj), indent=indent, ensure_ascii=False)
