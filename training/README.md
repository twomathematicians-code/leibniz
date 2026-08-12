# Leibniz Prover — Training Framework

This directory contains the **training pipeline** for the Leibniz prover model.
Per the project's "pipeline-now, fine-tune-later" decision, the framework is
complete and reproducible; the actual fine-tune run is deferred until you have
GPU access.

> The rest of the engine runs on the **StubBackend** with no ML stack at all.
> You only need this directory when you are ready to train a real model.

---

## 1. Install heavy dependencies

```bash
pip install -r leibniz/training/requirements.txt
```

This installs `torch`, `transformers`, `peft`, `trl`, `datasets`, `accelerate`.

## 2. (Optional) Build a larger corpus

A small bundled corpus ships here so everything runs out-of-the-box:

```bash
python leibniz/training/data/build_corpus.py --source bundled --out corpus.jsonl
# or pull public benchmarks (network required):
python leibniz/training/data/build_corpus.py --source minif2f  --out minif2f.jsonl
```

Each row uses the schema:
`{"name","statement","proof","domain","difficulty"}`

## 3. Smoke-test the data + eval harness (no model needed)

```bash
python leibniz/training/data/format.py                      # corpus sanity check
python leibniz/training/eval.py --stub --limit 20           # harness + provisional pass rate
```

## 4. Fine-tune

```bash
# LoRA (recommended; single GPU, ~8GB VRAM)
python leibniz/training/train.py --config leibniz/training/configs/finetune_lora.yaml

# Full fine-tune (more capacity; needs more VRAM)
python leibniz/training/train.py --config leibniz/training/configs/finetune_full.yaml
```

Checkpoints are written to `leibniz/training/checkpoints/`.

## 5. Evaluate (pass@k)

`eval.py` samples `k` proofs per held-out theorem and checks how many compile:

```bash
# Provisional (no Lean installed) — uses the encyclopedia pattern-match:
python leibniz/training/eval.py --stub --k 4

# Real (needs Lean installed for formal pass@k):
python leibniz/training/eval.py \
  --config leibniz/training/configs/finetune_lora.yaml \
  --checkpoint leibniz/training/checkpoints/lora --k 4
```

## Layout

```
training/
├── data/
│   ├── build_corpus.py      # bundled + minif2f/proofnet sources
│   ├── bundled_sample.jsonl # ~30 core-compilable Lean pairs
│   └── format.py            # SFT prompt/completion formatting
├── configs/
│   ├── base_model.yaml      # base-model reference
│   ├── finetune_lora.yaml   # recommended LoRA config
│   └── finetune_full.yaml   # full fine-tune config
├── train.py                 # HF Trainer + PEFT
└── eval.py                  # pass@k (stub + real)
```

## Notes

- **GPU**: LoRA on `Qwen2.5-Math-1.5B-Instruct` trains comfortably on a single
  8–12 GB GPU. Full fine-tuning of a 7B model needs ≥24 GB.
- **Real `pass@k` requires Lean** — install `elan` and run `lake build` in
  `leibniz/lean/`. Without Lean, `eval.py` reports provisional pass rates only.
- Swap `base_model` in the config for any HuggingFace causal LM you prefer.
