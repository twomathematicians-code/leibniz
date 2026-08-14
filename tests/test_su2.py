"""Tests for the SU(2) noncommutative compute cell (exact symbolic math).

Every test checks against textbook closed forms (Condon–Shortley
convention, Sakurai/Várshalovich tables) or against the Peter–Weyl
theorem itself — never against a stored snapshot.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

sympy = pytest.importorskip("sympy")

import sympy as sp
from leibniz.groups.su2 import (
    wigner_d, wigner_d_matrix, character, character_by_trace,
    peter_weyl_inner, verify_peter_weyl, wigner_3j,
    tensor_decomposition, dual_card, su2_report,
)

t = sp.Symbol("theta", positive=True)


def _eq(a, b):
    return sp.simplify(sp.trigsimp(sp.expand(a - b))) == 0


class TestWignerD:
    """Known closed forms — the textbook d^l tables."""

    def test_d_l0(self):
        assert wigner_d(0, 0, 0, t) == 1

    def test_d1_full_matrix(self):
        # wigner_d_matrix indexes m,n from −l to +l (row 0 = m = −1)
        c2, s2 = sp.cos(t / 2) ** 2, sp.sin(t / 2) ** 2
        sq2 = sp.sqrt(2)
        s = sp.sin(t)
        expected = sp.Matrix([
            [c2,  s / sq2, s2],
            [-s / sq2, sp.cos(t), s / sq2],
            [s2, -s / sq2, c2],
        ])  # (m,n) = (−1,−1)…(1,1) grid
        M = wigner_d_matrix(1, t)
        assert all(_eq(M[i, j], expected[i, j]) for i in range(3) for j in range(3))

    def test_d2_00_legendre(self):
        # d^l_{00}(θ) = P_l(cos θ), the Legendre polynomial
        assert _eq(wigner_d(2, 0, 0, t), sp.legendre(2, sp.cos(t)))

    def test_unitarity_at_zero(self):
        # d^l(0) = identity
        for l in range(3):
            M = wigner_d_matrix(l, t).subs(t, 0)
            assert M == sp.eye(2 * l + 1)

    def test_orthogonal_matrix(self):
        # d^l(θ) real orthogonal: d·dᵀ = I for a numeric exact point
        for l in (1, 2):
            M = wigner_d_matrix(l, t).subs(t, sp.pi / 3)
            prod = sp.simplify(M * M.T)
            assert prod == sp.eye(2 * l + 1)

    def test_domain_error(self):
        with pytest.raises(ValueError):
            wigner_d(1, 2, 0, t)


class TestCharacters:
    def test_weyl_formula_matches_trace(self):
        for l in range(4):
            assert _eq(character(l, t), character_by_trace(l, t))

    def test_chi_values(self):
        assert _eq(character(0, t), sp.Integer(1))
        assert _eq(character(1, t), 1 + 2 * sp.cos(t))
        assert _eq(character(2, t), 1 + 2 * sp.cos(t) + 2 * sp.cos(2 * t))

    def test_dimension_at_identity(self):
        # χ_l(θ) → 2l+1 as θ → 0 (the dimension)
        for l in range(4):
            assert sp.simplify(sp.limit(character(l, t), t, 0)) == 2 * l + 1


class TestPeterWeyl:
    """The machine-verified theorem: exact symbolic integration."""

    def test_diagonal_l0(self):
        val = peter_weyl_inner(0, 0, 0, 0, 0, 0)
        assert sp.simplify(val - 1) == 0           # 1/(2·0+1) = 1

    def test_diagonal_l1(self):
        val = peter_weyl_inner(1, 1, 1, 1, 1, 1)
        assert sp.simplify(val - sp.Rational(1, 3)) == 0

    def test_cross_l_zero(self):
        # same (m,n), different l ⇒ 0
        val = peter_weyl_inner(1, 0, 0, 2, 0, 0)
        assert sp.simplify(val) == 0

    def test_torus_phases_force_zero(self):
        # different (m,n) ⇒ None (0 by Fourier orthogonality on the torus)
        assert peter_weyl_inner(1, 1, 0, 1, 0, 0) is None

    def test_full_verification_l1(self):
        checks = verify_peter_weyl(1)
        assert all(c["verified"] for c in checks)
        assert len(checks) >= 6


class TestFusion:
    def test_tensor_decomposition(self):
        # V_1 ⊗ V_1 = V_0 ⊕ V_1 ⊕ V_2
        assert tensor_decomposition(1, 1) == [0, 1, 2]
        # V_1 ⊗ V_2 = V_1 ⊕ V_2 ⊕ V_3
        assert tensor_decomposition(1, 2) == [1, 2, 3]

    def test_dimension_additivity(self):
        # Σ_l (2l+1) over the decomposition must equal (2a+1)(2b+1)
        for a in range(3):
            for b in range(3):
                dims = sum(2 * l + 1 for l in tensor_decomposition(a, b))
                assert dims == (2 * a + 1) * (2 * b + 1)

    def test_wigner_3j_known(self):
        # 3j(1,1,2; 0,0,0)² — nonzero since 1⊗1 ⊃ 2
        val = wigner_3j(1, 1, 2, 0, 0, 0)
        assert sp.simplify(val ** 2) != 0
        # 3j selection: m1+m2+m3 ≠ 0 ⇒ exactly 0
        assert wigner_3j(1, 1, 1, 0, 0, 0) == 0   # triangle: 1,1,1 invalid
        assert wigner_3j(1, 1, 0, 1, -1, 0) ** 2 != 0


class TestDualCard:
    def test_dimensions(self):
        card = dual_card(2)
        assert card.dimensions == {0: 1, 1: 3, 2: 5}

    def test_report(self):
        rep = su2_report(1)
        assert rep["peter_weyl_all_verified"] is True
        assert rep["group"] == "SU(2)"
