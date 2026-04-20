"""VKOSPI (한국판 VIX) 수집 — pykrx 사용"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from pykrx import stock

from modules.price.db import get_local_session, init_local_db
from modules.price.models import VkospiLocal

logger = logging.getLogger(__name__)

# VKOSPI 저변동 임계값 (이하이면 is_low_vol=True)
LOW_VOL_THRESHOLD = 15.0


def fetch_vkospi(start: date, end: date) -> list[dict]:
    """pykrx로 VKOSPI 일별 데이터 수집.

    Args:
        start: 조회 시작일
        end: 조회 종료일

    Returns:
        [{"date": date, "vkospi": float}, ...]
    """
    df = stock.get_index_ohlcv(
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
        "1005",  # KRX 인덱스 코드: VKOSPI
    )
    if df is None or df.empty:
        logger.warning("VKOSPI 데이터 없음: %s ~ %s", start, end)
        return []

    results = []
    for idx, row in df.iterrows():
        close = row.get("종가") or row.get("Close")
        if close is None:
            continue
        results.append({"date": idx.date(), "vkospi": float(close)})
    return results


def save_vkospi(records: list[dict]) -> int:
    """수집된 VKOSPI 레코드를 로컬 DB에 저장 (중복 날짜 건너뜀).

    Returns:
        저장된 건수
    """
    if not records:
        return 0

    session = get_local_session()
    saved = 0
    try:
        existing_dates = {r.date for r in session.query(VkospiLocal.date).all()}
        for rec in records:
            if rec["date"] in existing_dates:
                continue
            row = VkospiLocal(
                date=rec["date"],
                vkospi=rec["vkospi"],
                is_low_vol=rec["vkospi"] < LOW_VOL_THRESHOLD,
            )
            session.add(row)
            saved += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return saved


def collect_vkospi(start: date, end: date) -> int:
    """VKOSPI 수집 + 저장 통합 실행.

    Returns:
        저장된 건수
    """
    init_local_db()
    records = fetch_vkospi(start, end)
    saved = save_vkospi(records)
    logger.info("VKOSPI 저장 완료: %d건 (%s ~ %s)", saved, start, end)
    return saved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 3)  # 최근 3년
    collect_vkospi(start_date, end_date)
