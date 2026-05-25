"""Crawler engine + seed report integration tests.

The engine tests use injected mock fetchers to stay fully offline.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.crawler.engine.compliance import CompliancePolicy
from app.crawler.engine.crawler import Crawler, FetchResult
from app.crawler.seed_report import build_seed_report

# --- Crawler engine ------------------------------------------------------

class TestCrawlerEngine:
    @pytest.mark.asyncio
    async def test_fetch_via_injected_fetcher(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:
            return FetchResult(url=url, status_code=200, html="<p>ok</p>")

        crawler = Crawler(
            fetcher=fake_fetch,
            policy=CompliancePolicy(respect_robots_txt=False),
        )
        result = await crawler.fetch("https://example.com/x")
        assert result.status_code == 200
        assert result.html == "<p>ok</p>"

    @pytest.mark.asyncio
    async def test_compliance_blocks_login_url(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:  # pragma: no cover
            raise AssertionError("should not be called")

        crawler = Crawler(fetcher=fake_fetch)
        with pytest.raises(PermissionError, match="authenticated"):
            await crawler.fetch("https://example.com/login")

    @pytest.mark.asyncio
    async def test_robots_required_when_policy_enabled(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:  # pragma: no cover
            raise AssertionError("should not be called")

        crawler = Crawler(fetcher=fake_fetch)
        with pytest.raises(PermissionError, match="robots_loader"):
            await crawler.fetch("https://example.com/page")

    @pytest.mark.asyncio
    async def test_robots_blocks(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:  # pragma: no cover
            raise AssertionError("should not be called")

        async def robots_loader(url: str) -> str:
            return "User-agent: *\nDisallow: /\n"

        crawler = Crawler(fetcher=fake_fetch, robots_loader=robots_loader)
        with pytest.raises(PermissionError, match="robots"):
            await crawler.fetch("https://example.com/page")

    @pytest.mark.asyncio
    async def test_robots_allows(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:
            return FetchResult(url=url, status_code=200, html="ok")

        async def robots_loader(url: str) -> str:
            return "User-agent: *\nAllow: /\n"

        crawler = Crawler(fetcher=fake_fetch, robots_loader=robots_loader)
        result = await crawler.fetch("https://example.com/page")
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_robots_loader_none_fails_closed(self) -> None:
        async def fake_fetch(url: str) -> FetchResult:  # pragma: no cover
            raise AssertionError("should not be called")

        async def robots_loader(url: str) -> None:
            return None

        crawler = Crawler(
            fetcher=fake_fetch,
            robots_loader=robots_loader,
            policy=CompliancePolicy(respect_robots_txt=True, requests_per_second_per_domain=10),
        )
        with pytest.raises(PermissionError, match="robots.txt unavailable"):
            await crawler.fetch("https://example.com/x")


# --- Seed report ---------------------------------------------------------

NOW = datetime(2026, 5, 20, 12, 0, 0)


def _make_products() -> list[dict]:
    base = NOW
    return [
        {
            "platform": "jd",
            "id": "jd:1",
            "title": "Anker 737 移动电源 官方旗舰店",
            "brand": "Anker",
            "price_current": 599.0,
            "crawled_at": base,
        },
        {
            "platform": "taobao",
            "id": "tb:1",
            "title": "Anker 737 移动电源 正品包邮",
            "brand": "Anker",
            "price_current": 549.0,
            "crawled_at": base,
        },
        {
            "platform": "jd",
            "id": "jd:2",
            "title": "罗技 G502 鼠标",
            "brand": "Logitech",
            "price_current": 399.0,
            "crawled_at": base,
        },
        # Duplicate of jd:1 by (platform, id) with newer timestamp — dedup keeps this.
        {
            "platform": "jd",
            "id": "jd:1",
            "title": "Anker 737 移动电源 旗舰店 新款",
            "brand": "Anker",
            "price_current": 569.0,
            "crawled_at": datetime(2026, 5, 20, 13, 0, 0),
        },
    ]


def _make_reviews() -> list[dict]:
    return [
        {"platform": "jd", "id": "r1", "content": "续航很好", "sentiment": "positive"},
        {"platform": "jd", "id": "r2", "content": "充电速度快", "sentiment": "positive"},
        {"platform": "jd", "id": "r3", "content": "外壳掉漆", "sentiment": "negative"},
        {"platform": "jd", "id": "r4", "content": "一般般", "sentiment": "neutral"},
    ]


def _make_posts() -> list[dict]:
    return [
        {
            "platform": "weibo",
            "id": "w1",
            "author_hash": "kol_alice_aaaaaa",
            "content": "试用感受：很顶 #移动电源",
            "sentiment": "positive",
            "posted_at": datetime(2026, 5, 18, 10),
        },
        {
            "platform": "weibo",
            "id": "w2",
            "author_hash": "kol_alice_aaaaaa",
            "content": "续测一周：稳",
            "sentiment": "positive",
            "posted_at": datetime(2026, 5, 19, 9),
        },
        {
            "platform": "xhs",
            "id": "x1",
            "author_hash": "kol_bob_bbbbbb",
            "content": "拔草帖：发热严重",
            "sentiment": "negative",
            "posted_at": datetime(2026, 5, 19, 18),
        },
    ]


class TestSeedReport:
    def test_basic_shape_and_counts(self) -> None:
        report = build_seed_report(
            "proj-1",
            products=_make_products(),
            reviews=_make_reviews(),
            posts=_make_posts(),
            now=NOW,
        )
        assert report["project_id"] == "proj-1"
        assert report["generated_at"] == "2026-05-20T12:00:00"
        # 4 raw products → 3 after dedup (jd:1 collapsed).
        assert report["counts"]["products"] == 3
        assert report["counts"]["reviews"] == 4
        assert report["counts"]["posts"] == 3

    def test_sentiment_distribution(self) -> None:
        report = build_seed_report("p", reviews=_make_reviews())
        assert report["review_sentiment_distribution"] == {
            "positive": 2,
            "negative": 1,
            "neutral": 1,
        }

    def test_timeline_buckets_per_day_and_sentiment(self) -> None:
        report = build_seed_report("p", posts=_make_posts())
        timeline = report["sentiment_volume_timeline"]
        # Sorted by (day, sentiment).
        assert timeline == [
            {"date": "2026-05-18", "sentiment": "positive", "count": 1},
            {"date": "2026-05-19", "sentiment": "negative", "count": 1},
            {"date": "2026-05-19", "sentiment": "positive", "count": 1},
        ]

    def test_top_kols_ranked(self) -> None:
        report = build_seed_report("p", posts=_make_posts())
        top = report["top_kols"]
        assert top[0] == {"author_hash": "kol_alice_aaaaaa", "post_count": 2}
        assert top[1] == {"author_hash": "kol_bob_bbbbbb", "post_count": 1}

    def test_cross_platform_alignment(self) -> None:
        report = build_seed_report("p", products=_make_products())
        groups = report["cross_platform_groups"]
        assert any(
            sorted(ids) == ["jd:1", "tb:1"] for ids in groups.values()
        ), groups

    def test_summary_text_mentions_product_count(self) -> None:
        report = build_seed_report(
            "p",
            products=_make_products(),
            reviews=_make_reviews(),
            posts=_make_posts(),
        )
        assert "覆盖 3 件商品" in report["summary_text"]
        # Avg price line included when prices are present.
        assert "平均价" in report["summary_text"]

    def test_empty_input_safe(self) -> None:
        report = build_seed_report("empty")
        assert report["counts"] == {
            "products": 0,
            "reviews": 0,
            "posts": 0,
            "cross_platform_groups": 0,
        }
        assert report["summary_text"].startswith("暂无可用数据")
