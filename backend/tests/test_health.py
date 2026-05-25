"""Health endpoint multi-channel check (M6.4)."""

from __future__ import annotations

from typing import Any


def test_health_ok_shape(client: Any) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.get_json()
    # Top-level shape
    assert payload["service"] == "echolens2-backend"
    assert "version" in payload
    assert payload["status"] in {"ok", "degraded", "error"}
    # Multi-channel checks block
    checks = payload["checks"]
    assert "duckdb" in checks
    assert "llm" in checks
    assert "cors" in checks


def test_health_duckdb_reachable(client: Any) -> None:
    """In tests we use a temp DuckDB path — it must be reachable."""
    resp = client.get("/health")
    body = resp.get_json()
    assert body["checks"]["duckdb"]["ok"] is True
    assert body["checks"]["duckdb"]["path"].endswith(".duckdb")


def test_health_llm_reports_configuration(client: Any) -> None:
    """LLM probe is config-only (no outbound call). conftest sets a dummy key."""
    resp = client.get("/health")
    body = resp.get_json()
    llm = body["checks"]["llm"]
    assert llm["configured"] is True  # conftest sets LLM_API_KEY=test-key
    assert llm["base_url"]
    assert llm["model"]


def test_health_cors_reports_mode(client: Any) -> None:
    """ALLOWED_ORIGINS empty in tests → wildcard mode."""
    resp = client.get("/health")
    body = resp.get_json()
    cors = body["checks"]["cors"]
    assert cors["mode"] in {"wildcard", "allowlist"}
    assert isinstance(cors["allowlist_size"], int)
