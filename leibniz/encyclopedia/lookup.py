"""
Encyclopedia — retrievable knowledge base of verified thoughts
==============================================================
Leibniz's second pillar. A tiny built-in JSON knowledge base (data.json)
provides ground-truth theorems with informal statements, Lean 4 statements,
proofs, domains, and keyword concepts.

Used by:
    * StubBackend.discover  (seed -> matching conjectures)
    * StubBackend.prove     (known-good proof hints)
    * the alignment gate     (concept lookup)
    * the verify stage       (provisional pattern-match fallback)

It is intentionally a plain JSON file so it can grow without code changes.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


class Encyclopedia:
    """In-memory index over the knowledge base."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or _DEFAULT_PATH
        with open(self.path, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
        self.meta = {k: v for k, v in blob.items() if k != "entries"}
        self.entries: List[Dict] = list(blob.get("entries", []))
        self._by_name: Dict[str, Dict] = {e["name"]: e for e in self.entries}

    # --- accessors ---

    def all(self) -> List[Dict]:
        return list(self.entries)

    def get(self, name: str) -> Optional[Dict]:
        return self._by_name.get(name)

    def concepts_for(self, entry: Dict) -> List[str]:
        """The concept tokens for an entry (keywords + domain words)."""
        tokens: List[str] = list(entry.get("keywords", []))
        tokens.extend(entry.get("domain", "").replace("_", " ").split())
        # de-duplicate preserving order, lowercase
        seen, out = set(), []
        for t in tokens:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # --- retrieval ---

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Keyword-scored retrieval: matches on name, domain, keywords, informal text."""
        q = _tokenize(query)
        if not q:
            return list(self.entries[:limit])

        scored: List[tuple] = []
        for e in self.entries:
            hay = set()
            hay.update(_tokenize(e.get("name", "")))
            hay.update(_tokenize(e.get("domain", "")))
            hay.update(t.lower() for t in e.get("keywords", []))
            hay.update(_tokenize(e.get("informal", "")))
            score = sum(1 for tok in q if tok in hay)
            # Exact name match gets a large boost so `search("add_smul_vec")`
            # always returns add_smul_vec first, even when keywords overlap.
            if e.get("name", "").lower() == query.lower():
                score += 100
            elif query.lower() in e.get("name", "").lower():
                score += 50
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: (-x[0], self.entries.index(x[1])))
        return [e for _, e in scored[:limit]]


def _tokenize(s: str) -> List[str]:
    """Lowercase alphanumeric tokens."""
    out, cur = [], []
    for ch in (s or "").lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


# --- module-level default instance (lazy) ---

_default: Optional[Encyclopedia] = None


def default() -> Encyclopedia:
    """Return a process-wide default Encyclopedia (lazily loaded)."""
    global _default
    if _default is None:
        _default = Encyclopedia()
    return _default
