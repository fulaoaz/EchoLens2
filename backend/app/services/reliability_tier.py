"""Single source of truth for the weakest-link reliability tier mapping.

The dashboard chip (``frontend/src/components/decision/DecisionBoardPanel.vue``
via ``frontend/src/composables/useReliabilityTier.ts``), the printed markdown
report (``app/services/report_builder._reliability_tier``), and the print/PDF
HTML stylesheet (``app/services/report_html._RELIABILITY_TIER_SLUG`` plus the
``metric-reliability-{strong|fair|weak|unknown}`` CSS rules) all classify the
exact same snapshot value into the exact same tier. To keep that contract from
silently drifting, every backend caller imports from THIS module — there is no
local duplicate of ``0.7`` / ``0.4`` anywhere else in ``app/services/``.

The frontend composable mirrors the same constants in TypeScript. The
double-sided contract is enforced by:

- ``backend/tests/test_reliability_tier.py``
- ``frontend/src/composables/__tests__/useReliabilityTier.spec.ts``

Both files exercise the same edge-value sample set so any future threshold
change must update both ends or the tests turn red simultaneously.
"""

from __future__ import annotations

from typing import Final

# ---------- thresholds (the single authoritative copy) -----------------------

# A reliability ``>= STRONG_THRESHOLD`` is considered strong evidence.
STRONG_THRESHOLD: Final[float] = 0.7

# A reliability ``>= FAIR_THRESHOLD`` (and below ``STRONG_THRESHOLD``) is fair.
# Below ``FAIR_THRESHOLD`` is weak. ``None`` / unparseable values are unknown.
FAIR_THRESHOLD: Final[float] = 0.4


# ---------- canonical (label, slug) pairs ------------------------------------

# The ordered list mirrors ``frontend/src/composables/useReliabilityTier.ts``
# so anyone scanning the file finds the same four buckets in the same order.
TIER_STRONG: Final[tuple[str, str]] = ("强", "strong")
TIER_FAIR: Final[tuple[str, str]] = ("一般", "fair")
TIER_WEAK: Final[tuple[str, str]] = ("弱", "weak")
TIER_UNKNOWN: Final[tuple[str, str]] = ("未知", "unknown")

# Public ordered tuple — used by ``report_html`` to derive the (label → slug)
# map without re-typing it. Order is meaningful for any future iteration that
# needs strong/fair/weak/unknown sequencing for, say, a legend.
TIERS: Final[tuple[tuple[str, str], ...]] = (
    TIER_STRONG,
    TIER_FAIR,
    TIER_WEAK,
    TIER_UNKNOWN,
)


def tier_for(value: float | int | None) -> tuple[str, str]:
    """Map a weakest-link reliability value into ``(label_zh, slug)``.

    Rules (must match
    ``frontend/src/composables/useReliabilityTier.ts::tierFor``):

    - ``value is None`` → ``("未知", "unknown")``
    - ``float(value)`` raises (e.g. value is ``""`` / ``"abc"``) →
      ``("未知", "unknown")``
    - ``f >= STRONG_THRESHOLD`` (0.7) → ``("强", "strong")``
    - ``f >= FAIR_THRESHOLD`` (0.4) → ``("一般", "fair")``
    - else → ``("弱", "weak")``

    The function intentionally accepts ``int`` as well as ``float`` because
    decision snapshots round-trip through JSON and may surface integer 0/1
    values for boundary cases.
    """
    if value is None:
        return TIER_UNKNOWN
    try:
        f = float(value)
    except (TypeError, ValueError):
        return TIER_UNKNOWN
    if f >= STRONG_THRESHOLD:
        return TIER_STRONG
    if f >= FAIR_THRESHOLD:
        return TIER_FAIR
    return TIER_WEAK


# Convenience: ``label → slug`` mapping derived from ``TIERS`` so downstream
# modules don't hand-roll the dict (and risk falling out of sync).
LABEL_TO_SLUG: Final[dict[str, str]] = {label: slug for label, slug in TIERS}


__all__ = [
    "STRONG_THRESHOLD",
    "FAIR_THRESHOLD",
    "TIER_STRONG",
    "TIER_FAIR",
    "TIER_WEAK",
    "TIER_UNKNOWN",
    "TIERS",
    "LABEL_TO_SLUG",
    "tier_for",
]
