"""universe/registry.py — 전 상장사(~2,600) 마스터 레지스트리 동기화 (U0).

DART corpCode.xml(전량) + KRX 상장법인목록(KIND) 교차 → CompanyRegistry 적재.

원천 선택 사유: pykrx의 OTP/세션 기반 API가 이 환경에서 KRX에 'LOGOUT'으로
거부됨(세션 흐름 불안정) — KIND(kind.krx.co.kr)의 정적 다운로드는 비인증·
단일 GET으로 완결돼 안정적이다. 시가총액(pykrx 전용 데이터)은 marketcap.py가
별도로 pykrx→yfinance 폴백을 시도한다(U-D6) — 이 파일은 상장 목록·시장구분만.
"""

from __future__ import annotations

import io
import logging

import pandas as pd
import requests

from modules.relation.ingest.dart import fetch_dart_stock_to_corp_map
from modules.relation.storage.db import get_local_session, init_local_db
from modules.relation.storage.models import CompanyRegistry

logger = logging.getLogger(__name__)

KIND_CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
_HTTP_TIMEOUT = 20

# 코넥스 제외 — 전 상장사 스코프는 코스피+코스닥만(universe/PLAN.md §0)
_MARKET_MAP = {"유가": "KOSPI", "코스닥": "KOSDAQ"}


def fetch_krx_listing() -> pd.DataFrame:
    """KIND 상장법인목록 다운로드 → KOSPI/KOSDAQ만 필터링한 DataFrame.

    반환 컬럼: 종목코드(ticker 6자리) · market(KOSPI|KOSDAQ) · 회사명 · 업종 · 상장일
    """
    r = requests.get(
        KIND_CORP_LIST_URL,
        params={"method": "download", "searchType": "13"},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    r.encoding = "euc-kr"
    df = pd.read_html(io.StringIO(r.text))[0]
    df = df[df["시장구분"].isin(_MARKET_MAP)].copy()
    df["market"] = df["시장구분"].map(_MARKET_MAP)
    df["종목코드"] = df["종목코드"].astype(str).str.strip()
    return df


def sync() -> dict:
    """DART corp_code 맵 + KRX 상장목록 교차 → CompanyRegistry upsert.

    listing_status는 이 동기화에서 발견된 전량을 'listed'로만 표시한다.
    상장폐지 판정(M1 루프의 diff 기반)은 이 함수의 책임이 아니다 — 별도
    호출자가 이전 스냅샷과 비교해 listing_status='delisted'로 전환한다.

    Returns: {'total': int, 'matched': int, 'unmatched_tickers': [...]}
    """
    init_local_db()
    stock_to_corp = fetch_dart_stock_to_corp_map()
    krx = fetch_krx_listing()

    matched = 0
    unmatched: list[str] = []
    session = get_local_session()
    try:
        for _, row in krx.iterrows():
            ticker = row["종목코드"]
            market = row["market"]
            name = str(row["회사명"]).strip()
            mapping = stock_to_corp.get(ticker)
            if not mapping:
                unmatched.append(f"{ticker} ({name})")
                continue
            corp_code, dart_name = mapping
            matched += 1
            existing = session.query(CompanyRegistry).filter_by(corp_code=corp_code).first()
            if existing:
                existing.ticker = ticker
                existing.name_current = dart_name or name
                existing.market = market
                existing.listing_status = "listed"
            else:
                session.add(
                    CompanyRegistry(
                        corp_code=corp_code,
                        ticker=ticker,
                        name_current=dart_name or name,
                        market=market,
                        listing_status="listed",
                    )
                )
        session.commit()
    finally:
        session.close()

    result = {"total": int(len(krx)), "matched": matched, "unmatched_tickers": unmatched}
    logger.info(
        f"registry sync: {matched}/{len(krx)} 매칭 완료 (미매칭 {len(unmatched)}건)"
    )
    return result


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(sync(), ensure_ascii=False, indent=2))
