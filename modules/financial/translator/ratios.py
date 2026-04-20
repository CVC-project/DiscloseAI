"""수익성·효율성 재무비율 계산.

FirmYear에 이미 들어 있는 숫자만으로 다섯 가지 비율을 산출한다.
필요 컬럼이 None이거나 분모가 0이면 해당 비율은 None.

- 매출총이익률 = (매출 - 매출원가) / 매출
- 영업이익률   = 영업이익 / 매출
- 순이익률     = 순이익 / 매출
- ROE          = 순이익 / 자본총계
- ROA          = 순이익 / 자산총계
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional

from ..eqs.types import FirmYear


@dataclass
class Ratios:
    """단일 연도 재무비율 묶음. 값은 모두 퍼센트(%)."""

    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None

    def as_dict(self) -> Dict[str, Optional[float]]:
        return asdict(self)


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or not den:
        return None
    return num / den * 100


def compute_ratios(year: FirmYear) -> Ratios:
    """FirmYear → Ratios. 누락 데이터는 자동으로 None."""
    gross_profit: Optional[float] = None
    if year.revenue is not None and year.cogs is not None:
        gross_profit = year.revenue - year.cogs

    return Ratios(
        gross_margin=_safe_div(gross_profit, year.revenue),
        operating_margin=_safe_div(year.operating_income, year.revenue),
        net_margin=_safe_div(year.net_income, year.revenue),
        roe=_safe_div(year.net_income, year.total_equity),
        roa=_safe_div(year.net_income, year.total_assets),
    )


# 각 비율 UI 라벨. dashboard.py에서 import.
LABELS: Dict[str, str] = {
    "gross_margin": "매출총이익률",
    "operating_margin": "영업이익률",
    "net_margin": "순이익률",
    "roe": "ROE",
    "roa": "ROA",
}
