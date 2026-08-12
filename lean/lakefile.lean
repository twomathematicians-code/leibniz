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
  version := v!"0.1.0"
  srcDir := "."

-- NOTE: no `require mathlib` by default (keeps the build fast & lightweight).

@[default_target]
lean_lib Leibniz where
  -- Only build the core modules; MathlibBridge is opt-in and excluded here.
  roots := #[`Leibniz.Basic, `Leibniz.Examples, `Leibniz.LinearAlgebra]
