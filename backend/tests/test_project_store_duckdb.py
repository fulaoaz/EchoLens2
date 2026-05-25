"""DuckDB-backed ProjectStore — persistence + isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.project import Project


@pytest.fixture(autouse=True)
def _isolate_duckdb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Each test gets its own DuckDB file via DUCKDB_PATH + cache reset.

    Teardown clears the singleton so the next test (possibly in another
    file) re-initializes against the current ``DUCKDB_PATH``.
    """
    from app.config import get_settings
    from app.services import crawler_store, project_store

    db_path = tmp_path / "store.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    get_settings.cache_clear()  # type: ignore[attr-defined]
    project_store.reset_store_singleton()
    crawler_store.reset_crawler_store_singleton()
    yield
    project_store.reset_store_singleton()
    crawler_store.reset_crawler_store_singleton()
    get_settings.cache_clear()  # type: ignore[attr-defined]


def _project(name: str = "p", **fields: object) -> Project:
    return Project(name=name, **fields)


def test_create_and_get() -> None:
    from app.services.project_store import get_store

    p = _project("alpha", keywords=["k1"], target_platforms=["jd"])
    store = get_store()
    store.create(p)

    fetched = store.get(p.id)
    assert fetched is not None
    assert fetched.id == p.id
    assert fetched.name == "alpha"
    assert fetched.keywords == ["k1"]
    assert fetched.target_platforms == ["jd"]
    assert fetched.status == "created"


def test_persistence_across_instances() -> None:
    """Data survives losing the Python store object — that's the whole point."""
    from app.services import project_store

    store1 = project_store.get_store()
    p = _project("beta", description="持久化测试")
    store1.create(p)

    project_store.reset_store_singleton()
    store2 = project_store.get_store()

    fetched = store2.get(p.id)
    assert fetched is not None
    assert fetched.name == "beta"
    assert fetched.description == "持久化测试"


def test_list_returns_recent_first() -> None:
    from app.services.project_store import get_store

    store = get_store()
    a = _project("a")
    b = _project("b")
    c = _project("c")
    store.create(a)
    store.create(b)
    store.create(c)

    listed = store.list()
    assert {p.name for p in listed} == {"a", "b", "c"}


def test_update_changes_status_and_updated_at() -> None:
    from app.services.project_store import get_store

    store = get_store()
    p = _project("x")
    store.create(p)
    original_updated_at = p.updated_at

    updated = store.update(p.id, status="seed_ready")
    assert updated is not None
    assert updated.status == "seed_ready"
    assert updated.updated_at >= original_updated_at


def test_update_missing_returns_none() -> None:
    from app.services.project_store import get_store

    assert get_store().update("missing", status="failed") is None


def test_delete_removes_row() -> None:
    from app.services.project_store import get_store

    store = get_store()
    p = _project("doomed")
    store.create(p)
    assert store.delete(p.id) is True
    assert store.get(p.id) is None
    assert store.delete(p.id) is False  # already gone


def test_clear_drops_all() -> None:
    from app.services.project_store import get_store

    store = get_store()
    store.create(_project("a"))
    store.create(_project("b"))
    store.clear()
    assert store.list() == []


def test_unicode_round_trip() -> None:
    from app.services.project_store import get_store

    store = get_store()
    p = _project(
        "美妆双 11",
        description="国货美妆 / 抗老精华",
        keywords=["国货", "抗老", "618"],
    )
    store.create(p)

    got = store.get(p.id)
    assert got is not None
    assert got.name == "美妆双 11"
    assert got.keywords == ["国货", "抗老", "618"]
