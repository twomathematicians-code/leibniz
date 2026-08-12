"""Core type and difficulty tests."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from leibniz.core.types import (Theorem, Proof, Conjecture, CandidateProof,
                                VerificationResult, AlignmentReport, TierVerdict,
                                ReadingReport, GateReport, CertifiedProof,
                                DiscoveryResult, to_dict, to_json)
from leibniz.core.difficulty import Difficulty, parse_difficulty, TIER_RUBRIC


class TestDifficulty:
    def test_enum_values(self):
        assert Difficulty.EASY.value == "easy"
        assert Difficulty.MEDIUM.value == "medium"
        assert Difficulty.HARD.value == "hard"

    def test_parse(self):
        assert parse_difficulty("easy") == Difficulty.EASY
        assert parse_difficulty("EASY") == Difficulty.EASY
        assert parse_difficulty("eAsY") == Difficulty.EASY  # case-insensitive
        assert parse_difficulty("eas") == Difficulty.EASY     # prefix
        assert parse_difficulty("hard") == Difficulty.HARD
        assert parse_difficulty("garbage") == Difficulty.MEDIUM  # default

    def test_rubric(self):
        for d in Difficulty:
            assert len(TIER_RUBRIC[d]) > 10


class TestTheorem:
    def test_construction(self):
        t = Theorem("add_zero", "n+0=n", "theorem x : n+0=n", "algebra", "easy",
                     ["addition", "identity"])
        assert t.name == "add_zero"
        assert t.difficulty == Difficulty.EASY
        assert len(t.keywords) == 2

    def test_coerces_difficulty(self):
        t = Theorem("x", "", difficulty="hard")  # string -> enum
        assert t.difficulty == Difficulty.HARD

    def test_defaults(self):
        t = Theorem("x", "")
        assert t.difficulty == Difficulty.MEDIUM
        assert t.domain == "general"
        assert t.keywords == []


class TestGateReport:
    def test_overall_pass_when_valid_and_aligned(self):
        t = Theorem("t", "")
        p = Proof(lean_tactics="by rfl")
        rep = GateReport(
            theorem=t, proof=p,
            validity=VerificationResult(passed=True),
            alignment=AlignmentReport(score=0.8),
            reading=ReadingReport(overall_verdict="pass"),
        )
        assert rep.overall_pass is True

    def test_fails_on_low_alignment(self):
        rep = GateReport(
            theorem=Theorem("t", ""), proof=Proof(),
            validity=VerificationResult(passed=True),
            alignment=AlignmentReport(score=0.3),
            reading=ReadingReport(overall_verdict="pass"),
        )
        assert rep.overall_pass is False

    def test_fails_on_reading_fail(self):
        rep = GateReport(
            theorem=Theorem("t", ""), proof=Proof(),
            validity=VerificationResult(passed=True),
            alignment=AlignmentReport(score=0.9),
            reading=ReadingReport(overall_verdict="fail"),
        )
        assert rep.overall_pass is False


class TestSerialization:
    def test_to_dict(self):
        t = Theorem("two_plus_two", "2+2=4", difficulty=Difficulty.EASY)
        d = to_dict(t)
        assert d["name"] == "two_plus_two"
        assert d["difficulty"] == "easy"  # serialized as string

    def test_to_json(self):
        t = Theorem("x", "", difficulty="hard")
        assert '"difficulty": "hard"' in to_json(t)

    def test_roundtrip_gatereport(self):
        rep = GateReport(
            theorem=Theorem("x", ""),
            proof=Proof(lean_tactics="rfl"),
            validity=VerificationResult(passed=True, formal=True, certificate="lean:exit0"),
            alignment=AlignmentReport(score=1.0, matched_concepts=["a"], rationale="ok"),
            reading=ReadingReport(overall_verdict="pass", tiers=[
                TierVerdict(tier=Difficulty.EASY, verdict="pass", comments=["good"]),
            ]),
        )
        d = to_dict(rep)
        assert d["alignment"]["score"] == 1.0
        assert d["reading"]["tiers"][0]["verdict"] == "pass"


class TestDiscoveryResult:
    def test_success_rate(self):
        dr = DiscoveryResult(seed="s", certified=[
            CertifiedProof(Theorem("a", ""), Proof(), "c"),
            CertifiedProof(Theorem("b", ""), Proof(), "c"),
        ], failed=[Conjecture(Theorem("c", ""))])
        assert len(dr.conjectures) == 0  # we didn't set conjectures
        # But success_rate uses len(conjectures) as denominator
        # Let's test with proper setup
        dr2 = DiscoveryResult(
            seed="s",
            conjectures=[Conjecture(Theorem("a", "")), Conjecture(Theorem("b", "")),
                         Conjecture(Theorem("c", ""))],
            certified=[CertifiedProof(Theorem("a", ""), Proof(), "c")],
            failed=[Conjecture(Theorem("b", "")), Conjecture(Theorem("c", ""))],
        )
        assert dr2.success_rate == 1 / 3

    def test_discovery_result_empty(self):
        dr = DiscoveryResult(seed="empty")
        assert dr.success_rate == 0.0
        assert dr.certified == []
        assert dr.failed == []
