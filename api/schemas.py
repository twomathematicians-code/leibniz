"""
API Schemas (Pydantic v2)
=========================
Request/response models for the Leibniz proof-engine API.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# --- inputs ---

class TheoremIn(BaseModel):
    name: str = Field(..., description="Theorem identifier")
    informal: str = ""
    lean_statement: Optional[str] = Field(default=None, description="Lean 4 statement (no proof)")
    domain: str = "general"
    difficulty: str = "medium"
    keywords: List[str] = Field(default_factory=list)


class ProofIn(BaseModel):
    lean_tactics: Optional[str] = None
    informal: Optional[str] = None
    author: str = "user"


class DiscoverReq(BaseModel):
    seed: str = Field(..., description="Seed topic, e.g. 'prime numbers'")
    n: int = Field(default=5, ge=1, le=20)
    k: int = Field(default=4, ge=1, le=16, description="Candidate proofs per conjecture")


class ProveReq(BaseModel):
    theorem: TheoremIn
    k: int = Field(default=4, ge=1, le=16)


class ReviewReq(BaseModel):
    theorem: TheoremIn
    proof: ProofIn = Field(default_factory=ProofIn)


class VerifyReq(BaseModel):
    theorem: TheoremIn
    proof: ProofIn


# --- outputs ---

class HealthResp(BaseModel):
    status: str
    backend: str
    lean_available: bool
    model: Optional[str] = None
    uptime_seconds: float


class EncyclopediaResp(BaseModel):
    query: str
    results: List[dict]
