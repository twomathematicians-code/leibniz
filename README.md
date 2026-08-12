<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Lean-4.14.0-brightgreen?logo=lean" alt="Lean 4">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Tests-53%2F53%20passing-success" alt="Tests">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/HuggingFace-Space-FF9D00?logo=huggingface&logoColor=white" alt="HF Space">
</p>

<h1 align="center">🧮 Leibniz</h1>
<h3 align="center"><em>A Universal Calculator for Truth</em></h3>

<p align="center">
  A three-stage, LLM-driven mathematical <strong>discovery &amp; proof-checking engine</strong><br>
  realizing Leibniz's 400-year-old vision with modern tools — Lean 4 + LLMs.
</p>

<p align="center">
  <a href="https://twomathematicians-code.github.io/leibniz/">🎮 Live Demo</a> ·
  <a href="#quick-start">🚀 Quick Start</a> ·
  <a href="#how-it-works">⚙️ How It Works</a> ·
  <a href="#deploy">☁️ Deploy</a>
</p>

---

## 🏛 Leibniz's Three Pillars (~1666)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   CHARACTERISTICA UNIVERSALIS          ENCYCLOPEDIA                  │
│   (universal logical language)         (verified thoughts)           │
│                                                                      │
│   Theorem · Proof · Conjecture         12‑entry knowledge base       │
│   GateReport · DiscoveryResult         + Mathlib bridge              │
│          │                                      │                    │
│          └──────────────┬───────────────────────┘                    │
│                         │                                            │
│               CALCULUS RATIOCINATOR                                  │
│               (engine of reason)                                     │
│                                                                      │
│         StubBackend  │  HFBackend  │  RemoteBackend                  │
│         (zero deps)     (local GPU)    (API endpoint)                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Two Modes

<table>
<tr>
<td width="50%" align="center">

### 🔍 Discovery

```
  SEED TOPIC
      │
      ▼
  DISCOVER
  (conjectures)
      │
      ▼
  PROVE
  (k candidates)
      │
      ▼
  VERIFY
  (Lean compile)
      │
      ▼
  ✅ CERTIFIED
```

</td>
<td width="50%" align="center">

### 📋 Review

```
  THEOREM + PROOF
      │
      ▼
  ┌─────────────────┐
  │ GATE 1: VALIDITY │   Lean type-check
  │   ✓ / ✗ / ⚪   │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ GATE 2: ALIGNMENT│   Concept overlap
  │   0.0 — 1.0     │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ GATE 3: READING  │   easy → medium → hard
  │  pass/warn/fail  │
  └────────┬────────┘
           ▼
       🏁 OVERALL
```

</td>
</tr>
</table>

---

## 🎮 Interactive Demo

<p align="center">
  <strong>Open in any browser — no install, no server.</strong><br>
  <img src="https://img.shields.io/badge/Try_it-Proof_Checker_Playground-4338ca?style=for-the-badge" alt="Try it">
</p>

