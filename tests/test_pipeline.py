"""End-to-end pipeline tests (StubBackend, no network/GPU/Lean required)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from leibniz.pipeline import Engine, review, discover_and_verify, discover as _discover
from leibniz.core.types import Theorem, Proof, GateReport, DiscoveryResult
from leibniz.core.difficulty import Difficulty


engine = Engine()


class TestPipelineReview:
    def test_review_mode(self):
        t = Theorem("two_plus_two", "2+2=4", "theorem two_plus_two : 2 + 2 = 4",
                     "arithmetic", Difficulty.EASY, ["addition"])
        p = Proof(lean_tactics="by rfl")
        rep = engine.review(t, p)
        assert isinstance(rep, GateReport)
        assert rep.theorem.name == "two_plus_two"
        assert rep.proof.lean_tactics == "by rfl"
        # Either True (formal/provisional) or None (no Lean, not matched)
        assert rep.validity.passed in (True, None)
        assert 0.0 <= rep.alignment.score <= 1.0
        assert rep.reading.overall_verdict in ("pass", "warn", "fail")
        assert isinstance(rep.overall_pass, bool)

    def test_review_convenience(self):
        rep = review(
            Theorem("add_comm_nat",
                    "Addition of natural numbers is commutative: a + b = b + a.",
                    "theorem add_comm_nat (a b : Nat) : a + b = b + a"),
            Proof(lean_tactics="by rw [Nat.add_comm]")
        )
        assert rep.overall_pass is True

    def test_review_fails_on_bad_proof(self):
        t = Theorem("two_plus_two", "", "theorem two_plus_two : 2 + 2 = 4")
        rep = review(t, Proof(lean_tactics="by sorry"))
        assert rep.reading.tiers[0].verdict == "fail"


class TestPipelineDiscovery:
    def test_discover_mode(self):
        conjs = _discover("arithmetic", n=3)
        assert len(conjs) >= 1
        assert all(c.theorem.name for c in conjs)

    def test_discover_and_verify(self):
        result = engine.discover_and_verify("arithmetic", n=4, k=3)
        assert isinstance(result, DiscoveryResult)
        assert result.seed == "arithmetic"
        assert len(result.conjectures) >= 1
        assert len(result.certified) + len(result.failed) == len(result.conjectures)
        # Known provable theorems should certify
        assert len(result.certified) >= 2
        assert 0.0 <= result.success_rate <= 1.0

    def test_discover_and_verify_convenience(self):
        res = discover_and_verify("primes", n=3, k=2)
        assert isinstance(res, DiscoveryResult)
        assert res.seed == "primes"


class TestEngineSingleton:
    def test_creates_engines(self):
        e2 = Engine()
        assert isinstance(e2.backend.name, str)
        assert e2.backend.name == "stub"
