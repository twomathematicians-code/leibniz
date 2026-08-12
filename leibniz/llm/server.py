"""
Optional Inference Server
=========================
A tiny FastAPI app that exposes a Backend over HTTP, so a local model
(HFBackend) can be served once and consumed by RemoteBackend clients
(e.g. the HF Space calling a GPU host).

Run:
    LEIBNIZ_BACKEND=hf LEIBNIZ_MODEL=Qwen/Qwen2.5-Math-1.5B-Instruct \\
        uvicorn leibniz.llm.server:app --host 0.0.0.0 --port 8431

This module imports fastapi lazily so the core package stays import-free
when the server isn't used.
"""

from __future__ import annotations

from typing import List, Optional

from .backend import get_backend
from ..config import config
from ..core.types import Theorem, Proof
from ..core.difficulty import Difficulty, parse_difficulty


def _build_app():
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    app = FastAPI(
        title="Leibniz Backend Server",
        description="HTTP wrapper around a Leibniz LLM backend (stub/hf/remote).",
        version="0.1.0",
    )

    backend = get_backend(config)

    class DiscoverReq(BaseModel):
        seed: str
        n: int = Field(default=5, ge=1, le=20)

    class ProveReq(BaseModel):
        name: str
        informal: str = ""
        lean_statement: str = ""
        domain: str = "general"
        difficulty: str = "medium"
        keywords: List[str] = Field(default_factory=list)
        k: int = Field(default=4, ge=1, le=16)

    class AlignReq(BaseModel):
        name: str
        informal: str = ""
        lean_statement: str = ""
        domain: str = "general"
        difficulty: str = "medium"
        keywords: List[str] = Field(default_factory=list)
        lean_tactics: Optional[str] = None
        informal_sketch: Optional[str] = None

    class ReadReq(AlignReq):
        tier: str = "medium"

    @app.get("/health")
    def health():
        return {"status": "healthy", "backend": backend.name, "model": config.model}

    @app.post("/discover")
    def discover(req: DiscoverReq):
        return {"conjectures": backend.discover(req.seed, req.n)}

    @app.post("/prove")
    def prove(req: ProveReq):
        t = Theorem(req.name, req.informal, req.lean_statement, req.domain, req.difficulty, req.keywords)
        return {"proofs": backend.prove(t, req.k)}

    @app.post("/align")
    def align(req: AlignReq):
        t = Theorem(req.name, req.informal, req.lean_statement, req.domain, req.difficulty, req.keywords)
        p = Proof(req.lean_tactics, req.informal_sketch, author="remote")
        return backend.align(t, p)

    @app.post("/read")
    def read(req: ReadReq):
        t = Theorem(req.name, req.informal, req.lean_statement, req.domain, req.difficulty, req.keywords)
        p = Proof(req.lean_tactics, req.informal_sketch, author="remote")
        tier = parse_difficulty(req.tier)
        return backend.read_tier(t, p, tier)

    return app


# `app` is created at import time so `uvicorn leibniz.llm.server:app` works.
app = _build_app()
