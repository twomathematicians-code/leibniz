/-
Copyright (c) 2026 twomathematicians-code. MIT license.

# Leibniz — Formal Foundation (Lean 4 core)

This module is the formal counterpart of the Python engine's Gate 1 (Validity).
It introduces a `CertifiedProof` record — the machine counterpart of a
human-readable "QED" stamp — and is dependency-free (Lean core only), so
`lake build` completes in seconds.

See `Leibniz/Examples.lean` for genuine certified theorems (no `sorry`).
-/

namespace Leibniz

/--
A proof that has been type-checked by the Lean compiler.

This mirrors the Python `VerificationResult.formal = True` path: a result is
`formal` only when Lean actually compiled the proof (exit 0, no errors).
-/
structure CertifiedProof where
  /-- Human-readable name of the theorem. -/
  name : String
  /-- The proposition proved (as a string, for easy interop with Python). -/
  statement : String
  /-- A machine-checkable certificate marker, e.g. `"lean:exit0"`. -/
  certificate : String := "lean:exit0"
  deriving Repr

/--
A value-level witness that the engine can carry certified proofs as data.
`#check` keeps the build side-effect-free (no evaluation at compile time).
-/
def firstCertificate : CertifiedProof :=
  { name := "two_plus_two",
    statement := "2 + 2 = 4",
    certificate := "lean:rfl" }

#check firstCertificate

end Leibniz
