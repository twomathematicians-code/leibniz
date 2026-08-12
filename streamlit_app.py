"""
Leibniz — Streamlit App  (Two Mathematicians brand)
=====================================================
Monochrome proof verification engine.  PDF + JSONL upload,
3‑gate review, discovery mode, examples & counter‑examples.

Brand: Inter 300–800, Playfair Display italic accent, black/white/zinc.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st  # type: ignore
import pandas as pd

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict
from leibniz.encyclopedia import default as default_enc

# ═══════════════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Leibniz — Proof Verifier",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════
# Brand CSS  (Two Mathematicians — monochrome)
# ═══════════════════════════════════════════════════════════════════════

BRAND_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,600;1,400&display=swap');

  :root {
    --ink: #000000;
    --slate: #1f2937;
    --muted: #6b7280;
    --faint: #f3f4f6;
    --line: #e5e7eb;
    --paper: #ffffff;
    --mono: 'SF Mono', 'Consolas', 'Roboto Mono', monospace;
  }

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: var(--ink);
  }

  h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  .brand-accent {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-weight: 400;
  }

  .brand-label {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--muted);
  }

  .brand-mono {
    font-family: var(--mono);
  }

  code, pre, .stCodeBlock {
    font-family: var(--mono) !important;
    background: var(--faint) !important;
    border: 1px solid var(--line) !important;
    border-radius: 3px !important;
  }

  /* Verdict indicators — monochrome */
  .verdict-pass { color: var(--ink); font-weight: 700; }
  .verdict-warn { color: var(--muted); font-weight: 500; }
  .verdict-fail { color: var(--line); font-weight: 400; text-decoration: line-through; }

  /* Pipeline motif */
  .pipeline { display: flex; gap: 0; align-items: center; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
  .pipeline-step { padding: 4px 10px; border: 1px solid var(--ink); color: var(--ink); }
  .pipeline-arrow { padding: 4px 6px; color: var(--muted); }

  /* Gate cards */
  .gate { border: 1px solid var(--line); border-radius: 3px; padding: 16px; margin: 8px 0; background: var(--paper); }
  .gate-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .gate-title { font-weight: 700; font-size: 1.02rem; }

  /* Progress bar — monochrome */
  .stProgress > div > div > div > div { background-color: var(--ink) !important; }
</style>
"""
st.markdown(BRAND_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# Session state
# ═══════════════════════════════════════════════════════════════════════

if "engine" not in st.session_state:
    st.session_state.engine = Engine()
engine = st.session_state.engine
enc = default_enc()

SAMPLE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra.jsonl"
SAMPLE_PDF = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra_proofs.pdf"

# ═══════════════════════════════════════════════════════════════════════
# Examples & counter‑examples
# ═══════════════════════════════════════════════════════════════════════

EXAMPLES = {
    "PASS — vector addition commutes": {
        "name": "add_comm_vec", "informal": "v + w = w + v for vectors in ℝⁿ",
        "lean_statement": "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
        "lean_proof": "by ext i; exact add_comm (v i) (w i)",
        "domain": "linear_algebra", "difficulty": "easy", "expect": "pass",
    },
    "PASS — 2 + 2 = 4": {
        "name": "two_plus_two", "informal": "Two plus two equals four",
        "lean_statement": "theorem two_plus_two : 2 + 2 = 4",
        "lean_proof": "by rfl", "domain": "arithmetic", "difficulty": "easy", "expect": "pass",
    },
    "PASS — scalar distributivity": {
        "name": "smul_add_vec", "informal": "c · (v + w) = c·v + c·w",
        "lean_statement": "theorem smul_add_vec (c : ℝ) (v w : Fin n → ℝ) : c • (v + w) = c • v + c • w",
        "lean_proof": "by ext i; exact mul_add c (v i) (w i)",
        "domain": "linear_algebra", "difficulty": "medium", "expect": "pass",
    },
    "PASS — commutativity of + on ℕ": {
        "name": "add_comm_nat", "informal": "a + b = b + a for natural numbers",
        "lean_statement": "theorem add_comm_nat (a b : Nat) : a + b = b + a",
        "lean_proof": "by rw [Nat.add_comm]",
        "domain": "algebra", "difficulty": "medium", "expect": "pass",
    },
    "FAIL (Gate 1) — `sorry`": {
        "name": "two_plus_two", "informal": "",
        "lean_statement": "theorem two_plus_two : 2 + 2 = 4",
        "lean_proof": "by sorry", "domain": "arithmetic", "difficulty": "easy", "expect": "fail",
    },
    "FAIL (Gate 1) — unknown identifier": {
        "name": "add_comm_vec", "informal": "",
        "lean_statement": "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
        "lean_proof": "by not_a_tactic",
        "domain": "linear_algebra", "difficulty": "easy", "expect": "fail",
    },
    "FAIL (Gate 2) — wrong domain": {
        "name": "add_comm_vec", "informal": "Vector addition",
        "lean_statement": "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
        "lean_proof": "by rw [Nat.add_comm]",
        "domain": "linear_algebra", "difficulty": "easy", "expect": "fail",
    },
    "WARN (Gate 3) — insufficient": {
        "name": "eigenvalue_id", "informal": "Identity map eigenvalue",
        "lean_statement": "theorem eigenvalue_id (v : Fin n → ℝ) (hv : v ≠ 0) : (λ x : Fin n → ℝ => x) v = (1 : ℝ) • v",
        "lean_proof": "by trivial",
        "domain": "linear_algebra", "difficulty": "medium", "expect": "warn",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _parse_pdf(file_bytes: bytes) -> List[dict]:
    """Line-based extractor: a line starting with `theorem <name>` opens a
    statement; a following line starting with `by ` is its proof. Wrapped
    statement lines (continuations) are merged. Prose containing the word
    'theorem' is ignored because we anchor on the keyword at line start."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []

    lines: List[str] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            lines.extend((page.extract_text() or "").split("\n"))

    rows: List[dict] = []
    current: Optional[dict] = None
    awaiting_proof = False

    for line in lines:
        s = line.strip()
        if re.match(r"^theorem\s+\w+", s):
            if current:
                rows.append(current)
            current = {"lean_statement": s, "lean_proof": "", "domain": "general",
                       "difficulty": "medium", "keywords": []}
            awaiting_proof = True
        elif awaiting_proof and re.match(r"^by\s+", s):
            if current is not None:
                current["lean_proof"] = s
            awaiting_proof = False
        elif awaiting_proof and current is not None and s and not s.startswith("THEOREM"):
            # continuation of a wrapped statement line (math/code only)
            if any(op in s for op in ["*", "+", "=", "->", "=>", "(", ")", "<", ">", "≠", "λ"]):
                current["lean_statement"] += " " + s

    if current:
        rows.append(current)

    for i, r in enumerate(rows, 1):
        m = re.match(r"^theorem\s+(\w+)", r["lean_statement"])
        r["name"] = m.group(1) if m else f"pdf_{i}"
        r["informal"] = ""
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
    return Theorem(d.get("name", ""), d.get("informal", ""),
                   d.get("lean_statement", d.get("stmt", "")),
                   d.get("domain", "general"), d.get("difficulty", "medium"),
                   list(d.get("keywords", [])))


def _proof_from_dict(d: dict) -> Proof:
    return Proof(lean_tactics=d.get("lean_proof", d.get("proof", "")), informal=d.get("informal", ""))


def _gate_mark(passed: Optional[bool]) -> str:
    """Monochrome indicator: ● pass  ◐ skip  ○ fail."""
    if passed is True:
        return '<span class="verdict-pass">●</span>'
    if passed is False:
        return '<span class="verdict-fail">○</span>'
    return '<span class="verdict-warn">◐</span>'


def _verdict_label(v: str) -> str:
    return {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}.get(v, v.upper())


# ═══════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown('<p class="brand-accent" style="font-size:1.6rem;margin-bottom:0;">Leibniz</p>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="brand-label">Universal Calculator for Truth</p>', unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.markdown(f"""
| | |
|---|---|
| Engine | `{engine.backend.name}` |
| Encyclopedia | {len(enc.all())} entries |
| Lean | {"available" if engine.lean.available else "provisional"} |
""")

mode = st.sidebar.radio("", ["Compute", "Single Review", "Batch Upload", "Formalize", "Discovery", "About"], label_visibility="collapsed")

st.sidebar.markdown('<p class="brand-label">Sample data</p>', unsafe_allow_html=True)
if SAMPLE_FILE.exists():
    with open(SAMPLE_FILE, "rb") as f:
        st.sidebar.download_button("Linear Algebra · JSONL", f.read(), "linear_algebra.jsonl", "application/jsonl",
                                   use_container_width=True)
if SAMPLE_PDF.exists():
    with open(SAMPLE_PDF, "rb") as f:
        st.sidebar.download_button("LA Proofs · PDF (3 pages)", f.read(), "linear_algebra_proofs.pdf", "application/pdf",
                                   use_container_width=True)
SAMPLE_PDF_BIG = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra_big_theorems.pdf"
if SAMPLE_PDF_BIG.exists():
    with open(SAMPLE_PDF_BIG, "rb") as f:
        st.sidebar.download_button("LA Big Theorems · PDF (5 pages)", f.read(), "linear_algebra_big_theorems.pdf", "application/pdf",
                                   use_container_width=True)

st.sidebar.markdown("**Resources**  \n[Streamlit App](https://leibniz.streamlit.app/)  \n[Browser playground](https://twomathematicians-code.github.io/leibniz/)  \n[GitHub](https://github.com/twomathematicians-code/leibniz)")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Single Review
# ═══════════════════════════════════════════════════════════════════════

# MODE: Compute (Wolfram-Alpha-style symbolic engine)
if mode == "Compute":
    st.markdown('<p class="brand-label">Symbolic Computation</p>', unsafe_allow_html=True)
    st.markdown("## Compute")
    st.caption("Exact, step-by-step symbolic computation — solve, differentiate, integrate, matrices.")

    c1, c2 = st.columns([1, 1])
    with c1:
        examples_compute = [
            "(custom)",
            "solve x^2 - 5*x + 6 = 0",
            "derivative of x^3 + 2*x^2",
            "integral of 1/(1 + x^2)",
            "limit of sin(x)/x as x -> 0",
            "taylor series of exp(x)",
            "simplify (x^2 - 1)/(x - 1)",
            "factor x^3 - 6*x^2 + 11*x - 6",
            "expand (x + 2)^4",
            "determinant of [[1,2],[3,4]]",
            "inverse of [[1,2],[3,4]]",
            "eigenvalues of [[2,0],[0,3]]",
            "rank of [[1,2,3],[2,4,6],[1,1,1]]",
            "trace of [[1,2],[3,4]]",
            "2/3 + 5/7",
        ]
        choice = st.selectbox("Load example", examples_compute, label_visibility="collapsed")
        default_q = "" if choice == "(custom)" else choice
        q = st.text_input("Query", value=default_q, placeholder="e.g. solve x^2 - 1 = 0",
                          label_visibility="collapsed")
        go_c = st.button("Compute", type="primary", use_container_width=True)

    with c2:
        if go_c and q.strip():
            r = engine.compute(q.strip())
            st.markdown('<div class="brand-label">Input interpretation</div>', unsafe_allow_html=True)
            st.code(r.input_interpretation or q)
            st.markdown('<div class="brand-label">Answer</div>', unsafe_allow_html=True)
            if r.ok:
                st.markdown(f"**{r.answer}**")
                if r.answer_latex and r.answer_latex != r.answer:
                    st.latex(r.answer_latex)
                with st.expander("Step-by-step"):
                    for s in r.steps:
                        st.markdown(s)
            else:
                st.error(r.error or "Computation failed.")

elif mode == "Single Review":
    st.markdown('<p class="brand-label">Single Review</p>', unsafe_allow_html=True)
    st.markdown("## Theorem Review")

    # Pipeline motif
    st.markdown(
        '<div class="pipeline">'
        '<span class="pipeline-step">Theorem</span><span class="pipeline-arrow">→</span>'
        '<span class="pipeline-step">Gate 1 · Validity</span><span class="pipeline-arrow">→</span>'
        '<span class="pipeline-step">Gate 2 · Alignment</span><span class="pipeline-arrow">→</span>'
        '<span class="pipeline-step">Gate 3 · Reading</span><span class="pipeline-arrow">→</span>'
        '<span class="pipeline-step">Verdict</span>'
        '</div><br>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        example = st.selectbox("Load example", ["— custom —"] + list(EXAMPLES.keys()), label_visibility="collapsed")

        if example != "— custom —":
            ex = EXAMPLES[example]
            def_name, def_stmt, def_proof, def_domain, def_diff, def_inf = (
                ex["name"], ex["lean_statement"], ex["lean_proof"], ex["domain"], ex["difficulty"], ex.get("informal",""))
            st.caption(f"Expected: {ex['expect'].upper()}")
        else:
            def_name = def_stmt = def_proof = ""
            def_domain, def_diff, def_inf = "linear_algebra", "easy", ""

        name = st.text_input("Name", value=def_name, placeholder="add_comm_vec", label_visibility="collapsed")
        domain = st.selectbox("Domain", ["linear_algebra", "arithmetic", "algebra", "number_theory", "set_theory", "general"],
                              index=["linear_algebra","arithmetic","algebra","number_theory","set_theory","general"].index(def_domain) if def_domain in ["linear_algebra","arithmetic","algebra","number_theory","set_theory","general"] else 0)
        diff = st.selectbox("Difficulty", ["easy", "medium", "hard"],
                           index=["easy","medium","hard"].index(def_diff) if def_diff in ["easy","medium","hard"] else 0)

        stmt = st.text_area("Lean statement", value=def_stmt, height=80,
                           placeholder="theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v",
                           label_visibility="collapsed")
        proof = st.text_area("Proof", value=def_proof, height=80,
                            placeholder="by ext i; exact add_comm (v i) (w i)",
                            label_visibility="collapsed")
        go = st.button("Run 3‑Gate Review", type="primary", use_container_width=True)

    with c2:
        if go and stmt.strip():
            t = Theorem(name.strip() or "unnamed", "", stmt.strip(), domain, diff)
            p = Proof(lean_tactics=proof.strip() or None)
            report = to_dict(engine.review(t, p))

            v = report["validity"]
            formal = "· formal" if v.get("formal") else "· provisional"
            st.markdown(f'<div class="brand-label">Gate 1 — Validity {formal}</div>', unsafe_allow_html=True)
            st.markdown(f"##### {_gate_mark(v.get('passed'))} &nbsp;{'Certified' if v.get('passed') else 'Rejected' if v.get('passed') is False else 'Skipped'}")
            if v.get("certificate"):
                st.code(v["certificate"])
            if v.get("error"):
                st.caption(v["error"])

            a = report["alignment"]
            st.markdown('<div class="brand-label">Gate 2 — Alignment</div>', unsafe_allow_html=True)
            st.progress(a["score"])
            st.markdown(f"Score **{a['score']:.2f}** &nbsp; matched: `{', '.join(a.get('matched_concepts',[]) or ['—'])}` &nbsp; missing: `{', '.join(a.get('missing_concepts',[]) or ['—'])}`")
            st.caption(a.get("rationale",""))

            r = report["reading"]
            st.markdown('<div class="brand-label">Gate 3 — Reading</div>', unsafe_allow_html=True)
            cols = st.columns(3)
            for i, tv in enumerate(r.get("tiers", [])):
                with cols[i]:
                    label = _verdict_label(tv["verdict"])
                    st.markdown(f"**{tv['tier'].upper()}**  \n{label}")
                    for c in tv.get("comments", []):
                        st.caption(c)

            overall = report["overall_pass"]
            if overall:
                st.success("Passed all three gates.")
            else:
                st.warning("Attention — one or more gates flagged issues.")

            st.download_button("Download report · JSON", json.dumps(report, indent=2, ensure_ascii=False),
                              f"review_{name.strip()}.json", "application/json", use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# MODE: Batch Upload
# ═══════════════════════════════════════════════════════════════════════

elif mode == "Batch Upload":
    st.markdown('<p class="brand-label">Batch Upload</p>', unsafe_allow_html=True)
    st.markdown("## Batch Verification")

    tab1, tab2 = st.tabs(["JSONL", "PDF"])

    with tab1:
        jf = st.file_uploader("Upload JSONL file", type=["jsonl", "json"], key="jl")
        if jf:
            rows = _parse_jsonl(jf.read().decode("utf-8", errors="replace"))
            pr = [r for r in rows if r.get("lean_proof","").strip()]
            st.caption(f"{len(rows)} theorems · {len(pr)} with proofs")

            if st.button("Verify batch", type="primary", use_container_width=True):
                results = []
                prog = st.progress(0)
                passed = 0
                for i, r in enumerate(rows):
                    t = _theorem_from_dict(r)
                    p = _proof_from_dict(r)
                    rep = to_dict(engine.review(t, p))
                    rep["_name"] = t.name
                    results.append(rep)
                    if rep.get("overall_pass"):
                        passed += 1
                    prog.progress((i + 1) / len(rows))

                df = pd.DataFrame([{
                    "Theorem": r["_name"], "V": _gate_mark(r["validity"].get("passed")),
                    "A": f"{r['alignment']['score']:.2f}",
                    "R": _verdict_label(r["reading"]["overall_verdict"]),
                    "Overall": "●" if r["overall_pass"] else "○",
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.metric("Pass rate", f"{passed}/{len(rows)}")
                st.download_button("Download results · JSON", json.dumps(results, indent=2, ensure_ascii=False),
                                  "batch_results.json", "application/json", use_container_width=True)

    with tab2:
        pf = st.file_uploader("Upload PDF", type=["pdf"], key="pdf")
        if pf:
            rows = _parse_pdf(pf.read())
            if rows:
                st.caption(f"Extracted {len(rows)} candidate pairs")
                if st.button("Verify PDF pairs", type="primary", use_container_width=True):
                    results = []
                    prog = st.progress(0)
                    passed = 0
                    for i, r in enumerate(rows):
                        t = _theorem_from_dict(r)
                        p = _proof_from_dict(r)
                        rep = to_dict(engine.review(t, p))
                        rep["_name"] = t.name
                        results.append(rep)
                        if rep.get("overall_pass"):
                            passed += 1
                        prog.progress((i + 1) / len(rows))
                    st.metric("Pass rate", f"{passed}/{len(rows)}")
                    st.download_button("Download results · JSON", json.dumps(results, indent=2, ensure_ascii=False),
                                      "pdf_results.json", "application/json", use_container_width=True)
            else:
                st.caption("No theorem–proof pairs extracted. Try a JSONL file instead.")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Formalize (NL → Lean)
# ═══════════════════════════════════════════════════════════════════════

elif mode == "Formalize":
    st.markdown('<p class="brand-label">Autoformalization</p>', unsafe_allow_html=True)
    st.markdown("## Natural Language → Lean 4")
    st.markdown(
        "Type an informal theorem. The engine recognises it against the encyclopedia "
        "(knowledge-base-assisted formalization) and, for novel statements, asks the LLM "
        "backend to translate. Each result references the corresponding Mathlib lemma."
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        examples_nl = [
            "(custom)",
            "The rank-nullity theorem: dim(range) + dim(kernel) = dim(V).",
            "A matrix is invertible iff its determinant is nonzero.",
            "det(A·B) = det(A)·det(B).",
            "Every eigenvalue of a real symmetric matrix is real.",
            "Cayley-Hamilton: a matrix satisfies its characteristic polynomial.",
            "A linear map is injective iff its kernel is trivial.",
        ]
        choice = st.selectbox("Load example", examples_nl, label_visibility="collapsed")
        default_nl = "" if choice == "(custom)" else choice
        informal = st.text_area("Informal statement", value=default_nl, height=110,
                                placeholder="e.g. The rank-nullity theorem...", label_visibility="collapsed")
        go_f = st.button("Formalize", type="primary", use_container_width=True)

    with c2:
        if go_f and informal.strip():
            r = engine.formalize(informal.strip())
            st.markdown('<div class="brand-label">Result</div>', unsafe_allow_html=True)

            src_icon = {"recognised": "●", "generated": "◐", "none": "○"}.get(r.source, "○")
            st.markdown(f"**Source:** {src_icon} `{r.source}` &nbsp; **Confidence:** `{r.confidence:.2f}`")
            if r.matched_entry:
                st.markdown(f"**Recognised as:** `{r.matched_entry}`")

            if r.lean_statement:
                st.markdown('<div class="brand-label">Lean 4 statement</div>', unsafe_allow_html=True)
                st.code(r.lean_statement, language="lean")
            else:
                st.caption("No Lean statement produced.")

            if r.mathlib_refs:
                st.markdown('<div class="brand-label">Mathlib references</div>', unsafe_allow_html=True)
                for ref in r.mathlib_refs:
                    st.markdown(f"- `{ref}`")

            st.caption(r.notes)

            # Optional: run the 3-gate review on the formalized statement
            if r.lean_statement and st.button("Run 3-gate review on this statement", use_container_width=True):
                rep = to_dict(engine.formalize_and_review(informal.strip()))
                v = rep["validity"]; a = rep["alignment"]; rd = rep["reading"]
                vmark = "●" if v.get("passed") is True else ("○" if v.get("passed") is False else "◐")
                st.markdown(f"**Gate 1 Validity:** {vmark} &nbsp; **Gate 2 Alignment:** {a['score']:.2f} &nbsp; **Gate 3 Reading:** {rd['overall_verdict'].upper()}")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Discovery
# ═══════════════════════════════════════════════════════════════════════

elif mode == "Discovery":
    st.markdown('<p class="brand-label">Discovery</p>', unsafe_allow_html=True)
    st.markdown("## Discover → Prove → Certify")

    c1, c2 = st.columns([1, 2])
    with c1:
        seed = st.text_input("Seed topic", "linear algebra")
        n_conj = st.slider("Conjectures", 1, 10, 5)
        k_cands = st.slider("Candidates per conjecture", 1, 8, 4)
        go_d = st.button("Run discovery", type="primary", use_container_width=True)

    with c2:
        if go_d:
            with st.spinner("Discovering…"):
                res = to_dict(engine.discover_and_verify(seed, n=n_conj, k=k_cands))
            cert = res.get("certified", [])
            fail = res.get("failed", [])
            st.metric("Success", f"{len(cert)}/{len(cert)+len(fail)}")

            if cert:
                st.markdown("**Certified**")
                for c in cert:
                    t, p = c["theorem"], c["proof"]
                    st.code(f"{t['lean_statement']}  :=  {p['lean_tactics']}")
            if fail:
                st.markdown("**Unproven**")
                for c in fail:
                    st.markdown(f"· {c['theorem']['name']}")

            st.download_button("Download · JSON", json.dumps(res, indent=2, ensure_ascii=False),
                              f"discovery_{seed.replace(' ','_')}.json", "application/json", use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# MODE: About
# ═══════════════════════════════════════════════════════════════════════

elif mode == "About":
    st.markdown('<p class="brand-label">About</p>', unsafe_allow_html=True)
    st.markdown("## Leibniz · A Universal Calculator for Truth")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Encyclopedia", len(enc.all()))
    with c2:
        st.metric("Lean theorems", 16)
    with c3:
        st.metric("Tests", "53")

    st.markdown("---")

    st.markdown("""
    ### Three pillars  *(Leibniz, ca. 1666)*

    | Pillar | Realisation |
    |--------|------------|
    | **Characteristica Universalis** — a universal logical language | `Theorem` · `Proof` · Lean 4 bridge |
    | **Encyclopedia** — a library of verified thoughts | 24‑entry knowledge base + Mathlib |
    | **Calculus Ratiocinator** — an engine that derives facts automatically | Stub / HF / Remote LLM backends |

    ### Three gates

    | Gate | Question | Output |
    |------|----------|--------|
    | **Validity** | Is the proof logically sound? | ● Pass / ◐ Skip / ○ Reject |
    | **Alignment** | Does the proof address the theorem's concepts? | Score 0.00 – 1.00 |
    | **Reading** | How does it hold up under human scrutiny? | Easy → Medium → Hard per‑tier verdict |
    """)

    st.markdown("---")
    st.markdown("### Examples & counter‑examples")

    for label, ex in EXAMPLES.items():
        expect = ex["expect"]
        with st.expander(f"{label}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.code(f"{ex['lean_statement']}  :=  {ex['lean_proof']}")
            with c2:
                st.caption(f"Domain: {ex['domain']} · {ex['difficulty']}")
                if st.button(f"Test", key=f"t_{ex['name']}_{label[:10]}"):
                    t = Theorem(ex["name"], ex.get("informal",""), ex["lean_statement"], ex["domain"], ex["difficulty"])
                    p = Proof(lean_tactics=ex["lean_proof"])
                    rep = to_dict(engine.review(t, p))
                    icon = "●" if rep["overall_pass"] else "○"
                    st.markdown(f"Result: {icon} &nbsp; V:{_gate_mark(rep['validity']['passed'])} &nbsp; A:{rep['alignment']['score']:.2f} &nbsp; R:{_verdict_label(rep['reading']['overall_verdict'])}", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Encyclopedia coverage")
    doms = {}
    for e in enc.all():
        d = e.get("domain", "general")
        doms[d] = doms.get(d, 0) + 1
    st.dataframe(pd.DataFrame([{"Domain": k, "Entries": v} for k, v in sorted(doms.items())]), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown('<p style="text-align:center;color:var(--muted);font-style:italic;">"If we had an exact language … one could simply say: <strong>Let us calculate!</strong>" — Leibniz, 1677</p>', unsafe_allow_html=True)
