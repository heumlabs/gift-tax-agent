"""Configuration helpers for the AI chat prototype."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_INITIALISED = False


def _ensure_env_loaded() -> None:
    """Load .env files (root, backend) once so CLI usage matches backend config."""
    global _ENV_INITIALISED
    if _ENV_INITIALISED:
        return

    for candidate in (Path(".env"), Path("backend/.env")):
        if candidate.exists():
            load_dotenv(candidate, override=False)

    _ENV_INITIALISED = True


def _read_env(key: str, default: str = "") -> str:
    _ensure_env_loaded()
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else default


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    model: str = "gemini-2.5-flash"
    request_timeout: float = 30.0
    base_url: str = "https://generativelanguage.googleapis.com"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    embedding_batch_size: int = 100
    # Law search settings
    law_search_table: str = "law_sources_v3"
    law_search_keyword_weight: float = 0.3
    law_search_embedding_weight: float = 0.7

    @classmethod
    def from_env(cls) -> "GeminiSettings":
        api_key = _read_env("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")

        model = _read_env("GEMINI_MODEL", cls.model)
        timeout_raw = _read_env("GEMINI_TIMEOUT_SECONDS", str(cls.request_timeout))

        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = cls.request_timeout

        # Embedding settings (optional overrides)
        embedding_model = _read_env("GEMINI_EMBEDDING_MODEL", cls.embedding_model)
        embedding_dim_raw = _read_env("GEMINI_EMBEDDING_DIMENSION", str(cls.embedding_dimension))
        try:
            embedding_dim = int(embedding_dim_raw)
        except ValueError:
            embedding_dim = cls.embedding_dimension

        # Law search settings (optional overrides)
        law_search_table = _read_env("LAW_SEARCH_TABLE", cls.law_search_table)
        law_kw_weight_raw = _read_env("LAW_SEARCH_KEYWORD_WEIGHT", str(cls.law_search_keyword_weight))
        law_emb_weight_raw = _read_env("LAW_SEARCH_EMBEDDING_WEIGHT", str(cls.law_search_embedding_weight))

        try:
            law_kw_weight = float(law_kw_weight_raw)
        except ValueError:
            law_kw_weight = cls.law_search_keyword_weight

        try:
            law_emb_weight = float(law_emb_weight_raw)
        except ValueError:
            law_emb_weight = cls.law_search_embedding_weight

        return cls(
            api_key=api_key,
            model=model,
            request_timeout=timeout,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dim,
            law_search_table=law_search_table,
            law_search_keyword_weight=law_kw_weight,
            law_search_embedding_weight=law_emb_weight,
        )

    @property
    def endpoint(self) -> str:
        model_name = self.model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        base = self.base_url.rstrip("/")
        return f"{base}/v1beta/{model_name}:generateContent"

    @property
    def embedding_endpoint(self) -> str:
        """Endpoint for single embedding generation."""
        base = self.base_url.rstrip("/")
        return f"{base}/v1beta/models/{self.embedding_model}:embedContent"

    @property
    def embedding_batch_endpoint(self) -> str:
        """Endpoint for batch embedding generation."""
        base = self.base_url.rstrip("/")
        return f"{base}/v1beta/models/{self.embedding_model}:batchEmbedContents"
