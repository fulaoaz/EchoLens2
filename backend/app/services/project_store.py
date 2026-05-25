"""Project store — DuckDB-backed persistence (M1.3).

Schema::

    projects(
        id           VARCHAR PRIMARY KEY,
        name         VARCHAR,
        description  VARCHAR,
        keywords     VARCHAR,           -- JSON-encoded list[str]
        target_platforms VARCHAR,       -- JSON-encoded list[str]
        status       VARCHAR,
        created_at   TIMESTAMP,
        updated_at   TIMESTAMP
    )

The store is process-wide (single DuckDB file) and thread-safe via a coarse
``threading.Lock`` — DuckDB's own writer is single-threaded per file, the lock
just keeps Python-level read-modify-write paths honest.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any

from app.models.project import Project
from app.services.duckdb_store import connect

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS projects (
    id               VARCHAR PRIMARY KEY,
    name             VARCHAR NOT NULL,
    description      VARCHAR DEFAULT '',
    keywords         VARCHAR DEFAULT '[]',
    target_platforms VARCHAR DEFAULT '[]',
    status           VARCHAR DEFAULT 'created',
    created_at       TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP NOT NULL
);
"""


def _row_to_project(row: tuple[Any, ...]) -> Project:
    (
        pid,
        name,
        description,
        keywords_json,
        platforms_json,
        status,
        created_at,
        updated_at,
    ) = row
    return Project(
        id=pid,
        name=name,
        description=description or "",
        keywords=json.loads(keywords_json or "[]"),
        target_platforms=json.loads(platforms_json or "[]"),
        status=status or "created",
        created_at=created_at,
        updated_at=updated_at,
    )


class ProjectStore:
    """DuckDB-backed project store. All methods open a fresh connection."""

    _COLUMNS = (
        "id, name, description, keywords, target_platforms, "
        "status, created_at, updated_at"
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with connect() as conn:
            conn.execute(_SCHEMA_DDL)

    def create(self, project: Project) -> Project:
        with self._lock, connect() as conn:
            conn.execute(
                "INSERT INTO projects "
                f"({self._COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    project.id,
                    project.name,
                    project.description,
                    json.dumps(project.keywords, ensure_ascii=False),
                    json.dumps(project.target_platforms, ensure_ascii=False),
                    project.status,
                    project.created_at,
                    project.updated_at,
                ],
            )
        return project

    def get(self, project_id: str) -> Project | None:
        with connect() as conn:
            row = conn.execute(
                f"SELECT {self._COLUMNS} FROM projects WHERE id = ?",
                [project_id],
            ).fetchone()
        return _row_to_project(row) if row else None

    def list(self) -> list[Project]:
        with connect() as conn:
            rows = conn.execute(
                f"SELECT {self._COLUMNS} FROM projects "
                "ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        return [_row_to_project(r) for r in rows]

    def update(self, project_id: str, **fields: object) -> Project | None:
        with self._lock:
            current = self.get(project_id)
            if current is None:
                return None
            data = current.model_dump()
            data.update(fields)
            data["updated_at"] = datetime.utcnow()
            updated = Project.model_validate(data)
            with connect() as conn:
                conn.execute(
                    "UPDATE projects SET "
                    "name = ?, description = ?, keywords = ?, "
                    "target_platforms = ?, status = ?, updated_at = ? "
                    "WHERE id = ?",
                    [
                        updated.name,
                        updated.description,
                        json.dumps(updated.keywords, ensure_ascii=False),
                        json.dumps(updated.target_platforms, ensure_ascii=False),
                        updated.status,
                        updated.updated_at,
                        updated.id,
                    ],
                )
            return updated

    def delete(self, project_id: str) -> bool:
        with self._lock, connect() as conn:
            cur = conn.execute(
                "DELETE FROM projects WHERE id = ? RETURNING id",
                [project_id],
            )
            return cur.fetchone() is not None

    def clear(self) -> None:
        with self._lock, connect() as conn:
            conn.execute("DELETE FROM projects")


_store: ProjectStore | None = None
_store_lock = threading.Lock()


def get_store() -> ProjectStore:
    """Lazy singleton — created on first access so tests can patch settings first."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ProjectStore()
    return _store


def reset_store_singleton() -> None:
    """Test hook: drop the cached singleton (e.g. after switching duckdb path)."""
    global _store
    with _store_lock:
        _store = None


__all__ = ["ProjectStore", "get_store", "reset_store_singleton"]
