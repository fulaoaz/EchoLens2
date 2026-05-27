"""Runtime settings API for desktop/mobile clients."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import set_key
from flask import Blueprint, Response, current_app, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import get_settings

bp = Blueprint("settings", __name__, url_prefix="/api/settings")

_ENV_PATH = Path(os.environ.get("ECHOLENS_ENV_FILE", ".env"))


class RuntimeSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    llm_base_url: str = Field(..., min_length=1, max_length=500)
    llm_model_name: str = Field(..., min_length=1, max_length=200)
    llm_api_key: str | None = Field(default=None, max_length=2000)


def _ok(data: object, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


def _validation_message(exc: ValidationError) -> str:
    fields = sorted({".".join(str(part) for part in err["loc"]) for err in exc.errors()})
    return f"请求参数无效：{', '.join(fields)}" if fields else "请求参数无效"


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname in {"127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _is_trusted_origin(origin: str | None) -> bool:
    if not origin:
        return True
    parsed = urlparse(origin)
    if parsed.scheme in {"tauri", "capacitor"}:
        return True
    if parsed.scheme in {"http", "https"} and _is_loopback_host(parsed.hostname):
        return True
    settings = get_settings()
    return origin in settings.allowed_origins


def _public_settings() -> dict[str, object]:
    settings = get_settings()
    return {
        "llm_base_url": settings.llm_base_url,
        "llm_model_name": settings.llm_model_name,
        "llm_api_key_configured": bool(settings.llm_api_key),
    }


def _persist_env(updates: dict[str, str]) -> None:
    _ENV_PATH.touch(exist_ok=True)
    for key, value in updates.items():
        set_key(str(_ENV_PATH), key, value)
        os.environ[key] = value


@bp.get("")
@bp.get("/")
def get_runtime_settings() -> tuple[Response, int]:
    return _ok(_public_settings())


@bp.put("")
@bp.put("/")
def update_runtime_settings() -> tuple[Response, int]:
    if not _is_trusted_origin(request.headers.get("Origin")):
        return _err("不允许从当前来源修改运行时配置", 403)

    raw = request.get_json(silent=True) or {}
    try:
        payload = RuntimeSettingsIn.model_validate(raw)
    except ValidationError as exc:
        return _err(_validation_message(exc), 400)

    updates = {
        "LLM_BASE_URL": payload.llm_base_url,
        "LLM_MODEL_NAME": payload.llm_model_name,
    }
    if payload.llm_api_key is not None and payload.llm_api_key.strip():
        updates["LLM_API_KEY"] = payload.llm_api_key.strip()

    _persist_env(updates)
    get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = get_settings()
    current_app.config.update(
        LLM_API_KEY=settings.llm_api_key,
        LLM_BASE_URL=settings.llm_base_url,
        LLM_MODEL_NAME=settings.llm_model_name,
    )
    return _ok(_public_settings())
