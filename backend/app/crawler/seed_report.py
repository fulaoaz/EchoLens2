"""Seed report generator.

Aggregates crawled records into a 'first impression' profile of a project.
This is what Step 1 of the new dual-track UI hands off to Step 2.

Pure-Python; no I/O. Caller passes already-cleaned records (dicts, not Pydantic
models) so this stays test-friendly and works even before real crawler data
is available — the demo path can hand-craft records.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime
from statistics import mean
from typing import Any, TypedDict

from .pipeline.align import align_products
from .pipeline.dedup import dedup_records


class SeedReport(TypedDict):
    """Schema of the seed report JSON returned to the frontend."""

    project_id: str
    generated_at: str
    counts: dict[str, int]
    products: list[dict[str, Any]]
    review_sentiment_distribution: dict[str, int]
    sentiment_volume_timeline: list[dict[str, Any]]
    top_kols: list[dict[str, Any]]
    cross_platform_groups: dict[str, list[str]]
    summary_text: str


def _bucket_day(ts: Any) -> str | None:
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d")
    if isinstance(ts, str) and ts:
        try:
            return datetime.fromisoformat(ts).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _summarize(
    products: Sequence[dict[str, Any]],
    review_sent: Counter[str],
    top_kol: tuple[str, int] | None,
) -> str:
    n_products = len(products)
    if not n_products:
        return "暂无可用数据，建议检查关键词或上传更多原始资料。"
    brands = sorted({(p.get("brand") or "未知") for p in products})
    pos = review_sent.get("positive", 0)
    neg = review_sent.get("negative", 0)
    total = sum(review_sent.values())
    pct_pos = (pos * 100 / total) if total else 0.0
    pct_neg = (neg * 100 / total) if total else 0.0
    line_brands = "、".join(brands[:5]) + ("…" if len(brands) > 5 else "")
    line_kol = f"，主要 KOL：{top_kol[0]}（提及 {top_kol[1]} 次）" if top_kol else ""
    return (
        f"覆盖 {n_products} 件商品、{len(brands)} 个品牌（{line_brands}）。"
        f"评论正负比 {pct_pos:.0f}% / {pct_neg:.0f}%{line_kol}。"
    )


def build_seed_report(
    project_id: str,
    products: Iterable[dict[str, Any]] = (),
    reviews: Iterable[dict[str, Any]] = (),
    posts: Iterable[dict[str, Any]] = (),
    *,
    now: datetime | None = None,
) -> SeedReport:
    """Aggregate raw records into a seed report.

    ``products`` / ``reviews`` / ``posts`` are dicts; this function dedups them
    in place, computes summary stats, and returns the JSON-serializable
    seed-report payload defined by ``SeedReport``.
    """
    products_list = dedup_records(products)
    reviews_list = dedup_records(reviews)
    posts_list = dedup_records(posts)

    review_sent: Counter[str] = Counter(
        r.get("sentiment", "unknown") for r in reviews_list
    )

    timeline_counter: Counter[tuple[str, str]] = Counter()
    for p in posts_list:
        day = _bucket_day(p.get("posted_at") or p.get("crawled_at"))
        if day is None:
            continue
        timeline_counter[(day, p.get("sentiment", "unknown"))] += 1
    timeline = [
        {"date": day, "sentiment": sent, "count": cnt}
        for (day, sent), cnt in sorted(timeline_counter.items())
    ]

    kol_counter: Counter[str] = Counter()
    for p in posts_list:
        author = p.get("author_hash")
        if author:
            kol_counter[author] += 1
    top_kols = [
        {"author_hash": author, "post_count": cnt}
        for author, cnt in kol_counter.most_common(10)
    ]

    cross_groups = align_products(products_list)

    # Sample product summary — lightweight, dashboard renders full list separately.
    product_samples: list[dict[str, Any]] = [
        {
            "id": p.get("id"),
            "platform": p.get("platform"),
            "title": p.get("title"),
            "brand": p.get("brand"),
            "price_current": p.get("price_current"),
        }
        for p in products_list[:50]
    ]

    avg_price = (
        mean(
            p["price_current"]
            for p in products_list
            if isinstance(p.get("price_current"), (int, float))
        )
        if any(isinstance(p.get("price_current"), (int, float)) for p in products_list)
        else None
    )

    top_kol = (
        (kol_counter.most_common(1)[0])
        if kol_counter
        else None
    )

    summary = _summarize(products_list, review_sent, top_kol)

    return {
        "project_id": project_id,
        "generated_at": (now or datetime.utcnow()).isoformat(timespec="seconds"),
        "counts": {
            "products": len(products_list),
            "reviews": len(reviews_list),
            "posts": len(posts_list),
            "cross_platform_groups": len(cross_groups),
        },
        "products": product_samples,
        "review_sentiment_distribution": dict(review_sent),
        "sentiment_volume_timeline": timeline,
        "top_kols": top_kols,
        "cross_platform_groups": cross_groups,
        "summary_text": summary
        + (f" 平均价 ¥{avg_price:.0f}。" if avg_price is not None else ""),
    }


__all__ = ["SeedReport", "build_seed_report"]
