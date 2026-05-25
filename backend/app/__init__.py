"""EchoLens 2.0 Flask application factory."""

from __future__ import annotations

import logging
import time
from typing import Any

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS

from app.config import Settings, get_settings

_VERSION = "0.1.0"


def _check_duckdb(settings: Settings) -> dict[str, Any]:
    """Probe DuckDB with `SELECT 1`. Non-fatal."""
    try:
        from app.services.duckdb_store import connect

        with connect() as conn:
            row = conn.execute("SELECT 1").fetchone()
        ok = bool(row and row[0] == 1)
        return {"ok": ok, "path": settings.duckdb_path}
    except Exception as exc:  # noqa: BLE001 — health probes never raise
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}


def _check_llm(settings: Settings) -> dict[str, Any]:
    """Configuration-only probe — does NOT call out to the LLM."""
    return {
        "configured": bool(settings.llm_api_key),
        "base_url": settings.llm_base_url,
        "model": settings.llm_model_name,
    }


def _check_cors(settings: Settings, cors_origins: str | list[str]) -> dict[str, Any]:
    if cors_origins == "*":
        return {"mode": "wildcard", "allowlist_size": 0}
    return {"mode": "allowlist", "allowlist_size": len(settings.allowed_origins)}


def _build_health_payload(
    settings: Settings, cors_origins: str | list[str]
) -> dict[str, Any]:
    """Compose multi-channel health payload.

    Status semantics
    ----------------
    - ``ok``       — DB reachable, LLM configured.
    - ``degraded`` — DB reachable but LLM not configured (or other soft fail).
                     Still returns HTTP 200; the front-end / CI can warn.
    - ``error``    — DB unreachable. Still returns HTTP 200 (caller decides);
                     callers needing a hard liveness signal should check
                     ``checks.duckdb.ok``.
    """
    duckdb_check = _check_duckdb(settings)
    llm_check = _check_llm(settings)
    cors_check = _check_cors(settings, cors_origins)

    if not duckdb_check["ok"]:
        status = "error"
    elif not llm_check["configured"]:
        status = "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "service": "echolens2-backend",
        "version": _VERSION,
        "checks": {
            "duckdb": duckdb_check,
            "llm": llm_check,
            "cors": cors_check,
        },
    }


def _configure_logging(app: Flask, level: str) -> None:
    """Wire app.logger into a sane stream handler with a uniform format."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    log_level = getattr(logging, level.upper(), logging.INFO)
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    logging.getLogger("werkzeug").setLevel(log_level)


def _register_request_logging(app: Flask) -> None:
    @app.before_request
    def _start_timer() -> None:
        g.request_start = time.perf_counter()
        app.logger.info("→ %s %s", request.method, request.path)

    @app.after_request
    def _log_response(response: Response) -> Response:
        start = getattr(g, "request_start", None)
        elapsed_ms = (time.perf_counter() - start) * 1000 if start else 0.0
        app.logger.info(
            "← %s %s %s %.1fms",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response


def _register_blueprints(app: Flask) -> None:
    from app.api.crawler import bp as crawler_bp
    from app.api.decision import bp as decision_bp
    from app.api.prediction import bp as prediction_bp
    from app.api.projects import bp as projects_bp
    from app.api.report import bp as report_bp
    from app.api.simulation import bp as simulation_bp

    for bp in (
        projects_bp,
        crawler_bp,
        simulation_bp,
        prediction_bp,
        decision_bp,
        report_bp,
    ):
        app.register_blueprint(bp)


def create_app(config_overrides: dict[str, Any] | None = None) -> Flask:
    """Build and configure the Flask app instance."""
    settings = get_settings()
    app = Flask(__name__)
    app.config.from_mapping(
        LLM_API_KEY=settings.llm_api_key,
        LLM_BASE_URL=settings.llm_base_url,
        LLM_MODEL_NAME=settings.llm_model_name,
        KUZU_DB_PATH=settings.kuzu_db_path,
        DUCKDB_PATH=settings.duckdb_path,
        UPLOAD_DIR=settings.upload_dir,
        LOG_LEVEL=settings.log_level,
        ALLOWED_ORIGINS=settings.allowed_origins,
        TESTING=False,
    )
    if config_overrides:
        app.config.update(config_overrides)

    cors_origins = settings.cors_origins_value
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
    )

    _configure_logging(app, app.config["LOG_LEVEL"])
    _register_request_logging(app)
    _register_blueprints(app)

    if cors_origins == "*":
        app.logger.warning(
            "CORS allowed_origins is wildcard '*'. "
            "Set ALLOWED_ORIGINS in production to a strict whitelist."
        )
    else:
        app.logger.info("CORS allowed_origins: %s", cors_origins)

    @app.get("/health")
    def health() -> Response:
        return jsonify(_build_health_payload(settings, cors_origins))

    app.logger.info("EchoLens 2.0 backend initialized.")
    return app


__all__ = ["create_app"]
