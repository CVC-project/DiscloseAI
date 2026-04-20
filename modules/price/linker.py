"""공시 ↔ 주가 연결 파이프라인.

역할:
  1. shared DB의 DisclosureData에서 미처리 공시 조회
  2. yfinance로 해당 종목 주가 수집 (collector)
  3. 공시 후 5일 변동 라벨링 (labeler)
  4. 결과를 shared DB의 PriceData에 저장

모듈 간 연결은 import 금지 → shared DB 테이블로만 데이터 공유 (CLAUDE.md 규칙).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from shared.db import get_session
from shared.models import DisclosureData, PriceData

from modules.price.collector import collect_prices, fetch_prices, MARKET_SUFFIX
from modules.price.labeler import label_disclosure

logger = logging.getLogger(__name__)

# 주가 수집 범위: 공시일 기준 앞뒤로 얼마나 가져올지
_PRE_DAYS = 5    # 공시 전 버퍼 (거래일 기준이 아닌 달력일)
_POST_DAYS = 15  # 공시 후 버퍼 (5거래일 확보를 위해 여유 있게)


def fetch_unlinked_disclosures(limit: int = 500) -> list[DisclosureData]:
    """shared DB에서 아직 주가 라벨이 없는 공시 조회.

    PriceData에 해당 disclosure_id가 없는 것만 가져옴.
    """
    session = get_session()
    try:
        # NOT EXISTS 서브쿼리 — notin_(대량 set) 대비 DB 성능 우수
        linked_subq = (
            session.query(PriceData.disclosure_id)
            .filter(PriceData.disclosure_id == DisclosureData.disclosure_id)
            .correlate(DisclosureData)
            .exists()
        )
        rows = (
            session.query(DisclosureData)
            .filter(
                ~linked_subq,
                DisclosureData.disclosure_date.isnot(None),
                DisclosureData.corp_code.isnot(None),
            )
            .order_by(DisclosureData.disclosure_date.desc())
            .limit(limit)
            .all()
        )
        logger.info("미연결 공시: %d건", len(rows))
        return rows
    finally:
        session.close()


def _detect_market(corp_code: str) -> str:
    """corp_code로 시장 구분 추정.

    완전한 구분은 KRX 종목 목록 DB 필요.
    현재는 코드 패턴으로 1차 추정:
      - 0으로 시작하는 6자리 → KOSPI 가능성 높음
      - 그 외 → KOSDAQ 가능성 높음
    link_single()에서 KOSPI 실패 시 KOSDAQ으로 폴백.
    """
    if corp_code.startswith("0"):
        return "KOSPI"
    return "KOSDAQ"


def push_to_shared(
    corp_code: str,
    label_result: dict,
    prices: list[dict],
) -> int:
    """라벨링 결과 + 주가 시계열을 shared PriceData에 저장.

    Args:
        corp_code: 기업코드
        label_result: label_disclosure() 반환값
        prices: fetch_prices() 반환값

    Returns:
        저장된 건수
    """
    session = get_session()
    saved = 0
    try:
        existing = {
            (r.corp_code, r.date)
            for r in session.query(PriceData.corp_code, PriceData.date)
            .filter(PriceData.corp_code == corp_code)
            .all()
        }

        for p in prices:
            key = (p["corp_code"], p["date"])
            if key in existing:
                continue

            is_base = p["date"] == label_result.get("base_date")
            row = PriceData(
                corp_code=p["corp_code"],
                date=p["date"],
                close_price=p.get("close_price"),
                daily_return=p.get("daily_return"),
                post_disclosure_5d=label_result["change_pct"] if is_base else None,
                label=label_result["label"] if is_base else None,
                disclosure_id=label_result["disclosure_id"] if is_base else None,
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


def link_single(disclosure: DisclosureData, market: str | None = None) -> bool:
    """공시 1건 처리: 주가 수집 → 라벨링 → shared DB 저장.

    시장 감지 실패 시 KOSPI → KOSDAQ 순으로 폴백.

    Returns:
        성공 여부
    """
    corp_code = disclosure.corp_code
    disc_date: date = disclosure.disclosure_date
    start = disc_date - timedelta(days=_PRE_DAYS)
    end = disc_date + timedelta(days=_POST_DAYS)

    # 시장 결정 — 명시 없으면 추정 후 폴백
    markets_to_try = [market] if market else [_detect_market(corp_code)]
    if markets_to_try[0] == "KOSPI":
        markets_to_try.append("KOSDAQ")
    else:
        markets_to_try.append("KOSPI")

    prices: list[dict] = []
    resolved_market = markets_to_try[0]
    for mkt in markets_to_try:
        # 1. 주가 수집 (로컬 DB에도 저장, 캐시 활용)
        collect_prices(corp_code, mkt, start, end)
        prices = fetch_prices(corp_code, mkt, start, end)
        if prices:
            resolved_market = mkt
            break
        logger.debug("주가 없음(%s), 폴백: %s", mkt, corp_code)

    if not prices:
        logger.warning("주가 수집 실패 (KOSPI+KOSDAQ 모두): %s", corp_code)
        return False

    # 2. 라벨링 (로컬 DB 업데이트)
    result = label_disclosure(
        corp_code=corp_code,
        disclosure_date=disc_date,
        disclosure_id=disclosure.disclosure_id,
    )
    if result is None:
        logger.warning("라벨링 실패: %s %s", corp_code, disc_date)
        return False

    # 3. shared DB 저장 (fetch_prices 결과 재사용 — 이중 호출 없음)
    pushed = push_to_shared(corp_code, result, prices)
    logger.info(
        "[%s/%s] 연결 완료 — 라벨: %s, 변동: %.2f%%, 저장: %d건",
        corp_code, resolved_market, result["label"], result["change_pct"], pushed,
    )
    return True


def run_pipeline(limit: int = 500) -> dict:
    """미연결 공시 전체 배치 처리.

    Args:
        limit: 한 번에 처리할 최대 공시 수

    Returns:
        {"total": int, "success": int, "failed": int}
    """
    disclosures = fetch_unlinked_disclosures(limit=limit)
    total = len(disclosures)
    success = 0

    for disc in disclosures:
        try:
            ok = link_single(disc)
            if ok:
                success += 1
        except Exception as e:
            logger.error("처리 실패: %s — %s", disc.disclosure_id, e)

    result = {"total": total, "success": success, "failed": total - success}
    logger.info("파이프라인 완료: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline(limit=100)
