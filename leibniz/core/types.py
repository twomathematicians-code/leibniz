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

    # --- Truth weight -------------------------------------------------------
    # A transparent heuristic composite of the three gates, on a 0-100 scale.
    # It is a WEIGHT OF EVIDENCE, not a probability: each gate contributes a
    # documented share (validity 50%, alignment 25%, reading 25%) and the
    # mapping from verdicts to numbers is fixed and inspectable below.
    #   validity: formal certificate 1.0 | provisional 0.7 | skipped 0.4 | rejected 0.0
    #   reading : per-tier pass 1.0 | warn 0.5 | fail 0.0, averaged over tiers

    _VALIDITY_WEIGHT_SHARE = 0.50
    _ALIGNMENT_WEIGHT_SHARE = 0.25
    _READING_WEIGHT_SHARE = 0.25

    def _validity_component(self) -> float:
        v = self.validity
        if v.passed is True:
            return 1.0 if v.formal else 0.7   # formal Lean cert vs provisional match
        if v.passed is None:
            return 0.4                        # skipped / inconclusive
        return 0.0                            # rejected

    def _reading_component(self) -> float:
        if not self.reading.tiers:
            return 0.0
        value = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
        return sum(value.get(t.verdict, 0.5) for t in self.reading.tiers) / len(self.reading.tiers)

    @property
    def truth_weight(self) -> int:
        """Composite weight of truth, 0-100 (heuristic; see class docstring)."""
        score = (
            self._VALIDITY_WEIGHT_SHARE * self._validity_component()
            + self._ALIGNMENT_WEIGHT_SHARE * self.alignment.score
            + self._READING_WEIGHT_SHARE * self._reading_component()
        )
        return round(100 * max(0.0, min(1.0, score)))

    def truth_breakdown(self) -> Dict[str, object]:
        """The inspectable components behind `truth_weight`."""
        return {
            "truth_weight": self.truth_weight,
            "validity_component": round(self._validity_component(), 3),
            "alignment_component": round(self.alignment.score, 3),
            "reading_component": round(self._reading_component(), 3),
            "shares": {"validity": self._VALIDITY_WEIGHT_SHARE,
                       "alignment": self._ALIGNMENT_WEIGHT_SHARE,
                       "reading": self._READING_WEIGHT_SHARE},
            "note": ("heuristic weight of evidence across the three gates; "
                     "not a probability"),
        }


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
        d["truth_weight"] = obj.truth_weight
        d["truth_breakdown"] = obj.truth_breakdown()
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
