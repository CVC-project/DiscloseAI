"""저변동 시기(VKOSPI 낮은 날) 공시 효과 분리 유틸리티.

핵심 아이디어:
  VKOSPI가 낮을 때는 시장 노이즈가 작아서 공시 자체의 효과가
  주가 변동에 더 순수하게 반영된다.
  → 저변동 시기 공시만 필터링하면 라벨 정확도가 올라간다.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal

from sqlalchemy.orm import Session

from modules.price.models import PriceLocal, VkospiLocal

logger = logging.getLogger(__name__)

VolLabel = Literal["low", "medium", "high"]


def get_vkospi_on_date(session: Session, target_date: date) -> float | None:
    """특정 날짜의 VKOSPI 값 반환 (없으면 None)."""
    row = session.query(VkospiLocal).filter(VkospiLocal.date == target_date).first()
    return row.vkospi if row else None


def classify_volatility(vkospi: float) -> VolLabel:
    """VKOSPI 값을 저/중/고 변동 구간으로 분류.

    기준:
        low    : VKOSPI < 15   (시장 안정, 공시 효과 선명)
        medium : 15 ≤ VKOSPI < 25
        high   : VKOSPI ≥ 25  (시장 불안, 공시 노이즈 큼)
    """
    if vkospi < 15.0:
        return "low"
    if vkospi < 25.0:
        return "medium"
    return "high"


def filter_low_volatility_disclosures(
    session: Session,
    disclosure_ids: list[str] | None = None,
) -> list[PriceLocal]:
    """저변동 시기(is_low_vol=True)에 해당하는 공시-주가 레코드 반환.

    Args:
        session: 로컬 DB 세션
        disclosure_ids: 특정 공시 ID 목록으로 좁힐 경우 지정 (None이면 전체)

    Returns:
        저변동 시기 공시 레코드 리스트
    """
    # VKOSPI 저변동 날짜 집합
    low_vol_dates: set[date] = {
        row.date
        for row in session.query(VkospiLocal)
        .filter(VkospiLocal.is_low_vol.is_(True))
        .all()
    }

    if not low_vol_dates:
        logger.warning(
            "저변동 날짜 데이터 없음 — vkospi_collector.py를 먼저 실행하세요."
        )
        return []

    query = session.query(PriceLocal).filter(
        PriceLocal.date.in_(low_vol_dates),
        PriceLocal.disclosure_id.isnot(None),
    )
    if disclosure_ids:
        query = query.filter(PriceLocal.disclosure_id.in_(disclosure_ids))

    results = query.all()
    logger.info("저변동 시기 공시 레코드: %d건", len(results))
    return results


def compute_label_purity(
    all_records: list[PriceLocal],
    low_vol_records: list[PriceLocal],
) -> dict:
    """전체 vs 저변동 시기의 라벨 분포를 비교해 노이즈 감소 효과를 측정.

    Returns:
        {
            "total": {"수혜": int, "악재": int, "중립": int, "total": int},
            "low_vol": {"수혜": int, "악재": int, "중립": int, "total": int},
            "non_neutral_ratio": {"total": float, "low_vol": float},
        }
    """

    def _count(records: list[PriceLocal]) -> dict:
        counts: dict[str, int] = {"수혜": 0, "악재": 0, "중립": 0}
        for r in records:
            label = r.label or "중립"
            if label in counts:
                counts[label] += 1
        counts["total"] = len(records)
        return counts

    total_counts = _count(all_records)
    low_vol_counts = _count(low_vol_records)

    def _non_neutral_ratio(counts: dict) -> float:
        t = counts["total"]
        if t == 0:
            return 0.0
        return round((counts["수혜"] + counts["악재"]) / t, 4)

    return {
        "total": total_counts,
        "low_vol": low_vol_counts,
        "non_neutral_ratio": {
            "total": _non_neutral_ratio(total_counts),
            "low_vol": _non_neutral_ratio(low_vol_counts),
        },
    }
