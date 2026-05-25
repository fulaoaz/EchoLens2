"""DuckDB columnar store — facts persistence + analytic queries."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import duckdb

from app.config import get_settings


@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection bound to the configured path."""
    settings = get_settings()
    settings.ensure_dirs()
    conn = duckdb.connect(settings.duckdb_path)
    try:
        yield conn
    finally:
        conn.close()


__all__ = ["connect"]
