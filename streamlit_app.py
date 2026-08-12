"""
Leibniz — Streamlit App
========================
PDF + JSONL upload → 3‑gate proof verification + discovery mode.

Deploy on Streamlit Community Cloud: just push this file + requirements.txt.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure the leibniz package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st  # type: ignore
import pandas as pd

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict
from leibniz.core.difficulty import Difficulty
from leibniz.encyclopedia import default as default_enc

# ═══════════════════════════════════════════════════════════════════════
# Config & session state
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Leibniz — Proof Verifier",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "engine" not in st.session_state:
    st.session_state.engine = Engine()
if "results" not in st.session_state:
    st.session_state.results = []
if "last_upload" not in st.session_state:
    st.session_state.last_upload = None

engine = st.session_state.engine
enc = default_enc()

# ═══════════════════════════════════════════════════════════════════════
# Sample data
# ═══════════════════════════════════════════════════════════════════════

SAMPLE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra.jsonl"

EXAMPLES = {
    "✅ Valid — vector addition commutes": {
        "name": "add_comm_vec",
        "informal": "v + w = w + v for vectors in ℝⁿ",
        "lean_statement": "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
        "lean_proof": "by ext i; exact add_comm (v i) (w i)",
        "domain": "linear_algebra", "difficulty": "easy",
    },
    "✅ Valid — 2 + 2 = 4": {
        "name": "two_plus_two",
        "informal": "Two plus two equals four",
        "lean_statement": "theorem two_plus_two : 2 + 2 = 4",
        "lean_proof": "by rfl",
        "domain": "arithmetic", "difficulty": "easy",
    },
    "✅ Valid — scalar distributivity": {
        "name": "smul_add_vec",
        "informal": "c · (v + w) = c·v + c·w",
        "lean_statement": "theorem smul_add_vec (c : ℝ) (v w : Fin n → ℝ) : c • (v + w) = c • v + c • w",
        "lean_proof": "by ext i; exact mul_add c (v i) (w i)",
        "domain": "linear_algebra", "difficulty": "medium",
    },
    "❌ Counter‑example — `sorry` (Gate 1 fails)": {
        "name": "two_plus_two",
        "informal": "Two plus two equals four",
        "lean_statement": "theorem two_plus_two : 2 + 2 = 4",
        "lean_proof": "by sorry",
        "domain": "arithmetic", "difficulty": "easy",
    },
    "❌ Counter‑example — wrong domain (Gate 2 fails)": {
        "name": "add_comm_vec",
        "informal": "v + w = w + v (vectors)",
        "lean_statement": "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
        "lean_proof": "by rw [Nat.add_comm]",
        "domain": "linear_algebra", "difficulty": "easy",
    },
    "⚠️ Counter‑example — insufficient (Gate 3 warns)": {
        "name": "eigenvalue_id",
        "informal": "Identity map eigenvalue",
        "lean_statement": "theorem eigenvalue_id (v : Fin n → ℝ) (hv : v ≠ 0) : (λ x : Fin n → ℝ => x) v = (1 : ℝ) • v",
        "lean_proof": "by trivial",
        "domain": "linear_algebra", "difficulty": "medium",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _parse_pdf(file_bytes: bytes) -> List[dict]:
    """Extract text from a PDF and attempt to find theorem–proof pairs."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        st.error("`pdfplumber` is required for PDF parsing. Install: `pip install pdfplumber`")
        return []

    rows: List[dict] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Heuristic: split on double newlines, look for "theorem" / "proof" markers
    chunks = full_text.split("\n\n")
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Try to extract a theorem statement and proof
        lines = chunk.split("\n")
        stmt, proof = "", ""
        in_proof = False
        for line in lines:
            if "theorem" in line.lower() and not stmt:
                stmt = line.strip()
            elif "proof" in line.lower() or "by " in line.lower():
                proof = line.strip()
                in_proof = True
            elif in_proof:
                proof += " " + line.strip()
        if stmt:
            rows.append({
                "name": f"pdf_theorem_{i+1}",
                "informal": "",
                "lean_statement": stmt,
                "lean_proof": proof,
                "domain": "general",
                "difficulty": "medium",
                "keywords": [],
            })
    return rows


