"""
LLM Backends — the Calculus Ratiocinator
========================================
A single `BaseBackend` interface with three implementations:

    * StubBackend   (default) — deterministic, zero-dependency, rule-based.
    * HFBackend     — local HuggingFace causal-LM (needs torch + transformers).
    * RemoteBackend — calls an HF Inference / OpenAI-compatible endpoint (needs requests).

The engine calls the same four high-level methods regardless of backend:
    discover(seed, n)   -> list of conjecture dicts
    prove(theorem, k)   -> list of candidate tactic strings
    align(theorem, p)   -> {score, matched, missing, rationale}
    read_tier(t, p, tier) -> {verdict, comments}

Selection happens via `get_backend(cfg)` using `cfg.backend` (env: LEIBNIZ_BACKEND).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..config import EngineConfig, config as default_config
from ..core.types import Theorem, Proof
from ..core.difficulty import Difficulty
from . import prompts


# ============================================================================
# Base interface
# ============================================================================

class BaseBackend(ABC):
    """Common interface every backend implements."""

    name = "base"

    def __init__(self, cfg: Optional[EngineConfig] = None):
        self.cfg = cfg or default_config

    @abstractmethod
    def discover(self, seed: str, n: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def prove(self, theorem: Theorem, k: int) -> List[str]:
        ...

    @abstractmethod
    def align(self, theorem: Theorem, proof: Proof) -> Dict[str, Any]:
        ...

    @abstractmethod
    def read_tier(self, theorem: Theorem, proof: Proof, tier: Difficulty) -> Dict[str, Any]:
        ...

    # --- shared helpers for LLM backends ---

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Tolerantly extract the first JSON object/array from a model response."""
        text = text.strip()
        # strip ```json ... ``` fences if present
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        # fallback: first balanced {...} or [...]
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            if start == -1:
                continue
            depth = 0
            for i in range(start, len(text)):
                if text[i] == opener:
                    depth += 1
                elif text[i] == closer:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except Exception:
                            break
        return {}


# ============================================================================
# Stub backend (default) — no dependencies, fully deterministic
# ============================================================================

