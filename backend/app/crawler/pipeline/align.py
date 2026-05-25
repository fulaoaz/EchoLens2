"""Cross-platform product alignment.

Group product records that look like the same physical product across
different platforms (taobao / jd / pdd) by normalized brand+title.

Implementation note
-------------------
Real-world alignment needs catalog matching (GTIN, brand attribute, model
number). For M1.2 we ship a deterministic baseline:

1. Normalize each title: lowercase, drop ASCII/CJK punctuation, collapse
   whitespace, drop common marketing tokens (``官方旗舰店``, ``正品``, ``包邮``).
2. Group by ``(brand_lower, title_normalized)``.
3. Return ``{group_key: [product_id, ...]}``.

This is good enough to power the seed report's "same product, different
platform price" panel. Fuzzy matching can replace the keying step later
without changing the function signature.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_MARKETING_TOKENS = (
    "官方旗舰店",
    "旗舰店",
    "官方",
    "正品",
    "包邮",
    "新款",
    "热销",
    "授权",
    "直营",
)

_PUNCT_RE = re.compile(r"[\s\-_/\\|•·，。、！？：；'\"“”‘’（）()\[\]【】{}<>~`!@#\$%\^&\*\+=]+")


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    out = title.lower()
    for tok in _MARKETING_TOKENS:
        out = out.replace(tok.lower(), " ")
    out = _PUNCT_RE.sub(" ", out)
    return " ".join(out.split())


def align_products(records: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    """Group ``records`` (dicts with ``id``, ``brand``, ``title``).

    Returns ``{"<brand>|<normalized_title>": [id1, id2, ...]}`` containing
    only groups with 2+ ids (single-platform products are dropped from the
    alignment view).
    """
    groups: dict[str, list[str]] = {}
    for rec in records:
        rid = rec.get("id")
        if not rid:
            continue
        brand = (rec.get("brand") or "").strip().lower()
        title = _normalize_title(rec.get("title") or "")
        if not title:
            continue
        key = f"{brand}|{title}"
        groups.setdefault(key, []).append(str(rid))
    return {k: ids for k, ids in groups.items() if len(ids) > 1}


__all__ = ["align_products"]
