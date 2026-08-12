#!/usr/bin/env python
"""
Fine-Tuning Trainer
===================
YAML-driven SFT trainer for the Leibniz prover model.

    * method: lora  -> PEFT LoRA adapters (cheap; recommended; single GPU OK)
    * method: full  -> full fine-tuning (more capacity; needs more VRAM)

Usage:
    pip install -r leibniz/training/requirements.txt
    python leibniz/training/train.py --config leibniz/training/configs/finetune_lora.yaml

This script needs torch + transformers + peft (+ datasets). It is intentionally
NOT importable by the core package — it only runs on demand.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))  # leibniz/ project dir for `training.*`

from training.data.format import load_corpus, filter_provable, train_val_split, format_sft  # noqa: E402


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Leibniz SFT trainer.")
    parser.add_argument("--config", required=True, help="Path to a YAML training config.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    method = cfg.get("method", "lora")

    # --- heavy imports (deferred so --help works without them) ---
    try:
        import torch
        from datasets import Dataset
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  TrainingArguments, Trainer, DataCollatorForLanguageModeling)
    except ImportError as exc:
        raise SystemExit(
            "Training needs torch/transformers/datasets. "
            "Run: pip install -r leibniz/training/requirements.txt"
        ) from exc

    if method == "lora":
        from peft import LoraConfig, get_peft_model   # type: ignore

    # --- data ---
    corpus_path = cfg["data"]["corpus"]
    if not os.path.isabs(corpus_path):
        corpus_path = os.path.join(HERE, corpus_path.replace("/", os.sep))
    rows = filter_provable(load_corpus(corpus_path))
    if not rows:
        raise SystemExit(f"No provable rows found in {corpus_path}")
    train_rows, val_rows = train_val_split(rows, cfg["data"].get("val_split", 0.1))
    print(f"[train] {len(train_rows)} train / {len(val_rows)} val rows")

    # --- model + tokenizer ---
    base = cfg["base_model"]
    tok = AutoTokenizer.from_pretrained(cfg.get("tokenizer") or base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}.get(
        cfg.get("torch_dtype", "bf16"), torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=dtype)

    if method == "lora":
        lc = cfg.get("lora", {})
        peft_cfg = LoraConfig(
            r=lc.get("r", 16), lora_alpha=lc.get("alpha", 32),
            lora_dropout=lc.get("dropout", 0.05), bias="none", task_type="CAUSAL_LM",
            target_modules=lc.get("target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
        )
        model = get_peft_model(model, peft_cfg)
        model.print_trainable_parameters()

    max_len = cfg.get("max_seq_length") or cfg.get("training", {}).get("max_seq_length", 1024)

    def encode(rows_split):
        texts = [format_sft(r)["prompt"] + format_sft(r)["completion"] + tok.eos_token
                 for r in rows_split]
        return tok(texts, truncation=True, max_length=max_len)

    train_ds = Dataset.from_list(encode(train_rows))
    val_ds = Dataset.from_list(encode(val_rows)) if val_rows else None

    collator = DataCollatorForLanguageModeling(tok, mlm=False)
    t = cfg["training"]
    args = TrainingArguments(
        output_dir=t["output_dir"],
        num_train_epochs=t.get("epochs", 3),
        per_device_train_batch_size=t.get("batch_size", 4),
        gradient_accumulation_steps=t.get("grad_accum", 4),
        learning_rate=t.get("lr", 2e-4),
        warmup_ratio=t.get("warmup_ratio", 0.03),
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch" if val_ds else "no",
        report_to=[],
        fp16=(dtype == torch.float16),
        bf16=(dtype == torch.bfloat16),
    )

    trainer = Trainer(
        model=model, args=args,
        train_dataset=train_ds, eval_dataset=val_ds,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(t["output_dir"])
    tok.save_pretrained(t["output_dir"])
    print(f"[train] saved model -> {t['output_dir']}")


if __name__ == "__main__":
    main()
