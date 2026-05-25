"""Compliance layer tests — robots.txt, rate limit, precheck."""

from __future__ import annotations

import asyncio

import pytest

from app.crawler.engine.compliance import (
    CompliancePolicy,
    RateLimiter,
    is_allowed_by_robots,
    parse_robots,
    precheck_url,
)

# --- robots.txt ---------------------------------------------------------

ROBOTS_PERMISSIVE = """\
User-agent: *
Allow: /
"""

ROBOTS_RESTRICTIVE = """\
User-agent: *
Disallow: /private/
Disallow: /admin
Disallow: /api/internal
"""

ROBOTS_FULL_BLOCK = """\
User-agent: *
Disallow: /
"""


class TestRobots:
    def test_permissive_allows_anything(self) -> None:
        assert is_allowed_by_robots("https://x.com/foo", ROBOTS_PERMISSIVE)

    def test_disallows_private_path(self) -> None:
        assert not is_allowed_by_robots(
            "https://x.com/private/data",
            ROBOTS_RESTRICTIVE,
        )

    def test_allows_other_paths_under_restrictive(self) -> None:
        assert is_allowed_by_robots("https://x.com/public/x", ROBOTS_RESTRICTIVE)

    def test_full_block(self) -> None:
        assert not is_allowed_by_robots("https://x.com/anything", ROBOTS_FULL_BLOCK)

    def test_parse_robots_returns_parser(self) -> None:
        rp = parse_robots(ROBOTS_PERMISSIVE)
        assert rp.can_fetch("*", "https://x.com/")


# --- precheck -----------------------------------------------------------

class TestPrecheck:
    def test_allows_plain_https(self) -> None:
        ok, reason = precheck_url("https://example.com/page")
        assert ok and reason == ""

    def test_rejects_non_http(self) -> None:
        ok, reason = precheck_url("ftp://example.com/x")
        assert not ok and "http" in reason

    def test_rejects_login_url(self) -> None:
        ok, reason = precheck_url("https://example.com/login")
        assert not ok and "authenticated" in reason

    def test_rejects_token_query(self) -> None:
        ok, _ = precheck_url("https://example.com/page?token=abc123")
        assert not ok

    def test_allows_authenticated_when_policy_says_so(self) -> None:
        policy = CompliancePolicy(allow_authenticated=True)
        ok, _ = precheck_url("https://example.com/login", policy)
        assert ok


# --- rate limiter --------------------------------------------------------

class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_first_request_no_wait(self) -> None:
        limiter = RateLimiter(CompliancePolicy(requests_per_second_per_domain=2.0))
        wait = await limiter.acquire("https://a.com/x")
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_second_request_within_window_waits(self) -> None:
        # 1 req/s, burst=1: after first call we must wait ~1s for the next.
        clock = [0.0]
        limiter = RateLimiter(
            CompliancePolicy(requests_per_second_per_domain=1.0, burst_size=1.0),
        )
        limiter._now = lambda: clock[0]

        async def fast_sleep(seconds: float) -> None:
            # Simulate time passing without actually sleeping.
            clock[0] += seconds

        # Patch asyncio.sleep on this limiter call.
        original_sleep = asyncio.sleep
        asyncio.sleep = fast_sleep  # type: ignore[assignment]
        try:
            assert await limiter.acquire("https://a.com/1") == 0.0
            wait = await limiter.acquire("https://a.com/2")
            assert wait == pytest.approx(1.0, abs=0.01)
        finally:
            asyncio.sleep = original_sleep  # type: ignore[assignment]

    @pytest.mark.asyncio
    async def test_per_domain_isolation(self) -> None:
        limiter = RateLimiter(
            CompliancePolicy(requests_per_second_per_domain=1.0, burst_size=1.0),
        )
        # Two different domains, both should be free on first call.
        assert await limiter.acquire("https://a.com/1") == 0.0
        assert await limiter.acquire("https://b.com/1") == 0.0
