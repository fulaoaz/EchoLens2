"""End-to-end test for /api/projects CRUD."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.project_store import get_store


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    get_store().clear()


def test_create_and_list(client: Any) -> None:
    resp = client.post(
        "/api/projects",
        json={"name": "双 11 美妆活动", "keywords": ["美妆", "国货"]},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["success"] is True
    pid = body["data"]["id"]
    assert body["data"]["name"] == "双 11 美妆活动"
    assert body["data"]["status"] == "created"

    listing = client.get("/api/projects").get_json()
    assert listing["data"]["count"] == 1
    assert listing["data"]["items"][0]["id"] == pid


def test_get_404(client: Any) -> None:
    resp = client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


def test_create_rejects_empty_name(client: Any) -> None:
    resp = client.post("/api/projects", json={"name": ""})
    assert resp.status_code == 400


def test_create_rejects_extra_fields(client: Any) -> None:
    resp = client.post("/api/projects", json={"name": "x", "evil": "field"})
    assert resp.status_code == 400


def test_delete(client: Any) -> None:
    pid = client.post("/api/projects", json={"name": "tmp"}).get_json()["data"]["id"]
    assert client.delete(f"/api/projects/{pid}").status_code == 200
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_ping_now_implemented(client: Any) -> None:
    resp = client.get("/api/projects/ping")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["implemented"] is True
