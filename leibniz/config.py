"""
Configuration Module
====================
Central, environment-overridable configuration for the Leibniz engine.
Mirrors the style of rh_services/config.py (dataclass + env overrides + global instance).
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EngineConfig:
    """Master configuration for the Leibniz engine."""

    # --- LLM backend ---
    # stub : deterministic, no deps (default; always works)
    # hf   : local HuggingFace causal-LM (needs torch+transformers)
    # remote : call an OpenAI-compatible / HF Inference endpoint (needs requests)
    backend: str = "stub"
    model: str = "Qwen/Qwen2.5-Math-1.5B-Instruct"
    remote_url: Optional[str] = None          # e.g. https://api-inference.huggingface.co
    hf_token: Optional[str] = None            # HF access token (for private/gated models)
    device: Optional[str] = None              # None -> autodetect (cuda if available else cpu)
    temperature: float = 0.7
    max_new_tokens: int = 512
    sample_k: int = 4                         # number of candidate proofs to sample per theorem

    # --- Formal verification (Lean) ---
    lean_cmd: str = "lean"                    # executable name resolved on PATH
    lake_cmd: str = "lake"
    lean_timeout_s: float = 30.0              # per-proof compile timeout

    # --- Pipeline ---
    max_conjectures: int = 5                  # discoveries per seed
    encyclopedia_path: Optional[str] = None   # override path to encyclopedia data.json

    # --- API host (api/) ---
    api_host: str = "0.0.0.0"
    api_port: int = 8430                      # distinct from RH services (8420)
    api_workers: int = 2
    cors_allow_all: bool = True

    def __post_init__(self):
        if self.encyclopedia_path is None:
            self.encyclopedia_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "encyclopedia", "data.json",
            )


# --- Environment overrides ---

def load_config() -> EngineConfig:
    """Load configuration from environment variables with sensible defaults."""
    cfg = EngineConfig()

    env_map = {
        "LEIBNIZ_BACKEND": ("backend", str),
        "LEIBNIZ_MODEL": ("model", str),
        "LEIBNIZ_REMOTE_URL": ("remote_url", str),
        "LEIBNIZ_HF_TOKEN": ("hf_token", str),
        "LEIBNIZ_DEVICE": ("device", str),
        "LEIBNIZ_TEMPERATURE": ("temperature", float),
        "LEIBNIZ_MAX_NEW_TOKENS": ("max_new_tokens", int),
        "LEIBNIZ_SAMPLE_K": ("sample_k", int),
        "LEIBNIZ_LEAN_CMD": ("lean_cmd", str),
        "LEIBNIZ_LAKE_CMD": ("lake_cmd", str),
        "LEIBNIZ_LEAN_TIMEOUT": ("lean_timeout_s", float),
        "LEIBNIZ_MAX_CONJECTURES": ("max_conjectures", int),
        "LEIBNIZ_API_HOST": ("api_host", str),
        "LEIBNIZ_API_PORT": ("api_port", int),
        "LEIBNIZ_API_WORKERS": ("api_workers", int),
    }

    for env_var, (attr, cast) in env_map.items():
        val = os.environ.get(env_var)
        if val is not None and val != "":
            try:
                setattr(cfg, attr, cast(val))
            except (TypeError, ValueError):
                # Ignore malformed env values; keep the default.
                pass

    # HF token often lives in the conventional env var too.
    if cfg.hf_token is None:
        cfg.hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    return cfg


# Global config instance
config = load_config()
