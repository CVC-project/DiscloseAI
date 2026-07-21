"""universe/marketcap.py — 시가총액 스냅샷 (U0, U-D6).

원천 우선순위:
  1. pykrx (KRX 정보데이터시스템, 키 불요) — 이 환경에서 OTP/세션 호출이 KRX에
     거부(LOGOUT)되어 현재 비활성. 코드는 향후 환경을 위해 유지.
  2. 네이버금융 시가총액순 페이지(finance.naver.com/sise/sise_market_sum) — 시총
     내림차순 정렬 페이지네이션이라 top-400 선정에 정확히 맞고, 인증 불요라
     이 환경에서 안정적으로 동작(registry.py의 KIND와 같은 이유로 선택).
  3. yfinance — 개별 티커 스팟 확인·향후 폴백용(현재 marketcap.py는 미사용,
     대량 조회는 순차 호출 비용이 커 실용적이지 않음 — 필요 시 스팟체크만).

cap_asof에 실제 스냅샷 기준일을 기록해 신선도를 표기한다(U-D6, 폴백 시에도
"언제 데이터인지"는 항상 알 수 있어야 함).
"""

from __future__ import annotations

import logging
import time

import requests
from bs4 import BeautifulSoup

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry

logger = logging.getLogger(__name__)

_NAVER_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_HTTP_TIMEOUT = 15
_RATE_LIMIT_SEC = 0.3
_MAX_PAGES = 60  # 안전장치 — KOSPI+KOSDAQ 합쳐 실측 ~54페이지(50행/페이지)

# universe/PLAN.md U-D6: 시장별 상위 200
TOP_N_PER_MARKET = 200

_SOSOK = {"KOSPI": 0, "KOSDAQ": 1}


def _fetch_naver_page(sosok: int, page: int) -> list[dict]:
    """한 페이지(최대 50행) → [{rank, ticker, name, market_cap_eok}, ...].

    market_cap_eok 단위 = 억원(네이버 표기 그대로, 1억원=100,000,000원).
    """
    r = requests.get(
        _NAVER_URL, params={"sosok": sosok, "page": page}, headers=_HEADERS, timeout=_HTTP_TIMEOUT
    )
    r.raise_for_status()
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.select_one("table.type_2")
    if table is None:
        return []

    rows: list[dict] = []
    for tr in table.select("tr"):
        a = tr.select_one("a.tltle")
        if not a:
            continue
        href = a.get("href", "")
        ticker = href.rsplit("code=", 1)[-1].strip() if "code=" in href else ""
        if not ticker:
            continue
        tds = tr.select("td")
        rank_txt = tds[0].text.strip() if tds else ""
        cap_txt = tds[6].text.strip() if len(tds) > 6 else ""
        try:
            rank = int(rank_txt)
            cap_eok = float(cap_txt.replace(",", ""))
        except ValueError:
            continue
        rows.append(
            {"rank": rank, "ticker": ticker, "name": a.text.strip(), "market_cap_eok": cap_eok}
        )
    return rows


def fetch_naver_ranked(market: str, top_n: int | None = None) -> list[dict]:
    """market('KOSPI'|'KOSDAQ') 시총 내림차순 전량(또는 top_n까지) 조회.

    페이지가 빈 결과를 반환하면(마지막 페이지 초과) 중단.
    """
    sosok = _SOSOK[market]
    all_rows: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        rows = _fetch_naver_page(sosok, page)
        if not rows:
            break
        all_rows.extend(rows)
        if top_n and len(all_rows) >= top_n:
            break
        time.sleep(_RATE_LIMIT_SEC)
    return all_rows[:top_n] if top_n else all_rows


def sync(as_of: str) -> dict:
    """KOSPI+KOSDAQ 전량 시총 스냅샷 → CompanyRegistry.market_cap_krw/cap_asof 갱신.

    Args:
        as_of: 스냅샷 기준일 문자열(예: '2026-07-21') — 호출자가 명시적으로 전달
               (환경의 실제 날짜 신뢰 불확실성을 코드 내부에서 추정하지 않는다).

    Returns: {'KOSPI': n, 'KOSDAQ': n, 'unmatched': [...]}
    """
    session = get_local_session()
    counts = {"KOSPI": 0, "KOSDAQ": 0}
    unmatched: list[str] = []
    try:
        for market in ("KOSPI", "KOSDAQ"):
            logger.info(f"{market} 시총 전량 조회 중 (네이버금융)...")
            rows = fetch_naver_ranked(market)
            logger.info(f"{market}: {len(rows)}건 조회 완료")
            for row in rows:
                reg = (
                    session.query(CompanyRegistry)
                    .filter_by(ticker=row["ticker"], market=market)
                    .first()
                )
                if not reg:
                    unmatched.append(f"{market}:{row['ticker']}({row['name']})")
                    continue
                reg.market_cap_krw = row["market_cap_eok"] * 100_000_000  # 억원 → 원
                reg.cap_asof = as_of
                counts[market] += 1
        session.commit()
    finally:
        session.close()

    result = {**counts, "unmatched": unmatched}
    logger.info(
        f"시총 동기화 완료: KOSPI {counts['KOSPI']} · KOSDAQ {counts['KOSDAQ']} "
        f"(미매칭 {len(unmatched)})"
    )
    return result


def select_top400() -> dict:
    """시장별 시총 상위 200 → universe_tier='named400', 나머지 → 'dot'.

    market_cap_krw가 null인 행(시총 미조회분)은 'dot'으로 처리(named400 후보에서 제외).
    universe_rank는 시장 내 시총 순위(1-base).
    """
    session = get_local_session()
    result = {}
    try:
        for market in ("KOSPI", "KOSDAQ"):
            ranked = (
                session.query(CompanyRegistry)
                .filter(
                    CompanyRegistry.market == market,
                    CompanyRegistry.market_cap_krw.isnot(None),
                )
                .order_by(CompanyRegistry.market_cap_krw.desc())
                .all()
            )
            for i, reg in enumerate(ranked, start=1):
                reg.universe_rank = i
                reg.universe_tier = "named400" if i <= TOP_N_PER_MARKET else "dot"
            # 시총 미조회분은 dot 처리(순위 없음)
            no_cap = (
                session.query(CompanyRegistry)
                .filter(
                    CompanyRegistry.market == market,
                    CompanyRegistry.market_cap_krw.is_(None),
                )
                .all()
            )
            for reg in no_cap:
                reg.universe_tier = "dot"
            result[market] = {
                "named400": min(len(ranked), TOP_N_PER_MARKET),
                "dot": max(0, len(ranked) - TOP_N_PER_MARKET) + len(no_cap),
            }
        session.commit()
    finally:
        session.close()
    return result


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", required=True, help="스냅샷 기준일 (예: 2026-07-21)")
    args = parser.parse_args()

    sync_result = sync(args.as_of)
    select_result = select_top400()
    print(json.dumps({"sync": sync_result, "select": select_result}, ensure_ascii=False, indent=2))
