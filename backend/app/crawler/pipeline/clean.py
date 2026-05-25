"""Cleaning utilities: PII masking, HTML strip, whitespace normalization.

Used by adapters before constructing schema models. No network. No deps beyond
the standard library so this stays cheap to call inside hot loops.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

# --- PII masking ---------------------------------------------------------

# Mainland China mobile (1[3-9]xxxxxxxxx — 11 digits, fairly tight pattern).
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# Generic email — RFC-ish, deliberately permissive.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Mainland China ID card (18 digits with optional X check digit, or legacy 15-digit).
_IDCARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx]|\d{15})(?!\d)")


def mask_pii(text: str) -> str:
    """Mask PII (phone, email, id-card) in a free-text string.

    Replaces matches with a fixed token so downstream layers can detect that
    masking happened (and so we never accidentally roundtrip raw PII into a
    model).
    """
    if not text:
        return text
    out = _PHONE_RE.sub("[PHONE]", text)
    out = _EMAIL_RE.sub("[EMAIL]", out)
    out = _IDCARD_RE.sub("[IDCARD]", out)
    return out


# --- HTML stripping ------------------------------------------------------

class _StripParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def strip_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace.

    - Decodes HTML entities (``&amp;`` → ``&``).
    - Drops ``<script>`` / ``<style>`` content along with tags.
    - Normalizes runs of whitespace to a single space and trims edges.
    """
    if not text:
        return text
    # Drop script/style bodies before parsing so their text doesn't leak.
    cleaned = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parser = _StripParser()
    parser.feed(cleaned)
    plain = parser.get_text()
    # Collapse whitespace runs (incl. \xa0 nbsp).
    return re.sub(r"\s+", " ", plain.replace("\xa0", " ")).strip()


def normalize_whitespace(text: str) -> str:
    """Trim + collapse internal whitespace runs to a single space."""
    if not text:
        return text
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["mask_pii", "strip_html", "normalize_whitespace"]
