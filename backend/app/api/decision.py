"""/api/decision blueprint — fused simulation + prediction snapshot.

Endpoints
---------
- GET /api/decision/<project_id>/snapshot
    Aggregate latest finished simulation + latest forecast/causal runs into a
    single decision payload with rules-based risk score and recommendations.
- GET /api/decision/ping
    Liveness check.
"""

from __future__ import annotations

from flask import Blueprint, Response, jsonify

from app.services.decision_engine import build_snapshot
from app.services.project_store import get_store

bp = Blueprint("decision", __name__, url_prefix="/api/decision")


def _ok(data: object, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "decision", "implemented": True})


@bp.get("/<project_id>/snapshot")
def snapshot(project_id: str) -> tuple[Response, int]:
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    return _ok(build_snapshot(project_id))
