"""
SCITAMEHTAM Leibniz — the mathematician's engine (simplified UI)
================================================================
Three tasks a mathematician actually has, nothing else on the front page:

    1. Ask a question   — anything: compute, name a theorem, paste a proof
    2. Check a proof    — paste it, get the three gates + a truth weight
    3. Upload files     — PDFs and problem sets, batch-verified

Advanced tools (Compute, SU(2) analysis, Discover, Formalize) live in a
drawer. Plain language everywhere; every result auditable.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict
from leibniz.encyclopedia import default as default_enc

# ═══════════════════════════════════════════════════════════════════════
# Page setup + brand
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Leibniz — the mathematician's engine",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;1,400&display=swap');
  :root { --ink:#000; --slate:#1f2937; --muted:#6b7280; --faint:#f3f4f6;
          --line:#e5e7eb; --paper:#fff; }
  html, body, [class*="css"] { font-family:'Inter',sans-serif; color:var(--ink); }
  h1,h2,h3 { font-weight:700; letter-spacing:-0.4px; }
  .brand-accent { font-family:'Playfair Display',serif; font-style:italic; }
  .brand-label { font-size:.72rem; font-weight:600; text-transform:uppercase;
                 letter-spacing:1.5px; color:var(--muted); }
  code, pre { font-family:'SF Mono',Consolas,monospace !important;
              background:var(--faint) !important; border:1px solid var(--line);
              border-radius:3px !important; }
  .verdict-pass { color:var(--ink); font-weight:700; }
  .verdict-warn { color:var(--muted); font-weight:500; }
  .verdict-fail { color:var(--line); font-weight:400; text-decoration:line-through; }
  div[data-testid="stMetricValue"] { font-weight:800; }
</style>
"""
st.markdown(BRAND_CSS, unsafe_allow_html=True)

if "engine" not in st.session_state:
    st.session_state.engine = Engine()
engine = st.session_state.engine
enc = default_enc()

SAMPLE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra.jsonl"
SAMPLE_PDF = Path(os.path.dirname(os.path.abspath(__file__))) / "app" / "samples" / "linear_algebra_proofs.pdf"

# ═══════════════════════════════════════════════════════════════════════
# Sidebar — three tasks, advanced in a drawer
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown('<p class="brand-accent" style="font-size:1.6rem;margin-bottom:0;">Leibniz</p>',
                    unsafe_allow_html=True)
st.sidebar.markdown('<p class="brand-label">the mathematician&rsquo;s engine</p>',
                    unsafe_allow_html=True)
st.sidebar.markdown("---")

task = st.sidebar.radio(
    "What do you want to do?",
    ["Ask a question", "Check a proof", "Upload files"],
    label_visibility="collapsed",
)

with st.sidebar.expander("Advanced tools"):
    adv = st.radio(
        "Advanced",
        ["(pick a tool…)", "Compute (symbolic)", "SU(2) analysis",
         "Discover conjectures", "Translate to Lean"],
        label_visibility="collapsed",
    )
    if adv == "Compute (symbolic)":
        task = "adv_compute"
    elif adv == "SU(2) analysis":
        task = "adv_su2"
    elif adv == "Discover conjectures":
        task = "adv_discover"
    elif adv == "Translate to Lean":
        task = "adv_formalize"

if st.sidebar.button("About this engine", use_container_width=True):
    task = "about"

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<p class="brand-label">status</p>'
    f'encyclopedia: {len(enc.all())} theorems &nbsp;·&nbsp; '
    f'lean: {"available" if engine.lean.available else "provisional"}',
    unsafe_allow_html=True,
)
if SAMPLE_FILE.exists():
    with open(SAMPLE_FILE, "rb") as f:
        st.sidebar.download_button("Sample problem set (JSONL)", f.read(),
                                   "linear_algebra.jsonl", use_container_width=True)
if SAMPLE_PDF.exists():
    with open(SAMPLE_PDF, "rb") as f:
        st.sidebar.download_button("Sample proof set (PDF)", f.read(),
                                   "linear_algebra_proofs.pdf",
                                   "application/pdf", use_container_width=True)
