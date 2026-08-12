"""
Leibniz Gradio App — Production-ready proof checking & discovery
================================================================
Features:
  • File upload (JSONL theorem/proof batches)
  • Pre-loaded Linear Algebra sample dataset (15 theorems)
  • Individual theorem review with 3-gate output
  • Batch processing: upload → review all → download results
  • Real model inference (HF backend when available, falls back to Stub)
  • Model status indicator
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import gradio as gr  # type: ignore

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict
from leibniz.encyclopedia import default as default_enc
from leibniz.llm.backend import get_backend
from leibniz.config import config

# ---- sample data path ----
SAMPLES_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "samples"
SAMPLE_FILE = SAMPLES_DIR / "linear_algebra.jsonl"


# ---- engine ----
engine = Engine()

# Attempt HF backend if torch + transformers are available
model_loaded = False
hf_model = None
hf_tokenizer = None
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    hf_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-Math-1.5B-Instruct",
        torch_dtype=torch.float32, device_map="cpu", low_cpu_mem_usage=True,
    )
    hf_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Math-1.5B-Instruct")
    hf_model.eval()
    model_loaded = True
except Exception as e:
    print(f"[app] HF model not available: {e}")
    print("[app] Using StubBackend (deterministic, offline).")

# ---- helpers ----

def load_jsonl(path: str | Path) -> List[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _theorem_from_row(r: dict) -> Theorem:
    return Theorem(
        name=r.get("name", ""),
        informal=r.get("informal", ""),
        lean_statement=r.get("lean_statement", r.get("stmt", "")),
        domain=r.get("domain", "general"),
        difficulty=r.get("difficulty", "medium"),
        keywords=list(r.get("keywords", [])),
    )


def _proof_from_row(r: dict) -> Proof:
    return Proof(
        lean_tactics=r.get("lean_proof", r.get("proof", "")),
        informal=r.get("informal", ""),
    )


def _render_gate_report(report: dict) -> str:
    lines = []
    v = report.get("validity", {})
    if v.get("passed") is True and v.get("formal"):
        lines.append("### 🔐 Gate 1 — Validity: ✅ FORMALLY CERTIFIED")
    elif v.get("passed") is True:
        lines.append(f"### 🔐 Gate 1 — Validity: ⚠️ PROVISIONAL")
    elif v.get("passed") is None:
        lines.append(f"### 🔐 Gate 1 — Validity: ⚪ SKIPPED")
    else:
        lines.append(f"### 🔐 Gate 1 — Validity: ❌ REJECTED")
    if v.get("certificate"):
        lines.append(f"> `{v['certificate']}`")

    a = report.get("alignment", {})
    lines.append(f"### 🧭 Gate 2 — Alignment: **{a.get('score',0):.2f}**  "
                 f"(matched: {', '.join(a.get('matched_concepts',[])) or '(none)'})")

    r = report.get("reading", {})
    lines.append(f"### 📖 Gate 3 — Reading: **{r.get('overall_verdict','').upper()}**")
    for tv in r.get("tiers", []):
        e = {"pass":"✅","warn":"⚠️","fail":"❌"}.get(tv.get("verdict",""),"⚪")
        lines.append(f"- {e} `{tv.get('tier','')}` — {(tv.get('comments',['']))[0] if tv.get('comments') else ''}")

    overall = report.get("overall_pass", False)
    icon = "✅ PASS" if overall else "⚠️ ATTENTION"
    lines.append(f"\n### 🏁 Overall: {icon}")
    return "\n".join(lines)


# ---- callbacks ----

def cb_single_review(name, informal, stmt, proof, domain, difficulty):
    """Review ONE theorem/proof through all 3 gates."""
    if not stmt.strip():
        return "⚠️ Please enter a Lean theorem statement."
    if not proof.strip():
        return "⚠️ Please enter a proof (tactic block or proof term)."

    t = Theorem(
        name=name.strip() or "unnamed",
        informal=informal.strip(),
        lean_statement=stmt.strip(),
        domain=domain.strip() or "general",
        difficulty=difficulty,
    )
    p = Proof(lean_tactics=proof.strip(), informal=informal.strip())
    report = to_dict(engine.review(t, p))
    return _render_gate_report(report)


def cb_load_sample():
    """Load and return the sample dataset preview."""
    if not SAMPLE_FILE.exists():
        return "⚠️ Sample file not found.", gr.update(choices=[])

    rows = load_jsonl(SAMPLE_FILE)
    lines = [f"## 📂 Loaded: {SAMPLE_FILE.name}", f"**{len(rows)} theorems** ready for batch processing.", ""]
    lines.append("| # | Name | Difficulty | Domain |")
    lines.append("|---|------|-----------|--------|")
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | `{r.get('name','?')}` | {r.get('difficulty','?')} | {r.get('domain','?')} |")
    return "\n".join(lines), gr.update(choices=[r["name"] for r in rows], value=rows[0]["name"] if rows else None)


def cb_load_row(selected_name: str):
    """Load a specific row from the sample file into the form fields."""
    if not selected_name or not SAMPLE_FILE.exists():
        return "", "", "", "", ""
    rows = load_jsonl(SAMPLE_FILE)
    for r in rows:
        if r.get("name") == selected_name:
            return (
                r.get("name", ""),
                r.get("informal", ""),
                r.get("lean_statement", r.get("stmt", "")),
                r.get("lean_proof", r.get("proof", "")),
                r.get("domain", "linear_algebra"),
            )
    return "", "", "", "", ""


def cb_batch_process(file_obj, selected_sample_name):
    """Process an uploaded JSONL file or the selected sample through all 3 gates."""
    start = time.time()
    # Determine source
    if file_obj is not None:
        path = file_obj.name
        source = os.path.basename(path)
    else:
        path = str(SAMPLE_FILE)
        source = SAMPLE_FILE.name

    if not os.path.exists(path):
        return f"⚠️ No data source found.", None, ""

    rows = load_jsonl(path)
    results: List[dict] = []
    summary_lines = [f"# 📊 Batch Review: {source}", f"Processing {len(rows)} theorems…", ""]

    passed = 0
    for i, r in enumerate(rows):
        t = _theorem_from_row(r)
        p = _proof_from_row(r)
        report = to_dict(engine.review(t, p))
        report["_index"] = i + 1
        report["_name"] = t.name
        results.append(report)
        if report.get("overall_pass"):
            passed += 1

        # Status
        validity = report.get("validity", {}).get("passed")
        v_icon = "✅" if validity is True else ("❌" if validity is False else "⚪")
        align = report.get("alignment", {}).get("score", 0)
        read = report.get("reading", {}).get("overall_verdict", "?")
        summary_lines.append(
            f"| {i+1:2d} | `{t.name[:28]:28s}` | {v_icon} | {align:.2f} | `{read:4s}` | "
            f"{'✅' if report.get('overall_pass') else '⚠️'} |"
        )

    elapsed = time.time() - start
    summary_lines.insert(3, "| # | Theorem | Validity | Align | Read | Overall |")
    summary_lines.insert(4, "|---|---------|----------|-------|------|---------|")
    summary_lines.append(f"\n**Passed: {passed}/{len(rows)} ({passed/len(rows)*100:.0f}%)** · {elapsed:.1f}s")

    # Prepare download
    download_path = os.path.join(tempfile.gettempdir(), "leibniz_batch_results.json")
    with open(download_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return "\n".join(summary_lines), download_path, ""


def cb_model_status():
    if model_loaded:
        return f"🧠 **Real model loaded:** `Qwen/Qwen2.5-Math-1.5B-Instruct` (CPU, {hf_model.num_parameters():,} params)"
    return f"📋 **StubBackend active** (deterministic, offline). Encyc: {len(default_enc().all())} entries."


def cb_review_uploaded(file_obj):
    if file_obj is None:
        return "⚠️ Please upload a JSONL file first.", None
    return cb_batch_process(file_obj, None)


# ---- UI ----

css = """
.gate-pass { background: #d1fae5; color: #059669; padding: 2px 8px; border-radius: 4px; }
.gate-warn { background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 4px; }
.gate-fail { background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 4px; }
.mono { font-family: 'Cascadia Code', 'Fira Code', monospace; }
"""

def build():
    with gr.Blocks(title="🧮 Leibniz — Proof Engine", fill_height=True) as app:
        gr.Markdown("""# 🧮 Leibniz — A Universal Calculator for Truth
        **Three-stage mathematical discovery & proof checking**, with Lean 4 formal verification.
        24 encyclopedia entries · 5 pipeline stages · 3 backends.""")
        status = gr.Markdown("⏳ Loading…")

        with gr.Tabs():
            # ═══════════════════════════════════════════════════════
            # TAB 1: SINGLE REVIEW
            # ═══════════════════════════════════════════════════════
            with gr.TabItem("📋 Single Review"):
                gr.Markdown("Paste a theorem and proof → 3-gate review (Validity → Alignment → Reading).")
                with gr.Row():
                    with gr.Column(scale=2):
                        name = gr.Textbox("add_comm_vec", label="Theorem name")
                        stmt = gr.Textbox(
                            "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
                            label="Lean 4 statement", lines=2,
                        )
                        proof = gr.Textbox(
                            "by ext i; exact add_comm (v i) (w i)",
                            label="Proof (tactic block)", lines=3,
                        )
                        with gr.Row():
                            domain_in = gr.Dropdown(
                                ["linear_algebra", "arithmetic", "algebra", "number_theory", "set_theory", "general"],
                                value="linear_algebra", label="Domain",
                            )
                            diff_in = gr.Dropdown(
                                ["easy", "medium", "hard"], value="easy", label="Difficulty",
                            )
                        informal_in = gr.Textbox("v + w = w + v for vectors in ℝⁿ", label="Informal statement")
                        with gr.Row():
                            review_btn = gr.Button("🔍 Run Review", variant="primary", size="lg")
                            clear_btn = gr.Button("✕ Clear", size="lg")

                    with gr.Column(scale=3):
                        review_out = gr.Markdown("*(Results appear here after review.)*")

                review_btn.click(
                    cb_single_review,
                    [name, informal_in, stmt, proof, domain_in, diff_in],
                    review_out,
                )
                clear_btn.click(
                    lambda: ("", "", "", "", "linear_algebra", "easy", "*(Cleared.)*"),
                    [], [name, informal_in, stmt, proof, domain_in, diff_in, review_out],
                )

            # ═══════════════════════════════════════════════════════
            # TAB 2: BATCH PROCESSING
            # ═══════════════════════════════════════════════════════
            with gr.TabItem("📦 Batch Processing"):
                gr.Markdown("Upload a JSONL file of theorems, or use the built-in Linear Algebra sample.")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📁 Upload file")
                        upload_file = gr.File(label="Upload JSONL", file_types=[".jsonl", ".json"])
                        upload_btn = gr.Button("🔍 Review Uploaded File", variant="secondary")
                        gr.Markdown("---")
                        gr.Markdown("### 🧮 Sample dataset")
                        load_sample_btn = gr.Button("📂 Load Linear Algebra Sample", variant="secondary")
                        sample_preview = gr.Markdown("")

                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")
                        batch_output = gr.Markdown("*(Upload or load sample to start.)*")
                        download_out = gr.File(label="⬇ Download results (JSON)", visible=True)

                upload_btn.click(cb_review_uploaded, upload_file, [batch_output, download_out])
                load_sample_btn.click(cb_load_sample, [], [sample_preview])

                # Quick load a specific theorem from sample
                with gr.Row():
                    sample_selector = gr.Dropdown([], label="Quick-load theorem into Single Review tab", interactive=True)
                sample_selector.change(cb_load_row, sample_selector, [name, informal_in, stmt, proof, domain_in])
                load_sample_btn.click(
                    cb_load_sample, [], [sample_preview, sample_selector]
                )

            # ═══════════════════════════════════════════════════════
            # TAB 3: DISCOVERY
            # ═══════════════════════════════════════════════════════
            with gr.TabItem("🔍 Discovery"):
                gr.Markdown("Seed a topic → Discover conjectures → Prove → Verify.")
                with gr.Row():
                    seed = gr.Textbox("linear algebra", label="Seed topic")
                    n_slider = gr.Slider(1, 10, value=5, step=1, label="Conjectures")
                    k_slider = gr.Slider(1, 8, value=4, step=1, label="Candidates/theorem")
                disc_btn = gr.Button("🚀 Run Discovery", variant="primary", size="lg")
                disc_out = gr.Markdown("*(Results appear here.)*")

                def cb_discover(seed_val, n_val, k_val):
                    result = to_dict(engine.discover_and_verify(seed_val, n=n_val, k=k_val))
                    lines = [
                        f"## 🔍 Discovery: `{result['seed']}`",
                        f"**Conjectures:** {len(result['conjectures'])} · "
                        f"**Certified:** {len(result['certified'])} · "
                        f"**Failed:** {len(result['failed'])} · "
                        f"**Rate:** {result.get('success_rate',0):.0%}\n",
                    ]
                    for c in result["certified"]:
                        t, p = c["theorem"], c["proof"]
                        lines.append(f"✅ **{t['name']}** ({t['domain']})")
                        lines.append(f"> `{t['lean_statement']}  :=  {p['lean_tactics']}`")
                    for c in result["failed"]:
                        lines.append(f"❌ **{c['theorem']['name']}** ({c['theorem']['domain']}) — no passing proof")
                    return "\n".join(lines)

                disc_btn.click(cb_discover, [seed, n_slider, k_slider], disc_out)

            # ═══════════════════════════════════════════════════════
            # TAB 4: ABOUT
            # ═══════════════════════════════════════════════════════
            with gr.TabItem("ℹ️ About"):
                gr.Markdown(f"""
                ## Leibniz Engine v0.1.0

                | Gate | What | Method |
                |------|------|--------|
                | **Validity** | Does the proof compile in Lean 4? | Formal type-check / pattern-match |
                | **Alignment** | Does it target the right concepts? | Encyclopedia overlap score 0–1 |
                | **Reading** | Human-style scrutiny | easy → medium → hard |

                ### Model Status
                {cb_model_status()}

                ### Quick start — command line
                ```bash
                pip install -r requirements.txt
                python scripts/demo.py --seed "linear algebra"
                python -m uvicorn api.main:app --port 8430
                ```

                ### References
                - **Tudor Achim** — *The Path to Mathematical Superintelligence* (TED)
                - **G.W. Leibniz** — *De Arte Combinatoria* (1666)
                - [GitHub repo](https://github.com/twomathematicians-code/leibniz)
                - [Browser playground](https://twomathematicians-code.github.io/leibniz/)
                """)

        # Initialize status
        app.load(lambda: cb_model_status(), [], status)

    return app


if __name__ == "__main__":
    app = build()
    app.launch(
        server_name="127.0.0.1", server_port=7860, share=False,
        css=css,
    )
