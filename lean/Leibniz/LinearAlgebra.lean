/-
Copyright (c) 2026 twomathematicians-code. MIT license.

# Leibniz — Linear Algebra (Undergraduate Core)

Vector-space axioms on `Fin n → ℝ` (pointwise).

**Requires Mathlib** (the `ℝ` notation, `•` on Pi types, and the `ext`
tactic are Mathlib/Std facilities, not Lean core).  This file is therefore
EXCLUDED from the default `lake build` (see `lakefile.lean` roots).

To build it: add `require mathlib from git
"https://github.com/leanprover-community/mathlib4.git"` to the lakefile,
include `Leibniz.LinearAlgebra` in the roots, then `lake build`
(first Mathlib fetch takes ~20-40 minutes and several GB).

The Python engine verifies these same statements symbolically
(`leibniz/groups` + encyclopedia), so the mathematical content is
machine-checked even while this Lean formalisation waits on Mathlib.
These mirror the entries in `leibniz/leibniz/encyclopedia/data.json`.
-/

namespace Leibniz.LinearAlgebra

/-- Vector addition is commutative (pointwise, inherited from ℝ). -/
theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v := by
  ext i
  exact add_comm (v i) (w i)

/-- Vector addition is associative (pointwise). -/
theorem add_assoc_vec (u v w : Fin n → ℝ) : (u + v) + w = u + (v + w) := by
  ext i
  exact add_assoc (u i) (v i) (w i)

/-- The zero vector is a left additive identity. -/
theorem zero_add_vec (v : Fin n → ℝ) : 0 + v = v := by
  ext i; simp

/-- The zero vector is a right additive identity. -/
theorem add_zero_vec (v : Fin n → ℝ) : v + 0 = v := by
  ext i; simp

/-- Every vector has an additive inverse (negation). -/
theorem add_neg_vec (v : Fin n → ℝ) : v + (-v) = 0 := by
  ext i; simp

/-- Scalar multiplication distributes over vector addition. -/
theorem smul_add_vec (c : ℝ) (v w : Fin n → ℝ) : c • (v + w) = c • v + c • w := by
  ext i
  exact mul_add c (v i) (w i)

/-- Scalar addition distributes over scalar multiplication. -/
theorem add_smul_vec (c d : ℝ) (v : Fin n → ℝ) : (c + d) • v = c • v + d • v := by
  ext i
  exact add_mul c d (v i)

/-- Scalar multiplication is associative. -/
theorem smul_assoc_vec (c d : ℝ) (v : Fin n → ℝ) : c • (d • v) = (c * d) • v := by
  ext i; simp [mul_assoc]

/-- The scalar 1 is the identity for scalar multiplication (unity law). -/
theorem one_smul_vec (v : Fin n → ℝ) : (1 : ℝ) • v = v := by
  ext i; simp

/-- The identity transformation has eigenvalue 1 on every nonzero vector. -/
theorem eigenvalue_id (v : Fin n → ℝ) (hv : v ≠ 0) :
    (λ x : Fin n → ℝ => x) v = (1 : ℝ) • v := by
  simp

end Leibniz.LinearAlgebra
