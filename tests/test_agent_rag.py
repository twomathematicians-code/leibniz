"""Tests for the mathematical RAG layer and the mathematician's agent."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

from leibniz.rag import default_rag, MathRAG, _tokens
from leibniz.agent import ask, _route, _extract_proof


class TestRAG:
    def test_retrieval_returns_known_entries(self):
        rag = default_rag()
        hits = rag.retrieve("rank nullity dimension kernel range", k=3)
        assert hits and hits[0].name == "rank_nullity"

    def test_retrieval_peter_weyl(self):
        hits = default_rag().retrieve("Peter-Weyl orthogonality compact group", k=3)
        assert hits and hits[0].name == "peter_weyl_orthogonality"

    def test_scores_ordered(self):
        hits = default_rag().retrieve("determinant of a matrix product", k=5)
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_scores_in_unit_interval(self):
        hits = default_rag().retrieve("vector space basis", k=10)
        assert all(0.0 <= h.score <= 1.0 for h in hits)

    def test_empty_query(self):
        assert default_rag().retrieve("") == []

    def test_tokens_expand_lemmas(self):
        toks = _tokens("mul_add")
        assert "distributivity" in toks and "multiplication" in toks

    def test_tokens_drop_stopwords(self):
        assert "the" not in _tokens("the determinant of the matrix")

    def test_hit_serialization(self):
        h = default_rag().retrieve("trace", k=1)[0]
        d = h.to_dict()
        assert set(d) >= {"name", "informal", "domain", "score"}


class TestAgentRouting:
    def test_compute_route(self):
        assert "compute" in _route("compute the eigenvalues of [[2,0],[0,3]]")

    def test_matrix_triggers_compute(self):
        assert "compute" in _route("what is [[1,2],[3,4]]")

    def test_formalize_route(self):
        assert "formalize" in _route("formalize the rank nullity theorem")

    def test_review_route(self):
        assert "review" in _route("verify this proof by rw [Nat.add_comm]")

    def test_retrieve_always_first(self):
        assert _route("anything")[0] == "retrieve"


class TestAgentAsk:
    def test_compute_answer(self):
        a = ask("compute eigenvalues of [[2,0],[0,3]]")
        assert any(s.tool == "compute" for s in a.trail)
        assert "2" in a.answer and "3" in a.answer

    def test_formalize_answer_has_lean(self):
        a = ask("formalize the rank nullity theorem for me")
        assert any(s.tool == "formalize" for s in a.trail)
        assert "theorem" in a.answer.lower() or "lean" in a.answer.lower()

    def test_review_with_proof(self):
        a = ask("verify by rw [Nat.add_comm] commutativity of vector addition")
        review = [s for s in a.trail if s.tool == "review"]
        assert review, "review step expected"

    def test_trail_always_has_retrieve(self):
        a = ask("hello")
        assert a.trail[0].tool == "retrieve"

    def test_answer_serializable(self):
        d = ask("derivative rules").to_dict()
        assert set(d) == {"query", "route", "answer", "trail"}

    def test_extract_proof(self):
        assert _extract_proof("check by ext i; simp") == "by ext i; simp"
        assert _extract_proof("no proof here") is None
