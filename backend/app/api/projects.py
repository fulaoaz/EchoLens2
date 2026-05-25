"""/api/projects blueprint — project CRUD + raw-record ingest + seed report.

Endpoints
---------

- POST   /api/projects                — create project
- GET    /api/projects                — list projects
- GET    /api/projects/<id>           — fetch one project
- DELETE /api/projects/<id>           — delete project (cascades raw records)
- POST   /api/projects/<id>/seed_data — bulk-load demo records (products / reviews / posts)
- GET    /api/projects/<id>/seed_report — aggregate persisted records into a SeedReport
- GET    /api/projects/ping           — liveness check
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.crawler.seed_report import build_seed_report
from app.models.project import Project
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store

bp = Blueprint("projects", __name__, url_prefix="/api/projects")


class CreateProjectIn(BaseModel):
    """Inbound payload for POST /api/projects."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    target_platforms: list[str] = Field(default_factory=list)


class SeedDataIn(BaseModel):
    """Inbound payload for POST /api/projects/<id>/seed_data."""

    model_config = ConfigDict(extra="forbid")

    products: list[dict[str, Any]] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    posts: list[dict[str, Any]] = Field(default_factory=list)


def _ok(data: object, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "projects", "implemented": True})


@bp.post("")
@bp.post("/")
def create_project() -> tuple[Response, int]:
    raw = request.get_json(silent=True) or {}
    try:
        payload = CreateProjectIn.model_validate(raw)
    except ValidationError as exc:
        return _err(str(exc), 400)
    project = Project(**payload.model_dump())
    get_store().create(project)
    return _ok(project.model_dump(mode="json"), 201)


@bp.get("")
@bp.get("/")
def list_projects() -> tuple[Response, int]:
    items = [p.model_dump(mode="json") for p in get_store().list()]
    return _ok({"items": items, "count": len(items)})


@bp.get("/<project_id>")
def get_project(project_id: str) -> tuple[Response, int]:
    p = get_store().get(project_id)
    if not p:
        return _err(f"project {project_id!r} not found", 404)
    return _ok(p.model_dump(mode="json"))


@bp.delete("/<project_id>")
def delete_project(project_id: str) -> tuple[Response, int]:
    get_crawler_store().delete_for_project(project_id)
    ok = get_store().delete(project_id)
    if not ok:
        return _err(f"project {project_id!r} not found", 404)
    return _ok({"deleted": project_id})


@bp.post("/<project_id>/seed_data")
def ingest_seed_data(project_id: str) -> tuple[Response, int]:
    """Bulk-load raw records for a project. Accepts products/reviews/posts arrays."""
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    raw = request.get_json(silent=True) or {}
    try:
        payload = SeedDataIn.model_validate(raw)
    except ValidationError as exc:
        return _err(str(exc), 400)
    crawler = get_crawler_store()
    counts = {
        "products": crawler.upsert_many(project_id, "product", payload.products),
        "reviews": crawler.upsert_many(project_id, "review", payload.reviews),
        "posts": crawler.upsert_many(project_id, "post", payload.posts),
    }
    # Bump project status to seed_ready if any data was ingested.
    if any(counts.values()):
        get_store().update(project_id, status="seed_ready")
    return _ok({"ingested": counts}, 201)


@bp.get("/<project_id>/seed_report")
def seed_report(project_id: str) -> tuple[Response, int]:
    """Compute a SeedReport from persisted records for ``project_id``."""
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    crawler = get_crawler_store()
    report = build_seed_report(
        project_id,
        products=crawler.list_for_project(project_id, "product"),
        reviews=crawler.list_for_project(project_id, "review"),
        posts=crawler.list_for_project(project_id, "post"),
        now=datetime.utcnow(),
    )
    return _ok(report)
