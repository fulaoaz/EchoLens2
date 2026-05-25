"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_ENV_LOADED = False


def _load_env_once() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(override=False)
    _ENV_LOADED = True


@dataclass(frozen=True)
class Settings:
    """Strongly-typed settings consumed by the Flask app and CLI tools."""

    llm_api_key: str
    llm_base_url: str
    llm_model_name: str
    kuzu_db_path: str
    duckdb_path: str
    upload_dir: str
    log_level: str
    allowed_origins: tuple[str, ...]

    def ensure_dirs(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.kuzu_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def cors_origins_value(self) -> str | list[str]:
        """Value to pass to flask-cors `origins=`.

        - Empty tuple → `"*"` (development, permissive)
        - Non-empty   → list[str] (production, strict whitelist)
        """
        if not self.allowed_origins:
            return "*"
        return list(self.allowed_origins)


def _required_for_runtime() -> tuple[str, ...]:
    # LLM_API_KEY is required when not testing; the test fixture sets a dummy value.
    return ("LLM_BASE_URL", "LLM_MODEL_NAME")


def _validate(settings: Settings) -> None:
    """Light validation; empties are tolerated only in TESTING contexts."""
    if os.environ.get("ECHOLENS_SKIP_ENV_VALIDATION") == "1":
        return
    missing = [k for k in _required_for_runtime() if not getattr(settings, k.lower())]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in values."
        )
    # LLM_API_KEY is "soft required" — warn but do not crash, so tests/CI can run.
    if not settings.llm_api_key:
        # Logging not yet configured; print so it surfaces during boot.
        print("[echolens2] WARNING: LLM_API_KEY is empty; LLM-dependent endpoints will fail.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_once()
    raw_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
    origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
    settings = Settings(
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        llm_base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model_name=os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
        kuzu_db_path=os.environ.get("KUZU_DB_PATH", "./data/kuzu_db"),
        duckdb_path=os.environ.get("DUCKDB_PATH", "./data/echolens.duckdb"),
        upload_dir=os.environ.get("UPLOAD_DIR", "./data/uploads"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        allowed_origins=origins,
    )
    _validate(settings)
    return settings


__all__ = ["Settings", "get_settings"]
