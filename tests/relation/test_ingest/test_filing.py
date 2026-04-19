"""Phase 2c — ingest/filing.py 단위 테스트 (best-effort 영역).

HTML 파싱 정규화 로직 + extract 섹션 동작 확인 위주.
"""

from __future__ import annotations

from pathlib import Path

from modules.relation.ingest import filing

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_relation_kind_maps_variants():
    assert filing._extract_relation_kind("지배기업") == "지배"
    assert filing._extract_relation_kind("종속회사 현황") == "종속"
    assert filing._extract_relation_kind("관계기업 투자") == "관계"
    assert filing._extract_relation_kind("공동기업") == "공동"
    assert filing._extract_relation_kind("우리 회사") is None


def test_clean_name_drops_bad_candidates():
    assert filing._clean_name("123,456") == ""
    assert filing._clean_name("비고") == ""
    assert (
        filing._clean_name("회사와의 거래에 관한 설명이 길게 들어가는 경우 배제") == ""
    )
    assert filing._clean_name("삼성전자(주)") == "삼성전자(주)"


def test_parse_related_party_section_extracts_table():
    html = (FIXTURES / "filing_related_party_sample.html").read_text("utf-8")
    parsed = filing.parse_related_party_section(html)

    # 샘플 4개 관계 행 + 1개 비고(관계=비고) 행 중 유효 4개
    names = {p["name"] for p in parsed}
    assert "삼성전자(주)" in names
    assert "삼성디스플레이(주)" in names
    assert "삼성SDI(주)" in names
    assert "세메스(주)" in names

    # 관계 유형 분류
    kinds = {(p["name"], p["relation_kind"]) for p in parsed}
    assert ("삼성전자(주)", "지배") in kinds
    assert ("삼성SDI(주)", "관계") in kinds
