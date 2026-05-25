"""Shared test fixtures."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Set non-interactive defaults BEFORE importing app code.
_TMP_TEST_ROOT = Path(tempfile.mkdtemp(prefix="echolens2-test-"))
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("LLM_MODEL_NAME", "test-model")
os.environ["KUZU_DB_PATH"] = str(_TMP_TEST_ROOT / "kuzu_db")
os.environ["DUCKDB_PATH"] = str(_TMP_TEST_ROOT / "test.duckdb")
os.environ["UPLOAD_DIR"] = str(_TMP_TEST_ROOT / "uploads")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ECHOLENS_SKIP_ENV_VALIDATION", "1")


@pytest.fixture(scope="session")
def app() -> Iterator[Any]:
    from app import create_app
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    app = create_app({"TESTING": True})
    yield app


@pytest.fixture
def client(app: Any) -> Any:
    return app.test_client()


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:  # noqa: ARG001
    shutil.rmtree(_TMP_TEST_ROOT, ignore_errors=True)
