"""
Mathematical RAG — retrieval over the encyclopedia knowledge base
==================================================================
The draft's "RAG / Advanced RAG using mathematical basis" idea, realised as
an honest first stage: lexical-statistical retrieval (TF-IDF with query
expansion through the lemma-concept map), over the 57-entry encyclopedia.

Vector-embedding RAG (semantic, model-backed) is the roadmap stage; this
module is the retrieval substrate it will plug into — same interface,
deterministic, zero extra dependencies.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .encyclopedia.lookup import default as default_enc


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RetrievalHit:
    """One retrieved encyclopedia entry with its relevance score."""
    name: str
    informal: str
    domain: str
    score: float                      # cosine similarity, 0..1
    statement: str = ""
    mathlib_ref: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "informal": self.informal,
            "domain": self.domain, "score": round(self.score, 4),
            "lean_statement": self.statement, "mathlib_ref": self.mathlib_ref,
        }


# ---------------------------------------------------------------------------
# Tokenisation shared with the lemma-aware layer
# ---------------------------------------------------------------------------

_LEMMA_CONCEPTS = {
    "mul_add": "distributivity multiplication",
    "add_mul": "distributivity multiplication",
    "add_comm": "commutativity addition",
    "mul_comm": "commutativity multiplication",
    "add_assoc": "associativity addition",
    "mul_assoc": "associativity multiplication",
    "smul": "scalar multiplication vector linear algebra",
    "vec": "vector space linear algebra",
    "ext": "pointwise vector",
    "rw": "rewrite",
    "simp": "simplify",
    "rfl": "definitional equality",
    "sorry": "unproven",
    "trace": "trace matrix linear algebra",
    "det": "determinant matrix",
    "eigen": "eigenvalue spectrum",
    "span": "span submodule basis",
    "measure": "measure theory integration",
    "deriv": "derivative calculus",
    "integral": "integration calculus",
}

_STOP = {
    "a", "an", "the", "of", "is", "are", "for", "with", "and", "or", "if",
    "then", "that", "this", "it", "its", "as", "by", "at", "to", "in", "on",
    "every", "some", "any", "all", "does", "do", "not", "no", "can", "you",
    "me", "my", "we", "our", "be", "have", "has", "what", "which", "how",
    "tell", "show", "find", "give", "please", "about",
}


def _tokens(text: str) -> List[str]:
    """Underscore-aware, stopword-filtered, lemma-expanded tokens."""
    out: List[str] = []
    for chunk in re.split(r"[^a-zA-Z0-9_]", (text or "").lower()):
        for tok in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", chunk):
            out.append(tok)
            parts = [p for p in tok.split("_") if p]
            out.extend(parts)
    expanded: List[str] = []
    for tok in out:
        if tok in _STOP or len(tok) < 2:
            continue
        expanded.append(tok)
        concept = _LEMMA_CONCEPTS.get(tok)
        if concept:
            expanded.extend(concept.split())
    return expanded


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------

class MathRAG:
    """TF-IDF retrieval over the encyclopedia with lemma-aware query expansion."""

    def __init__(self, encyclopedia=None):
        self._enc = encyclopedia or default_enc()
        self._docs: List[Dict] = self._enc.all()
        self._doc_tokens: List[List[str]] = []
        self._tf: List[Dict[str, float]] = []
        self._idf: Dict[str, float] = {}
        self._build()

    # -- index construction ------------------------------------------------

    def _doc_text(self, entry: Dict) -> str:
        parts = [entry.get("name", ""),
                 entry.get("informal", ""),
                 entry.get("domain", "").replace("_", " "),
                 " ".join(entry.get("keywords", [])),
                 entry.get("lean_statement", "") or "",
                 entry.get("mathlib_ref", "") or ""]
        return " ".join(parts)

    def _build(self) -> None:
        df: Dict[str, int] = {}
        n = max(len(self._docs), 1)
        for entry in self._docs:
            toks = _tokens(self._doc_text(entry))
            self._doc_tokens.append(toks)
            counts: Dict[str, float] = {}
            for t in toks:
                counts[t] = counts.get(t, 0.0) + 1.0
            # sublinear tf
            self._tf.append({t: 1.0 + math.log(c) for t, c in counts.items()})
            for t in counts:
                df[t] = df.get(t, 0) + 1
        self._idf = {t: math.log(n / df_t) + 1.0 for t, df_t in df.items()}

    def _vec(self, tokens: List[str]) -> Dict[str, float]:
        counts: Dict[str, float] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0.0) + 1.0
        v = {t: (1.0 + math.log(c)) * self._idf.get(t, math.log(len(self._docs)) + 1.0)
             for t, c in counts.items()}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        return {t: w / norm for t, w in v.items()}

    # -- query ----------------------------------------------------------------

    def retrieve(self, query: str, k: int = 5) -> List[RetrievalHit]:
        """Top-k encyclopedia entries by cosine similarity to the query."""
        qv = self._vec(_tokens(query))
        if not qv:
            return []
        scored: List[Tuple[float, Dict]] = []
        for entry, tf in zip(self._docs, self._tf):
            dv = {t: w * self._idf.get(t, 1.0) for t, w in tf.items()}
            norm = math.sqrt(sum(w * w for w in dv.values())) or 1.0
            dv = {t: w / norm for t, w in dv.items()}
            score = sum(w * dv.get(t, 0.0) for t, w in qv.items())
            scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        hits: List[RetrievalHit] = []
        for score, e in scored[:k]:
            if score <= 0:
                break
            hits.append(RetrievalHit(
                name=e.get("name", ""),
                informal=e.get("informal", ""),
                domain=e.get("domain", "general"),
                score=score,
                statement=e.get("lean_statement", "") or "",
                mathlib_ref=e.get("mathlib_ref", "") or "",
            ))
        return hits


# module-level default (lazy)
_default_rag: Optional[MathRAG] = None


def default_rag() -> MathRAG:
    global _default_rag
    if _default_rag is None:
        _default_rag = MathRAG()
    return _default_rag
