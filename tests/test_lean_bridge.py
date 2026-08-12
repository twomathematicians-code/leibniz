"""Lean bridge unit tests. Skips real Lean compilation when no toolchain is present."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

from leibniz.core.types import Theorem, Proof
from leibniz.formal.lean_client import LeanClient
from leibniz.formal import snippets


lean = LeanClient()


class TestSnippets:
    def test_assemble_simple(self):
        t = Theorem("t", "", "theorem t : 2 + 2 = 4", "arithmetic", "easy")
        p = Proof(lean_tactics="by rfl")
        assert snippets.assemble(t, p) == "theorem t : 2 + 2 = 4 := by rfl"

    def test_assemble_missing(self):
        assert snippets.assemble(Theorem("x", "", None), Proof()) == ""
        assert snippets.assemble(Theorem("x", "", "theorem x : True"), Proof()) == ""

    def test_assemble_no_double_colon(self):
        t = Theorem("t", "", "theorem t : 2+2 = 4 :=", "arithmetic", "easy")
        p = Proof(lean_tactics="rfl")
        assert snippets.assemble(t, p) == "theorem t : 2+2 = 4 := rfl"

    def test_wrap_module(self):
        t = Theorem("t", "", "theorem two_plus_two : 2 + 2 = 4", "arithmetic", "easy")
        p = Proof(lean_tactics="by rfl")
        src = snippets.wrap_module(t, p)
        assert "Auto-generated" in src
        assert "theorem two_plus_two : 2 + 2 = 4 := by rfl" in src


class TestLeanClient:
    def test_client_created(self):
        assert isinstance(lean.available, bool)
        assert isinstance(lean.cfg.lean_timeout_s, (int, float))

    def test_check_missing_statement(self):
        t = Theorem("t", "", None)
        res = lean.check(t, Proof(lean_tactics="by rfl"))
        assert res.passed is None
        assert res.formal is False

    def test_check_no_lean_toolchain(self):
        """When Lean is not installed, every check returns (passed=None or True provisional)."""
        if not lean.available:
            t = Theorem("unknown", "", "theorem t : 1=1")
            res = lean.check(t, Proof(lean_tactics="by not_a_tactic"))
            # Not matched in encyclopedia → None, or Lean actually runs → False
            assert res.passed in (None, False)
            assert res.formal is False

    @pytest.mark.skipif(not lean.available, reason="Lean toolchain not installed")
    def test_real_compile_passes(self):
        """Real Lean compile — only runs when `lean` is on PATH."""
        t = Theorem("two_plus_two", "", "theorem two_plus_two : 2 + 2 = 4", "arithmetic", "easy")
        p = Proof(lean_tactics="by rfl")
        res = lean.check(t, p)
        assert res.passed is True
        assert res.formal is True
        assert res.certificate is not None
        assert "compiled clean" in res.certificate

    @pytest.mark.skipif(not lean.available, reason="Lean toolchain not installed")
    def test_real_compile_fails(self):
        t = Theorem("two_plus_two", "", "theorem two_plus_two : 2 + 2 = 4", "arithmetic", "easy")
        p = Proof(lean_tactics="by sorry")
        res = lean.check(t, p)
        assert res.passed is False
        assert res.formal is True  # Lean DID run, but rejected
