"""
The Mathematician's Agent — an orchestrating companion
=======================================================
The draft's "agents for the mathematicians' community" idea, realised as an
honest first agent: given a natural-language request, it ROUTES the request
through the existing engine capabilities and synthesises an answer:

    retrieve (RAG over the encyclopedia)
        -> compute   (symbolic: solve/integrate/matrices)
        -> formalize (natural language -> Lean + Mathlib ref)
        -> review    (3-gate proof audit + truth weight)

It claims nothing beyond what the underlying tools return; each answer
carries the tool trail so a mathematician can audit every step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .pipeline import Engine


# Intent signals for routing
_COMPUTE_WORDS = {
    "solve", "compute", "calculate", "evaluate", "integrate", "integral",
    "derivative", "differentiate", "limit", "taylor", "series", "factor",
    "expand", "simplify", "determinant", "eigenvalue", "eigenvalues",
    "inverse", "rank", "trace", "rref",
}
_FORMALIZE_WORDS = {
    "formalize", "formalise", "lean", "state", "statement", "translate",
    "mathlib",
}
_REVIEW_WORDS = {
    "prove", "proof", "verify", "check", "review", "audit", "true",
    "correct", "validate",
}
_MATRIX_RE = re.compile(r"\[\[.*?\]\]")


@dataclass
class AgentStep:
    """One tool invocation in the agent's trail."""
    tool: str            # retrieve | compute | formalize | review | none
    input: str
    summary: str
    detail: dict = field(default_factory=dict)


@dataclass
class AgentAnswer:
    """The synthesised answer plus the auditable tool trail."""
    query: str
    route: str                          # human-readable routing decision
    answer: str
    trail: List[AgentStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query, "route": self.route, "answer": self.answer,
            "trail": [{"tool": s.tool, "input": s.input,
                       "summary": s.summary, "detail": s.detail}
                      for s in self.trail],
        }


# A pasted Lean theorem+proof: "theorem name ... : ... := by ..." (or term)
_PASTED_PROOF_RE = re.compile(
    r"(theorem\s+\w+[^:]*:.+?)\s*:=\s*(by\b.+|[\w\.\[\]\(\)\s]+)$",
    re.DOTALL,
)


