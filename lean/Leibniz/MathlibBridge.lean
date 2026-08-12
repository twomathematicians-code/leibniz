/-
Copyright (c) 2026 twomathematicians-code. MIT license.

# Leibniz — OPTIONAL Mathlib Bridge

This file is **NOT built by default**: `lake build` skips it (it is absent from
`lean_lib Leibniz`'s `roots`, and the lakefile has no `require mathlib`).

To enable Mathlib-backed proofs:

  1. Add the following to `lakefile.lean` (before the `lean_lib`):
       require mathlib from git
         "https://github.com/leanprover-community/mathlib4.git"
  2. Run `lake build Leibniz.MathlibBridge`
     (the first run downloads Mathlib — expect ~20-40 minutes and several GB).

Once enabled, this file can state and certify deeper theorems that rely on
Mathlib's analytic / number-theoretic library.
-/

import Mathlib

namespace Leibniz.MathlibBridge

/-- Mathlib's formal notion of a prime number (here we only sanity-check it). -/
#check @Nat.Prime

/-- Infinitude of primes is available in Mathlib (`Nat.exists_infinite_primes`). -/
#check Nat.exists_infinite_primes

end Leibniz.MathlibBridge
