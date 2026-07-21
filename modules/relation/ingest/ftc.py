"""공정거래위원회 OpenAPI 수집 (data.go.kr).

MVP 필수 2 API로 핵심 데이터 모두 커버:
- publicYmList/publicYmListApi  (사용가능 공개년월)
- appnGroupAffiList/appnGroupAffiListApi  (지정 대규모기업집단 소속회사 전체)

appnGroupAffiList 응답의 `unityGrupNm` 필드가 집단명을 제공하므로 별도의
"지정된 대규모기업집단 조회" API 없이 집단 목록도 이 데이터에서 추출 가능.

상세는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict

from modules.relation.common.names import build_ticker_map_from_registry, normalize_company_name
from modules.relation.ingest._http import ftc_get_all_pages
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyNode, CompanyRegistry, RelationRaw

logger = logging.getLogger(__name__)


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


def _hub_ticker(session, tickers: set[str]) -> str:
    """집단 내 스타 허브 선정 — 시총 최댓값 기업(★U1, U-D4).

    CompanyRegistry.market_cap_krw 기준(U0에서 전량 확보됨). 동률·결측 시
    ticker 오름차순으로 결정적 타이브레이크(재실행 시 허브가 흔들리지 않도록).
    """
    rows = (
        session.query(CompanyRegistry.ticker, CompanyRegistry.market_cap_krw)
        .filter(CompanyRegistry.ticker.in_(tickers))
        .all()
    )
    cap_by_ticker = {t: (cap or 0) for t, cap in rows}
    return max(sorted(tickers), key=lambda t: cap_by_ticker.get(t, 0))


def collect(yyyymm: str | None = None) -> dict:
    """공정위 API 호출 → 전 상장사 교차 매칭 → ftc_group 엣지 생성.

    흐름:
      1. fetch_available_months() → 최신 YYYYMM 결정 (기본)
      2. fetch_all_affiliates(yyyymm) → 전체 소속회사 (~3000건)
      3. 각 소속회사명 normalize → CompanyRegistry(전 상장사) ticker 매칭 (★U1)
      4. 매칭된 기업의 CompanyNode.group_name UPSERT (레거시 top50 노드, 과도기 호환)
      5. 같은 집단 내 시총 최댓값 기업을 허브로 선정 → **스타 토폴로지**로
         ftc_group 엣지를 RelationRaw에 INSERT (★U1, U-D4 — 기존 클리크
         combinations()는 집단 크기 n에 O(n²) 엣지 폭발, 삼성 17개사면 136엣지)

    Returns: {'yyyymm', 'affiliates_total', 'registry_matched', 'groups_covered',
              'ftc_group_edges'}
    """
    if yyyymm is None:
        yyyymm = latest_yyyymm()
    logger.info(f"FTC 수집 시작: yyyymm={yyyymm}")

    affiliates = fetch_all_affiliates(yyyymm)
    logger.info(f"공정위 소속회사 전체: {len(affiliates):,}건")

    session = get_local_session()
    ticker_map = build_ticker_map_from_registry(session)

    # group_name → {ticker} 수집
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
        f"전 상장사 매칭: {len(matched_tickers)}건 | 커버된 집단 {len(group_to_tickers)}개"
    )

    edge_count = 0
    try:
        # 1. group_name 업데이트 (레거시 CompanyNode — graph/build.py 전환 완료까지 병존)
        for group_name, tickers in group_to_tickers.items():
            for ticker in tickers:
                node = session.query(CompanyNode).filter_by(ticker=ticker).first()
                if node:
                    node.group_name = group_name

        # 2. ftc_group 엣지 — 스타 토폴로지(허브→소속사). 재수집 시 기존 ftc 삭제 후 재생성
        session.query(RelationRaw).filter_by(source_type="ftc").delete()

        for group_name, tickers in group_to_tickers.items():
            if len(tickers) < 2:
                continue
            hub = _hub_ticker(session, tickers)
            for member in sorted(tickers):
                if member == hub:
                    continue
                detail = json.dumps(
                    {"group_name": group_name, "yyyymm": yyyymm, "hub": hub},
                    ensure_ascii=False,
                )
                session.add(
                    RelationRaw(
                        source_name=hub,
                        target_name=member,
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

    result = {
        "yyyymm": yyyymm,
        "affiliates_total": len(affiliates),
        "registry_matched": len(matched_tickers),
        "groups_covered": len(group_to_tickers),
        "ftc_group_edges": edge_count,
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
