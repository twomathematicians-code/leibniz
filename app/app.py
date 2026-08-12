"""
Leibniz Gradio App — Hugging Face Space demo
=============================================
Two tabs running the full engine inline (StubBackend), with optional
remote-API mode via LEIBNIZ_API_URL.

Usage:
    pip install -r leibniz/app/requirements.txt
    python leibniz/app/app.py                      # local: http://127.0.0.1:7860
    LEIBNIZ_API_URL=https://my-api.onrender.com python leibniz/app/app.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure the leibniz package is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import gradio as gr  # type: ignore


API_URL = os.environ.get("LEIBNIZ_API_URL", "").rstrip("/")
USE_API = bool(API_URL)

if USE_API:
    import requests
    print(f"[app] calling remote API at {API_URL}")
else:
    from leibniz.pipeline import Engine
    from leibniz.core.types import Theorem, Proof
    engine = Engine()
    print(f"[app] inline engine  backend={engine.backend.name}  lean_available={engine.lean.available}")


# ---- shared helpers ----

def _api(path: str, body: dict = None) -> dict:
    resp = requests.post(f"{API_URL}{path}", json=body or {}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _render_report(report: dict) -> str:
    lines = []
    v = report.get("validity", {})
    cert = v.get("certificate") or ""
    if v.get("passed") is True and v.get("formal"):
        tag = "✅ FORMALLY CERTIFIED"
    elif v.get("passed") is True:
        tag = f"⚠️  PROVISIONAL  ({cert})"
    elif v.get("passed") is None:
        tag = f"⚪ SKIPPED  ({v.get('error','')})"
    else:
        tag = f"❌ REJECTED  ({v.get('error','')})"
    lines.append(f"### 🔐 Gate 1 — Validity\n{tag}")

    a = report.get("alignment", {})
    lines.append(f"### 🧭 Gate 2 — Alignment\nScore: **{a.get('score',0):.2f}**  "
                 f"Matched: {a.get('matched_concepts',[])}  Missing: {a.get('missing_concepts',[])}")

    r = report.get("reading", {})
    lines.append(f"### 📖 Gate 3 — Reading\nOverall: **{r.get('overall_verdict','')}**")
    for tv in r.get("tiers", []):
        lines.append(f"- `{tv.get('tier','')}` `{tv.get('verdict','')}`  "
                     f"{(tv.get('comments',['']))[0]}")
    overall = report.get("overall_pass", False)
    lines.append(f"\n### 🏁 Overall: {'✅ PASS' if overall else '⚠️  ATTENTION'}")
    return "\n".join(lines)


def _render_discovery(result: dict) -> str:
    seed = result.get("seed", "?")
    conjs = result.get("conjectures", [])
    cert = result.get("certified", [])
    failed = result.get("failed", [])
    rate = result.get("success_rate", 0)
    lines = [
        f"## Discovery: `{seed}`",
        f"Conjectures: {len(conjs)} | Certified: {len(cert)} | Failed: {len(failed)} | Rate: {rate:.0%}\n",
    ]
    lines.append("### ✅ Certified")
    for c in cert:
        t = c.get("theorem", {})
        p = c.get("proof", {})
        lines.append(f"- **{t.get('name','')}**  "
                     f"`{t.get('lean_statement','')}`  : = `{p.get('lean_tactics','')}`")
    if failed:
        lines.append("\n### ❌ Unproven")
    for c in failed:
        t = c.get("theorem", {})
        lines.append(f"- {t.get('name','')}  ({t.get('domain','')})")
    return "\n".join(lines)


# ---- callbacks ----

def cb_review(name, informal, stmt, proof, domain, difficulty) -> str:
    if USE_API:
        report = _api("/review", {
            "theorem": {"name": name, "informal": informal, "lean_statement": stmt.strip() or None,
                        "domain": domain, "difficulty": difficulty, "keywords": []},
            "proof": {"lean_tactics": proof.strip() or None, "informal": informal, "author": "user"},
        })
    else:
        t = Theorem(name, informal, stmt.strip() or None, domain, difficulty)
        p = Proof(lean_tactics=proof.strip() or None)
        from leibniz.core.types import to_dict
        report = to_dict(engine.review(t, p))
    return _render_report(report)


def cb_discover(seed, n, k) -> str:
    if USE_API:
        result = _api("/discover", {"seed": seed, "n": n, "k": k})
    else:
        from leibniz.core.types import to_dict
        result = to_dict(engine.discover_and_verify(seed, n=n, k=k))
    return _render_discovery(result)


def cb_health() -> str:
    if USE_API:
        d = _api("/health", {})
    else:
        d = {
            "status": "healthy", "backend": engine.backend.name,
            "lean_available": engine.lean.available, "model": engine.cfg.model,
            "uptime_seconds": 0,
        }
    return f"Backend: **{d['backend']}** | Model: `{d.get('model','?')}` | Lean: {'✅' if d.get('lean_available') else '❌'}"


# ---- UI ----

def build() -> gr.Blocks:
    with gr.Blocks(title="Leibniz Engine") as app:
        gr.Markdown("# 🧮 Leibniz — A Universal Calculator for Truth")
        gr.Markdown("Three-stage LLM-driven mathematical discovery & proof checking. "
                    f"Engine: `{API_URL + ' (remote)' if USE_API else 'inline (StubBackend)'}`.")

        with gr.Tabs():
            # --- Discovery Playground ---
            with gr.TabItem("🔍 Discovery Playground"):
                gr.Markdown("**Discover → Prove → Verify**: seed a topic and watch the engine propose, prove, and certify theorems.")
                with gr.Row():
                    seed = gr.Textbox("arithmetic and primes", label="Seed topic")
                    n_slider = gr.Slider(1, 15, value=5, step=1, label="Conjectures")
                    k_slider = gr.Slider(1, 8, value=4, step=1, label="Candidates per conjecture")
                run_btn = gr.Button("🚀 Run Discovery", variant="primary")
                disc_out = gr.Markdown("*(results appear here)*")

                run_btn.click(cb_discover, [seed, n_slider, k_slider], disc_out)

            # --- Proof Reviewer ---
            with gr.TabItem("📋 Proof Reviewer"):
                gr.Markdown("**Validity → Alignment → Reading**: paste a theorem and proof for the 3-gate review.")
                with gr.Row():
                    name = gr.Textbox("add_comm_nat", label="Theorem name")
                    domain = gr.Textbox("algebra", label="Domain")
                    diff = gr.Dropdown(["easy", "medium", "hard"], value="medium", label="Difficulty")
                informal = gr.Textbox("Addition of natural numbers is commutative: a + b = b + a.", label="Informal statement", lines=2)
                stmt = gr.Textbox("theorem add_comm_nat (a b : Nat) : a + b = b + a", label="Lean 4 statement", lines=2)
                proof = gr.Textbox("by rw [Nat.add_comm]", label="Proof (tactic block / proof term)", lines=3)
                review_btn = gr.Button("🔍 Run Review", variant="primary")
                review_out = gr.Markdown("*(results appear here)*")

                review_btn.click(cb_review, [name, informal, stmt, proof, domain, diff], review_out)

            # --- Info ---
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
                ## How it works

                | Gate | What it checks | Method |
                |------|---------------|--------|
                | **Validity** | Does the proof compile in Lean 4? | Formal type-check (or provisional pattern-match) |
                | **Alignment** | Do the proof's concepts match the theorem? | Encyclopedia concept-overlap score 0–1 |
                | **Reading** | How does the proof hold up under human-style scrutiny? | Three graded tiers: easy → medium → hard |

                ### The Leibniz vision (~1666)

                | Pillar | Our component |
                |--------|-------------|
                | *Characteristica Universalis* (logical language) | `theorem` / `proof` types + Lean 4 bridge |
                | *Encyclopedia* (verified thoughts) | Bundled knowledge base + Mathlib |
                | *Calculus Ratiocinator* (engine of reason) | LLM backends (stub/hf/remote) + the 5-stage pipeline |

                ### Run locally
                ```bash
                pip install -r leibniz/requirements.txt
                python leibniz/scripts/demo.py
                ```

                [GitHub](https://github.com/twomathematicians-code/riemann-hypothesis)
                """)
                gr.Button("🩺 Health Check").click(cb_health, [], gr.Markdown())

    return app


if __name__ == "__main__":
    app = build()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False,
              css="footer{display:none!important} .tab-nav button{font-size:1.05em}")
