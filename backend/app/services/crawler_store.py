"""Raw-records store — DuckDB-backed persistence for crawler output.

Stores the three record streams that ``build_seed_report`` consumes:

- ``products``: e-commerce product snapshots
- ``reviews``: product reviews (with sentiment)
- ``posts``: social posts (with sentiment + author hash)

Each row is keyed by ``(project_id, platform, id)``. Inserts are
last-write-wins on the natural key — late-arriving rows overwrite earlier
duplicates, mirroring the in-memory dedup behavior of
``app.crawler.pipeline.dedup``.

Records are stored as JSON blobs in addition to a few indexed columns. This
gives us schema flexibility (the crawler pipeline emits dict shapes that
evolve) while still letting the seed-report query pull plain dicts back out.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.services.duckdb_store import connect

_KIND_TABLE = {
    "product": "raw_products",
    "review": "raw_reviews",
    "post": "raw_posts",
}

_SCHEMA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_products (
        project_id   VARCHAR NOT NULL,
        platform     VARCHAR NOT NULL,
        record_id    VARCHAR NOT NULL,
        crawled_at   TIMESTAMP,
        payload      VARCHAR NOT NULL,
        PRIMARY KEY (project_id, platform, record_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_reviews (
        project_id   VARCHAR NOT NULL,
        platform     VARCHAR NOT NULL,
        record_id    VARCHAR NOT NULL,
        crawled_at   TIMESTAMP,
        payload      VARCHAR NOT NULL,
        PRIMARY KEY (project_id, platform, record_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_posts (
        project_id   VARCHAR NOT NULL,
        platform     VARCHAR NOT NULL,
        record_id    VARCHAR NOT NULL,
        crawled_at   TIMESTAMP,
        payload      VARCHAR NOT NULL,
        PRIMARY KEY (project_id, platform, record_id)
    );
    """,
]


def _coerce_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _serialize(record: dict[str, Any]) -> str:
    """JSON-encode a record, converting datetimes to ISO strings."""

    def _default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"unserializable: {type(o).__name__}")

    return json.dumps(record, ensure_ascii=False, default=_default)


def _deserialize(payload: str) -> dict[str, Any]:
    """JSON-decode a stored row. Best-effort restores known timestamp fields."""
    data = json.loads(payload)
    for k in ("crawled_at", "posted_at", "placed_at", "started_at"):
        if k in data and isinstance(data[k], str) and data[k]:
            try:
                data[k] = datetime.fromisoformat(data[k])
            except ValueError:
                pass
    return data


class CrawlerStore:
    """Persist raw crawler records keyed by ``(project_id, platform, id)``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with connect() as conn:
            for ddl in _SCHEMA_DDL:
                conn.execute(ddl)

    def _table(self, kind: str) -> str:
        try:
            return _KIND_TABLE[kind]
        except KeyError as exc:
            raise ValueError(
                f"unknown record kind {kind!r}; expected one of {list(_KIND_TABLE)}"
            ) from exc

    def upsert_many(
        self,
        project_id: str,
        kind: str,
        records: Iterable[dict[str, Any]],
    ) -> int:
        """Insert (or overwrite) ``records`` under ``project_id``. Returns count."""
        table = self._table(kind)
        rows: list[tuple[Any, ...]] = []
        for r in records:
            rid = r.get("id")
            platform = r.get("platform") or "unknown"
            if not rid:
                continue
            crawled = _coerce_dt(r.get("crawled_at"))
            rows.append(
                (project_id, platform, str(rid), crawled, _serialize(r))
            )
        if not rows:
            return 0
        with self._lock, connect() as conn:
            # DuckDB INSERT OR REPLACE not supported; emulate via DELETE + INSERT
            # in one transaction. The composite key list is small per call.
            keys = [(pid, plat, rid) for pid, plat, rid, _, _ in rows]
            conn.execute("BEGIN")
            try:
                conn.executemany(
                    f"DELETE FROM {table} "
                    "WHERE project_id = ? AND platform = ? AND record_id = ?",
                    keys,
                )
                conn.executemany(
                    f"INSERT INTO {table} "
                    "(project_id, platform, record_id, crawled_at, payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return len(rows)

    def list_for_project(
        self, project_id: str, kind: str
    ) -> list[dict[str, Any]]:
        table = self._table(kind)
        with connect() as conn:
            rows = conn.execute(
                f"SELECT payload FROM {table} WHERE project_id = ? "
                "ORDER BY crawled_at DESC NULLS LAST",
                [project_id],
            ).fetchall()
        return [_deserialize(p[0]) for p in rows]

    def delete_for_project(self, project_id: str) -> int:
        with self._lock, connect() as conn:
            total = 0
            for table in _KIND_TABLE.values():
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE project_id = ? RETURNING 1",
                    [project_id],
                )
                total += len(cur.fetchall())
            return total

    def clear(self) -> None:
        with self._lock, connect() as conn:
            for table in _KIND_TABLE.values():
                conn.execute(f"DELETE FROM {table}")


_store: CrawlerStore | None = None
_store_lock = threading.Lock()


def get_crawler_store() -> CrawlerStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = CrawlerStore()
    return _store


def reset_crawler_store_singleton() -> None:
    global _store
    with _store_lock:
        _store = None


__all__ = [
    "CrawlerStore",
    "get_crawler_store",
    "reset_crawler_store_singleton",
]
