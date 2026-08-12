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
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []
    rows: List[dict] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    chunks = full_text.split("\n\n")
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        stmt, proof = "", ""
        for line in chunk.split("\n"):
            if "theorem" in line.lower() and not stmt:
                stmt = line.strip()
            elif "proof" in line.lower() or "by " in line.lower():
                proof = line.strip()
            elif proof:
                proof += " " + line.strip()
        if stmt:
            rows.append({"name": f"pdf_{i+1}", "informal": "", "lean_statement": stmt, "lean_proof": proof, "domain": "general", "difficulty": "medium", "keywords": []})
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

mode = st.sidebar.radio("", ["Single Review", "Batch Upload", "Discovery", "About"], label_visibility="collapsed")

st.sidebar.markdown("---")
if SAMPLE_FILE.exists():
    with open(SAMPLE_FILE) as f:
        st.sidebar.download_button("Download LA sample · JSONL", f.read(), "linear_algebra.jsonl", "application/jsonl",
                                   use_container_width=True)

st.sidebar.markdown("**Resources**  \n[Streamlit App](https://leibniz.streamlit.app/)  \n[Browser playground](https://twomathematicians-code.github.io/leibniz/)  \n[GitHub](https://github.com/twomathematicians-code/leibniz)")

# ═══════════════════════════════════════════════════════════════════════
# MODE: Single Review
# ═══════════════════════════════════════════════════════════════════════

if mode == "Single Review":
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
