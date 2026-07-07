"""공시 후 5일 주가변동 라벨링 — 수혜 / 악재 / 중립"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from modules.price.db import get_local_session
from modules.price.models import PriceLocal

logger = logging.getLogger(__name__)

# 라벨링 임계값 (CLAUDE.md 기준)
POSITIVE_THRESHOLD = 2.0  # +2% 이상 → 수혜
NEGATIVE_THRESHOLD = -2.0  # -2% 이하 → 악재


def _next_trading_day(
    session: Session,
    corp_code: str,
    from_date: date,
    max_days: int = 7,
) -> PriceLocal | None:
    """from_date 다음 날부터 첫 번째 거래일 레코드 반환 (최대 max_days 탐색).

    공시일 당일은 제외: DART 공시는 장 마감 후(16:00~) 접수 가능하므로
    공시 당일 종가는 공시 발표 전 가격일 수 있어 이벤트 스터디 관행상 다음 거래일을 기준으로 사용.
    """
    for offset in range(1, max_days + 1):
        target = from_date + timedelta(days=offset)
        row = (
            session.query(PriceLocal)
            .filter(
                PriceLocal.corp_code == corp_code,
                PriceLocal.date == target,
            )
            .first()
        )
        if row and row.close_price is not None:
            return row
    return None


def _nth_trading_day(
    session: Session,
    corp_code: str,
    from_date: date,
    n: int,
) -> PriceLocal | None:
    """from_date 이후 n번째 거래일 레코드 반환 (DB에 있는 날짜 기준)."""
    rows = (
        session.query(PriceLocal)
        .filter(
            PriceLocal.corp_code == corp_code,
            PriceLocal.date > from_date,
            PriceLocal.close_price.isnot(None),
        )
        .order_by(PriceLocal.date)
        .limit(n)
        .all()
    )
    return rows[-1] if len(rows) == n else None


def compute_label(change_pct: float) -> str:
    """수익률 → 라벨 변환."""
    if change_pct >= POSITIVE_THRESHOLD:
        return "수혜"
    if change_pct <= NEGATIVE_THRESHOLD:
        return "악재"
    return "중립"


def label_disclosure(
    corp_code: str,
    disclosure_date: date,
    disclosure_id: str,
    trading_days: int = 5,
) -> dict | None:
    """단일 공시에 대해 주가변동 계산 + 라벨 부여 후 DB 업데이트.

    Args:
        corp_code: 기업코드
        disclosure_date: 공시일
        disclosure_id: DART 접수번호
        trading_days: 변동 측정 기준 거래일 수 (기본 5)

    Returns:
        {"disclosure_id": str, "change_pct": float, "label": str} 또는 None (데이터 부족)
    """
    session = get_local_session()
    try:
        # 공시일 당일 또는 직후 첫 거래일 종가
        base_row = _next_trading_day(session, corp_code, disclosure_date)
        if base_row is None:
            logger.warning("기준 종가 없음: %s %s", corp_code, disclosure_date)
            return None

        # 기준일로부터 n번째 거래일 종가
        end_row = _nth_trading_day(session, corp_code, base_row.date, trading_days)
        if end_row is None:
            logger.warning(
                "%d거래일 후 데이터 없음: %s (기준일: %s)",
                trading_days,
                corp_code,
                base_row.date,
            )
            return None

        change_pct = (end_row.close_price / base_row.close_price - 1) * 100
        label = compute_label(change_pct)

        # base_row에 라벨 기록
        base_row.post_disclosure_5d = round(change_pct, 4)
        base_row.label = label
        base_row.disclosure_id = disclosure_id
        session.commit()

        logger.info(
            "[%s] %s → %s일 후 %.2f%% → %s",
            corp_code,
            base_row.date,
            trading_days,
            change_pct,
            label,
        )
        return {
            "disclosure_id": disclosure_id,
            "base_date": base_row.date,
            "end_date": end_row.date,
            "change_pct": round(change_pct, 4),
            "label": label,
        }

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def label_bulk(
    disclosures: list[dict],
    trading_days: int = 5,
) -> list[dict]:
    """여러 공시 일괄 라벨링.

    Args:
        disclosures: [
            {"corp_code": str, "disclosure_date": date, "disclosure_id": str},
            ...
        ]
        trading_days: 측정 기준 거래일 수

    Returns:
        라벨링 성공 결과 리스트
    """
    results = []
    for d in disclosures:
        result = label_disclosure(
            corp_code=d["corp_code"],
            disclosure_date=d["disclosure_date"],
            disclosure_id=d["disclosure_id"],
            trading_days=trading_days,
        )
        if result:
            results.append(result)

    success = len(results)
    total = len(disclosures)
    logger.info("라벨링 완료: %d/%d건 성공", success, total)
    return results


def label_summary(corp_code: str | None = None) -> dict:
    """DB에 저장된 라벨 분포 요약.

    Args:
        corp_code: 특정 기업만 조회 (None이면 전체)

    Returns:
        {"수혜": int, "악재": int, "중립": int, "미라벨": int, "total": int}
    """
    session = get_local_session()
    try:
        query = session.query(PriceLocal)
        if corp_code:
            query = query.filter(PriceLocal.corp_code == corp_code)
        rows = query.all()

        counts: dict[str, int] = {"수혜": 0, "악재": 0, "중립": 0, "미라벨": 0}
        for r in rows:
            key = r.label if r.label in counts else "미라벨"
            counts[key] += 1
        counts["total"] = len(rows)
        return counts
    finally:
        session.close()