st.sidebar.markdown(
    '[leibniz.streamlit.app](https://leibniz.streamlit.app) · '
    '[GitHub](https://github.com/twomathematicians-code/leibniz)'
)

# ═══════════════════════════════════════════════════════════════════════
# Shared helpers — plain-language rendering
# ═══════════════════════════════════════════════════════════════════════

def _gate_mark(passed: Optional[bool]) -> str:
    if passed is True:
        return '<span class="verdict-pass">●</span>'
    if passed is False:
        return '<span class="verdict-fail">○</span>'
    return '<span class="verdict-warn">◐</span>'


def soundness_words(rep: dict) -> str:
    v = rep.get("validity", {})
    if v.get("passed") is True and v.get("formal"):
        return "Machine-certified — Lean compiled the proof (exit 0)."
    if v.get("passed") is True:
        return "Recognized — matches a certified proof in the encyclopedia."
    if v.get("passed") is False:
        return "Rejected — the proof does not hold (e.g. `sorry` or a broken step)."
    return "Not formally checked — no Lean toolchain here; judged on structure."


def topic_words(rep: dict) -> str:
    a = rep.get("alignment", {})
    s = a.get("score", 0.0)
    if s >= 0.7:
        return f"On target ({s:.2f}) — the proof addresses the theorem's concepts."
    if s >= 0.4:
        return f"Partly on target ({s:.2f}) — some concepts present, some missing."
    return f"Off target ({s:.2f}) — likely the wrong setting for this statement."


def reading_words(rep: dict) -> str:
    r = rep.get("reading", {})
    label = {"pass": "survives close reading",
             "warn": "has reservations", "fail": "fails under scrutiny"}
    plain = {"easy": "quick check", "medium": "logic check", "hard": "deep check"}
    tiers = " · ".join(f"{plain.get(t.get('tier'), t.get('tier'))}: "
                       f"{t.get('verdict')}" for t in r.get("tiers", []))
    return f"{label.get(r.get('overall_verdict'), '?')} — {tiers}"


def render_review(rep: dict) -> None:
    """The one, plain-language review card used everywhere."""
    tw = rep.get("truth_weight", 0)
    ok = rep.get("overall_pass", False)
    verdict = "PASS" if ok else "ATTENTION"

    col_m, col_v = st.columns([1, 2])
    with col_m:
        st.metric("Truth weight", f"{tw}/100",
                  delta=verdict, delta_color="normal" if ok else "off")
    with col_v:
        st.markdown(f"**Is it logically sound?** &nbsp;{_gate_mark(rep['validity'].get('passed'))} "
                    f"{soundness_words(rep)}", unsafe_allow_html=True)
        st.markdown(f"**Is it about the right things?** &nbsp;{topic_words(rep)}")
        st.markdown(f"**Does it survive close reading?** &nbsp;{reading_words(rep)}")

    with st.expander("The detail (gates, certificate, concepts)"):
        v = rep.get("validity", {})
        if v.get("certificate"):
            st.caption(f"certificate: {v['certificate']}")
        if v.get("error"):
            st.caption(f"gate 1 note: {v['error']}")
        a = rep.get("alignment", {})
        if a.get("matched_concepts"):
            st.caption(f"concepts present: {', '.join(a['matched_concepts'])}")
        if a.get("missing_concepts"):
            st.caption(f"concepts missing: {', '.join(a['missing_concepts'])}")
        if a.get("rationale"):
            st.caption(a["rationale"])
        b = rep.get("truth_breakdown", {})
        if b:
            st.caption(f"weight breakdown — soundness {b.get('shares',{}).get('validity')}, "
                       f"on-topic {b.get('shares',{}).get('alignment')}, "
                       f"reading {b.get('shares',{}).get('reading')} "
                       f"(a weight of evidence, not a probability)")


