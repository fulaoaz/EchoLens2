"""Reliability-tier threshold contract — backend half.

This file pins the ``(label, slug)`` outcome of every meaningful boundary
value so the threshold can never silently drift. The ``frontend`` half lives
at:

    frontend/src/composables/__tests__/useReliabilityTier.spec.ts

If you change ``STRONG_THRESHOLD`` / ``FAIR_THRESHOLD`` /
``tier_for`` in ``app/services/reliability_tier.py``, the matching frontend
table in ``useReliabilityTier.ts`` MUST be updated in lock-step or both test
files turn red simultaneously. That dual-failure is the whole point — it is
the guard rail that stops the dashboard chip and the printed/PDF report from
classifying the same snapshot value into different tiers.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services import report_builder
from app.services.reliability_tier import (
    FAIR_THRESHOLD,
    STRONG_THRESHOLD,
    tier_for,
)

# Boundary sample set — kept identical (modulo language) with the matching
# array in ``useReliabilityTier.spec.ts`` so the two halves of the contract
# walk through the same values.
_SAMPLES: list[tuple[Any, tuple[str, str]]] = [
    # weak: strictly below FAIR_THRESHOLD (0.4)
    (0.0, ("弱", "weak")),
    (0.1, ("弱", "weak")),
    (0.39, ("弱", "weak")),
    (0.3999999, ("弱", "weak")),
    # fair: [FAIR_THRESHOLD, STRONG_THRESHOLD)
    (0.4, ("一般", "fair")),
    (0.5, ("一般", "fair")),
    (0.69, ("一般", "fair")),
    (0.6999999, ("一般", "fair")),
    # strong: >= STRONG_THRESHOLD (0.7)
    (0.7, ("强", "strong")),
    (0.85, ("强", "strong")),
    (1.0, ("强", "strong")),
    # int round-trip — JSON snapshots may surface integer 0/1 boundary values
    (0, ("弱", "weak")),
    (1, ("强", "strong")),
    # unknown — None / unparseable input
    (None, ("未知", "unknown")),
    ("", ("未知", "unknown")),
    ("abc", ("未知", "unknown")),
    (float("nan"), ("弱", "weak")),  # NaN compares False to all → falls to weak
]


def test_thresholds_are_pinned() -> None:
    """Pinning guards against accidental edits to the authoritative numbers."""
    assert STRONG_THRESHOLD == 0.7
    assert FAIR_THRESHOLD == 0.4
    # Strong must dominate fair — preserve the implicit ordering invariant.
    assert STRONG_THRESHOLD > FAIR_THRESHOLD


@pytest.mark.parametrize(("value", "expected"), _SAMPLES)
def test_tier_for_boundary_values(
    value: Any, expected: tuple[str, str]
) -> None:
    """Each boundary sample maps to its canonical ``(label, slug)`` pair."""
    if isinstance(value, float) and value != value:  # noqa: PLR0124 — NaN check
        # NaN: treat the result as best-effort but still deterministic.
        assert tier_for(value) == expected
        return
    assert tier_for(value) == expected


@pytest.mark.parametrize(("value", "expected"), _SAMPLES)
def test_report_builder_alias_matches_shared_module(
    value: Any, expected: tuple[str, str]
) -> None:
    """``report_builder._reliability_tier`` must stay a thin alias.

    The alias is the public name that older call sites and existing
    tests reference — if it ever drifts away from ``tier_for`` we lose the
    single-source-of-truth guarantee. Asserting the alias against the same
    sample set as ``tier_for`` ensures the two never disagree.
    """
    if isinstance(value, float) and value != value:  # noqa: PLR0124
        assert report_builder._reliability_tier(value) == expected
        return
    assert report_builder._reliability_tier(value) == expected
    # Belt-and-suspenders: the alias and the shared function return the same
    # tuple object equality on every sample, not just the parametrized one.
    assert report_builder._reliability_tier(value) == tier_for(value)


def test_label_slug_pairs_are_unique_and_stable() -> None:
    """The four canonical labels/slugs must remain distinct and ASCII-friendly.

    A regression in this test usually means somebody renamed a tier label or
    introduced a duplicate slug — both of which would break the print-mode
    CSS selectors keyed off ``metric-reliability-{slug}``.
    """
    seen_labels = set()
    seen_slugs = set()
    for label, slug in [
        ("强", "strong"),
        ("一般", "fair"),
        ("弱", "weak"),
        ("未知", "unknown"),
    ]:
        # Sanity: the shared module produces THIS exact pair for at least one
        # input on the boundary sample set above.
        produced = {tier_for(v) for v, _ in _SAMPLES}
        assert (label, slug) in produced, (
            f"({label}, {slug}) is never produced by tier_for — sample set drift?"
        )
        seen_labels.add(label)
        seen_slugs.add(slug)
    assert len(seen_labels) == 4
    assert len(seen_slugs) == 4
    # Slugs must be ASCII so the CSS class ``metric-reliability-{slug}`` is
    # always a valid selector.
    for slug in seen_slugs:
        assert slug.isascii() and slug.isalpha()