class StubBackend(BaseBackend):
    """Rule-based backend. Uses the Encyclopedia as ground truth so the whole
    pipeline is meaningful without any ML stack or network."""

    name = "stub"

    def __init__(self, cfg: Optional[EngineConfig] = None):
        super().__init__(cfg)
        # lazy to avoid import cycle at package import time
        from ..encyclopedia.lookup import default as _default_enc
        self._enc = _default_enc()

    # --- discover ---

    def discover(self, seed: str, n: int) -> List[Dict[str, Any]]:
        hits = self._enc.search(seed, limit=max(n, 1))
        if not hits:
            hits = self._enc.all()[:n]
        out: List[Dict[str, Any]] = []
        for e in hits[:n]:
            out.append({
                "name": e["name"],
                "informal": e.get("informal", ""),
                "lean_statement": e.get("lean_statement", ""),
                "domain": e.get("domain", "general"),
                "difficulty": e.get("difficulty", "medium"),
                "keywords": list(e.get("keywords", [])),
                "rationale": e.get("rationale", ""),
            })
        return out

    # --- prove ---

    def prove(self, theorem: Theorem, k: int) -> List[str]:
        entry = self._enc.get(theorem.name)
        candidates: List[str] = []
        # 1) the encyclopedia's known-good proof (if any) is the first candidate
        if entry and entry.get("lean_proof"):
            candidates.append(entry["lean_proof"].strip())
        # 2) shape-based fallbacks
        shape = _shape_of(theorem)
        for tac in _TEMPLATES.get(shape, []):
            if tac not in candidates:
                candidates.append(tac)
        # 3) a couple of generic attempts
        for tac in ("by simp", "by decide", "by rfl"):
            if tac not in candidates:
                candidates.append(tac)
        # pad/truncate to k
        if len(candidates) < k:
            candidates = candidates + [candidates[-1]] * (k - len(candidates))
        return candidates[:k]

    # --- align ---

    def align(self, theorem: Theorem, proof: Proof) -> Dict[str, Any]:
        entry = self._enc.get(theorem.name)
        expected = self._enc.concepts_for(entry) if entry else (
            list(theorem.keywords) + theorem.domain.replace("_", " ").split()
        )
        expected = [c.lower() for c in expected]
        hay = _tokens(theorem.informal) | _tokens(theorem.lean_statement or "") | \
            _tokens(proof.lean_tactics or "") | _tokens(proof.informal or "")

        def _hit(concept: str) -> bool:
            # exact token match, or a shared 4-char prefix (e.g. "addition" ~ "add")
            return any(concept == h or (len(concept) >= 4 and len(h) >= 4 and concept[:4] == h[:4])
                       for h in hay)

        matched = [c for c in expected if _hit(c)]
        missing = [c for c in expected if not _hit(c)]
        denom = max(len(expected), 1)
        score = round(len(matched) / denom, 3)
        rationale = (
            f"Concept overlap {len(matched)}/{len(expected)} between the proof and the "
            f"encyclopedia entry for '{theorem.name}'."
        )
        # A proof that reproduces the encyclopedia's known-good proof is a strong
        # alignment signal even when the concept vocabulary is sparse.
        known_good = (entry or {}).get("lean_proof", "").strip()
        if known_good and (proof.lean_tactics or "").strip() == known_good:
            score = min(1.0, round(score + 0.5, 3))
            rationale += " Boosted: proof reproduces the certified encyclopedia proof."
        return {
            "score": score,
            "matched_concepts": matched,
            "missing_concepts": missing,
            "rationale": rationale,
        }

    # --- read (graded tiers) ---

    def read_tier(self, theorem: Theorem, proof: Proof, tier: Difficulty) -> Dict[str, Any]:
        tactics = (proof.lean_tactics or "").strip()
        comments: List[str] = []
        verdict = "warn"

        if tier is Difficulty.EASY:
            if not tactics:
                verdict, comments = "fail", ["No formal proof supplied."]
            elif tactics.lower().startswith("by sorry") or "sorry" in tactics:
                verdict, comments = "fail", ["Proof uses `sorry` (an admitted goal)."]
            elif tactics.startswith("by ") or tactics.startswith("rfl") or "=" not in tactics:
                verdict = "pass"
                comments = ["Well-formed tactic block; surface syntax looks fine."]
            else:
                verdict = "warn"
                comments = ["Proof term present; verify it has the expected type."]

        elif tier is Difficulty.MEDIUM:
            entry = self._enc.get(theorem.name)
            known_good = (entry or {}).get("lean_proof", "").strip()
            if known_good and tactics == known_good:
                verdict = "pass"
                comments = ["Tactic sequence matches the known-good proof; logic flow is sound."]
            elif "rw [" in tactics or "simp" in tactics or "induction" in tactics:
                verdict = "pass"
                comments = ["Uses a recognised rewriting/simplification step; intermediate goals likely resolve."]
            else:
                verdict = "warn"
                comments = ["Could not confirm each tactic's preconditions; review the goal sequence."]

        else:  # HARD
            entry = self._enc.get(theorem.name)
            known_good = (entry or {}).get("lean_proof", "").strip()
            if known_good and tactics == known_good:
                verdict = "pass"
                comments = [
                    "Proof matches the certified encyclopedia proof.",
                    "Minimal and conceptually faithful; edge cases covered by the general statement.",
                ]
            elif not tactics:
                verdict = "fail"
                comments = ["No proof to assess at the hardest tier."]
            else:
                verdict = "warn"
                comments = [
                    "Plausible but not independently verified at the deep tier.",
                    "Recommend a full formal (Lean) check before trusting.",
                ]

        return {"tier": tier.value, "verdict": verdict, "comments": comments}