def _parse_jsonl(content: str) -> List[dict]:
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _theorem_from_dict(d: dict) -> Theorem:
    return Theorem(
        name=d.get("name", ""),
        informal=d.get("informal", ""),
        lean_statement=d.get("lean_statement", d.get("stmt", "")),
        domain=d.get("domain", "general"),
        difficulty=d.get("difficulty", "medium"),
        keywords=list(d.get("keywords", [])),
    )


def _proof_from_dict(d: dict) -> Proof:
    return Proof(
        lean_tactics=d.get("lean_proof", d.get("proof", "")),
        informal=d.get("informal", ""),
    )


def _gate_icon(passed: Optional[bool]) -> str:
    if passed is True:
        return "✅"
    if passed is False:
        return "❌"
    return "⚪"


def _verdict_color(v: str) -> str:
    return {"pass": "green", "warn": "orange", "fail": "red"}.get(v, "grey")


# ═══════════════════════════════════════════════════════════════════════
# UI — Sidebar
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.title("🧮 Leibniz")
st.sidebar.caption("v0.2.0 — Universal Calculator for Truth")

st.sidebar.markdown(f"""
**Engine:** `{engine.backend.name}`  
**Encyclopedia:** {len(enc.all())} theorems  
**Lean available:** {"✅" if engine.lean.available else "❌ (provisional mode)"}
""")

