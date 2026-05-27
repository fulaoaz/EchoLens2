"""Runtime settings API contract tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.api import settings as settings_api
from app.config import get_settings


def _reset_runtime(monkeypatch: Any, env_path: Path, api_key: str = "saved-key") -> None:
    monkeypatch.setattr(settings_api, "_ENV_PATH", env_path)
    monkeypatch.setenv("LLM_API_KEY", api_key)
    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("LLM_MODEL_NAME", "provider-model")
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_get_runtime_settings_never_returns_api_key(client: Any, monkeypatch: Any, tmp_path: Path) -> None:
    _reset_runtime(monkeypatch, tmp_path / ".env")

    resp = client.get("/api/settings")

    assert resp.status_code == 200
    payload = resp.get_json()
    data = payload["data"]
    assert payload["success"] is True
    assert data == {
        "llm_base_url": "https://provider.example/v1",
        "llm_model_name": "provider-model",
        "llm_api_key_configured": True,
    }
    assert "llm_api_key" not in data


def test_update_runtime_settings_persists_values_without_echoing_key(
    client: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    _reset_runtime(monkeypatch, env_path)

    resp = client.put(
        "/api/settings",
        json={
            "llm_base_url": "https://new-provider.example/v1",
            "llm_model_name": "new-model",
            "llm_api_key": "new-secret-key",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["llm_base_url"] == "https://new-provider.example/v1"
    assert data["llm_model_name"] == "new-model"
    assert data["llm_api_key_configured"] is True
    assert "llm_api_key" not in data
    assert os.environ["LLM_API_KEY"] == "new-secret-key"
    env_text = env_path.read_text(encoding="utf-8")
    assert "LLM_API_KEY" in env_text
    assert "new-secret-key" in env_text


def test_update_runtime_settings_blank_key_keeps_existing_key(
    client: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    _reset_runtime(monkeypatch, env_path, api_key="existing-secret")

    resp = client.put(
        "/api/settings",
        json={
            "llm_base_url": "https://blank-key.example/v1",
            "llm_model_name": "blank-key-model",
            "llm_api_key": "   ",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["llm_base_url"] == "https://blank-key.example/v1"
    assert data["llm_model_name"] == "blank-key-model"
    assert data["llm_api_key_configured"] is True
    assert os.environ["LLM_API_KEY"] == "existing-secret"
    env_text = env_path.read_text(encoding="utf-8")
    assert "LLM_API_KEY" not in env_text


def test_update_runtime_settings_rejects_untrusted_browser_origin(
    client: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    _reset_runtime(monkeypatch, tmp_path / ".env")

    resp = client.put(
        "/api/settings",
        headers={"Origin": "https://evil.example"},
        json={
            "llm_base_url": "https://attacker.example/v1",
            "llm_model_name": "attacker-model",
        },
    )

    assert resp.status_code == 403
    assert os.environ["LLM_BASE_URL"] == "https://provider.example/v1"
    assert os.environ["LLM_MODEL_NAME"] == "provider-model"


def test_update_runtime_settings_validation_error_does_not_echo_secret(
    client: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    _reset_runtime(monkeypatch, tmp_path / ".env")
    secret = "x" * 2001

    resp = client.put(
        "/api/settings",
        json={
            "llm_base_url": "https://provider.example/v1",
            "llm_model_name": "provider-model",
            "llm_api_key": secret,
        },
    )

    assert resp.status_code == 400
    body = resp.get_data(as_text=True)
    assert secret not in body
    assert "llm_api_key" in body
