# 🧮 Leibniz — A Universal Calculator for Truth

**[Leibniz's 400-year-old vision](https://en.wikipedia.org/wiki/Characteristica_universalis), realised with modern tools.**

A three-stage, LLM-driven **mathematical discovery and proof-checking engine** — build conjectures, search for proofs, formally verify them in Lean 4, and subject every proof to a 3-gate qualitative review.

---

## Leibniz's Three Pillars (ca. 1666)

| Pillar | Meaning | Our realization |
|--------|---------|-----------------|
| **Characteristica Universalis** | A universal logical language | `Theorem` / `Proof` data types + Lean 4 bridge |
| **Encyclopedia** | A complete library of verified thoughts | Bundled knowledge base + Mathlib |
| **Calculus Ratiocinator** | An engine that derives facts automatically | LLM backends (stub/hf/remote) + the five-stage pipeline |

---

## Two Modes

### 🔍 Discovery — Discover → Prove → Verify
1. **Discover**: from a seed topic (e.g. *"prime numbers"*), the engine proposes conjectures with informal + Lean 4 statements.
2. **Prove**: for each conjecture, it generates *k* candidate tactic blocks.
3. **Verify**: each candidate is compiled in Lean 4 → the first passing proof becomes a **certified** theorem.

### 📋 Review — Validity → Alignment → Reading
Three gates on any submitted (theorem, proof) pair:

| Gate | What it checks | Mechanism |
|------|---------------|-----------|
| **Validity** | Does the proof compile? | Lean 4 type-check (exit 0 = certified) |
| **Alignment** | Do the concepts match? | Encyclopedia concept-overlap score 0→1 |
| **Reading** | Human-style scrutiny | Three graded tiers: easy → medium → hard |

---

## Quick Start

```bash
# 1. Install core deps (~3 light packages — no ML)
pip install -r leibniz/requirements.txt

# 2. Run the one-shot demo (StubBackend — works on any machine)
python leibniz/scripts/demo.py

# 3. Start the API server
python -m uvicorn api.main:app --app-dir leibniz --host 0.0.0.0 --port 8430
# → Open http://localhost:8430/docs for the Swagger UI

# 4. Run the Gradio interactive demo (local)
pip install gradio  # one-time
python leibniz/app/app.py
# → Open http://127.0.0.1:7860

# 5. Run tests
pip install pytest fastapi
PYTHONPATH=leibniz pytest leibniz/tests -q
```

### Output example

```
DISCOVERY MODE  —  seed: 'arithmetic'
Conjectures generated: 5  |  Certified: 4  |  Unproven: 1  |  Success: 80%

  ✓ [PROVISIONAL] two_plus_two  (arithmetic)
      theorem two_plus_two : 2 + 2 = 4 := by rfl
  ✓ [PROVISIONAL] add_comm_nat  (algebra)
      theorem add_comm_nat (a b : Nat) : a + b = b + a := by rw [Nat.add_comm]

REVIEW MODE  —  Theorem: add_comm_nat
  GATE 1 — VALIDITY:    ✓ PROVISIONAL (pattern-match)
  GATE 2 — ALIGNMENT:   score=1.00  matched=['addition','commutativity','natural numbers']
  GATE 3 — READING:     overall=pass
      [easy  ] pass — Well-formed tactic block
      [medium] pass — Tactic sequence matches the known-good proof
      [hard  ] pass — Proof matches the certified encyclopedia proof
  => OVERALL: PASS ✓
```

---

## Component Map

```
leibniz/
├── leibniz/              Python package
│   ├── core/             types.py  + difficulty model
│   ├── llm/              backend.py (Stub/HF/Remote) + prompts.py
│   ├── stages/           discover · prove · verify · align · read
│   ├── formal/           lean_client.py + snippet assembler
│   ├── encyclopedia/     lookup.py + seeded data.json (12 entries)
│   ├── pipeline.py       orchestrator (discover_and_verify / review)
│   └── config.py         dataclass + env overrides
├── api/                  FastAPI host (port 8430) → Render / Fly.io
├── app/                  Gradio HF Space demo (2 tabs)
├── lean/                 Lean 4 project — 6 certified core theorems (no sorry)
├── training/             Fine-tuning framework (LoRA / full) + bundled SFT corpus
├── scripts/              demo.py + run_local.py
└── tests/                5 test modules (StubBackend; CI-green)
```

---

## Backends

| Backend | How to select | Dependencies | When to use |
|---------|--------------|--------------|-------------|
| **StubBackend** *(default)* | `LEIBNIZ_BACKEND=stub` | None | Demos, tests, CI — always works |
| **HFBackend** | `LEIBNIZ_BACKEND=hf` + `LEIBNIZ_MODEL=...` | `torch`, `transformers` | Local model inference |
| **RemoteBackend** | `LEIBNIZ_BACKEND=remote` + `LEIBNIZ_REMOTE_URL=...` | `requests` | HF Space → GPU host bridge |

The whole pipeline is **runnable with zero heavy dependencies** via the StubBackend.

---

## Formal Verification (Lean 4)

The `leibniz/lean/` directory is a standalone Lean 4 project (Mathlib-free — `lake build` completes in seconds):

- `Leibniz/Basic.lean` — `CertifiedProof` structure
- `Leibniz/Examples.lean` — 6 genuine `theorem` statements (no `sorry`) mirroring the encyclopedia
- `Leibniz/MathlibBridge.lean` — OPTIONAL deep proofs (requires `require mathlib` in lakefile)

When a Lean toolchain is available, the Python engine's provisional pattern-matches turn into **real `lean:exit0` certificates**.

---

## Fine-Tuning a Prover Model

See `leibniz/training/README.md`. The framework is complete; the actual fine-tune run is deferred until GPU access.

```bash
pip install -r leibniz/training/requirements.txt
python leibniz/training/data/build_corpus.py --out corpus.jsonl
python leibniz/training/train.py --config leibniz/training/configs/finetune_lora.yaml
python leibniz/training/eval.py --config ... --checkpoint ... --k 4
```

---

## Deploy

| Surface | File | Port | Notes |
|---------|------|------|-------|
| API host | `api/main.py` | 8430 | FastAPI, Dockerfile, Render/Fly-ready |
| HF Space | `app/app.py` | 7860 (local) | Gradio, free CPU tier, inline or remote |
| Model server | `leibniz/llm/server.py` | 8431 | Optional GPU-hosted bridge |

---

## Inspirations

- **Tudor Achim**, *The Path to Mathematical Superintelligence* (TED)
- **David Loeffler & Michael Stoll**, *Formalizing Zeta and L-Functions in Lean*
- **Gottfried Wilhelm Leibniz**, *De Arte Combinatoria* (1666) and the dream of a *calculus ratiocinator*
- **Terence Tao** on formal proof assistants and the future of mathematical discovery

## License

MIT — same as the parent Riemann Hypothesis repository.
