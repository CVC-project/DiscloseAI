"""EQS v3 업종 보정값 생성과 점수 변환.

v2는 회사명별 하드코딩 업종과 사람이 정한 cutoff를 사용했다. v3는 같은
KSIC 업종의 실제 재무 패널에서 분위수 기준을 생성한다. 따라서 사용자에게
"동일 업종 유효 표본 N개 중 어느 구간인가"를 그대로 설명할 수 있다.

점수 앵커는 각 지표의 P10/P25/P50/P75/P90이다. 높은 값이 좋은 지표는
각각 0/25/50/75/100점, 낮은 값이 좋은 지표는 반대로 100/75/50/25/0점이다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from math import sqrt
from typing import Iterable, Optional

from .types import FirmPanel


MIN_PEERS = 20
PERCENTILES = (0.10, 0.25, 0.50, 0.75, 0.90)


@dataclass(frozen=True)
class PeerProfile:
    """한 업종·한 지표의 재현 가능한 보정 구간."""

    group: str
    metric: str
    sample_size: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float

    def anchors(self) -> tuple[float, float, float, float, float]:
        return (self.p10, self.p25, self.p50, self.p75, self.p90)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationResult:
    """패널 전체에서 생성한 업종별 보정값."""

    profiles: dict[tuple[str, str], PeerProfile]
    min_peers: int = MIN_PEERS
    financial_min_peers: int = MIN_PEERS

    def profile_for(self, group: str, metric: str) -> Optional[PeerProfile]:
        return self.profiles.get((group, metric))

    def as_dict(self) -> dict:
        return {
            "method": "industry_percentile_v1",
            "min_peers": self.min_peers,
            "financial_min_peers": self.financial_min_peers,
            "percentiles": list(PERCENTILES),
            "profiles": [p.as_dict() for p in self.profiles.values()],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "CalibrationResult":
        """Restore a calibration file produced by :meth:`as_dict`."""
        profiles = {
            (item["group"], item["metric"]): PeerProfile(
                group=item["group"],
                metric=item["metric"],
                sample_size=int(item["sample_size"]),
                p10=float(item["p10"]),
                p25=float(item["p25"]),
                p50=float(item["p50"]),
                p75=float(item["p75"]),
                p90=float(item["p90"]),
            )
            for item in raw.get("profiles", [])
        }
        min_peers = int(raw.get("min_peers", MIN_PEERS))
        return cls(
            profiles=profiles,
            min_peers=min_peers,
            financial_min_peers=int(raw.get("financial_min_peers", min_peers)),
        )


def load_calibration(path: Path) -> CalibrationResult:
    """Load the versioned calibration JSON used by the scoring batch."""
    return CalibrationResult.from_dict(json.loads(path.read_text(encoding="utf-8")))


def is_financial_ksic(code: Optional[str]) -> bool:
    """KSIC 대분류 K(64~66) 여부. DART company.json induty_code를 받는다."""
    return (code or "").strip()[:2] in {"64", "65", "66"}


def peer_groups(code: Optional[str]) -> tuple[str, ...]:
    """세분류 -> 대분류 -> 전체시장 순의 비교 집합 키.

    세분류 표본이 작으면 대분류로 자동 확장한다. 이름 기반 예외를 두지 않는다.
    """
    normalized = "".join(ch for ch in (code or "") if ch.isdigit())
    if is_financial_ksic(normalized):
        # 금융사는 KSIC 세분류·대분류가 작아도 비금융 시장과 섞지 않는다.
        # 마지막 FINANCIAL은 은행·증권·보험을 모두 포함하는 넓은 금융 내부 비교군이다.
        groups = []
        if len(normalized) >= 3:
            groups.append(f"KSIC-{normalized[:3]}")
        if len(normalized) >= 2:
            groups.append(f"KSIC-{normalized[:2]}")
        groups.append("FINANCIAL")
        return tuple(dict.fromkeys(groups))
    if len(normalized) >= 3:
        return (f"KSIC-{normalized[:3]}", f"KSIC-{normalized[:2]}", "MARKET")
    if len(normalized) >= 2:
        return (f"KSIC-{normalized[:2]}", "MARKET")
    return ("MARKET",)


def _valid_years(panel: FirmPanel) -> list:
    return panel.years[-3:]


def _recent_weighted_average(values: list[float]) -> float:
    """최근값일수록 높은 1:2:3 가중평균. 입력은 과거->최근 순서."""
    tail = values[-3:]
    weights = list(range(1, len(tail) + 1))
    return sum(value * weight for value, weight in zip(tail, weights)) / sum(weights)


def metric_values(panel: FirmPanel) -> dict[str, float]:
    """v3 보정에 쓰는 원시 지표.

    M2는 금융업에 맞지 않아 제외한다. 수주산업은 회사명 하드코딩 대신 실제
    계약자산이 존재할 때 매출채권에 합산한다.
    """
    years = _valid_years(panel)
    out: dict[str, float] = {}

    # M2: 최신 2개 연도 매출 대비 미수채권 변화.
    if not is_financial_ksic(panel.industry_code) and len(years) >= 2:
        prev, curr = years[-2], years[-1]
        if prev.revenue and curr.revenue:
            rc_prev = prev.accounts_receivable
            rc_curr = curr.accounts_receivable
            if prev.contract_assets is not None and curr.contract_assets is not None:
                rc_prev = (rc_prev or 0.0) + prev.contract_assets
                rc_curr = (rc_curr or 0.0) + curr.contract_assets
            if rc_prev not in (None, 0) and rc_curr is not None:
                out["m2_receivable_gap"] = (
                    rc_curr / rc_prev - 1 - (curr.revenue / prev.revenue - 1)
                )

    latest = panel.latest()
    if latest and latest.total_equity and latest.total_equity > 0:
        if latest.total_liabilities is not None:
            out["m3_debt_to_equity"] = latest.total_liabilities / latest.total_equity

    margins = [
        y.operating_income / y.revenue
        for y in years
        if y.revenue not in (None, 0) and y.operating_income is not None
    ]
    if len(margins) >= 2:
        out["m4_average_margin"] = _recent_weighted_average(margins)
        out["m4_margin_volatility"] = max(margins) - min(margins)

    if len(years) >= 3:
        base, curr = years[0], years[-1]
        if base.total_equity and base.total_equity > 0 and curr.total_equity and curr.total_equity > 0:
            out["m5_equity_cagr"] = sqrt(curr.total_equity / base.total_equity) - 1
    return out


def _percentile(values: list[float], q: float) -> float:
    """의존성 없는 선형 분위수. 정렬된 표본의 위치를 보간한다."""
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    frac = position - low
    return values[low] + (values[high] - values[low]) * frac


def _is_financial_group(group: str) -> bool:
    return group == "FINANCIAL" or group.startswith(("KSIC-64", "KSIC-65", "KSIC-66"))


def build_calibration(
    panels: Iterable[FirmPanel],
    *,
    min_peers: int = MIN_PEERS,
    financial_min_peers: Optional[int] = None,
) -> CalibrationResult:
    """패널 목록에서 지표별 업종 분위수 보정 테이블을 생성한다."""
    grouped: dict[tuple[str, str], list[float]] = {}
    for panel in panels:
        metrics = metric_values(panel)
        for group in peer_groups(panel.industry_code):
            for metric, value in metrics.items():
                grouped.setdefault((group, metric), []).append(value)

    financial_min_peers = min_peers if financial_min_peers is None else financial_min_peers
    profiles: dict[tuple[str, str], PeerProfile] = {}
    for (group, metric), values in grouped.items():
        required = financial_min_peers if _is_financial_group(group) else min_peers
        if len(values) < required:
            continue
        anchors = tuple(_percentile(values, q) for q in PERCENTILES)
        profiles[(group, metric)] = PeerProfile(group, metric, len(values), *anchors)
    return CalibrationResult(
        profiles=profiles,
        min_peers=min_peers,
        financial_min_peers=financial_min_peers,
    )


def profile_for_panel(
    calibration: CalibrationResult, panel: FirmPanel, metric: str
) -> Optional[PeerProfile]:
    """세분류부터 시장 전체까지 유효 표본이 있는 첫 비교군을 반환한다."""
    for group in peer_groups(panel.industry_code):
        profile = calibration.profile_for(group, metric)
        if profile is not None:
            return profile
    return None


def _piecewise(value: float, anchors: tuple[float, float, float, float, float], scores: tuple[float, float, float, float, float]) -> float:
    if value <= anchors[0]:
        return scores[0]
    for index in range(1, len(anchors)):
        left_value, right_value = anchors[index - 1], anchors[index]
        left_score, right_score = scores[index - 1], scores[index]
        if value <= right_value:
            if right_value == left_value:
                return right_score
            ratio = (value - left_value) / (right_value - left_value)
            return left_score + ratio * (right_score - left_score)
    return scores[-1]


def score_against_peers(value: float, profile: PeerProfile, *, higher_is_better: bool) -> float:
    """P10/P25/P50/P75/P90 앵커를 0~100점으로 선형 변환한다."""
    scores = (0.0, 25.0, 50.0, 75.0, 100.0)
    if not higher_is_better:
        scores = tuple(reversed(scores))
    return round(_piecewise(value, profile.anchors(), scores), 1)
