"""Financial-industry EQS (F-EQS).

Financial companies have a different balance-sheet structure from industrial
companies. This module scores them against financial peers using dividend,
ROE, capital buffer, profit conversion, and equity growth metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import quantiles
from typing import Any


F_MODULE_LABELS = {
    "F1": "주주환원",
    "F2": "ROE 품질",
    "F3": "자본 완충력",
    "F4": "이익 전환",
    "F5": "자본 성장성",
}


@dataclass(frozen=True)
class FinancialModuleScore:
    name: str
    score: float | None
    raw: float | None
    note: str


def _valid_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def weighted_average(values: list[tuple[int, float | None]]) -> float | None:
    """Return a recent-year weighted average with weights 1:2:3."""
    clean = [(year, _valid_number(value)) for year, value in values]
    clean = [(year, value) for year, value in clean if value is not None]
    if not clean:
        return None
    clean.sort(key=lambda item: item[0])
    tail = clean[-3:]
    weights = list(range(1, len(tail) + 1))
    return sum(value * weight for (_, value), weight in zip(tail, weights)) / sum(weights)


def CAGR(start: float | None, end: float | None, years: int) -> float | None:
    start = _valid_number(start)
    end = _valid_number(end)
    if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def dps_continuity_score(dps_by_year: dict[int, float]) -> float | None:
    """Score dividend maintenance/growth without penalizing healthy growth volatility."""
    if not dps_by_year:
        return None
    years = sorted(dps_by_year)[-3:]
    values = [max(0.0, float(dps_by_year[year])) for year in years]
    if not values:
        return None
    if all(value == 0 for value in values):
        return 0.0
    positive_years = sum(1 for value in values if value > 0)
    base = {1: 35.0, 2: 60.0, 3: 75.0}.get(positive_years, 0.0)
    cuts = sum(1 for prev, cur in zip(values, values[1:]) if prev > 0 and cur < prev * 0.9)
    growth_steps = sum(1 for prev, cur in zip(values, values[1:]) if cur > prev * 1.05)
    score = base - cuts * 20.0 + growth_steps * 7.5
    if positive_years == len(values) and not cuts:
        score += 10.0
    return max(0.0, min(100.0, score))


def percentile_profile(values: list[float]) -> dict[str, float] | None:
    clean = sorted(value for value in values if _valid_number(value) is not None)
    if len(clean) < 5:
        return None
    qs = quantiles(clean, n=100, method="inclusive")
    return {
        "p10": qs[9],
        "p25": qs[24],
        "p50": qs[49],
        "p75": qs[74],
        "p90": qs[89],
    }


def percentile_score(value: float | None, profile: dict[str, float] | None) -> float | None:
    value = _valid_number(value)
    if value is None or not profile:
        return None
    points = [
        (profile["p10"], 0.0),
        (profile["p25"], 25.0),
        (profile["p50"], 50.0),
        (profile["p75"], 75.0),
        (profile["p90"], 100.0),
    ]
    if value <= points[0][0]:
        return 0.0
    if value >= points[-1][0]:
        return 100.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            return round(y0 + (value - x0) / (x1 - x0) * (y1 - y0), 1)
    return None


def grade(total: float | None) -> str:
    if total is None:
        return "N/A"
    if total >= 75:
        return "A"
    if total >= 60:
        return "B"
    if total >= 50:
        return "C"
    if total >= 25:
        return "D"
    return "F"
