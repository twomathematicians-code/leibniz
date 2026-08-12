"""Unit tests for each pipeline stage (StubBackend, offline)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from leibniz.core.types import Theorem, Proof
from leibniz.core.difficulty import Difficulty, TIER_ORDER
from leibniz.llm.backend import get_backend
from leibniz.formal.lean_client import LeanClient
from leibniz.stages import discover, prove, verify, align, read
from leibniz.encyclopedia import default as default_enc


backend = get_backend()
lean = LeanClient()


class TestDiscover:
    def test_output_type(self):
        conjs = discover("prime numbers", 3, backend)
        assert len(conjs) > 0
        for c in conjs:
            assert c.theorem.name
            assert c.theorem.informal
            assert isinstance(c.theorem.keywords, list)
            assert c.theorem.difficulty in list(Difficulty)

    def test_all_bundled(self):
        """Every encyclopedia entry triggers via its own name as seed."""
        enc = default_enc()
        for e in enc.all():
            conjs = discover(e["name"], 1, backend)
            assert len(conjs) == 1
            assert conjs[0].theorem.name == e["name"]


class TestProve:
    def test_known_theorem(self):
        t = Theorem("two_plus_two", "2+2=4", "theorem two_plus_two : 2 + 2 = 4", "arithmetic", "easy")
        cands = prove(t, 3, backend)
        assert len(cands) >= 2
        assert any("by rfl" in c.proof.lean_tactics for c in cands)

    def test_generic_fallback(self):
        t = Theorem("unknown_theorem", "...", "theorem t : ∀ x, x = x", "general", "hard")
        cands = prove(t, 4, backend)
        assert len(cands) == 4
        assert all(c.proof.lean_tactics for c in cands)


class TestVerify:
    def test_missing_statement(self):
        t = Theorem("n", "no statement", None, "general", "easy")
        res = verify(t, Proof(lean_tactics="by rfl"), lean)
        assert res.passed is None
        assert "no formal" in (res.error or "").lower()

    def test_lean_available_flag(self):
        """lean_available is bool regardless of toolchain presence."""
        t = Theorem("two_plus_two", "", "theorem t : 2+2=4", "arithmetic", "easy")
        res = verify(t, Proof(lean_tactics="by rfl"), lean)
        assert isinstance(res.lean_available, bool)

    def test_provisional_known(self):
        """Stub match on encyclopedia proof returns passed=True, formal=False."""
        t = Theorem("two_plus_two", "", "theorem t : 2+2=4", "arithmetic", "easy")
        res = verify(t, Proof(lean_tactics="by rfl"), lean)
        # True with provisional, or possibly True formal if Lean is installed
        assert res.passed is True or res.passed is None
        if res.lean_available and res.passed is True:
            assert res.formal is True
        else:
            assert res.formal is False


class TestAlign:
    def test_score_range(self):
        t = Theorem("two_plus_two", "2+2=4", "theorem t : 2+2=4", "arithmetic", "easy", ["addition"])
        p = Proof(lean_tactics="by rfl")
        rpt = align(t, p, backend)
        assert 0.0 <= rpt.score <= 1.0
        assert isinstance(rpt.matched_concepts, list)
        assert isinstance(rpt.missing_concepts, list)
        assert rpt.rationale

    def test_known_good_boost(self):
        t = Theorem("two_plus_two", "2+2=4", "theorem two_plus_two : 2 + 2 = 4", "arithmetic", "easy")
        rpt = align(t, Proof(lean_tactics="by rfl"), backend)
        assert rpt.score >= 0.3  # boosted by known-good match


class TestRead:
    def test_all_tiers_return_dicts(self):
        t = Theorem("two_plus_two", "", "theorem t : 2+2=4", "arithmetic", "easy")
        rpt = read(t, Proof(lean_tactics="by rfl"), backend)
        assert rpt.overall_verdict in ("pass", "warn", "fail")
        assert len(rpt.tiers) == len(TIER_ORDER)
        for tv in rpt.tiers:
            assert tv.verdict in ("pass", "warn", "fail")
            assert len(tv.comments) >= 1

    def test_sorry_fails_easy(self):
        t = Theorem("two_plus_two", "", "theorem t : 2+2=4", "arithmetic", "easy")
        rpt = read(t, Proof(lean_tactics="by sorry"), backend)
        assert rpt.tiers[0].verdict == "fail"  # easy tier should catch sorry
