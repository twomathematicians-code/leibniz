"""Formal layer — the Lean verification bridge (the formal voice of Gate 1)."""

from .lean_client import LeanClient
from . import snippets

__all__ = ["LeanClient", "snippets"]