def _parse_pdf(file_bytes: bytes) -> List[dict]:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []
    lines: List[str] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            lines.extend((page.extract_text() or "").split("\n"))
    rows: List[dict] = []
    current = None
    awaiting = False
    for line in lines:
        s = line.strip()
        if re.match(r"^theorem\s+\w+", s):
            if current:
                rows.append(current)
            current = {"lean_statement": s, "lean_proof": "", "domain": "general",
                       "difficulty": "medium", "keywords": []}
            awaiting = True
        elif awaiting and re.match(r"^by\s+", s):
            if current is not None:
                current["lean_proof"] = s
            awaiting = False
        elif awaiting and current is not None and s and not s.startswith("THEOREM"):
            if any(op in s for op in ["*", "+", "=", "->", "=>", "(", ")", "<", ">"]):
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
    return Proof(lean_tactics=d.get("lean_proof", d.get("proof", "")),
                 informal=d.get("informal", ""))


# ═══════════════════════════════════════════════════════════════════════
# TASK 1 — Ask a question
# ═══════════════════════════════════════════════════════════════════════

if task == "Ask a question":
    st.markdown('<p class="brand-label">Ask</p>', unsafe_allow_html=True)
    st.markdown("## Ask anything mathematical")
    st.caption("A computation, a theorem's name, or paste a whole Lean proof — "
               "the engine works out what you need and shows every step it took.")

    examples = [
        "(type your own…)",
        "compute eigenvalues of [[2,0],[0,3]]",
        "integral of 1/(1+x^2)",
        "what is the Peter–Weyl orthogonality theorem?",
        "formalize the rank-nullity theorem",
        "theorem my_two : 2 + 2 = 4 := by rfl",
        "by ext i; exact mul_add c (v i) (w i)",
    ]
    choice = st.selectbox("Examples", examples, label_visibility="collapsed")
    default_q = "" if choice.startswith("(type") else choice
    query = st.text_area(
        "Your question",
        value=default_q, height=110,
        placeholder="e.g. determinant of [[1,2],[3,4]]   ·   "
                    "e.g. state Cayley–Hamilton in Lean   ·   or paste a proof",
        label_visibility="collapsed",
    )
    go = st.button("Ask", type="primary", use_container_width=True)

    if go and query.strip():
        from leibniz.agent import ask as agent_ask
        with st.spinner("Working…"):
            result = agent_ask(query.strip())
        st.markdown(f'<p class="brand-label">the engine used: {result.route}</p>',
                    unsafe_allow_html=True)
        st.markdown(result.answer)
        with st.expander("Every step the engine took (audit trail)"):
            for s in result.trail:
                st.markdown(f"**{s.tool}** — {s.summary}")
                for h in s.detail.get("hits", [])[:3]:
                    st.caption(f"{h['name']} ({h['domain']}, relevance {h['score']}): "
                               f"{h['informal'][:90]}")
                if s.detail.get("lean_statement"):
                    st.code(s.detail["lean_statement"], language="lean")
                if s.detail.get("truth_weight") is not None:
                    st.caption(f"truth weight {s.detail['truth_weight']}/100 · "
                               f"overall {'PASS' if s.detail['overall_pass'] else 'ATTENTION'}")
    elif go:
        st.info("Type a question above, or pick an example.")

# ═══════════════════════════════════════════════════════════════════════
# TASK 2 — Check a proof
# ═══════════════════════════════════════════════════════════════════════

