/-
Copyright (c) 2026 twomathematicians-code. MIT license.

# Leibniz — Big Linear-Algebra Theorems (Mathlib-backed)

This module states the major undergraduate linear-algebra theorems using
**Mathlib**'s `LinearAlgebra`, `Matrix`, and `Analysis` machinery. It is NOT
built by default (it needs `require mathlib` in the lakefile).

To enable:

  1. Edit `lakefile.lean` and add (before `lean_lib Leibniz`):

       require mathlib from git
         "https://github.com/leanprover-community/mathlib4.git"

  2. Replace the `lean_lib` roots line with:

       roots := #[`Leibniz.Basic, `Leibniz.Examples, `Leibniz.LinearAlgebra,
                  `Leibniz.MathlibLA]

  3. Run `lake build Leibniz.MathlibLA`
     (first build downloads Mathlib — ~20-40 min and several GB).

The statements below mirror the `mathlib_ref` fields in
`leibniz/encyclopedia/data.json`. Signatures may need minor adjustment to the
exact Mathlib version; the `mathlib_ref` field points at the canonical lemma.
-/

import Mathlib
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic
import Mathlib.LinearAlgebra.FiniteDimensional

namespace Leibniz.MathlibLA

open Module Submodule Matrix LinearMap

/-! ## Vector spaces & subspaces -/

/-- The span of any set is a submodule (hence a subspace). -/
#check (span : {K V : Type*} → [Field K] → [AddCommGroup V] → [Module K V] → Set V → Submodule K V)

/-- Two bases of a finite-dimensional space share the same cardinality. -/
#check (Basis.card_eq : ∀ {K V ι ι' : Type*} [Field K] [AddCommGroup V] [Module K V]
  [Fintype ι] [Fintype ι'] (b : Basis ι K V) (b' : Basis ι' K V), Fintype.card ι = Fintype.card ι')

/-! ## Linear maps -/

/-- Rank-nullity: finrank (range f) + finrank (ker f) = finrank V. -/
#check (LinearMap.finrank_range_add_finrank_ker :
  ∀ {K V W : Type*} [Field K] [AddCommGroup V] [Module K V] [AddCommGroup W] [Module K W]
    [FiniteDimensional K V] (f : V →ₗ[K] W),
    finrank K (range f) + finrank K (ker f) = finrank K V)

/-- A linear map is injective iff its kernel is trivial. -/
#check (LinearMap.injective_iff_ker_eq_bot :
  ∀ {K V W : Type*} [Field K] [AddCommGroup V] [Module K V] [AddCommGroup W] [Module K W]
    (f : V →ₗ[K] W), Function.Injective f ↔ ker f = ⊥)

/-! ## Matrices & determinants -/

/-- det(A * B) = det A * det B. -/
#check (Matrix.det_mul :
  ∀ {K : Type*} [Field K] {n : Type*} [Fintype n] [DecidableEq n]
    (A B : Matrix n n K), det (A * B) = det A * det B)

/-- det(Aᵀ) = det A. -/
#check (Matrix.det_transpose :
  ∀ {K : Type*} [Field K] {n : Type*} [Fintype n] [DecidableEq n]
    (A : Matrix n n K), det Aᵀ = det A)

/-- A square matrix over a field is invertible iff its determinant is nonzero. -/
#check (Matrix.isUnit_iff_isUnit_det :
  ∀ {K : Type*} [Field K] {n : Type*} [Fintype n] [DecidableEq n]
    (A : Matrix n n K), IsUnit A ↔ IsUnit (det A))

/-! ## Spectral theory -/

/-- Eigenvectors are nonzero. -/
#check (Module.End.IsEigenvector : ∀ {K V : Type*} [Field K] [AddCommGroup V] [Module K V]
  (f : End K V) (v : V), Prop)

/-- Cayley-Hamilton: a matrix is annihilated by its characteristic polynomial. -/
#check (Matrix.aeval_self_charpoly :
  ∀ {K : Type*} [Field K] {n : Type*} [Fintype n] [DecidableEq n]
    (A : Matrix n n K), A.eval (charpoly A) = 0)

end Leibniz.MathlibLA
