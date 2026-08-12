#!/usr/bin/env python
"""
Evaluator — pass@k
==================
Evaluates a prover model with the **pass@k** metric: for each held-out theorem,
sample k candidate proofs and check how many compile in Lean.

Two modes:
    * --stub : validate the harness WITHOUT a model or network (uses StubBackend
               and the bundled corpus). Proves eval.py + format.py are wired up.
    * real   : load the fine-tuned model, sample k proofs, compile each via the
               LeanClient, report pass@k.

Usage:
    python leibniz/training/eval.py --stub
    python leibniz/training/eval.py --config .../finetune_lora.yaml --checkpoint ... --k 4
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))   # leibniz/ project dir
sys.path.insert(0, PROJECT)                            # makes `leibniz` and `training` importable

import yaml  # type: ignore

from leibniz.core.types import Theorem, Proof  # noqa: E402
from leibniz.llm.backend import get_backend, StubBackend  # noqa: E402
from leibniz.formal.lean_client import LeanClient  # noqa: E402
from leibniz.config import EngineConfig  # noqa: E402
from training.data.format import load_corpus, filter_provable, train_val_split  # noqa: E402

try:
    import yaml as _yaml  # only needed for real-model mode; optional for --stub
except ImportError:  # pragma: no cover
    _yaml = None


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k (Chen et al. 2021): n samples, c correct."""
    if n - c < k:
        return 1.0
    return 1.0 - math.prod(1.0 - k / (n - i) for i in range(c))


def _row_to_theorem(row: dict) -> Theorem:
    return Theorem(
        name=row["name"],
        informal=row.get("domain", ""),
        lean_statement=row["statement"],
        domain=row.get("domain", "general"),
        difficulty=row.get("difficulty", "medium"),
    )


def run_stub(corpus_path: str, k: int, limit: int) -> None:
    """Harness check: StubBackend candidates + LeanClient (skips if no Lean)."""
    rows = filter_provable(load_corpus(corpus_path))[:limit]
    backend = StubBackend()
    lean = LeanClient()
    print(f"[eval:stub] {len(rows)} theorems | lean_available={lean.available} | k={k}")

    passed = 0
    for row in rows:
        t = _row_to_theorem(row)
        cands = backend.prove(t, k)
        ok = False
        for tac in cands:
            res = lean.check(t, Proof(lean_tactics=tac))
            if res.passed is True:
                ok = True
                break
        passed += int(ok)
        flag = "✓" if ok else "·"
        print(f"  {flag} {t.name}")
    rate = passed / max(len(rows), 1)
    print(f"[eval:stub] provisional pass rate: {passed}/{len(rows)} = {rate:.0%}")
    print("(pass@k equals this rate in stub mode since k candidates share one verdict)")


def run_model(config_path: str, checkpoint: str, k: int, limit: int) -> None:
    if _yaml is None:
        raise SystemExit("Real eval needs pyyaml. pip install pyyaml")
    cfg = _yaml.safe_load(open(config_path, "r", encoding="utf-8"))
    corpus_path = cfg["data"]["corpus"]
    if not os.path.isabs(corpus_path):
        corpus_path = os.path.join(HERE, corpus_path.replace("/", os.sep))
    _, val_rows = train_val_split(filter_provable(load_corpus(corpus_path)),
                                 cfg["data"].get("val_split", 0.1))
    val_rows = val_rows[:limit]

    try:
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except ImportError as exc:
        raise SystemExit("Real eval needs torch+transformers. pip install -r training/requirements.txt") from exc

    tok = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModelForCausalLM.from_pretrained(checkpoint, torch_dtype="auto").eval()
    dev = next(model.parameters()).device

    enc = EngineConfig(backend="stub")
    lean = LeanClient(enc)
    from training.data.format import format_sft  # noqa: E402
    gen_cfg = cfg.get("generation", {})
    max_new = gen_cfg.get("max_new_tokens", 256)
    temp = gen_cfg.get("temperature", 0.7)

    total_passatk = 0.0
    for row in val_rows:
        t = _row_to_theorem(row)
        prompt = format_sft(row)["prompt"]
        ids = tok(prompt, return_tensors="pt").to(dev)
        outs = model.generate(**ids, max_new_tokens=max_new, do_sample=True,
                              temperature=max(temp, 1e-2), num_return_sequences=k,
                              pad_token_id=tok.eos_token_id)
        cands = [tok.decode(o[ids["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
                 for o in outs]
        correct = 0
        for tac in cands:
            res = lean.check(t, Proof(lean_tactics=tac))
            if res.passed is True and res.formal:
                correct += 1
        pk = pass_at_k(k, correct, k)
        total_passatk += pk
        print(f"  {t.name}: {correct}/{k} compiled -> pass@{k}={pk:.2f}")
    n = max(len(val_rows), 1)
    print(f"[eval:model] mean pass@{k} over {len(val_rows)} theorems: {total_passatk/n:.3f}")


def main() -> None:
    p = argparse.ArgumentParser(description="Leibniz pass@k evaluator.")
    p.add_argument("--stub", action="store_true", help="validate harness without a model")
    p.add_argument("--config", default=None, help="YAML config (real mode)")
    p.add_argument("--checkpoint", default=None, help="model checkpoint dir (real mode)")
    p.add_argument("--corpus", default=os.path.join(HERE, "data", "bundled_sample.jsonl"))
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    if args.stub:
        run_stub(args.corpus, args.k, args.limit)
    else:
        if not args.config or not args.checkpoint:
            raise SystemExit("Real mode needs --config and --checkpoint.")
        run_model(args.config, args.checkpoint, args.k, args.limit)


if __name__ == "__main__":
    main()
