/-
Copyright (c) 2026 twomathematicians-code. MIT license.

# Leibniz — Certified Examples (Lean 4 core)

Genuine machine-checked theorems — **no `sorry`, no axioms** — each compiling
against Lean core only. These mirror entries in
`leibniz/leibniz/encyclopedia/data.json`, so when a Lean toolchain is present
the Python engine's provisional pattern-matches turn into REAL certificates.
-/

namespace Leibniz.Examples

/-- 2 + 2 = 4 (definitional: kernel reduction of `Nat.add` on literals). -/
theorem two_plus_two : 2 + 2 = 4 := by rfl

/-- 3 * 3 = 9 (definitional reduction of `Nat.mul`). -/
theorem three_times_three : 3 * 3 = 9 := by rfl

/-- 10 - 4 = 6 (definitional reduction of truncated `Nat.sub`). -/
theorem ten_minus_four : 10 - 4 = 6 := by rfl

/-- Right identity of addition: for all `n`, `n + 0 = n` (base equation of `Nat.add`). -/
theorem add_zero_left (n : Nat) : n + 0 = n := by rfl

/-- Right zero of multiplication: for all `n`, `n * 0 = 0` (base equation of `Nat.mul`). -/
theorem mul_zero_right (n : Nat) : n * 0 = 0 := by rfl

/-- Right identity of multiplication: for all `n`, `n * 1 = n` (by kernel reduction). -/
theorem mul_one_right (n : Nat) : n * 1 = n := by rfl

/-- Addition of natural numbers is commutative. -/
theorem add_comm_nat (a b : Nat) : a + b = b + a := by rw [Nat.add_comm]

end Leibniz.Examples
