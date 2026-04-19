"""공정거래위원회 OpenAPI 수집 (data.go.kr).

MVP 필수 2 API로 핵심 데이터 모두 커버:
- publicYmList/publicYmListApi  (사용가능 공개년월)
- appnGroupAffiList/appnGroupAffiListApi  (지정 대규모기업집단 소속회사 전체)

appnGroupAffiList 응답의 `unityGrupNm` 필드가 집단명을 제공하므로 별도의
"지정된 대규모기업집단 조회" API 없이 집단 목록도 이 데이터에서 추출 가능.

상세는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from modules.relation.common.names import build_ticker_map, normalize_company_name
from modules.relation.ingest._http import ftc_get_all_pages
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyNode, RelationRaw

logger = logging.getLogger(__name__)

_TOP50_CSV = Path(__file__).parent.parent / "data" / "top50.csv"


# ============================================================
# 2b.1 — fetch_available_months
# ============================================================


def fetch_available_months() -> list[dict]:
    """사용 가능 공개년월 목록 조회.

    Returns: [{'othbcYm': 'YYYYMM', 'jobSeCode': ...}, ...] 최신순.
    """
    return ftc_get_all_pages("publicYmList/publicYmListApi", {}, item_key="publicYm")


def latest_yyyymm() -> str:
    """가장 최신 othbcYm 반환 (예: '202505')."""
    months = fetch_available_months()
    if not months:
        raise RuntimeError("FTC 사용가능 공개년월이 비어있음")
    # 내림차순 정렬
    months.sort(key=lambda m: m.get("othbcYm", ""), reverse=True)
    return months[0]["othbcYm"]


# ============================================================
# 2b.2 — fetch_all_affiliates (appnGroupAffiList)
# ============================================================


def fetch_all_affiliates(yyyymm: str, presentn_year: str | None = None) -> list[dict]:
    """지정된 대규모기업집단 소속회사 전체 조회.

    Args:
        yyyymm: 공개년월 (예: '202505')
        presentn_year: 당해년도 (YYYY, 기본=yyyymm의 앞 4자리)

    Returns: [{'unityGrupNm', 'entrprsNm', 'jurirno', 'bizrno', 'rprsntvNm',
               'fondDe', 'grinil'}, ...]  — 약 3000건
    """
    if presentn_year is None:
        presentn_year = yyyymm[:4]
    return ftc_get_all_pages(
        "appnGroupAffiList/appnGroupAffiListApi",
        {"othbcYm": yyyymm, "presentnYear": presentn_year, "numOfRows": 500},
        item_key="appnGroupAffi",
    )


# ============================================================
# 2b.3 — collect
# ============================================================


def _load_top50_rows() -> list[dict]:
    with open(_TOP50_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collect(yyyymm: str | None = None) -> dict:
    """공정위 API 호출 → top50 교차 매칭 → ftc_group 엣지 생성.

    흐름:
      1. fetch_available_months() → 최신 YYYYMM 결정 (기본)
      2. fetch_all_affiliates(yyyymm) → 전체 소속회사 (~3000건)
      3. 각 소속회사명 normalize → top50 ticker 매칭
      4. 매칭된 top50 기업의 CompanyNode.group_name UPSERT
      5. 같은 집단 내 top50 기업 쌍에 대해 ftc_group 엣지를 RelationRaw에 INSERT
         (source/target은 ticker 오름차순 정렬하여 중복 방지)

    Returns: {'yyyymm', 'affiliates_total', 'top50_matched', 'groups_covered',
              'ftc_group_edges', 'missing_group_tickers': [...]}
    """
    if yyyymm is None:
        yyyymm = latest_yyyymm()
    logger.info(f"FTC 수집 시작: yyyymm={yyyymm}")

    affiliates = fetch_all_affiliates(yyyymm)
    logger.info(f"공정위 소속회사 전체: {len(affiliates):,}건")

    # top50 ticker 맵 (normalized_name → ticker)
    ticker_map = build_ticker_map(_TOP50_CSV)

    # group_name → [ticker] 수집
    group_to_tickers: dict[str, set[str]] = defaultdict(set)
    matched_tickers: set[str] = set()

    for affi in affiliates:
        entrprs_nm = (affi.get("entrprsNm") or "").strip()
        unity_grup_nm = (affi.get("unityGrupNm") or "").strip()
        if not entrprs_nm or not unity_grup_nm:
            continue
        normalized = normalize_company_name(entrprs_nm)
        if not normalized:
            continue
        ticker = ticker_map.get(normalized)
        if ticker:
            group_to_tickers[unity_grup_nm].add(ticker)
            matched_tickers.add(ticker)

    logger.info(
        f"top50 매칭: {len(matched_tickers)}/50 | 커버된 집단 {len(group_to_tickers)}개"
    )

    # CompanyNode UPSERT 및 ftc_group 엣지 생성
    session = get_local_session()
    edge_count = 0
    try:
        # 1. group_name 업데이트
        for group_name, tickers in group_to_tickers.items():
            for ticker in tickers:
                node = session.query(CompanyNode).filter_by(ticker=ticker).first()
                if node:
                    node.group_name = group_name

        # 2. ftc_group 엣지 (같은 집단 내 쌍, ticker 정렬하여 중복 방지)
        # 중복 INSERT 방지 위해 기존 ftc 엣지 삭제 후 재생성
        session.query(RelationRaw).filter_by(source_type="ftc").delete()

        for group_name, tickers in group_to_tickers.items():
            if len(tickers) < 2:
                continue
            for a, b in combinations(sorted(tickers), 2):
                detail = json.dumps(
                    {"group_name": group_name, "yyyymm": yyyymm}, ensure_ascii=False
                )
                session.add(
                    RelationRaw(
                        source_name=a,
                        target_name=b,
                        relate=None,
                        ratio=None,
                        stock_knd=None,
                        source_type="ftc",
                        bsns_year=int(yyyymm[:4]),
                        raw_response=detail,
                    )
                )
                edge_count += 1

        session.commit()
    finally:
        session.close()

    # 미매칭 top50 티커
    all_top50_tickers = {r["ticker"] for r in _load_top50_rows() if r.get("ticker")}
    missing = sorted(all_top50_tickers - matched_tickers)

    result = {
        "yyyymm": yyyymm,
        "affiliates_total": len(affiliates),
        "top50_matched": len(matched_tickers),
        "groups_covered": len(group_to_tickers),
        "ftc_group_edges": edge_count,
        "missing_group_tickers": missing,
    }
    logger.info(f"FTC 수집 완료: {result}")
    return result


# ============================================================
# MVP 보조 API (v2 스켈레톤)
# ============================================================


def fetch_holding_subsidiaries(yyyymm: str) -> list[dict]:
    """지주회사 자회사 및 손자회사 현황 (보조 API, v2).

    endpoint 추정 필요. 활용신청 완료 상태이나 data.go.kr 데이터셋 ID
    확인 후 endpoint URL 확정 필요.
    """
    raise NotImplementedError("Phase 2 이후 endpoint 확인 후 구현")


def fetch_special_relation_shares(yyyymm: str) -> list[dict]:
    """특수관계인 내부지분 현황 (보조 API, v2)."""
    raise NotImplementedError("Phase 2 이후 endpoint 확인 후 구현")


def fetch_group_asset_ranking(yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 자산순위 (보조 API, v2)."""
    raise NotImplementedError("Phase 2 이후 endpoint 확인 후 구현")
