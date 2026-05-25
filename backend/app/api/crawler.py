"""/api/crawler blueprint — compliant public-web sentiment crawl orchestration."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Literal
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.crawler.engine.compliance import DEFAULT_POLICY
from app.crawler.engine.crawler import Crawler, FetchResult
from app.crawler.pipeline.clean import mask_pii, normalize_whitespace, strip_html
from app.models.project import Project
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store

bp = Blueprint("crawler", __name__, url_prefix="/api/crawler")

CrawlStatus = Literal["pending", "running", "success", "failed", "cancelled"]

_PLATFORM_HOST_HINTS = {
    "jd.com": "jd",
    "taobao.com": "taobao",
    "tmall.com": "taobao",
    "xiaohongshu.com": "xhs",
    "xhslink.com": "xhs",
    "weibo.com": "weibo",
    "douyin.com": "douyin",
    "zhihu.com": "zhihu",
}

_PRODUCT_PLATFORMS = {"jd", "taobao", "pdd", "douyin"}
_SOCIAL_PLATFORMS = {"weibo", "xhs", "zhihu", "news"}
_SEARCH_SOURCE_PLATFORMS = {"news", "weibo", "xhs", "zhihu"}

_jobs: dict[str, dict[str, object]] = {}
_jobs_lock = Lock()
_crawler_factory = Crawler


@dataclass(frozen=True)
class CrawlTarget:
    url: str
    platform: str
    keyword: str
    source: str


class StartCrawlIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    projectId: str = Field(..., min_length=1)
    platforms: list[str] = Field(default_factory=list, max_length=12)
    sourceUrls: list[str] = Field(default_factory=list, max_length=20)
    materialText: str = Field(default="", max_length=20_000)
    maxTargets: int = Field(default=12, ge=1, le=50)


def _ok(data: object, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


def _job_payload(job: dict[str, object]) -> dict[str, object]:
    return dict(job)


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _platform_from_url(url: str, allowed_platforms: set[str]) -> str:
    host = _domain(url)
    for hint, platform in _PLATFORM_HOST_HINTS.items():
        if hint in host:
            return platform
    if len(allowed_platforms) == 1:
        return next(iter(allowed_platforms))
    return "unknown"


def _robots_url(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


async def _load_robots(url: str) -> str | None:
    robots_url = _robots_url(url)
    if robots_url is None:
        return None

    def _fetch() -> str | None:
        req = Request(robots_url, headers={"User-Agent": DEFAULT_POLICY.user_agent})
        try:
            with urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    return None
                return resp.read(128_000).decode("utf-8", errors="replace")
        except Exception:
            return None

    return await asyncio.to_thread(_fetch)


def _extract_title(result: FetchResult) -> str:
    html = result.html or ""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        title = strip_html(match.group(1))
        if title:
            return normalize_whitespace(mask_pii(title))[:500]
    text = _extract_text(result)
    if text:
        return text[:80]
    return result.url


def _extract_text(result: FetchResult) -> str:
    text = result.markdown or strip_html(result.html or "")
    return normalize_whitespace(mask_pii(text))


def _extract_material_terms(project: Project, material_text: str) -> list[str]:
    text = normalize_whitespace(mask_pii(material_text))
    candidates: list[str] = [project.name, *project.keywords]
    if project.description:
        candidates.extend(re.findall(r"[\w一-鿿][\w一-鿿\-]{1,30}", project.description))
    if text:
        candidates.extend(re.findall(r"[\w一-鿿][\w一-鿿\-]{1,30}", text))

    stopwords = {
        "项目",
        "活动",
        "营销",
        "推广",
        "用户",
        "商品",
        "品牌",
        "平台",
        "the",
        "and",
        "for",
        "with",
    }
    terms: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        term = normalize_whitespace(str(raw)).strip("# ，,。.;；:：()（）[]【】")
        if len(term) < 2 or term.lower() in stopwords:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term[:60])
        if len(terms) >= 10:
            break
    return terms


def _search_url(platform: str, keyword: str) -> str:
    q = quote_plus(keyword)
    if platform == "weibo":
        return f"https://s.weibo.com/weibo?q={q}"
    if platform == "xhs":
        return f"https://www.xiaohongshu.com/search_result?keyword={q}"
    if platform == "zhihu":
        return f"https://www.zhihu.com/search?type=content&q={q}"
    return f"https://www.bing.com/news/search?q={q}"


def _build_targets(project: Project, payload: StartCrawlIn) -> list[CrawlTarget]:
    requested_platforms = {p.strip().lower() for p in payload.platforms if p.strip()}
    project_platforms = {p.strip().lower() for p in project.target_platforms if p.strip()}
    platforms = requested_platforms or project_platforms or {"news", "weibo", "xhs", "zhihu"}

    targets: list[CrawlTarget] = []
    seen_urls: set[str] = set()
    for source_url in payload.sourceUrls:
        url = source_url.strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        targets.append(
            CrawlTarget(
                url=url,
                platform=_platform_from_url(url, platforms),
                keyword="",
                source="manual_url",
            )
        )

    terms = _extract_material_terms(project, payload.materialText)
    # Material-driven discovery only when the user actually wants it:
    # - explicit materialText, or
    # - no sourceUrls were given (so we fall back to project signals).
    use_material = bool(payload.materialText.strip()) or not payload.sourceUrls
    if not use_material:
        terms = []
    search_platforms = [p for p in platforms if p in _SEARCH_SOURCE_PLATFORMS]
    if not search_platforms:
        search_platforms = ["news"]
    for term in terms:
        for platform in search_platforms:
            url = _search_url(platform, term)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            targets.append(CrawlTarget(url=url, platform=platform, keyword=term, source="material_search"))
            if len(targets) >= payload.maxTargets:
                return targets
    return targets[: payload.maxTargets]


def _record_from_fetch(
    result: FetchResult,
    target: CrawlTarget,
    allowed_platforms: set[str],
    now: datetime,
) -> tuple[str, dict[str, Any]]:
    platform = target.platform or _platform_from_url(result.url, allowed_platforms)
    title = _extract_title(result)
    text = _extract_text(result)
    record_id = f"{platform}:{uuid4().hex}"
    crawled_at = now.isoformat(timespec="seconds")
    base = {
        "id": record_id,
        "platform": platform if platform in _SOCIAL_PLATFORMS or platform in _PRODUCT_PLATFORMS else "news",
        "url": result.url,
        "crawled_at": crawled_at,
        "source_status_code": result.status_code,
        "source": target.source,
        "keyword": target.keyword,
    }
    if platform in _PRODUCT_PLATFORMS:
        return "product", {
            **base,
            "title": title,
            "brand": target.keyword or None,
            "source_text_sample": text[:1000],
        }
    return "post", {
        **base,
        "author_hash": f"source_{abs(hash(_domain(result.url))) % 10_000_000:07d}",
        "content": text[:20_000] or title,
        "sentiment": "unknown",
        "posted_at": None,
    }


async def _crawl_target(
    project_id: str,
    target: CrawlTarget,
    platforms: set[str],
) -> tuple[dict[str, int], list[str]]:
    crawler = _crawler_factory(robots_loader=_load_robots)
    store = get_crawler_store()
    counts = {"products": 0, "reviews": 0, "posts": 0}
    errors: list[str] = []
    now = datetime.utcnow()
    try:
        result = await crawler.fetch(target.url)
        if result.status_code >= 400:
            errors.append(f"{target.url} returned HTTP {result.status_code}")
            return counts, errors
        kind, record = _record_from_fetch(result, target, platforms, now)
        stored = store.upsert_many(project_id, kind, [record])
        if kind == "product":
            counts["products"] += stored
        elif kind == "review":
            counts["reviews"] += stored
        else:
            counts["posts"] += stored
    except Exception as exc:
        errors.append(f"{target.url}: {type(exc).__name__}: {exc}")
    return counts, errors


def _run_job(project_id: str, target: CrawlTarget, platforms: set[str]) -> dict[str, object]:
    now = datetime.utcnow()
    job_id = uuid4().hex
    job: dict[str, object] = {
        "id": job_id,
        "projectId": project_id,
        "platform": target.platform,
        "sourceUrl": target.url,
        "keyword": target.keyword,
        "source": target.source,
        "status": "running",
        "progress": 10,
        "itemsCollected": 0,
        "startedAt": now.isoformat(timespec="seconds"),
    }
    with _jobs_lock:
        _jobs[job_id] = job

    counts, errors = asyncio.run(_crawl_target(project_id, target, platforms))
    collected = sum(counts.values())
    finished_at = datetime.utcnow().isoformat(timespec="seconds")
    job.update(
        {
            "status": "success" if collected else "failed",
            "progress": 100,
            "itemsCollected": collected,
            "finishedAt": finished_at,
        }
    )
    if errors:
        job["error"] = "; ".join(errors)[:1000]
    with _jobs_lock:
        _jobs[job_id] = job
    return job


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "crawler", "implemented": True})


@bp.get("/jobs")
def list_jobs() -> tuple[Response, int]:
    project_id = request.args.get("projectId", "").strip()
    if not project_id:
        return _err("projectId is required", 400)
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    with _jobs_lock:
        jobs = [
            _job_payload(job)
            for job in _jobs.values()
            if job.get("projectId") == project_id
        ]
    jobs.sort(key=lambda item: str(item.get("startedAt", "")), reverse=True)
    return _ok(jobs)


@bp.post("/start")
def start() -> tuple[Response, int]:
    raw = request.get_json(silent=True) or {}
    try:
        payload = StartCrawlIn.model_validate(raw)
    except ValidationError as exc:
        return _err(str(exc), 400)
    project = get_store().get(payload.projectId)
    if not project:
        return _err(f"project {payload.projectId!r} not found", 404)

    targets = _build_targets(project, payload)
    if not targets:
        return _err("no crawl targets can be derived from project keywords, materialText, or sourceUrls", 400)

    platforms = {target.platform for target in targets if target.platform}
    get_store().update(payload.projectId, status="crawling")
    jobs = [_run_job(payload.projectId, target, platforms) for target in targets]
    if any(job.get("status") == "success" for job in jobs):
        get_store().update(payload.projectId, status="seed_ready")
    else:
        get_store().update(payload.projectId, status="failed")
    return _ok([_job_payload(job) for job in jobs], 201)


@bp.post("/jobs/<job_id>/cancel")
def cancel(job_id: str) -> tuple[Response, int]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return _err(f"crawler job {job_id!r} not found", 404)
        if job.get("status") in {"pending", "running"}:
            job.update(
                {
                    "status": "cancelled",
                    "finishedAt": datetime.utcnow().isoformat(timespec="seconds"),
                }
            )
        return _ok(_job_payload(job))


def clear_crawler_jobs() -> None:
    with _jobs_lock:
        _jobs.clear()


def set_crawler_factory(factory: Any) -> None:
    global _crawler_factory
    _crawler_factory = factory
