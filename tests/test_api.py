"""FastAPI TestClient tests (StubBackend)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest

from api.main import app
from fastapi.testclient import TestClient  # type: ignore


client = TestClient(app)


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        d = resp.json()
        assert d["status"] == "healthy"
        assert d["backend"] in ("stub", "hf", "remote")


class TestDiscovery:
    def test_discover_endpoint(self):
        resp = client.post("/discover", json={"seed": "arithmetic", "n": 3, "k": 2})
        assert resp.status_code == 200
        d = resp.json()
        assert d["seed"] == "arithmetic"
        assert len(d["certified"]) >= 2
        assert 0.0 <= d["success_rate"] <= 1.0

    def test_prove_endpoint(self):
        resp = client.post("/prove", json={
            "theorem": {"name": "two_plus_two", "informal": "",
                        "lean_statement": "theorem two_plus_two : 2 + 2 = 4",
                        "domain": "arithmetic", "difficulty": "easy"},
            "k": 3,
        })
        assert resp.status_code == 200
        proofs = resp.json()["proofs"]
        assert len(proofs) >= 2
        assert proofs[0]["lean_tactics"]


class TestReview:
    def test_review_endpoint(self):
        resp = client.post("/review", json={
            "theorem": {"name": "add_comm_nat", "informal": "",
                        "lean_statement": "theorem add_comm_nat (a b : Nat) : a + b = b + a",
                        "domain": "algebra", "difficulty": "medium"},
            "proof": {"lean_tactics": "by rw [Nat.add_comm]"},
        })
        assert resp.status_code == 200
        d = resp.json()
        assert d["reading"]["overall_verdict"] == "pass"

    def test_verify_endpoint(self):
        resp = client.post("/verify", json={
            "theorem": {"name": "two_plus_two", "informal": "",
                        "lean_statement": "theorem two_plus_two : 2 + 2 = 4"},
            "proof": {"lean_tactics": "by rfl"},
        })
        assert resp.status_code == 200
        d = resp.json()
        assert "passed" in d

    def test_review_sorry_fails(self):
        resp = client.post("/review", json={
            "theorem": {"name": "two_plus_two", "informal": "",
                        "lean_statement": "theorem two_plus_two : 2 + 2 = 4"},
            "proof": {"lean_tactics": "by sorry"},
        })
        d = resp.json()
        assert d["reading"]["tiers"][0]["verdict"] == "fail"


class TestEncyclopedia:
    def test_search(self):
        resp = client.get("/encyclopedia", params={"q": "prime", "limit": 5})
        assert resp.status_code == 200
        d = resp.json()
        assert d["query"] == "prime"
        assert len(d["results"]) >= 1

    def test_empty_query(self):
        resp = client.get("/encyclopedia", params={"q": "", "limit": 3})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 1


class TestLanding:
    def test_landing(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Leibniz" in resp.text
