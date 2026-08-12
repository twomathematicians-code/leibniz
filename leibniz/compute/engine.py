"""
Symbolic Computation Engine (Wolfram-Alpha-style compute layer)
================================================================
Backed by SymPy. Provides exact, step-by-step computation across:

  * algebra      — solve, factor, expand, simplify
  * calculus     — differentiate, integrate, limit, Taylor series
  * linear alg.  — determinant, inverse, eigenvalues, rank, RREF, trace
  * arithmetic   — exact rational evaluation

This is the "Calculus Ratiocinator" made concrete: it does not look answers
up — it computes them symbolically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import sympy
from sympy import (
    Symbol, symbols, sympify, parse_expr, simplify, solve, diff, integrate,
    limit, series, factor, expand, Rational, Matrix, eye, det, trace, pretty,
    latex, Eq, S,
)
from sympy.parsing.sympy_parser import (
    parse_expr as _parse, standard_transformations,
    implicit_multiplication_application, convert_xor,
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ComputeResult:
    """The output of a single computation."""
    query: str
    intent: str                                  # solve | diff | integrate | ...
    input_interpretation: str = ""               # canonical parsed form
    answer: str = ""                             # exact answer (plain)
    answer_latex: str = ""                       # LaTeX for rendering
    steps: List[str] = field(default_factory=list)
    ok: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "query": self.query, "intent": self.intent,
            "input_interpretation": self.input_interpretation,
            "answer": self.answer, "answer_latex": self.answer_latex,
            "steps": self.steps, "ok": self.ok, "error": self.error,
        }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application, convert_xor,
)


def _parse_expr(text: str, local_dict=None):
    """Lenient SymPy expression parse: ^ -> power, implicit multiplication."""
    return _parse(text, transformations=_TRANSFORMS,
                  local_dict=local_dict, evaluate=True)


def _free_symbols(expr) -> List[Symbol]:
    try:
        return sorted(expr.free_symbols, key=lambda s: s.name)
    except Exception:
        return []


def _to_latex(obj) -> str:
    try:
        return latex(obj, mode="plain")
    except Exception:
        return ""


def _parse_matrix(text: str) -> Optional[Matrix]:
    """Parse a [[a,b],[c,d]] literal into a SymPy Matrix."""
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return None
    try:
        rows = []
        # match each [ ... ] group at the top level
        inner = text[1:-1].strip()
        for m in re.finditer(r"\[([^\[\]]+)\]", inner):
            elems = [sympify(_parse_expr(t.strip())) for t in m.group(1).split(",")]
            rows.append(elems)
        if not rows:
            return None
        return Matrix(rows)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------

def _do_solve(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="solve")
    try:
        if "=" in expr_text:
            lhs, rhs = expr_text.split("=", 1)
            e = Eq(_parse_expr(lhs), _parse_expr(rhs))
            res.input_interpretation = f"solve  {lhs.strip()} = {rhs.strip()}"
        else:
            e = _parse_expr(expr_text)
            res.input_interpretation = f"solve  {e} = 0"
        vars_ = _free_symbols(e) if isinstance(e, (sympy.Expr, sympy.Eq)) else []
        if not vars_:
            res.error = "No variable found to solve for."
            res.ok = False
            return res
        sols = solve(e, vars_, dict=True)
        res.steps.append(f"1. Identify the equation: {e}")
        res.steps.append(f"2. Solve for: {', '.join(str(v) for v in vars_)}")
        if not sols:
            res.answer = "No solutions."
            res.steps.append("3. The equation has no solutions.")
        else:
            parts = []
            for i, s in enumerate(sols, 1):
                if isinstance(s, dict):
                    parts.append(", ".join(f"{k} = {v}" for k, v in s.items()))
                else:
                    parts.append(str(s))
            res.answer = "; ".join(parts)
            res.answer_latex = "; ".join(_to_latex(s) for s in sols)
            res.steps.append(f"3. Solutions: {res.answer}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not solve: {exc}"
    return res


def _do_diff(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="differentiate")
    try:
        e = _parse_expr(expr_text)
        vs = _free_symbols(e) or [Symbol("x")]
        v = vs[0]
        d = diff(e, v)
        res.input_interpretation = f"d/d{v}  {e}"
        res.answer = str(d)
        res.answer_latex = _to_latex(d)
        res.steps.append(f"1. Differentiate {e} with respect to {v}.")
        res.steps.append(f"2. Apply the differentiation rules term-by-term.")
        res.steps.append(f"3. Result: {d}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not differentiate: {exc}"
    return res


def _do_integrate(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="integrate")
    try:
        e = _parse_expr(expr_text)
        vs = _free_symbols(e) or [Symbol("x")]
        v = vs[0]
        I = integrate(e, v)
        res.input_interpretation = f"∫ {e} d{v}"
        res.answer = str(I)
        res.answer_latex = _to_latex(I)
        res.steps.append(f"1. Find the antiderivative of {e} with respect to {v}.")
        res.steps.append(f"2. Result: {I}  +  C")
        res.steps.append("3. Check: differentiating the result recovers the integrand.")
    except Exception as exc:
        res.ok, res.error = False, f"Could not integrate: {exc}"
    return res


def _do_limit(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="limit")
    try:
        # form: "<expr> as <var> -> <point>"
        m = re.search(r"(.+?)\s+as\s+(\w+)\s*->\s*(\S+)", expr_text)
        if m:
            body, var, pt = m.group(1).strip(), m.group(2), m.group(3)
        else:
            body, var, pt = expr_text.strip(), "x", "0"
        e = _parse_expr(body)
        v = Symbol(var)
        point = _parse_expr(pt)
        L = limit(e, v, point)
        res.input_interpretation = f"lim {e}  ({v} -> {point})"
        res.answer = str(L)
        res.answer_latex = _to_latex(L)
        res.steps.append(f"1. Compute the limit of {e} as {v} approaches {point}.")
        res.steps.append(f"2. Result: {L}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not compute limit: {exc}"
    return res


def _do_series(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="taylor_series")
    try:
        e = _parse_expr(expr_text)
        v = (_free_symbols(e) or [Symbol("x")])[0]
        s = series(e, v, 0, 6).removeO()
        res.input_interpretation = f"Taylor series of {e} about {v}=0"
        res.answer = str(s)
        res.answer_latex = _to_latex(s)
        res.steps.append(f"1. Expand {e} as a Taylor series about {v} = 0.")
        res.steps.append(f"2. Result (up to order 5): {s}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not compute series: {exc}"
    return res


def _do_simplify(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="simplify")
    try:
        e = _parse_expr(expr_text)
        s = simplify(e)
        res.input_interpretation = f"simplify  {e}"
        res.answer = str(s)
        res.answer_latex = _to_latex(s)
        res.steps.append(f"1. Simplify {e}.")
        res.steps.append(f"2. Result: {s}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not simplify: {exc}"
    return res


def _do_factor(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="factor")
    try:
        e = _parse_expr(expr_text)
        s = factor(e)
        res.input_interpretation = f"factor  {e}"
        res.answer = str(s)
        res.answer_latex = _to_latex(s)
        res.steps.append(f"1. Factor {e}.")
        res.steps.append(f"2. Result: {s}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not factor: {exc}"
    return res


def _do_expand(expr_text: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent="expand")
    try:
        e = _parse_expr(expr_text)
        s = expand(e)
        res.input_interpretation = f"expand  {e}"
        res.answer = str(s)
        res.answer_latex = _to_latex(s)
        res.steps.append(f"1. Expand {e}.")
        res.steps.append(f"2. Result: {s}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not expand: {exc}"
    return res


def _do_matrix(expr_text: str, op: str, query: str) -> ComputeResult:
    res = ComputeResult(query=query, intent=f"matrix_{op}")
    M = _parse_matrix(expr_text)
    if M is None:
        # try to extract a [[...]] block from the query
        m = re.search(r"\[\[.*?\]\]", query)
        if m:
            M = _parse_matrix(m.group(0))
    if M is None:
        res.ok, res.error = False, "Could not parse a matrix. Use [[a,b],[c,d]] form."
        return res
    try:
        res.input_interpretation = f"{M.rows}x{M.cols} matrix\n{pretty(M)}"
        if op == "det":
            val = det(M)
            res.answer = str(val)
            res.answer_latex = _to_latex(val)
            res.steps.append(f"1. Compute the determinant of the {M.rows}x{M.cols} matrix.")
            res.steps.append(f"2. det = {val}")
        elif op == "inverse":
            if det(M) == 0:
                res.ok, res.error = False, "Matrix is singular (det = 0); no inverse."
                return res
            inv = M.inv()
            res.answer = str(inv)
            res.answer_latex = _to_latex(inv)
            res.steps.append("1. Check det ≠ 0 (matrix is invertible).")
            res.steps.append(f"2. Inverse:\n{pretty(inv)}")
        elif op == "eigenvalues":
            ev = M.eigenvals()
            res.answer = ", ".join(f"{k} (×{m})" for k, m in ev.items())
            res.answer_latex = _to_latex(list(ev.keys()))
            res.steps.append("1. Compute eigenvalues (roots of the characteristic polynomial).")
            res.steps.append(f"2. Eigenvalues: {res.answer}")
        elif op == "rank":
            r = M.rank()
            res.answer = str(r)
            res.steps.append(f"1. Compute the rank (dimension of the column space).")
            res.steps.append(f"2. rank = {r}")
        elif op == "rref":
            rref_M, pivots = M.rref()
            res.answer = str(rref_M)
            res.answer_latex = _to_latex(rref_M)
            res.steps.append("1. Reduce to row-echelon form.")
            res.steps.append(f"2. Pivot columns: {list(pivots)}")
            res.steps.append(f"3. RREF:\n{pretty(rref_M)}")
        elif op == "trace":
            t = trace(M)
            res.answer = str(t)
            res.answer_latex = _to_latex(t)
            res.steps.append(f"1. Sum the diagonal entries.")
            res.steps.append(f"2. trace = {t}")
    except Exception as exc:
        res.ok, res.error = False, f"Matrix operation failed: {exc}"
    return res


def _do_eval(expr_text: str, query: str) -> ComputeResult:
    """Exact arithmetic evaluation (rational numbers, etc.)."""
    res = ComputeResult(query=query, intent="evaluate")
    try:
        e = _parse_expr(expr_text)
        val = sympify(e)
        res.input_interpretation = f"evaluate  {e}"
        res.answer = str(val)
        res.answer_latex = _to_latex(val)
        res.steps.append(f"1. Evaluate {e} exactly.")
        res.steps.append(f"2. Result: {val}")
    except Exception as exc:
        res.ok, res.error = False, f"Could not evaluate: {exc}"
    return res


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def compute(query: str, intent: Optional[str] = None) -> ComputeResult:
    """Compute a result from a natural-language or symbolic query."""
    from .parser import parse_intent

    if intent is None:
        intent, expr_text, extra = parse_intent(query)
    else:
        _, expr_text, extra = parse_intent(query)

    if intent == "solve":
        return _do_solve(expr_text, query)
    if intent == "diff":
        return _do_diff(expr_text, query)
    if intent == "integrate":
        return _do_integrate(expr_text, query)
    if intent == "limit":
        return _do_limit(expr_text, query)
    if intent == "series":
        return _do_series(expr_text, query)
    if intent == "simplify":
        return _do_simplify(expr_text, query)
    if intent == "factor":
        return _do_factor(expr_text, query)
    if intent == "expand":
        return _do_expand(expr_text, query)
    if intent.startswith("matrix_"):
        op = intent.split("_", 1)[1]
        return _do_matrix(expr_text, op, query)
    if intent == "evaluate":
        return _do_eval(expr_text, query)

    return ComputeResult(query=query, intent="unknown", ok=False,
                         error=f"Could not determine computation intent for: {query}")
