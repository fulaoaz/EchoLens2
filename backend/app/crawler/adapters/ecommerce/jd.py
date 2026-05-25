"""JD.com adapter — product / review extraction. Stub."""

from __future__ import annotations


async def fetch_product(url: str) -> None:  # pragma: no cover - stub
    raise NotImplementedError("M1: implement jd product adapter")


async def fetch_reviews(product_id: str, limit: int = 100) -> None:  # pragma: no cover
    raise NotImplementedError("M1: implement jd reviews adapter")
