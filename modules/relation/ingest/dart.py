"""DART OpenAPI 수집.

2개 엔드포인트 호출:
- hyslrSttus.json       (최대주주 및 특수관계인 현황 — 들어오는 지분)
- otrCprInvstmntSttus.json (타법인 출자현황 — 나가는 지분)

상세 파라미터·응답 필드는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations

BASE_URL = "https://opendart.fss.or.kr/api"
ENDPOINT_SHAREHOLDERS = "hyslrSttus.json"
ENDPOINT_INVESTMENTS = "otrCprInvstmntSttus.json"


def fetch_shareholders(
    corp_code: str, bsns_year: int, reprt_code: str = "11011"
) -> dict:
    """hyslrSttus 호출 → JSON 응답 반환."""
    raise NotImplementedError("Phase 2a에서 구현")


def fetch_investments(
    corp_code: str, bsns_year: int, reprt_code: str = "11011"
) -> dict:
    """otrCprInvstmntSttus 호출 → JSON 응답 반환."""
    raise NotImplementedError("Phase 2a에서 구현")


def collect(corp: str | None = None, bsns_year: int = 2024) -> None:
    """DART에서 top50 전체 (또는 --corp 지정 시 해당 1개) 기업의 지분 관계 수집.

    결과는 RAW JSON을 data/raw_cache/에 저장하고 RelationLocal에 초안 저장.
    개인·비상장 필터링은 이 단계에서 하지 않음 (transform/filters에서 처리).
    """
    raise NotImplementedError("Phase 2a에서 구현")
