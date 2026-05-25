"""Compliance layer: robots.txt parsing + per-domain rate limit + UA transparency.

This module is purposefully network-light. The robots.txt parser uses Python's
stdlib ``urllib.robotparser``; fetching the actual robots.txt is delegated to
the caller (the engine.crawler facade) so this module can be unit-tested
without network. The rate limiter is an in-process token bucket keyed by
domain.

Design choices
--------------
- **Hard-default to deny on parse failure.** If we can't read robots.txt, we
  refuse the URL — fail-closed for compliance.
- **No login scraping.** ``allow_authenticated`` defaults to False; adapters
  must opt in explicitly and document why.
- **UA is transparent.** The user-agent identifies EchoLens, not a stock
  browser string. This is a safety feature, not a hindrance — the platforms
  we're scraping (taobao/jd/weibo/xhs) all expect to see who's calling.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


@dataclass(frozen=True)
class CompliancePolicy:
    """Crawler compliance settings.

    Attributes:
        requests_per_second_per_domain: Token bucket refill rate. 1.0 = polite.
        respect_robots_txt: When True, ``check_allowed`` consults robots.txt
            and denies if disallowed. False is for white-listed test URLs only.
        allow_authenticated: When False, refuses URLs that look authenticated
            (contain session/login query strings or auth headers upstream).
        user_agent: Transparent UA string. Identifies us to remote sites.
        burst_size: Max tokens the bucket holds. Defaults to 1.0 = no burst.
    """

    requests_per_second_per_domain: float = 1.0
    respect_robots_txt: bool = True
    allow_authenticated: bool = False
    user_agent: str = "EchoLens2/0.1 (+https://github.com/echolens2)"
    burst_size: float = 1.0


DEFAULT_POLICY = CompliancePolicy()


# --- robots.txt ----------------------------------------------------------

def _domain_of(url: str) -> str:
    p = urlparse(url)
    return (p.hostname or "").lower()


def parse_robots(robots_txt_body: str) -> RobotFileParser:
    """Parse a robots.txt body into a RobotFileParser without any network."""
    rp = RobotFileParser()
    rp.parse(robots_txt_body.splitlines())
    return rp


def is_allowed_by_robots(
    url: str,
    robots_txt_body: str,
    user_agent: str = DEFAULT_POLICY.user_agent,
) -> bool:
    """Return True iff ``url`` is fetchable by ``user_agent`` per robots.txt.

    The body must be supplied by the caller — this function does no I/O so it
    can be unit-tested deterministically.
    """
    rp = parse_robots(robots_txt_body)
    return rp.can_fetch(user_agent, url)


# --- rate limiter --------------------------------------------------------

@dataclass
class _Bucket:
    tokens: float
    last_refill: float


@dataclass
class RateLimiter:
    """Per-domain async token bucket.

    Use ``await acquire(url)`` before every request. The bucket refills at
    ``policy.requests_per_second_per_domain`` and tops out at
    ``policy.burst_size`` tokens.

    Thread-safety: serialized by an asyncio Lock per limiter instance. Spin up
    one limiter per crawler process; do not share across processes.
    """

    policy: CompliancePolicy = field(default_factory=lambda: DEFAULT_POLICY)
    _buckets: dict[str, _Bucket] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _now: callable = time.monotonic  # injectable for tests

    async def acquire(self, url: str) -> float:
        """Block until a token is available for ``url``'s domain.

        Returns the number of seconds we slept (0.0 if the bucket had a token).
        """
        domain = _domain_of(url) or "_"
        async with self._lock:
            now = self._now()
            bucket = self._buckets.get(domain)
            if bucket is None:
                bucket = _Bucket(
                    tokens=self.policy.burst_size,
                    last_refill=now,
                )
                self._buckets[domain] = bucket
            else:
                # Refill.
                elapsed = now - bucket.last_refill
                bucket.tokens = min(
                    self.policy.burst_size,
                    bucket.tokens + elapsed * self.policy.requests_per_second_per_domain,
                )
                bucket.last_refill = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return 0.0
            # Need to wait until we have a full token.
            need = 1.0 - bucket.tokens
            wait = need / self.policy.requests_per_second_per_domain
            bucket.tokens = 0.0
            bucket.last_refill = now + wait
        await asyncio.sleep(wait)
        return wait


# --- combined check ------------------------------------------------------

_AUTH_HINTS = ("login", "signin", "sso", "session=", "token=", "auth=")


def _looks_authenticated(url: str) -> bool:
    lower = url.lower()
    return any(hint in lower for hint in _AUTH_HINTS)


def precheck_url(url: str, policy: CompliancePolicy = DEFAULT_POLICY) -> tuple[bool, str]:
    """Cheap synchronous compliance precheck (no network, no rate-limit wait).

    Returns ``(allowed, reason)``. ``reason`` is empty when allowed.
    Robots.txt is *not* checked here — the caller fetches robots.txt and uses
    ``is_allowed_by_robots`` because that requires network.
    """
    if not url or not url.startswith(("http://", "https://")):
        return False, "url must be http(s)"
    if not policy.allow_authenticated and _looks_authenticated(url):
        return False, "looks authenticated; allow_authenticated=False"
    return True, ""


__all__ = [
    "CompliancePolicy",
    "DEFAULT_POLICY",
    "RateLimiter",
    "is_allowed_by_robots",
    "parse_robots",
    "precheck_url",
]
