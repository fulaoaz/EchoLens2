"""Deduplicate crawled records.

Two-pass dedup:
1. Drop records that share the same ``(platform, id)`` key — keep the most
   recent (largest ``crawled_at``) when present, otherwise the first.
2. Drop records whose normalized content already appeared (sha256 fingerprint
   on the cleaned text). This catches re-posts under different ids.

Records are plain dicts; this layer runs before schema validation so the
caller can mix Product/Review/Post shapes. The only required keys are:
- ``platform`` (str)
- ``id`` (str)
- one of ``content`` / ``title`` / ``text`` for the content fingerprint
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from .clean import normalize_whitespace


def _content_of(rec: dict[str, Any]) -> str:
    for key in ("content", "title", "text"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip():
            return normalize_whitespace(v)
    return ""


def _fingerprint(rec: dict[str, Any]) -> str:
    body = _content_of(rec).lower()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _crawled_at(rec: dict[str, Any]) -> datetime | None:
    ts = rec.get("crawled_at")
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None
    return None


def dedup_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return ``records`` with duplicates removed. See module docstring."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in records:
        platform = rec.get("platform")
        rid = rec.get("id")
        if not platform or not rid:
            # Untyped record — keep but don't dedup by key.
            by_key[(str(id(rec)), "")] = rec
            continue
        key = (str(platform), str(rid))
        if key not in by_key:
            by_key[key] = rec
            continue
        existing = by_key[key]
        # Keep the newer one (or the existing one if newer is unknown).
        new_ts = _crawled_at(rec)
        old_ts = _crawled_at(existing)
        if new_ts is not None and (old_ts is None or new_ts > old_ts):
            by_key[key] = rec

    seen_fingerprints: set[str] = set()
    out: list[dict[str, Any]] = []
    for rec in by_key.values():
        fp = _fingerprint(rec)
        if fp == hashlib.sha256(b"").hexdigest():
            # No content — keep, can't fingerprint.
            out.append(rec)
            continue
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)
        out.append(rec)
    return out


__all__ = ["dedup_records"]
