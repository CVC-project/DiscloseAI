"""DART 사업보고서 주석 HTML 파싱 — 공정위 미포함 기업 한정.

대상 선정: CompanyNode에서 group_name IS NULL인 기업 (실전 1~3개 예상).
파싱 목표: "특수관계자 공시" 섹션의 기업명·관계 유형(지배/종속/관계/공동) 테이블.
결과: source_type="dart_filing" 엣지로 RelationLocal 저장.

상세는 modules/relation/ingest/CLAUDE.md 참조.
"""

from __future__ import annotations


def identify_missing_groups() -> list[str]:
    """CompanyNode에서 group_name IS NULL인 corp_code 목록 반환."""
    raise NotImplementedError("Phase 2c에서 구현")


def download_filing(corp_code: str, bsns_year: int) -> bytes:
    """DART document.json으로 사업보고서 ZIP 다운로드."""
    raise NotImplementedError("Phase 2c에서 구현")


def parse_related_party_section(html: str) -> list[dict]:
    """주석 HTML에서 '특수관계자' 섹션 → [{name, relation_kind}, ...].

    relation_kind: '지배' / '종속' / '관계' / '공동' 중 하나.
    """
    raise NotImplementedError("Phase 2c에서 구현")


def collect() -> None:
    """공정위 미포함 기업들에 대해 사업보고서 주석 파싱 → dart_filing 엣지 생성."""
    raise NotImplementedError("Phase 2c에서 구현")
