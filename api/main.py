"""
Leibniz Proof-Engine API
========================
FastAPI service exposing the Leibniz engine's two modes over REST:

    GET  /health            — service + backend + Lean status
    POST /discover          — Discover -> Prove -> Verify pipeline
    POST /review            — 3-gate review (Validity -> Alignment -> Reading)
    POST /prove             — candidate-proof generation only
    POST /verify            — formal (Lean) validity check only
    GET  /encyclopedia      — search the knowledge base
    GET  /                  — HTML landing page

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8430   # run from the leibniz/ dir
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager

# Make `leibniz` importable when running from the project dir.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from leibniz.pipeline import Engine
from leibniz.core.types import Theorem, Proof, to_dict
from leibniz.encyclopedia import default as default_enc

from .schemas import (
    DiscoverReq, ReviewReq, ProveReq, VerifyReq,
    TheoremIn, ProofIn, HealthResp, EncyclopediaResp,
)

# --- engine (default StubBackend; env can switch to hf/remote) ---
engine = Engine()
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[Leibniz API] backend={engine.backend.name} "
          f"model={engine.cfg.model} lean_available={engine.lean.available}")
    yield
    print("[Leibniz API] shutting down.")


app = FastAPI(
    title="Leibniz Proof-Engine API",
    description=(
        "### A Universal Calculator for Truth\n"
        "Three-stage LLM-driven mathematical discovery and proof checking.\n\n"
        "Two modes: **Discovery** (Discover → Prove → Verify) and "
        "**Review** (Validity → Alignment → Reading).\n\n"
        "Runs on the deterministic StubBackend by default; set "
        "`LEIBNIZ_BACKEND=hf` or `=remote` to plug in a real model."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# --- helpers ---

def _theorem(t: TheoremIn) -> Theorem:
    return Theorem(
        name=t.name, informal=t.informal, lean_statement=t.lean_statement,
        domain=t.domain, difficulty=t.difficulty, keywords=t.keywords,
    )


def _proof(p: ProofIn) -> Proof:
    return Proof(lean_tactics=p.lean_tactics, informal=p.informal, author=p.author)


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResp, tags=["System"])
async def health():
    """Service health, active backend, and Lean toolchain availability."""
    return HealthResp(
        status="healthy",
        backend=engine.backend.name,
        lean_available=engine.lean.available,
        model=engine.cfg.model,
        uptime_seconds=time.time() - START_TIME,
    )


@app.post("/discover", tags=["Discovery"], summary="Discover → Prove → Verify")
async def discover(req: DiscoverReq):
    """Run the full discovery pipeline on a seed topic."""
    result = engine.discover_and_verify(req.seed, n=req.n, k=req.k)
    return to_dict(result)


@app.post("/review", tags=["Review"], summary="3-gate review")
async def review(req: ReviewReq):
    """Run Validity → Alignment → Reading on a (theorem, proof) pair."""
    report = engine.review(_theorem(req.theorem), _proof(req.proof))
    return to_dict(report)


@app.post("/prove", tags=["Discovery"], summary="Candidate-proof generation")
async def prove(req: ProveReq):
    """Generate k candidate proofs for a theorem."""
    from leibniz.stages import prove as _prove
    cands = _prove(_theorem(req.theorem), req.k, engine.backend)
    return {"proofs": [{"lean_tactics": c.proof.lean_tactics, "source": c.source} for c in cands]}


@app.post("/verify", tags=["Review"], summary="Formal validity check (Lean)")
async def verify(req: VerifyReq):
    """Run Gate 1 (Lean compilation) only."""
    res = engine.lean.check(_theorem(req.theorem), _proof(req.proof))
    return to_dict(res)


@app.get("/encyclopedia", response_model=EncyclopediaResp, tags=["Encyclopedia"])
async def encyclopedia(q: str = Query("", description="search query"),
                       limit: int = Query(10, ge=1, le=50)):
    """Search the knowledge base of verified thoughts."""
    enc = default_enc()
    results = enc.search(q, limit=limit) if q else enc.all()[:limit]
    return EncyclopediaResp(query=q, results=results)


@app.post("/compute", tags=["Compute"], summary="Symbolic computation (Wolfram-Alpha-style)")
async def compute_endpoint(payload: dict):
    """Symbolically compute a result from a natural-language / symbolic query.

    Backed by SymPy: solve, differentiate, integrate, limit, series, simplify,
    factor, expand, and matrix operations (determinant, inverse, eigenvalues, rank, trace)."""
    query = (payload or {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Field 'query' is required.")
    result = engine.compute(query)
    return result.to_dict()


@app.post("/formalize", tags=["Formalize"], summary="Natural language to Lean (autoformalization)")
async def formalize_endpoint(payload: dict):
    """Translate an informal mathematical statement into a candidate Lean 4 statement."""
    informal = (payload or {}).get("informal", "")
    if not informal:
        raise HTTPException(status_code=400, detail="Field 'informal' is required.")
    r = engine.formalize(informal)
    return {
        "informal": r.informal, "lean_statement": r.lean_statement,
        "confidence": r.confidence, "source": r.source,
        "matched_entry": r.matched_entry, "mathlib_refs": r.mathlib_refs,
        "notes": r.notes,
    }


@app.get("/", response_class=HTMLResponse, tags=["System"])
async def landing():
    return LANDING_HTML


LANDING_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Leibniz — Universal Calculator for Truth</title>
<style>
  body{font-family:system-ui,Segoe UI,sans-serif;max-width:780px;margin:2rem auto;line-height:1.5;color:#222;padding:0 1rem}
  h1{margin-bottom:.2rem} .tag{color:#6a7f':';} code{background:#f4f4f4;padding:.1em .3em;border-radius:4px}
  pre{background:#f4f4f4;padding:1rem;border-radius:8px;overflow:auto}
  a{color:#0969da} .muted{color:#666}
</style></head><body>
<h1>🧮 Leibniz Proof-Engine</h1>
<p class="muted">A Universal Calculator for Truth — three-stage LLM-driven mathematical discovery &amp; proof checking.</p>
<ul>
  <li><code>POST /discover</code> — Discover → Prove → Verify</li>
  <li><code>POST /review</code> — 3-gate review (Validity → Alignment → Reading)</li>
  <li><code>POST /prove</code>, <code>POST /verify</code> — individual stages</li>
  <li><code>GET /encyclopedia?q=...</code> — search the knowledge base</li>
  <li><code>GET /health</code> — backend &amp; Lean status</li>
</ul>
<p>Interactive docs: <a href="/docs">/docs</a> (Swagger) · <a href="/redoc">/redoc</a></p>
<p class="muted">Runs on the deterministic StubBackend by default.
Set <code>LEIBNIZ_BACKEND=hf</code> (or <code>=remote</code>) to use a real model.</p>
</body></html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=engine.cfg.api_host, port=engine.cfg.api_port, reload=False)
