"""Thin facade over crawl4ai — unified async fetch interface.

Adapters call ``Crawler.fetch(url)`` instead of importing crawl4ai directly,
so we can:

- Apply compliance (precheck + robots + rate-limit) in one place
- Inject mock fetchers in tests without touching crawl4ai's heavy browser stack
- Add caching / persistence later without changing adapter call sites

The default fetcher uses crawl4ai's ``AsyncWebCrawler`` lazily — the import is
deferred to the first fetch so test environments without playwright installed
can still import this module.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .compliance import (
    DEFAULT_POLICY,
    CompliancePolicy,
    RateLimiter,
    is_allowed_by_robots,
    precheck_url,
)


@dataclass
class FetchResult:
    """Normalized fetch result. crawl4ai's CrawlResult is mapped onto this."""

    url: str
    status_code: int
    html: str = ""
    markdown: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# Type alias for a pluggable fetcher: ``async def fetch(url) -> FetchResult``.
FetcherFn = Callable[[str], Awaitable[FetchResult]]


async def _crawl4ai_fetcher(url: str) -> FetchResult:  # pragma: no cover - network
    """Default fetcher backed by crawl4ai. Imported lazily to avoid heavy deps."""
    from crawl4ai import AsyncWebCrawler  # type: ignore[import-not-found]

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    return FetchResult(
        url=url,
        status_code=200 if getattr(result, "success", False) else 0,
        html=getattr(result, "html", "") or "",
        markdown=getattr(result, "markdown", "") or "",
        extra={
            "links": getattr(result, "links", None),
            "media": getattr(result, "media", None),
        },
    )


@dataclass
class Crawler:
    """High-level async crawler with built-in compliance.

    Usage::

        crawler = Crawler()
        result = await crawler.fetch("https://example.com/p/1")

    Tests inject ``fetcher=`` and ``robots_loader=`` to stay offline.
    """

    policy: CompliancePolicy = field(default_factory=lambda: DEFAULT_POLICY)
    fetcher: FetcherFn = field(default=_crawl4ai_fetcher)
    # Loads robots.txt for a given origin. Returns None to skip robots check.
    robots_loader: Callable[[str], Awaitable[str | None]] | None = None
    _limiter: RateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self._limiter = RateLimiter(self.policy)

    async def fetch(self, url: str) -> FetchResult:
        """Fetch ``url`` honoring policy. Raises ``PermissionError`` if denied."""
        ok, reason = precheck_url(url, self.policy)
        if not ok:
            raise PermissionError(f"compliance denied: {reason} ({url})")

        if self.policy.respect_robots_txt:
            if self.robots_loader is None:
                raise PermissionError("robots.txt check required but no robots_loader configured")
            body = await self.robots_loader(url)
            if body is None:
                raise PermissionError(f"robots.txt unavailable for {url}")
            if not is_allowed_by_robots(url, body, self.policy.user_agent):
                raise PermissionError(f"robots.txt disallows {url}")

        await self._limiter.acquire(url)
        return await self.fetcher(url)


__all__ = ["Crawler", "FetchResult", "FetcherFn"]
