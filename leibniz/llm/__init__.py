"""LLM backend layer — the Calculus Ratiocinator's voice."""

from .backend import BaseBackend, StubBackend, HFBackend, RemoteBackend, get_backend

__all__ = ["BaseBackend", "StubBackend", "HFBackend", "RemoteBackend", "get_backend"]
