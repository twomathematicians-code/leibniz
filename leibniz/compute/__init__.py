"""Symbolic computation layer (SymPy-backed). Wolfram-Alpha-style compute."""

from .engine import compute, ComputeResult
from .parser import parse_intent

__all__ = ["compute", "ComputeResult", "parse_intent"]
