"""yfinance 주가 수집 — KOSPI(.KS) / KOSDAQ(.KQ)"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from functools import lru_cache

import yfinance as yf

from modules.price.db import get_local_session, init_local_db
from modules.price.models import PriceLocal

logger = logging.getLogger(__name__)

# 캐시 TTL: 5분 (yfinance 중복 호출 방지)
_CACHE_TTL = 300
_cache: dict[str, tuple[float, list[dict]]] = {}  # key → (timestamp, data)

MARKET_SUFFIX = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}


def _ticker(corp_code: str, market: str) -> str:
    """yfinance 티커 생성 (예: '005930' + 'KOSPI' → '005930.KS')."""
    suffix = MARKET_SUFFIX.get(market.upper(), ".KS")
    return f"{corp_code}{suffix}"


def fetch_prices(
    corp_code: str,
    market: str,
    start: date,
    end: date,
) -> list[dict]:
    """yfinance로 일별 종가 + 수익률 수집 (5분 캐시 적용).

    Args:
        corp_code: 기업코드 (예: '005930')
        market: 'KOSPI' 또는 'KOSDAQ'
        start: 조회 시작일
        end: 조회 종료일 (해당 일 포함)

    Returns:
        [{"corp_code": str, "date": date, "close_price": float, "daily_return": float}, ...]
    """
    cache_key = f"{corp_code}_{market}_{start}_{end}"
    now = time.time()

    if cache_key in _cache:
        cached_at, cached_data = _cache[cache_key]
        if now - cached_at < _CACHE_TTL:
            logger.debug("캐시 사용: %s", cache_key)
            return cached_data

    ticker = _ticker(corp_code, market)
    # yfinance end는 exclusive이므로 하루 추가
    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    if df is None or df.empty:
        logger.warning("주가 데이터 없음: %s (%s ~ %s)", ticker, start, end)
        _cache[cache_key] = (now, [])
        return []

    # 종가 컬럼 정규화
    # yfinance 1.x: MultiIndex 튜플 컬럼 ('Close', '005930.KS') → 평탄화
    # yfinance 0.x: 단순 문자열 컬럼 'Close'
    import pandas as pd
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    close_col = next(
        (c for c in df.columns if str(c).lower() == "close"),
        None,
    )
    if close_col is None:
        logger.error("종가 컬럼 없음: %s", df.columns.tolist())
        return []

    close_series = df[close_col].dropna()
    pct_series = close_series.pct_change() * 100  # 일간 수익률(%)

    results = []
    for idx in close_series.index:
        close_val = close_series.loc[idx]
        ret_val = pct_series.loc[idx]
        results.append(
            {
                "corp_code": corp_code,
                "date": idx.date() if hasattr(idx, "date") else idx,
                "close_price": float(close_val),
                "daily_return": float(ret_val) if ret_val == ret_val else None,  # NaN → None
            }
        )

    _cache[cache_key] = (now, results)
    logger.info("수집 완료: %s %d건", ticker, len(results))
    return results


def save_prices(records: list[dict]) -> int:
    """수집된 주가 레코드를 로컬 DB에 저장 (같은 corp_code+date 중복 건너뜀).

    Returns:
        저장된 건수
    """
    if not records:
        return 0

    session = get_local_session()
    saved = 0
    try:
        # 기존 (corp_code, date) 쌍 조회 — 저장 대상 corp_code만 필터링
        corp_codes = {rec["corp_code"] for rec in records}
        existing = {
            (r.corp_code, r.date)
            for r in session.query(PriceLocal.corp_code, PriceLocal.date)
            .filter(PriceLocal.corp_code.in_(corp_codes))
            .all()
        }

        for rec in records:
            key = (rec["corp_code"], rec["date"])
            if key in existing:
                continue
            row = PriceLocal(
                corp_code=rec["corp_code"],
                date=rec["date"],
                close_price=rec.get("close_price"),
                daily_return=rec.get("daily_return"),
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


def collect_prices(
    corp_code: str,
    market: str,
    start: date,
    end: date,
) -> int:
    """주가 수집 + 저장 통합 실행.

    Returns:
        저장된 건수
    """
    init_local_db()
    records = fetch_prices(corp_code, market, start, end)
    saved = save_prices(records)
    logger.info(
        "[%s] 저장 완료: %d건 (%s ~ %s)", corp_code, saved, start, end
    )
    return saved


def collect_bulk(
    targets: list[dict],
    start: date,
    end: date,
) -> dict[str, int]:
    """여러 종목 일괄 수집.

    Args:
        targets: [{"corp_code": "005930", "market": "KOSPI"}, ...]
        start: 조회 시작일
        end: 조회 종료일

    Returns:
        {corp_code: 저장건수, ...}
    """
    init_local_db()
    result: dict[str, int] = {}
    for t in targets:
        corp_code = t["corp_code"]
        market = t.get("market", "KOSPI")
        result[corp_code] = collect_prices(corp_code, market, start, end)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 사용 예시: 삼성전자 최근 1년
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    collect_prices("005930", "KOSPI", start_date, end_date)