elif task == "Check a proof":
    st.markdown('<p class="brand-label">Check</p>', unsafe_allow_html=True)
    st.markdown("## Check a proof")
    st.caption("Paste a Lean theorem with its proof — or just the proof "
               "(`by …`) plus the theorem's name — and get three plain answers: "
               "is it sound, is it on-topic, does it read well. Plus a truth weight.")

    proof_examples = {
        "(paste your own…)": "",
        "A correct proof": "theorem two_plus_two : 2 + 2 = 4 := by rfl",
        "A proof with a gap (`sorry`)": "theorem two_plus_two : 2 + 2 = 4 := by sorry",
        "The wrong setting (Nat lemma on vectors)":
            "theorem add_comm_vec (v w : Fin n → ℝ) : v + w = w + v := by rw [Nat.add_comm]",
        "Distributivity done properly":
            "theorem smul_add_vec (c : ℝ) (v w : Fin n → ℝ) : c • (v + w) = c • v + c • w := by ext i; exact mul_add c (v i) (w i)",
    }
    ex = st.selectbox("Examples", list(proof_examples), label_visibility="collapsed")
    pasted = st.text_area(
        "Theorem + proof",
        value=proof_examples[ex], height=130,
        placeholder="theorem my_thm (n : Nat) : n + 0 = n := by rfl",
        label_visibility="collapsed",
    )
    theorem_name_hint = st.text_input(
        "If you paste only a proof (no theorem), which theorem is it? (optional)",
        placeholder="e.g. two_plus_two",
    )
    go_check = st.button("Check", type="primary", use_container_width=True)

    if go_check and pasted.strip():
        from leibniz.agent import parse_pasted_proof
        parsed = parse_pasted_proof(pasted.strip())

        if parsed and parsed[0] and parsed[1]:
            statement, proof_text = parsed
            name_m = re.match(r"theorem\s+(\w+)", statement)
            t = Theorem(name_m.group(1) if name_m else "pasted_theorem", "",
                        statement, "general", "medium")
            rep = to_dict(engine.review(t, Proof(lean_tactics=proof_text)))
            render_review(rep)
        elif parsed and parsed[1]:
            proof_text = parsed[1]
            name = theorem_name_hint.strip() or ""
            entry = enc.get(name) if name else None
            if entry:
                t = Theorem(entry["name"], entry.get("informal", ""),
                            entry.get("lean_statement"), entry.get("domain", "general"),
                            entry.get("difficulty", "medium"))
                rep = to_dict(engine.review(t, Proof(lean_tactics=proof_text)))
                render_review(rep)
            else:
                st.warning("You pasted a bare proof. Add the theorem's name above "
                           "(e.g. `two_plus_two`) so the engine knows what it "
                           "should prove — or paste the full "
                           "`theorem … := by …` line.")
        else:
            st.warning("Could not find a proof to check. Paste something like "
                       "`theorem name : statement := by tactics`.")
    elif go_check:
        st.info("Paste a proof above, or pick an example.")

# ═══════════════════════════════════════════════════════════════════════
# TASK 3 — Upload files
# ═══════════════════════════════════════════════════════════════════════