mode = st.sidebar.radio(
    "Mode",
    ["📋 Single Review", "📦 Batch Upload", "🔍 Discovery", "ℹ️ About"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Sample Data")

if SAMPLE_FILE.exists():
    with open(SAMPLE_FILE) as f:
        sample_content = f.read()
    st.sidebar.download_button(
        "⬇ Linear Algebra sample (JSONL)",
        sample_content, "linear_algebra.jsonl", "application/jsonl",
    )

st.sidebar.markdown("### 🔗 Links")
st.sidebar.markdown("[GitHub](https://github.com/twomathematicians-code/leibniz)")
st.sidebar.markdown("[Browser Playground](https://twomathematicians-code.github.io/leibniz/)")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Single Review
# ═══════════════════════════════════════════════════════════════════════

if mode == "📋 Single Review":
    st.title("📋 Single Theorem Review")
    st.markdown("Paste a theorem and proof below — the engine runs all **3 gates** and returns a verdict.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Input")
        example_choice = st.selectbox(
            "Load an example or counter‑example:",
            ["(custom)"] + list(EXAMPLES.keys()),
            help="Select a pre‑loaded example to auto‑fill the form.",
        )

        if example_choice != "(custom)":
            ex = EXAMPLES[example_choice]
            default_name = ex["name"]
            default_stmt = ex["lean_statement"]
            default_proof = ex["lean_proof"]
            default_domain = ex["domain"]
            default_diff = ex["difficulty"]
            default_informal = ex["informal"]
        else:
            default_name = ""
            default_stmt = ""
            default_proof = ""
            default_domain = "linear_algebra"
            default_diff = "easy"
            default_informal = ""

        name = st.text_input("Theorem name", value=default_name, placeholder="e.g. add_comm_vec")
        domain = st.selectbox(
            "Domain",
            ["linear_algebra", "arithmetic", "algebra", "number_theory", "set_theory", "general"],
            index=["linear_algebra", "arithmetic", "algebra", "number_theory", "set_theory", "general"].index(default_domain),
        )
        diff = st.selectbox("Difficulty", ["easy", "medium", "hard"],
                           index=["easy", "medium", "hard"].index(default_diff))
        informal = st.text_area("Informal statement", value=default_informal, height=68,
                               placeholder="Plain‑English statement of the theorem")
        stmt = st.text_area(
            "Lean 4 statement",
            value=default_stmt,
            height=100,
            placeholder="theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
            help="The full Lean 4 theorem header (no proof).",
        )
        proof = st.text_area(
            "Proof (tactic block or proof term)",
            value=default_proof,
            height=100,
            placeholder="by ext i; exact add_comm (v i) (w i)",
            help="The tactic block following `:= ` — e.g., `by rfl`, `by simp`, `by rw [Nat.add_comm]`.",
        )

        go = st.button("🔍 Run 3‑Gate Review", type="primary", use_container_width=True)

    with col2:
        st.subheader("Result")
        if go:
            if not stmt.strip():
                st.error("Please enter a Lean 4 theorem statement.")
            elif not proof.strip():
                st.warning("No proof entered — Gate 1 will be skipped.")
                t = Theorem(name.strip() or "unnamed", informal.strip(), stmt.strip(), domain, diff)
                p = Proof(lean_tactics=None, informal=informal.strip())
                report = to_dict(engine.review(t, p))
            else:
                t = Theorem(name.strip() or "unnamed", informal.strip(), stmt.strip(), domain, diff)
                p = Proof(lean_tactics=proof.strip(), informal=informal.strip())
                report = to_dict(engine.review(t, p))

            # Gate 1
            v = report["validity"]
            icon = _gate_icon(v.get("passed"))
            formal_tag = " (formal)" if v.get("formal") else " (provisional)"
            st.markdown(f"### {icon} Gate 1 — Validity{formal_tag}")
            if v.get("certificate"):
                st.code(v["certificate"], language=None)
            if v.get("error"):
                st.caption(f"⚠️ {v['error']}")

            # Gate 2
            a = report["alignment"]
            st.markdown(f"### 🧭 Gate 2 — Alignment — Score: **{a['score']:.2f}**")
            st.progress(a["score"])
            cols = st.columns(2)
            with cols[0]:
                if a.get("matched_concepts"):
                    st.markdown("**✅ Matched:** " + ", ".join(f"`{c}`" for c in a["matched_concepts"]))
                else:
                    st.caption("(no concepts matched)")
            with cols[1]:
                if a.get("missing_concepts"):
                    st.markdown("**❌ Missing:** " + ", ".join(f"`{c}`" for c in a["missing_concepts"]))
                else:
                    st.caption("(no concepts missing)")
            if a.get("rationale"):
                st.caption(a["rationale"])

            # Gate 3
            r = report["reading"]
            st.markdown(f"### 📖 Gate 3 — Reading — **{r['overall_verdict'].upper()}**")
            for tv in r.get("tiers", []):
                vc = _verdict_color(tv["verdict"])
                with st.expander(f"{tv['tier'].upper()} — {tv['verdict'].upper()}", expanded=(tv['verdict']!='pass')):
                    for c in tv.get("comments", []):
                        st.markdown(f":{vc}[{c}]")

            # Overall
            overall = report["overall_pass"]
            if overall:
                st.success("🏁 **OVERALL: PASS** — the proof cleared all three gates.")
            else:
                st.warning("🏁 **OVERALL: ATTENTION** — one or more gates flagged issues. Review the details above.")

            # Download
            st.download_button(
                "⬇ Download report (JSON)",
                json.dumps(report, indent=2, ensure_ascii=False),
                f"leibniz_review_{name.strip() or 'report'}.json",
                "application/json",
            )

# ═══════════════════════════════════════════════════════════════════════
# MODE: Batch Upload
# ═══════════════════════════════════════════════════════════════════════

elif mode == "📦 Batch Upload":
    st.title("📦 Batch Proof Verification")
    st.markdown("Upload a **JSONL file** or a **PDF** of theorems — the engine verifies each against all 3 gates and gives you a downloadable report.")

    tab1, tab2 = st.tabs(["📄 JSONL Upload", "📑 PDF Upload"])

    with tab1:
        st.markdown("Upload a `.jsonl` file. Each line should be a JSON object with `lean_statement` and `lean_proof` fields.\n\nSee the sidebar to download a sample.")
        jsonl_file = st.file_uploader("Choose a JSONL file", type=["jsonl", "json"], key="jsonl_upload")

        if jsonl_file:
            content = jsonl_file.read().decode("utf-8", errors="replace")
            rows = _parse_jsonl(content)
            with_proofs = [r for r in rows if r.get("lean_proof", "").strip()]
            st.info(f"Parsed **{len(rows)}** theorems ({len(with_proofs)} with proofs).")

            if st.button("🔍 Verify All", type="primary", use_container_width=True):
                results = []
                progress = st.progress(0)
                status = st.empty()
                passed_count = 0

                for i, r in enumerate(rows):
                    status.text(f"Processing {i+1}/{len(rows)}: {r.get('name','?')}")
                    t = _theorem_from_dict(r)
                    p = _proof_from_dict(r)
                    report = to_dict(engine.review(t, p))
                    report["_name"] = t.name
                    report["_domain"] = t.domain
                    results.append(report)
                    if report.get("overall_pass"):
                        passed_count += 1
                    progress.progress((i + 1) / len(rows))

                status.text(f"Done. {passed_count}/{len(rows)} passed.")
                st.session_state.results = results
                st.session_state.last_upload = jsonl_file.name

                # Summary table
                df_data = []
                for r in results:
                    v = r["validity"]
                    a = r["alignment"]
                    rd = r["reading"]
                    df_data.append({
                        "Theorem": r["_name"],
                        "Domain": r.get("_domain", ""),
                        "Validity": _gate_icon(v.get("passed")),
                        "Alignment": f"{a['score']:.2f}",
                        "Reading": rd["overall_verdict"],
                        "Overall": "✅" if r["overall_pass"] else "⚠️",
                    })

                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
                st.metric("Pass Rate", f"{passed_count}/{len(rows)} ({passed_count/len(rows)*100:.0f}%)")

                # Download
                st.download_button(
                    "⬇ Download full results (JSON)",
                    json.dumps(results, indent=2, ensure_ascii=False),
                    "leibniz_batch_results.json",
                    "application/json",
                )

    with tab2:
        st.markdown("Upload a **PDF** (lecture notes, problem set, research draft). The engine extracts text and attempts to find theorem–proof pairs.")
        pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_upload")

        if pdf_file:
            rows = _parse_pdf(pdf_file.read())
            if rows:
                st.info(f"Extracted **{len(rows)}** candidate theorem–proof pairs from the PDF.")
                with st.expander("Preview extracted pairs"):
                    for i, r in enumerate(rows):
                        st.markdown(f"**{r['name']}**")
                        st.code(r.get("lean_statement", "")[:200])
                        if r.get("lean_proof"):
                            st.caption(f"Proof: `{r['lean_proof'][:100]}`")
                if st.button("🔍 Verify Extracted Pairs", type="primary", use_container_width=True, key="pdf_verify"):
                    results = []
                    progress = st.progress(0)
                    passed_count = 0
                    for i, r in enumerate(rows):
                        t = _theorem_from_dict(r)
                        p = _proof_from_dict(r)
                        report = to_dict(engine.review(t, p))
                        report["_name"] = t.name
                        results.append(report)
                        if report.get("overall_pass"):
                            passed_count += 1
                        progress.progress((i + 1) / len(rows))
                    st.metric("Pass Rate", f"{passed_count}/{len(rows)} ({passed_count/len(rows)*100:.0f}%)")
                    st.download_button(
                        "⬇ Download results (JSON)",
                        json.dumps(results, indent=2, ensure_ascii=False),
                        "leibniz_pdf_results.json",
                        "application/json",
                    )
            else:
                st.warning("Could not extract theorem–proof pairs from this PDF. Try a JSONL file instead.")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Discovery
# ═══════════════════════════════════════════════════════════════════════

elif mode == "🔍 Discovery":
    st.title("🔍 Discovery Mode")
    st.markdown("Seed a topic → the engine proposes **conjectures**, generates **candidate proofs**, and returns those that pass verification.")

    col1, col2 = st.columns([1, 2])
    with col1:
        seed = st.text_input("Seed topic", value="linear algebra",
                            placeholder="e.g. prime numbers, linear algebra, set theory")
        n_conj = st.slider("Conjectures to propose", 1, 10, 5)
        k_cands = st.slider("Candidate proofs per conjecture", 1, 8, 4)
        go_disc = st.button("🚀 Run Discovery", type="primary", use_container_width=True)

    with col2:
        if go_disc:
            with st.spinner(f"Discovering conjectures for '{seed}'…"):
                result = to_dict(engine.discover_and_verify(seed, n=n_conj, k=k_cands))

            certified = result.get("certified", [])
            failed = result.get("failed", [])
            rate = result.get("success_rate", 0)

            st.metric("Success Rate", f"{rate:.0%}", f"{len(certified)} certified / {len(failed)} failed")

            if certified:
                st.subheader("✅ Certified Theorems")
                for c in certified:
                    t, p = c["theorem"], c["proof"]
                    domain = t.get("domain", "")
                    diff = t.get("difficulty", "")
                    with st.expander(f"✅ {t['name']} ({domain}, {diff})"):
                        st.code(f"{t['lean_statement']}  :=  {p['lean_tactics']}", language="lean")
                        st.caption(f"Certificate: {c.get('certificate','')}")

            if failed:
                st.subheader("❌ Unproven Conjectures")
                for c in failed:
                    t = c["theorem"]
                    st.markdown(f"- **{t['name']}** ({t.get('domain','')}, {t.get('difficulty','')}) — no passing proof found")

            st.download_button(
                "⬇ Download discovery results (JSON)",
                json.dumps(result, indent=2, ensure_ascii=False),
                f"leibniz_discovery_{seed.replace(' ','_')}.json",
                "application/json",
            )

# ═══════════════════════════════════════════════════════════════════════
# MODE: About
# ═══════════════════════════════════════════════════════════════════════

elif mode == "ℹ️ About":
    st.title("ℹ️ About the Leibniz Engine")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### Leibniz's Three Pillars (~1666)

        | Pillar | Realisation |
        |--------|------------|
        | **Characteristica Universalis** (universal language) | `Theorem` · `Proof` · Lean 4 bridge |
        | **Encyclopedia** (verified thoughts) | 24‑entry knowledge base + Mathlib |
        | **Calculus Ratiocinator** (engine of reason) | Stub / HF / Remote LLM backends |
        """)

    with col2:
        st.markdown("""
        ### The Three Gates

        | Gate | Mechanism | Output |
        |------|-----------|--------|
        | **Validity** | Lean 4 type‑check or pattern‑match | ✅ / ❌ / ⚪ |
        | **Alignment** | Concept overlap vs. encyclopedia | 0.0 – 1.0 |
        | **Reading** | easy → medium → hard | pass / warn / fail |
        """)

    st.markdown("---")
    st.markdown("### 📊 Encyclopedia Coverage")

    domains = {}
    for e in enc.all():
        d = e.get("domain", "general")
        domains[d] = domains.get(d, 0) + 1
    df = pd.DataFrame([{"Domain": k, "Entries": v} for k, v in sorted(domains.items())])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🔬 Available Examples & Counter‑Examples")
    for label, ex in EXAMPLES.items():
        icon = label[:2]
        with st.expander(f"{icon} {label[2:]}"):
            st.code(f"{ex['lean_statement']}  :=  {ex['lean_proof']}", language="lean")
            st.caption(f"Domain: {ex['domain']} · Difficulty: {ex['difficulty']}")
            if st.button(f"🔍 Test this example", key=f"test_{ex['name']}_{hash(label)}"):
                t = Theorem(ex["name"], ex["informal"], ex["lean_statement"], ex["domain"], ex["difficulty"])
                p = Proof(lean_tactics=ex["lean_proof"])
                report = to_dict(engine.review(t, p))
                verdict = "✅ PASS" if report["overall_pass"] else "⚠️ ATTENTION"
                st.info(f"Result: {verdict} | Validity: {_gate_icon(report['validity']['passed'])} | Alignment: {report['alignment']['score']:.2f} | Reading: {report['reading']['overall_verdict']}")

    st.markdown("---")
    st.caption("Leibniz v0.2.0 · MIT License · [GitHub](https://github.com/twomathematicians-code/leibniz)")
