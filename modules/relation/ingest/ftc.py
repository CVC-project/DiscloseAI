"""공정거래위원회 OpenAPI 수집 (data.go.kr).

활용신청 완료된 10개 API (2026-04-19, 인증키 1개로 공통 호출):

MVP 필수 (Phase 2b 구현 대상):
  - 지정된 대규모기업집단 조회
  - 지정된 대규모기업집단 소속회사 조회
  - 사용 가능 공개년월 조회

MVP 보조 (여건 되면 Phase 2b에 포함):
  - 지주회사 자회사 및 손자회사 현황 (SK·LG·한화 등 지주사 구조 보강)
  - 특수관계인 내부지분 현황 (DART hyslrSttus와 크로스체크)
  - 지정된 대규모기업집단 자산순위 (노드 크기 정렬 보강)

v2 연기 (스켈레톤만 유지, 대회 이후):
  - 대규모기업집단 소속회사 재무현황 (financial 모듈 영역)
  - 대규모기업집단 소속회사 참여업종 (top50.csv sector 수동 매핑으로 대체 중)
  - 대규모기업집단 계열 편입/제외/유예 변경내역 (시계열 애니메이션용)
  - 기업집단별 순환출자 현황 (고급 분석)

상세 파라미터·응답 스펙은 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

BASE_URL = "https://apis.data.go.kr/1130000"


# ============================================================
# MVP 필수 3종
# ============================================================


def fetch_available_months() -> list[str]:
    """사용 가능 공개년월 목록 조회 → 최신 YYYYMM 확인용."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_designated_groups(yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 조회 → 기업집단 코드·명 목록."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_group_companies(group_code: str, yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 소속회사 조회 → 소속회사 리스트."""
    raise NotImplementedError("Phase 2b에서 구현")


# ============================================================
# MVP 보조 3종 (Phase 2b에서 여건 되면)
# ============================================================


def fetch_holding_subsidiaries(holding_code: str, yyyymm: str) -> list[dict]:
    """지주회사 자회사 및 손자회사 현황 — SK·LG·한화 등 지주사 구조 보강용."""
    raise NotImplementedError("Phase 2b/보조에서 구현")


def fetch_special_relation_shares(group_code: str, yyyymm: str) -> list[dict]:
    """특수관계인 내부지분 현황 — DART hyslrSttus와 크로스체크용."""
    raise NotImplementedError("Phase 2b/보조에서 구현")


def fetch_group_asset_ranking(yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 자산순위 — 노드 크기·정렬 보강용."""
    raise NotImplementedError("Phase 2b/보조에서 구현")


# ============================================================
# v2 연기 (스켈레톤만)
# ============================================================


def fetch_company_financials(company_code: str, yyyymm: str) -> dict:
    """소속회사 재무현황 — v2 (financial 모듈 영역과 중복)."""
    raise NotImplementedError("v2에서 구현")


def fetch_company_industries(company_code: str, yyyymm: str) -> list[dict]:
    """소속회사 참여업종 — v2 (top50.csv sector 수동 매핑으로 대체 중)."""
    raise NotImplementedError("v2에서 구현")


def fetch_affiliation_changes(yyyymm: str) -> list[dict]:
    """계열 편입/제외/유예 변경내역 — v2 시계열 애니메이션용."""
    raise NotImplementedError("v2에서 구현")


def fetch_circular_shareholding(group_code: str, yyyymm: str) -> list[dict]:
    """기업집단별 순환출자 현황 — v2 고급 분석용."""
    raise NotImplementedError("v2에서 구현")


# ============================================================
# 통합 진입점
# ============================================================


def collect() -> None:
    """공정위 API 호출 → top50 교차 매칭 → ftc_group 엣지 생성 후 RelationLocal 저장.

    Phase 2b에서 필수 3종을 먼저 구현. 시간 여유 있으면 보조 3종까지 포함.
    """
    raise NotImplementedError("Phase 2b에서 구현")