The [**Proof Checker Playground**](https://twomathematicians-code.github.io/leibniz/) runs the full 3‑gate review **in your browser**:

- Click any of **10 pre‑loaded theorems** (2+2=4, commutativity, set union…)
- Or type your own Lean 4 statement + proof
- Watch each gate fire with **animated pass/warn/fail verdicts**
- See concept‑alignment scores, tiered reading results, and a final certificate

> Enable GitHub Pages: **Settings → Pages → Source: `main` / `docs`**

---

## 🚀 Quick Start

```bash
# 1. Clone and install (3 light packages — no ML)
git clone https://github.com/twomathematicians-code/leibniz.git
cd leibniz
pip install -r requirements.txt

# 2. One‑shot demo (both modes)
python scripts/demo.py

# 3. API server → http://localhost:8430/docs
python -m uvicorn api.main:app --host 0.0.0.0 --port 8430

# 4. Gradio interactive app → http://127.0.0.1:7860
pip install gradio
python app/app.py

# 5. Run tests
pip install pytest fastapi
PYTHONPATH=. pytest tests -q
```

### Demo output

```
DISCOVERY MODE  —  seed: 'arithmetic'
Conjectures: 5  |  Certified: 4  |  Unproven: 1  |  Success: 80%

  ✓ two_plus_two          theorem two_plus_two : 2 + 2 = 4 := by rfl
  ✓ add_comm_nat          theorem add_comm_nat (a b : Nat) : a + b = b + a
                          := by rw [Nat.add_comm]

REVIEW MODE  —  Theorem: add_comm_nat
  GATE 1 — VALIDITY:    ✓ PROVISIONAL (pattern‑match)
  GATE 2 — ALIGNMENT:   score=1.00  matched=['addition','commutativity','natural numbers']
  GATE 3 — READING:     overall=pass
      [easy  ] pass — Well‑formed tactic block
      [medium] pass — Matches the known‑good proof
      [hard  ] pass — Certified encyclopedia proof
  => OVERALL: PASS ✓
```

---

## 🧱 Architecture

```
leibniz/
├── leibniz/                     Python engine
│   ├── core/types.py            Formal language (11 dataclasses)
│   ├── llm/
│   │   ├── backend.py           Stub │ HF │ Remote backends
│   │   └── prompts.py           Per‑stage prompt templates
│   ├── stages/                  5 pipeline stages
│   │   ├── discover.py          Conjecture generation
│   │   ├── prove.py             Candidate‑proof sampling
│   │   ├── verify.py            Gate 1 — Lean compile
│   │   ├── align.py             Gate 2 — Concept scoring
│   │   └── read.py              Gate 3 — Graded tiers
│   ├── formal/
│   │   ├── lean_client.py       Lean 4 CLI bridge
│   │   └── snippets.py          .lean source assembler
│   ├── encyclopedia/
│   │   ├── data.json            12 seeded theorems + proofs
│   │   └── lookup.py            Keyword retrieval engine
│   └── pipeline.py              Orchestrator
│
├── api/                         FastAPI host (Render / Fly.io)
│   ├── main.py                  REST API — 7 endpoints
│   └── Dockerfile               python:3.11-slim
│
├── app/                         Gradio HF Space
│   └── app.py                   2‑tab interactive demo
│
├── docs/
│   └── index.html               🎮 Browser proof‑checker playground
│
├── lean/                        Lean 4 library (Mathlib‑free)
│   └── Leibniz/
│       ├── Basic.lean           CertifiedProof structure
│       ├── Examples.lean        6 genuine theorems (no sorry)
│       └── MathlibBridge.lean   Optional deep proofs
│
├── training/                    Fine‑tuning framework
│   ├── data/bundled_sample.jsonl  30 SFT pairs
│   ├── train.py                 HF Trainer + LoRA / full FT
│   ├── eval.py                  pass@k evaluator
│   └── configs/                 3 YAML configs
│
└── tests/                       53 tests (all pass)
```

---

## 🔌 Backends

| Backend | Selection | Dependencies | When |
|---------|-----------|-------------|------|
| **StubBackend** *(default)* | `LEIBNIZ_BACKEND=stub` | **None** | Demos, tests, CI — always works |
| **HFBackend** | `LEIBNIZ_BACKEND=hf` | `torch`, `transformers` | Local GPU model inference |
| **RemoteBackend** | `LEIBNIZ_BACKEND=remote` | `requests` | HF Space → hosted endpoint bridge |

> The whole pipeline is **runnable with zero heavy deps** via the StubBackend.

---

## 📐 Formal Verification (Lean 4)

The `lean/` directory is a standalone Lean 4 project with **no Mathlib dependency** — `lake build` completes in seconds after installing `elan`.

```
lean/
└── Leibniz/
    ├── Basic.lean           CertifiedProof record
    ├── Examples.lean        6 theorems, 0 sorry, all compile
    └── MathlibBridge.lean   Opt‑in deep proofs
```

When a Lean toolchain is present, the Python engine's provisional pattern‑matches turn into **real `lean:exit0` certificates**.

---

## 🏋️ Fine-Tuning a Prover Model

```bash
pip install -r training/requirements.txt          # torch, transformers, peft
python training/data/build_corpus.py              # bundled 30‑row corpus
python training/train.py --config configs/finetune_lora.yaml  # LoRA (8 GB GPU)
python training/eval.py --config ... --checkpoint ... --k 4  # pass@k
```

| Config | Method | VRAM | Speed |
|--------|--------|------|-------|
| `finetune_lora.yaml` | LoRA | ~8 GB | ⚡ Fast |
| `finetune_full.yaml` | Full FT | ≥24 GB | 🐢 Slow |

See [`training/README.md`](training/README.md) for full details.

---

## ☁️ Deploy

| Surface | File | Port | Host |
|---------|------|------|------|
| API host | `api/main.py` | 8430 | Render / Fly.io / Railway |
| HF Space | `app/app.py` | — | huggingface.co/spaces |
| Model server | `leibniz/llm/server.py` | 8431 | GPU back‑end |
| Browser sim | `docs/index.html` | — | GitHub Pages |

---

## 📚 Inspirations

- **Tudor Achim** — *The Path to Mathematical Superintelligence* (TED)
- **Gottfried Wilhelm Leibniz** — *De Arte Combinatoria* (1666)
- **David Loeffler & Michael Stoll** — *Formalizing Zeta and L‑Functions in Lean*
- **Terence Tao** — On formal proof assistants & the future of mathematical discovery

---

<p align="center">
  <em>"If we had an exact language, or at least a truly philosophical script,<br>
  by means of which ideas could be reduced to a kind of alphabet of human thoughts,<br>
  then one could, in disputation, simply say: Let us calculate!"</em><br>
  — Gottfried Wilhelm Leibniz, 1677
</p>
