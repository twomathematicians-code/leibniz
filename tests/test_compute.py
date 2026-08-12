"""Tests for the symbolic compute engine (SymPy-backed)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

sympy = pytest.importorskip("sympy")  # skip whole module if sympy absent

from leibniz.pipeline import Engine
from leibniz.compute import compute, parse_intent

engine = Engine()


class TestAlgebra:
    def test_solve_quadratic(self):
        r = engine.compute("solve x^2 - 5*x + 6 = 0")
        assert r.ok
        assert "2" in r.answer and "3" in r.answer

    def test_solve_linear(self):
        r = engine.compute("solve 2*x + 7 = 15")
        assert r.ok
        assert "4" in r.answer

    def test_factor(self):
        r = engine.compute("factor x^3 - 6*x^2 + 11*x - 6")
        assert r.ok
        assert "x - 1" in r.answer and "x - 2" in r.answer and "x - 3" in r.answer

    def test_expand(self):
        r = engine.compute("expand (x + 2)^4")
        assert r.ok
        assert "x**4" in r.answer

    def test_simplify(self):
        r = engine.compute("simplify (x^2 - 1)/(x - 1)")
        assert r.ok
        assert r.answer.strip() == "x + 1"


class TestCalculus:
    def test_differentiate(self):
        r = engine.compute("derivative of x^3")
        assert r.ok
        assert "3*x**2" in r.answer

    def test_integrate(self):
        r = engine.compute("integral of 1/(1 + x^2)")
        assert r.ok
        assert "atan" in r.answer

    def test_limit(self):
        r = engine.compute("limit of sin(x)/x as x -> 0")
        assert r.ok
        assert r.answer.strip() == "1"

    def test_taylor_series(self):
        r = engine.compute("taylor series of exp(x)")
        assert r.ok
        assert "x**5" in r.answer  # 6-term expansion


class TestMatrices:
    def test_determinant_2x2(self):
        r = engine.compute("determinant of [[1,2],[3,4]]")
        assert r.ok
        assert r.answer.strip() == "-2"

    def test_determinant_3x3(self):
        r = engine.compute("determinant of [[2,0,1],[3,1,2],[1,0,2]]")
        assert r.ok
        assert r.answer.strip() == "3"

    def test_inverse(self):
        r = engine.compute("inverse of [[1,2],[3,4]]")
        assert r.ok
        assert "Matrix" in r.answer

    def test_inverse_singular(self):
        r = engine.compute("inverse of [[1,2],[2,4]]")
        assert not r.ok  # det = 0
        assert "singular" in (r.error or "").lower()

    def test_eigenvalues(self):
        r = engine.compute("eigenvalues of [[2,0],[0,3]]")
        assert r.ok
        assert "2" in r.answer and "3" in r.answer

    def test_rank(self):
        r = engine.compute("rank of [[1,2,3],[2,4,6],[1,1,1]]")
        assert r.ok
        assert r.answer.strip() == "2"

    def test_trace(self):
        r = engine.compute("trace of [[1,2],[3,4]]")
        assert r.ok
        assert r.answer.strip() == "5"


class TestArithmetic:
    def test_exact_rational(self):
        r = engine.compute("2/3 + 5/7")
        assert r.ok
        assert r.answer.strip() == "29/21"

    def test_simplification(self):
        r = engine.compute("sqrt(8)")
        assert r.ok
        assert "2*sqrt(2)" in r.answer


class TestParser:
    def test_intent_detection(self):
        cases = [
            ("solve x = 0", "solve"),
            ("derivative of x", "diff"),
            ("integrate x", "integrate"),
            ("limit of x as x -> 0", "limit"),
            ("taylor series of sin(x)", "series"),
            ("factor x^2", "factor"),
            ("expand (x+1)", "expand"),
            ("simplify x+x", "simplify"),
            ("determinant of [[1,2],[3,4]]", "matrix_det"),
        ]
        for q, expected in cases:
            intent, _, _ = parse_intent(q)
            assert intent == expected, f"parse_intent({q!r}) = {intent}, expected {expected}"


class TestResultShape:
    def test_result_has_steps(self):
        r = engine.compute("solve x^2 - 1 = 0")
        assert r.ok
        assert len(r.steps) >= 2

    def test_result_to_dict(self):
        r = engine.compute("2 + 2")
        d = r.to_dict()
        assert "query" in d and "answer" in d and "intent" in d