def parse_pasted_proof(text: str):
    """If the query IS a pasted Lean theorem+proof, split it.

    Returns (statement, proof) or None. Handles both 'theorem n : P := by tac'
    and a bare proof block like 'by rw [Nat.add_comm]'.
    """
    t = text.strip()
    m = _PASTED_PROOF_RE.search(t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if t.startswith("by ") or t.startswith("by\n"):
        return None, t
    return None


def _route(query: str) -> List[str]:
    """Decide which tools to run, in order. Always retrieves first."""
    q = query.lower()
    tools = ["retrieve"]
    # a pasted Lean theorem+proof, or a bare 'by ...' block -> review directly
    if _PASTED_PROOF_RE.search(query) or query.strip().startswith("by "):
        tools.append("review")
        return tools
    if any(w in q for w in _COMPUTE_WORDS) or _MATRIX_RE.search(query):
        tools.append("compute")
    if any(w in q for w in _FORMALIZE_WORDS):
        tools.append("formalize")
    if any(w in q for w in _REVIEW_WORDS):
        tools.append("review")
    return tools


def ask(query: str, engine: Optional[Engine] = None, k: int = 3) -> AgentAnswer:
    """The agent's single entry point: ask anything mathematical."""
    engine = engine or Engine()
    tools = _route(query)
    trail: List[AgentStep] = []
    sections: List[str] = []

    # --- 1. retrieve: always ground in the encyclopedia --------------------
    from .rag import default_rag
    hits = default_rag().retrieve(query, k=k)
    if hits:
        lines = [f"- **{h.name}** ({h.domain}, relevance {h.score:.2f}): "
                 f"{h.informal}" for h in hits[:k]]
        trail.append(AgentStep(
            tool="retrieve", input=query,
            summary=f"{len(hits)} encyclopedia entries retrieved",
            detail={"hits": [h.to_dict() for h in hits[:k]]},
        ))
        sections.append("**From the encyclopedia:**\n" + "\n".join(lines))
    else:
        trail.append(AgentStep(
            tool="retrieve", input=query,
            summary="no encyclopedia match above threshold",
        ))

    # --- 2. compute ---------------------------------------------------------
    if "compute" in tools:
        r = engine.compute(query)
        mark = "computed" if r.ok else f"failed ({r.error})"
        trail.append(AgentStep(
            tool="compute", input=query, summary=mark,
            detail=r.to_dict() if r.ok else {"error": r.error},
        ))
        if r.ok:
            body = f"`{r.input_interpretation}` → **{r.answer}**"
            if r.answer_latex and r.answer_latex != r.answer:
                body += f"  (LaTeX: {r.answer_latex})"
            sections.append("**Computed exactly:**\n" + body)

    # --- 3. formalize ---------------------------------------------------------
    if "formalize" in tools:
        f = engine.formalize(query)
        trail.append(AgentStep(
            tool="formalize", input=query,
            summary=(f"recognised as {f.matched_entry} "
                     f"(confidence {f.confidence:.2f})" if f.lean_statement
                     else "no formal statement produced"),
            detail={"source": f.source, "confidence": f.confidence,
                    "lean_statement": f.lean_statement,
                    "mathlib_refs": f.mathlib_refs},
        ))
        if f.lean_statement:
            body = f"```lean\n{f.lean_statement}\n```"
            if f.mathlib_refs:
                body += "\nMathlib: " + ", ".join(f"`{r}`" for r in f.mathlib_refs)
            sections.append("**Formalised (Lean 4):**\n" + body)

    # --- 4. review ------------------------------------------------------------
    if "review" in tools:
        from .core.types import Theorem, Proof, to_dict

        # Priority 1: the query IS a pasted theorem+proof -> review it directly
        parsed = parse_pasted_proof(query)
        reviewed_directly = False
        if parsed is not None and (parsed[0] or parsed[1]):
            statement, proof_text = parsed
            if statement and proof_text:
                name_m = re.match(r"theorem\s+(\w+)", statement)
                t = Theorem(
                    name=(name_m.group(1) if name_m else "pasted_theorem"),
                    informal="", lean_statement=statement,
                    domain="general", difficulty="medium",
                )
                rep = to_dict(engine.review(t, Proof(lean_tactics=proof_text)))
                summary = (f"reviewed the pasted proof of `{t.name}`: "
                           f"truth weight {rep['truth_weight']}/100 "
                           f"({'PASS' if rep['overall_pass'] else 'ATTENTION'})")
                trail.append(AgentStep(
                    tool="review", input=proof_text, summary=summary,
                    detail={"truth_weight": rep["truth_weight"],
                            "overall_pass": rep["overall_pass"]},
                ))
                sections.append(
                    f"**Reviewed your proof:** {summary}\n\n"
                    f"- Is it logically sound? {rep['validity'].get('passed')}\n"
                    f"- Is it about the right things? "
                    f"{rep['alignment']['score']:.2f}\n"
                    f"- Does it survive close reading? "
                    f"{rep['reading']['overall_verdict']}"
                )
                reviewed_directly = True
            elif proof_text and hits:
                # bare 'by ...' block + a retrieval match gives the theorem
                top = hits[0]
                t = Theorem(top.name, top.informal, top.statement or None,
                            top.domain, "medium")
                rep = to_dict(engine.review(t, Proof(lean_tactics=proof_text)))
                summary = (f"reviewed the supplied proof for `{top.name}`: "
                           f"truth weight {rep['truth_weight']}/100 "
                           f"({'PASS' if rep['overall_pass'] else 'ATTENTION'})")
                trail.append(AgentStep(
                    tool="review", input=proof_text, summary=summary,
                    detail={"truth_weight": rep["truth_weight"],
                            "overall_pass": rep["overall_pass"]},
                ))
                sections.append(
                    f"**Reviewed:** {summary}\n\n"
                    f"- Is it logically sound? {rep['validity'].get('passed')}\n"
                    f"- Is it about the right things? "
                    f"{rep['alignment']['score']:.2f}\n"
                    f"- Does it survive close reading? "
                    f"{rep['reading']['overall_verdict']}"
                )
                reviewed_directly = True

        # Priority 2: keyword-routed review with an encyclopedia context
        if not reviewed_directly:
            proof_text = _extract_proof(query)
            top = hits[0] if hits else None
            if proof_text and top:
                t = Theorem(top.name, top.informal, top.statement or None,
                            top.domain, "medium")
                rep = to_dict(engine.review(t, Proof(lean_tactics=proof_text)))
                summary = (f"reviewed the supplied proof for `{top.name}`: "
                           f"truth weight {rep['truth_weight']}/100 "
                           f"({'PASS' if rep['overall_pass'] else 'ATTENTION'})")
                trail.append(AgentStep(
                    tool="review", input=proof_text, summary=summary,
                    detail={"truth_weight": rep["truth_weight"],
                            "overall_pass": rep["overall_pass"]},
                ))
                sections.append(
                    f"**Reviewed:** {summary}\n\n"
                    f"- Is it logically sound? {rep['validity'].get('passed')}\n"
                    f"- Is it about the right things? "
                    f"{rep['alignment']['score']:.2f}\n"
                    f"- Does it survive close reading? "
                    f"{rep['reading']['overall_verdict']}"
                )
            else:
                trail.append(AgentStep(
                tool="review", input=query,
                summary="no proof text detected to review",
            ))

    answer = "\n\n".join(sections) if sections else (
        "No tool produced a result for this query. Try phrasing with a "
        "computation (e.g. 'eigenvalues of [[2,0],[0,3]]'), a theorem name, "
        "or a Lean proof to review."
    )
    return AgentAnswer(
        query=query,
        route=" -> ".join(tools),
        answer=answer,
        trail=trail,
    )


def _extract_proof(query: str) -> Optional[str]:
    """Pull a `by ...` tactic block out of the query, if present."""
    m = re.search(r"(by\s+[A-Za-z_][\w\s;\[\]\(\),.*+/=-]*)", query)
    if m:
        return m.group(1).strip()
    return None
