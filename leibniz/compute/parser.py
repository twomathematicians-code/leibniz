"""
Query Intent Parser — the NLU front door of the compute engine
================================================================
Maps free-form natural-language / ASCII math queries onto a compute intent
and the symbolic expression text to feed SymPy.

Returns: (intent, expr_text, extra)
  intent    one of solve|diff|integrate|limit|series|simplify|factor|expand|
            matrix_<op>|evaluate|unknown
  expr_text the substring that holds the mathematical expression
  extra     optional dict (e.g. matrix op)
"""

from __future__ import annotations

import re
from typing import Tuple

_MATRIX_OPS = ["determinant", "det", "inverse", "eigenvalue", "eigenvalues",
               "rank", "rref", "trace"]


def _strip(query: str) -> str:
    """Normalise surface forms: unicode -> ASCII, lowercase keywords kept."""
    q = query.strip()
    repl = {
        "×": "*", "·": "*", "÷": "/", "−": "-", "–": "-",
        "√": "sqrt", "π": "pi", "∞": "oo", "∫": "", "dx": "",
        "→": "->", "∛": "cbrt",
    }
    for k, v in repl.items():
        q = q.replace(k, v)
    # collapse "d/dx" variants to the word 'derivative'
    return q


def parse_intent(query: str) -> Tuple[str, str, dict]:
    q = _strip(query)
    ql = q.lower()
    extra: dict = {}

    # --- matrix operations ---
    if "[[" in q and any(k in ql for k in _MATRIX_OPS) or (
        "[[" in q and "matrix" in ql
    ):
        # determine the op
        if "determinant" in ql or re.search(r"\bdet\b", ql):
            op = "det"
        elif "inverse" in ql or "inv of" in ql:
            op = "inverse"
        elif "eigenvalue" in ql or "eigen" in ql:
            op = "eigenvalues"
        elif "rank" in ql:
            op = "rank"
        elif "rref" in ql or "row reduce" in ql or "row-echelon" in ql:
            op = "rref"
        elif "trace" in ql:
            op = "trace"
        else:
            op = "det"
        m = re.search(r"\[\[.*?\]\]", q)
        expr = m.group(0) if m else ""
        return f"matrix_{op}", expr, {"op": op}

    # --- a bare [[...]] matrix with no op: default to determinant ---
    if re.search(r"\[\[.*\]\]", q) and not any(c in ql for c in ["+", "*"]):
        m = re.search(r"\[\[.*\]\]", q)
        return "matrix_det", m.group(0) if m else "", {}

    # --- solve ---
    if "solve" in ql or "root" in ql or "find x" in ql or "= 0" in ql.replace(" ", "") and "d/d" not in ql:
        expr = _after_keyword(q, ["solve", "roots of", "root of", "find", "solve for"])
        if not expr:
            expr = q
        return "solve", expr, {}

    # --- differentiate ---
    if any(k in ql for k in ["derivative", "differentiate", "d/d", "differential"]):
        expr = _after_keyword(q, ["derivative of", "differentiate", "d/dx", "d/dy",
                                  "derivative", "differential of"])
        return "diff", expr or q, {}

    # --- integrate ---
    if any(k in ql for k in ["integrate", "integral", "antiderivative", "∫"]):
        expr = _after_keyword(q, ["integral of", "integrate", "antiderivative of",
                                  "integral", "integrate "])
        return "integrate", expr or q, {}

    # --- limit ---
    if "limit" in ql:
        expr = _after_keyword(q, ["limit of", "limit"])
        return "limit", expr or q, {}

    # --- taylor / series ---
    if any(k in ql for k in ["taylor", "series expansion", "maclaurin"]):
        expr = _after_keyword(q, ["taylor series of", "taylor expansion of",
                                  "series expansion of", "maclaurin series of",
                                  "taylor", "series"])
        return "series", expr or q, {}

    # --- factor ---
    if "factor" in ql:
        expr = _after_keyword(q, ["factor", "factorise", "factorize"])
        return "factor", expr or q, {}

    # --- expand ---
    if "expand" in ql:
        expr = _after_keyword(q, ["expand"])
        return "expand", expr or q, {}

    # --- simplify ---
    if "simplify" in ql:
        expr = _after_keyword(q, ["simplify"])
        return "simplify", expr or q, {}

    # --- fallback: try exact evaluation ---
    return "evaluate", q, {}


def _after_keyword(q: str, keywords) -> str:
    """Return the substring of q following the first matching keyword."""
    ql = q.lower()
    for kw in keywords:
        idx = ql.find(kw)
        if idx != -1:
            return q[idx + len(kw):].strip(" :.,'\"")
    return ""
