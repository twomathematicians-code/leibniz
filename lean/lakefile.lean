/-
Copyright (c) 2026 twomathematicians-code. MIT license.

Lean 4 project for the Leibniz engine's formal layer (Gate 1 — Validity).

It is intentionally **Mathlib-free**: there is no `require mathlib`, so
`lake build` finishes in seconds (no multi-gigabyte download). Every theorem
here compiles against Lean core only.

To opt into Mathlib-backed proofs, see `Leibniz/MathlibBridge.lean`.
-/

import Lake
open Lake.DSL

package «Leibniz» where
  srcDir := "."

-- NOTE: no `require mathlib` by default (keeps the build fast & lightweight).

@[default_target]
lean_lib Leibniz where
  -- Core-only modules (no Mathlib): build in seconds.
  -- Leibniz/LinearAlgebra.lean and Leibniz/MathlibLA.lean require Mathlib
  -- (Real notation •, ext, field lemmas) and are excluded from the default
  -- build; see those files' headers for enabling them.
  roots := #[`Leibniz.Basic, `Leibniz.Examples]