# Heuristics for the stub prover ------------------------------------------------

def _tokens(s: str) -> set:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", (s or "").lower()))


def _shape_of(theorem: Theorem) -> str:
    """Coarse shape of a Lean statement, to pick template tactics."""
    s = (theorem.lean_statement or "").lower()
    if "∀" in s or "forall" in s or "exists" in s or "∃" in s:
        return "quantified"
    if re.search(r"\d+\s*([+\-*/^])\s*\d*\s*=", s) or re.search(r"=\s*\d", s):
        return "numeric"
    if "<" in s or ">" in s or "≤" in s or "≥" in s:
        return "inequality"
    if "∪" in s or "∪" in s or "set" in s:
        return "set"
    return "algebraic"


_TEMPLATES: Dict[str, List[str]] = {
    "numeric": ["by rfl", "by decide", "by norm_num"],
    "algebraic": ["by rw [Nat.add_comm]", "by ring", "by simp"],
    "inequality": ["by omega", "by linarith", "by simp"],
    "quantified": ["by simp", "by aesop", "by intro"],
    "set": ["by ext; simp", "by simp [Set.or_self]", "by aesop"],
}


# ============================================================================
# HuggingFace backend (local model) — lazy heavy imports
# ============================================================================

class HFBackend(BaseBackend):
    """Loads a local causal-LM via transformers and samples real completions."""

    name = "hf"

    def __init__(self, cfg: Optional[EngineConfig] = None):
        super().__init__(cfg)
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except ImportError as exc:  # pragma: no cover - needs heavy deps
            raise ImportError(
                "HFBackend needs torch + transformers. "
                "Install with: pip install -r leibniz/training/requirements.txt"
            ) from exc
        self._torch = torch
        dev = self.cfg.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = dev
        tok_kwargs = {"token": self.cfg.hf_token} if self.cfg.hf_token else {}
        self.tokenizer = AutoTokenizer.from_pretrained(self.cfg.model, **tok_kwargs)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.cfg.model, torch_dtype="auto", **tok_kwargs
        ).to(dev)
        self.model.eval()

    # --- core generation ---

    def _generate(self, prompt: str, n: int = 1) -> List[str]:
        import torch  # type: ignore
        enc = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model.generate(
                **enc,
                max_new_tokens=self.cfg.max_new_tokens,
                do_sample=n > 1 or self.cfg.temperature > 0,
                temperature=max(self.cfg.temperature, 1e-2),
                num_return_sequences=n,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        texts = []
        for seq in out:
            gen = seq[enc["input_ids"].shape[-1]:]
            texts.append(self.tokenizer.decode(gen, skip_special_tokens=True))
        return texts

    # --- stage methods ---

    def discover(self, seed: str, n: int) -> List[Dict[str, Any]]:
        obj = self._parse_json(self._generate(prompts.discover_prompt(seed, n))[0])
        return list(obj.get("conjectures", []))[:n]

    def prove(self, theorem: Theorem, k: int) -> List[str]:
        # request k distinct proofs in one call
        obj = self._parse_json(self._generate(prompts.prove_prompt(theorem, k))[0])
        proofs = [str(p).strip() for p in obj.get("proofs", []) if str(p).strip()]
        if not proofs:  # fallback: k independent samples
            proofs = [p.strip() for p in self._generate(prompts.prove_prompt(theorem, 1), n=k)]
        return proofs[:k] or ["by sorry"]

    def align(self, theorem: Theorem, proof: Proof) -> Dict[str, Any]:
        obj = self._parse_json(self._generate(prompts.align_prompt(theorem, proof))[0])
        return {
            "score": float(obj.get("score", 0.0)),
            "matched_concepts": list(obj.get("matched", [])),
            "missing_concepts": list(obj.get("missing", [])),
            "rationale": str(obj.get("rationale", "")),
        }

    def read_tier(self, theorem: Theorem, proof: Proof, tier: Difficulty) -> Dict[str, Any]:
        obj = self._parse_json(self._generate(prompts.read_prompt(theorem, proof, tier))[0])
        verdict = str(obj.get("verdict", "warn")).lower()
        if verdict not in ("pass", "warn", "fail"):
            verdict = "warn"
        return {
            "tier": tier.value,
            "verdict": verdict,
            "comments": [str(c) for c in obj.get("comments", [])],
        }


# ============================================================================
# Remote backend (HF Inference API / OpenAI-compatible) — lazy requests
# ============================================================================

class RemoteBackend(BaseBackend):
    """Calls a hosted text-generation endpoint (HF Inference API style)."""

    name = "remote"

    def __init__(self, cfg: Optional[EngineConfig] = None):
        super().__init__(cfg)
        try:
            import requests  # type: ignore  # noqa: F401
        except ImportError as exc:  # pragma: no cover - needs requests
            raise ImportError("RemoteBackend needs `requests`. pip install requests") from exc
        from ..config import config as _c
        self._requests = requests
        if not self.cfg.remote_url:
            raise ValueError("RemoteBackend requires LEIBNIZ_REMOTE_URL (and LEIBNIZ_MODEL).")
        self.base = self.cfg.remote_url.rstrip("/")

    def _generate(self, prompt: str) -> str:
        url = f"{self.base}/models/{self.cfg.model}"
        headers = {"Content-Type": "application/json"}
        if self.cfg.hf_token:
            headers["Authorization"] = f"Bearer {self.cfg.hf_token}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": self.cfg.max_new_tokens,
                "temperature": max(self.cfg.temperature, 1e-2),
                "return_full_text": False,
            },
            "options": {"wait_for_model": True},
        }
        resp = self._requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # HF inference returns [{"generated_text": "..."}]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0].get("generated_text", "")
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        return json.dumps(data)

    def discover(self, seed: str, n: int) -> List[Dict[str, Any]]:
        return list(self._parse_json(self._generate(prompts.discover_prompt(seed, n))).get("conjectures", []))[:n]

    def prove(self, theorem: Theorem, k: int) -> List[str]:
        proofs = self._parse_json(self._generate(prompts.prove_prompt(theorem, k))).get("proofs", [])
        return [str(p).strip() for p in proofs if str(p).strip()][:k] or ["by sorry"]

    def align(self, theorem: Theorem, proof: Proof) -> Dict[str, Any]:
        obj = self._parse_json(self._generate(prompts.align_prompt(theorem, proof)))
        return {
            "score": float(obj.get("score", 0.0)),
            "matched_concepts": list(obj.get("matched", [])),
            "missing_concepts": list(obj.get("missing", [])),
            "rationale": str(obj.get("rationale", "")),
        }

    def read_tier(self, theorem: Theorem, proof: Proof, tier: Difficulty) -> Dict[str, Any]:
        obj = self._parse_json(self._generate(prompts.read_prompt(theorem, proof, tier)))
        verdict = str(obj.get("verdict", "warn")).lower()
        if verdict not in ("pass", "warn", "fail"):
            verdict = "warn"
        return {"tier": tier.value, "verdict": verdict, "comments": [str(c) for c in obj.get("comments", [])]}


# ============================================================================
# Factory
# ============================================================================

def get_backend(cfg: Optional[EngineConfig] = None) -> BaseBackend:
    """Return the backend selected by cfg.backend (env: LEIBNIZ_BACKEND)."""
    cfg = cfg or default_config
    kind = (cfg.backend or "stub").lower()
    if kind == "stub":
        return StubBackend(cfg)
    if kind == "hf":
        return HFBackend(cfg)
    if kind == "remote":
        return RemoteBackend(cfg)
    raise ValueError(f"Unknown backend '{kind}'. Use one of: stub, hf, remote.")
