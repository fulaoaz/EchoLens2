"""End-to-end tests for /api/crawler."""

from __future__ import annotations

from typing import Any

import pytest

from app.api import crawler as crawler_api
from app.crawler.engine.crawler import FetchResult
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store


class FakeCrawler:
    def __init__(self, robots_loader: Any | None = None, **_: Any) -> None:
        self.robots_loader = robots_loader

    async def fetch(self, url: str) -> FetchResult:
        if self.robots_loader is not None:
            await self.robots_loader(url)
        if "fail" in url:
            return FetchResult(url=url, status_code=500, html="")
        return FetchResult(
            url=url,
            status_code=200,
            html="""
            <html>
              <head><title>Anker 737 移动电源 - 官方详情页</title></head>
              <body>
                <h1>Anker 737 移动电源</h1>
                <p>公开页面采集内容，续航稳定，快充表现好。</p>
                <p>联系电话 13800138000 应被脱敏。</p>
              </body>
            </html>
            """,
        )


@pytest.fixture(autouse=True)
def _reset_stores() -> None:
    get_store().clear()
    get_crawler_store().clear()
    crawler_api.clear_crawler_jobs()
    crawler_api.set_crawler_factory(FakeCrawler)
    yield
    crawler_api.clear_crawler_jobs()
    crawler_api.set_crawler_factory(crawler_api.Crawler)


def _create_project(client: Any) -> str:
    resp = client.post("/api/projects", json={"name": "crawler-test", "keywords": ["anker"]})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()["data"]["id"]


def test_ping_now_implemented(client: Any) -> None:
    resp = client.get("/api/crawler/ping")
    assert resp.status_code == 200
    assert resp.get_json()["data"] == {"module": "crawler", "implemented": True}


def test_start_requires_project_and_some_signal(client: Any) -> None:
    missing_project = client.post(
        "/api/crawler/start",
        json={"projectId": "missing", "sourceUrls": ["https://example.com/product/1"]},
    )
    assert missing_project.status_code == 404

    # Project with name that is purely stopwords + no keywords/material/urls -> 400.
    resp = client.post("/api/projects", json={"name": "项目"})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    pid = resp.get_json()["data"]["id"]
    no_signal = client.post(
        "/api/crawler/start",
        json={"projectId": pid, "platforms": ["news"]},
    )
    assert no_signal.status_code == 400


def test_start_crawls_public_url_and_populates_seed_report(client: Any) -> None:
    pid = _create_project(client)
    resp = client.post(
        "/api/crawler/start",
        json={
            "projectId": pid,
            "platforms": ["jd"],
            "sourceUrls": ["https://item.jd.com/100012043978.html"],
        },
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    jobs = resp.get_json()["data"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "success"
    assert jobs[0]["itemsCollected"] == 1
    assert jobs[0]["platform"] == "jd"

    listing = client.get(f"/api/crawler/jobs?projectId={pid}")
    assert listing.status_code == 200
    assert listing.get_json()["data"][0]["id"] == jobs[0]["id"]

    report = client.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    assert report["counts"]["products"] == 1
    assert report["counts"]["posts"] == 0
    assert report["products"][0]["title"] == "Anker 737 移动电源 - 官方详情页"

    product = get_crawler_store().list_for_project(pid, "product")[0]
    assert "13800138000" not in product["source_text_sample"]
    assert "[PHONE]" in product["source_text_sample"]

    detail = client.get(f"/api/projects/{pid}").get_json()["data"]
    assert detail["status"] == "seed_ready"


def test_start_records_failed_job_when_fetch_fails(client: Any) -> None:
    pid = _create_project(client)
    resp = client.post(
        "/api/crawler/start",
        json={"projectId": pid, "sourceUrls": ["https://example.com/fail"]},
    )
    assert resp.status_code == 201
    job = resp.get_json()["data"][0]
    assert job["status"] == "failed"
    assert job["itemsCollected"] == 0
    assert "HTTP 500" in job["error"]

    detail = client.get(f"/api/projects/{pid}").get_json()["data"]
    assert detail["status"] == "failed"


def test_cancel_unknown_job_returns_404(client: Any) -> None:
    resp = client.post("/api/crawler/jobs/missing/cancel")
    assert resp.status_code == 404


def test_start_derives_targets_from_material_text(client: Any) -> None:
    # Project has no platforms or sourceUrls; targets must come from materialText.
    resp = client.post(
        "/api/projects",
        json={"name": "anker-material", "keywords": []},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    pid = resp.get_json()["data"]["id"]

    started = client.post(
        "/api/crawler/start",
        json={
            "projectId": pid,
            "materialText": (
                "Anker 737 移动电源 旗舰款 续航实测，舆情聚焦快充与发热表现。"
            ),
            "maxTargets": 4,
        },
    )
    assert started.status_code == 201, started.get_data(as_text=True)
    jobs = started.get_json()["data"]
    assert len(jobs) >= 1
    # Every derived job must come from material_search and carry a keyword.
    sources = {job.get("source") for job in jobs}
    assert sources == {"material_search"}
    assert all(job.get("keyword") for job in jobs)
    # Default search platforms include news/weibo/xhs/zhihu — at least one wins.
    assert any(
        job["platform"] in {"news", "weibo", "xhs", "zhihu"} for job in jobs
    )

    detail = client.get(f"/api/projects/{pid}").get_json()["data"]
    assert detail["status"] in {"seed_ready", "failed"}


def test_start_derives_targets_from_project_keywords(client: Any) -> None:
    # Keywords-only project (no platforms, no sourceUrls, no materialText).
    resp = client.post(
        "/api/projects",
        json={"name": "kw-only", "keywords": ["Anker 737"]},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    pid = resp.get_json()["data"]["id"]

    started = client.post(
        "/api/crawler/start",
        json={"projectId": pid, "maxTargets": 3},
    )
    assert started.status_code == 201, started.get_data(as_text=True)
    jobs = started.get_json()["data"]
    assert jobs, "expected keyword-driven targets"
    assert all(job.get("source") == "material_search" for job in jobs)
    assert all(job.get("keyword") for job in jobs)
