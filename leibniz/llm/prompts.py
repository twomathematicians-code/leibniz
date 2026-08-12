"""
Prompt Templates
================
Prompts for each pipeline stage when a real LLM backend (HF / remote) is used.
Every prompt requests strict JSON so the backend can parse structured output.

These are not used by StubBackend (which is rule-based), but they document the
contract between the engine and a plugged-in model.
"""

from __future__ import annotations

from typing import List

from ..core.types import Theorem, Proof
from ..core.difficulty import Difficulty, TIER_RUBRIC


SYSTEM = (
    "You are Lean-Prover, a formal-mathematics reasoning engine. "
    "You reason in Lean 4 and explain in clear mathematics. "
    "You ALWAYS respond with a single minified JSON object and nothing else."
)


def _fmt_theorem(t: Theorem) -> str:
    lines = [f"name: {t.name}", f"informal: {t.informal}", f"domain: {t.domain}"]
    if t.lean_statement:
        lines.append(f"lean_statement: {t.lean_statement}")
    if t.keywords:
        lines.append(f"keywords: {', '.join(t.keywords)}")
    return "\n".join(lines)


def _fmt_proof(p: Proof) -> str:
    parts = []
    if p.lean_tactics:
        parts.append(f"lean_tactics: {p.lean_tactics}")
    if p.informal:
        parts.append(f"informal_sketch: {p.informal}")
    return "\n".join(parts) if parts else "(no proof provided)"


def discover_prompt(seed: str, n: int) -> str:
    return (
        f"{SYSTEM}\n\n"
        f"TASK: Propose {n} interesting, well-formed mathematical conjectures related to: \"{seed}\".\n"
        f"For each, provide a name, an informal statement, a Lean 4 statement (theorem name : prop, "
        f"no proof), a domain, a difficulty in {{easy, medium, hard}}, 2-5 keywords, and a one-line rationale.\n"
        f"Respond strictly as: "
        f'{{"conjectures":[{{"name","informal","lean_statement","domain","difficulty","keywords",'
        f'"rationale"}}]}}'
    )


def prove_prompt(theorem: Theorem, k: int) -> str:
    return (
        f"{SYSTEM}\n\n"
        f"TASK: produce {k} DISTINCT candidate Lean 4 proofs for this theorem.\n"
        f"Each proof must be just the tactic block or proof term that follows `:= `.\n"
        f"THEOREM:\n{_fmt_theorem(theorem)}\n\n"
        f'Respond strictly as: {{"proofs":["by ...","by ...",...]}}'
    )


def align_prompt(theorem: Theorem, proof: Proof) -> str:
    return (
        f"{SYSTEM}\n\n"
        f"TASK: score how well the proof conceptually aligns with the theorem (0.0 to 1.0).\n"
        f"List which expected concepts the proof uses and which it omits.\n"
        f"THEOREM:\n{_fmt_theorem(theorem)}\n\n"
        f"PROOF:\n{_fmt_proof(proof)}\n\n"
        f'Respond strictly as: {{"score":0.0,"matched":["..."],"missing":["..."],"rationale":"..."}}'
    )


def read_prompt(theorem: Theorem, proof: Proof, tier: Difficulty) -> str:
    rubric = TIER_RUBRIC[tier]
    return (
        f"{SYSTEM}\n\n"
        f"TASK: act as a human proof reviewer at the **{tier.value}** difficulty tier.\n"
        f"Rubric for this tier: {rubric}\n"
        f"Give a verdict in {{pass, warn, fail}} and a short list of review comments.\n"
        f"THEOREM:\n{_fmt_theorem(theorem)}\n\n"
        f"PROOF:\n{_fmt_proof(proof)}\n\n"
        f'Respond strictly as: {{"verdict":"pass","comments":["..."]}}'
    )