elif task == "Upload files":
    st.markdown('<p class="brand-label">Upload</p>', unsafe_allow_html=True)
    st.markdown("## Upload problem sets or papers")
    st.caption("A PDF with theorems and proofs, or a JSONL file — every item "
               "goes through the same three checks and gets a truth weight. "
               "Download the sidebar samples to try it.")

    tab_pdf, tab_jsonl = st.tabs(["PDF", "JSONL"])

    with tab_pdf:
        pf = st.file_uploader("PDF file", type=["pdf"], key="pdf_up")
        if pf:
            rows = _parse_pdf(pf.read())
            if rows:
                st.info(f"Found **{len(rows)}** theorem–proof pair(s) in the PDF.")
                if st.button("Check all", type="primary", use_container_width=True):
                    results = []
                    prog = st.progress(0)
                    passed = 0
                    for i, r in enumerate(rows):
                        rep = to_dict(engine.review(_theorem_from_dict(r),
                                                    _proof_from_dict(r)))
                        rep["_name"] = r.get("name", f"item {i+1}")
                        results.append(rep)
                        if rep.get("overall_pass"):
                            passed += 1
                        prog.progress((i + 1) / len(rows))
                    st.metric("Checked", f"{passed}/{len(rows)} passed overall")
                    df = pd.DataFrame([{
                        "theorem": r["_name"],
                        "sound": r["validity"].get("passed"),
                        "on-topic": f"{r['alignment']['score']:.2f}",
                        "reads": r["reading"]["overall_verdict"],
                        "truth weight": r["truth_weight"],
                    } for r in results])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.download_button("Download the full report (JSON)",
                                       json.dumps(results, indent=2, ensure_ascii=False),
                                       "leibniz_pdf_report.json",
                                       use_container_width=True)
            else:
                st.warning("No theorem–proof pairs found. The extractor looks "
                           "for lines starting `theorem` and `by `. A JSONL "
                           "upload is more reliable.")
    with tab_jsonl:
        jf = st.file_uploader("JSONL file", type=["jsonl", "json"], key="jl_up")
        if jf:
            rows = _parse_jsonl(jf.read().decode("utf-8", errors="replace"))
            with_p = [r for r in rows if r.get("lean_proof", r.get("proof", "")).strip()]
            st.info(f"{len(rows)} theorems · {len(with_p)} with proofs")
            if rows and st.button("Check all", type="primary", use_container_width=True,
                                  key="jl_check"):
                results = []
                prog = st.progress(0)
                passed = 0
                for i, r in enumerate(rows):
                    rep = to_dict(engine.review(_theorem_from_dict(r),
                                                _proof_from_dict(r)))
                    rep["_name"] = r.get("name", f"item {i+1}")
                    results.append(rep)
                    if rep.get("overall_pass"):
                        passed += 1
                    prog.progress((i + 1) / len(rows))
                st.metric("Checked", f"{passed}/{len(rows)} passed overall")
                df = pd.DataFrame([{
                    "theorem": r["_name"],
                    "sound": r["validity"].get("passed"),
                    "on-topic": f"{r['alignment']['score']:.2f}",
                    "reads": r["reading"]["overall_verdict"],
                    "truth weight": r["truth_weight"],
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("Download the full report (JSON)",
                                   json.dumps(results, indent=2, ensure_ascii=False),
                                   "leibniz_jsonl_report.json",
                                   use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# ADVANCED TOOLS
# ═══════════════════════════════════════════════════════════════════════

elif task == "adv_compute":
    st.markdown('<p class="brand-label">Advanced · compute</p>', unsafe_allow_html=True)
    st.markdown("## Symbolic computation")
    st.caption("Exact, step-by-step — like a transparent, open Wolfram: "
               "solve, integrate, differentiate, matrices.")
    c1, c2 = st.columns(2)
    with c1:
        q = st.text_input("Query", placeholder="eigenvalues of [[2,0],[0,3]]",
                          label_visibility="collapsed")
        go_c = st.button("Compute", type="primary", use_container_width=True)
    with c2:
        if go_c and q.strip():
            r = engine.compute(q.strip())
            if r.ok:
                st.code(r.input_interpretation or q)
                st.markdown(f"**{r.answer}**")
                if r.answer_latex and r.answer_latex != r.answer:
                    st.latex(r.answer_latex)
                with st.expander("Step by step"):
                    for s in r.steps:
                        st.markdown(s)
            else:
                st.error(r.error or "Could not compute.")
        elif go_c:
            st.info("Type a computation above.")

elif task == "adv_su2":
    st.markdown('<p class="brand-label">Advanced · SU(2)</p>', unsafe_allow_html=True)
    st.markdown("## Harmonic analysis on SU(2)")
    st.caption("The engine computes the representation theory of the rotation "
               "group exactly — Wigner matrices, characters — and "
               "machine-verifies the Peter–Weyl theorem by exact symbolic "
               "integration. No floating point anywhere.")
    c1, c2 = st.columns(2)
    with c1:
        l_max = st.slider("Maximum rank l", 0, 3, 2)
        go_s = st.button("Run the analysis", type="primary", use_container_width=True)
    with c2:
        if go_s:
            rep = engine.su2_analysis(l_max)
            ok, total = rep["peter_weyl_passed"], rep["peter_weyl_checks"]
            st.metric("Peter–Weyl checks passed", f"{ok} / {total}")
            st.progress(ok / total if total else 0)
            st.caption("⟨t, t'⟩ = δ/(2l+1) — every check an exact symbolic "
                       "identity, not a numeric coincidence.")
            st.markdown(f"**Characters:** $\\chi_l = \\sin((2l+1)\\theta/2)/"
                        f"\\sin(\\theta/2)$, verified $= \\mathrm{{Tr}}\\,d^l$ for "
                        f"$l \\le {l_max}$")

elif task == "adv_discover":
    st.markdown('<p class="brand-label">Advanced · discover</p>', unsafe_allow_html=True)
    st.markdown("## Discover")
    st.caption("Seed a topic — the engine proposes conjectures, tries proofs, "
               "and certifies what passes. Honest about what it cannot prove.")
    c1, c2 = st.columns([1, 2])
    with c1:
        seed = st.text_input("Topic", value="linear algebra",
                             label_visibility="collapsed")
        n_conj = st.slider("Conjectures", 1, 10, 5)
        go_d = st.button("Discover", type="primary", use_container_width=True)
    with c2:
        if go_d and seed.strip():
            res = to_dict(engine.discover_and_verify(seed.strip(), n=n_conj))
            st.metric("Certified", f"{len(res['certified'])}/{len(res['certified']) + len(res['failed'])}")
            for c in res["certified"]:
                t, p = c["theorem"], c["proof"]
                st.markdown(f"● **{t['name']}** ({t['domain']})")
                st.code(f"{t['lean_statement']}  :=  {p['lean_tactics']}", language="lean")
            for c in res["failed"]:
                st.markdown(f"○ {c['theorem']['name']} — no proof found (honest failure)")

elif task == "adv_formalize":
    st.markdown('<p class="brand-label">Advanced · translate</p>', unsafe_allow_html=True)
    st.markdown("## Translate to Lean")
    st.caption("Say a theorem in English — the engine finds its formal Lean "
               "statement and the Mathlib reference.")
    c1, c2 = st.columns(2)
    with c1:
        q = st.text_input("Theorem (English)", placeholder="a matrix is invertible iff its determinant is nonzero",
                          label_visibility="collapsed")
        go_f = st.button("Translate", type="primary", use_container_width=True)
    with c2:
        if go_f and q.strip():
            r = engine.formalize(q.strip())
            if r.lean_statement:
                st.markdown(f"Recognised as **{r.matched_entry}** "
                            f"(confidence {r.confidence:.2f})")
                st.code(r.lean_statement, language="lean")
                if r.mathlib_refs:
                    st.caption("Mathlib: " + ", ".join(f"`{x}`" for x in r.mathlib_refs))
            else:
                st.warning("Not recognised. Try naming the theorem or using "
                           "its standard vocabulary.")

# ═══════════════════════════════════════════════════════════════════════
# ABOUT
# ═══════════════════════════════════════════════════════════════════════

elif task == "about":
    st.markdown('<p class="brand-label">About</p>', unsafe_allow_html=True)
    st.markdown("## The mathematician's engine")
    st.markdown(
        "Three checks on any proof — **is it sound, is it on-topic, does it "
        "read well** — combined into one truth weight. Underneath: symbolic "
        "computation (exact, SymPy), a Lean 4 verification layer, an "
        "encyclopedia of certified theorems, and exact harmonic analysis on "
        "SU(2) (Peter–Weyl machine-verified, 47/47 checks)."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Encyclopedia", f"{len(enc.all())} theorems")
    c2.metric("Tests", "113 passing")
    c3.metric("Peter–Weyl", "47/47 exact")
    st.markdown(
        "**Truth weight** — a transparent composite: soundness 50%, "
        "on-topic 25%, close-reading 25%. A weight of evidence, "
        "*not* a probability: every component is inspectable in the detail "
        "of each review."
    )
    st.markdown(
        "**Honest limits** — formal Lean certificates need the Mathlib "
        "toolchain (architecture ready); operator symbols R(x,l) on SU(2) "
        "are the next milestone; hard analysis is open research. "
        "The engine shows failures, never invents success."
    )
