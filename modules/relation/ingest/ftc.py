"""공정거래위원회 OpenAPI 수집 (data.go.kr).

MVP 5개 API (인증키 1개로 공통 호출):
- 필수: 지정된 대규모기업집단 조회 / 지정된 대규모기업집단 소속회사 조회 / 사용 가능 공개년월 조회
- 권장: 소속회사 주주현황 정보 조회 / 소속회사 개요 정보 조회

상세는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

BASE_URL = "https://apis.data.go.kr/1130000"


def fetch_available_months() -> list[str]:
    """사용 가능 공개년월 목록 조회 → 최신 YYYYMM 확인용."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_designated_groups(yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 조회 → 기업집단 코드·명 목록."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_group_companies(group_code: str, yyyymm: str) -> list[dict]:
    """지정된 대규모기업집단 소속회사 조회 → 소속회사 리스트."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_company_shareholders(company_code: str, yyyymm: str) -> list[dict]:
    """소속회사 주주현황 정보 조회 (권장 API, DART 크로스체크용)."""
    raise NotImplementedError("Phase 2b에서 구현")


def fetch_company_overview(company_code: str, yyyymm: str) -> dict:
    """소속회사 개요 정보 조회 (권장 API, CompanyNode 메타데이터 보강)."""
    raise NotImplementedError("Phase 2b에서 구현")


def collect() -> None:
    """공정위 API 전체 호출 → top50 교차 매칭 → ftc_group 엣지 생성 후 RelationLocal 저장."""
    raise NotImplementedError("Phase 2b에서 구현")
