"""특수관계자 주석 "구분/특수관계자명" 거버넌스 카테고리 표 파서 테스트.

fixture는 SK이노베이션 실제 공시(2026-07-22 수집, rcept 20260316000827)의
전체 노트 원문 — 거래금액 표 앞에 이 카테고리 표가 먼저 등장하는 실제 구조를
그대로 반영한다(sectioner의 평문 중복 렌더링 포함).
"""

from __future__ import annotations

from pathlib import Path

from modules.relation.storage.models import CompanyRegistry, RelationLocal
from modules.relation.valuechain.extract.related_party import (
    apply_governance,
    parse_governance_categories,
)

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_sk_innovation.txt"
)
FIXTURE_HYNIX = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_sk_hynix.txt"
)


def _parse_fixture() -> list[dict]:
    return parse_governance_categories(FIXTURE.read_text(encoding="utf-8"))


def test_parses_all_five_categories():
    results = _parse_fixture()
    categories = {r["category"] for r in results}
    assert "지배기업" in categories
    assert "관계기업" in categories
    assert "공동기업" in categories
    assert "기  타" in categories
    assert any(c.startswith("대규모기업집단") for c in categories)


def test_controlling_company_extracted():
    results = _parse_fixture()
    controlling = [r["counterparty"] for r in results if r["category"] == "지배기업"]
    assert controlling == ["SK(주)"]


def test_skips_plaintext_duplicate_before_clean_table():
    """sectioner가 같은 표를 평문으로 먼저 렌더링해도(콤마 구분 원문 재진술) 첫
    깨끗한 파이프 표 1개분만 처리해야 한다 — 중복 카운트 금지."""
    results = _parse_fixture()
    # SK(주)가 지배기업으로 단 한 번만 등장(평문 중복까지 세면 여러 번 나올 것)
    sk_count = sum(
        1
        for r in results
        if r["category"] == "지배기업" and r["counterparty"] == "SK(주)"
    )
    assert sk_count == 1


def test_footnote_row_not_treated_as_category():
    results = _parse_fixture()
    categories = {r["category"] for r in results}
    assert "(주1)" not in categories


def test_empty_or_none_input_returns_empty_list():
    assert parse_governance_categories(None) == []
    assert parse_governance_categories("") == []


def test_parses_hoesamyeong_label_variant():
    """SK하이닉스 실제 공시(2026-07-22 수집, rcept 20260317000635) — 헤더가
    "특수관계자명"이 아니라 "회사명"인 라벨 변형. 구조(카테고리별 콤마 구분
    나열)는 동일하므로 같은 파서가 흡수해야 한다."""
    results = parse_governance_categories(FIXTURE_HYNIX.read_text(encoding="utf-8"))
    categories = {r["category"] for r in results}
    assert "관계기업" in categories
    assert "공동기업" in categories
    assert "기타특수관계자" in categories
    sk_china = [r for r in results if r["counterparty"] == "SK China Company Limited"]
    assert len(sk_china) == 1
    assert sk_china[0]["category"] == "관계기업"


def _seed_registry(session):
    session.add(
        CompanyRegistry(
            corp_code="00073570",
            ticker="096770",
            name_current="SK이노베이션",
            market="KOSPI",
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00164779",
            ticker="000660",
            name_current="SK하이닉스",
            market="KOSPI",
        )
    )
    session.commit()


def _one_section():
    return [
        {
            "rcept_no": "20260316000827",
            "title": "특수관계자",
            "text_md": FIXTURE.read_text(encoding="utf-8"),
            "corp_code8": "00073570",
            "fiscal_year": 2025,
        }
    ]


def test_apply_governance_creates_relation_local_edge_for_linked_counterparty(
    in_memory_session,
):
    _seed_registry(in_memory_session)
    result = apply_governance(session=in_memory_session, sections=_one_section())

    assert result["notes_scanned"] == 1
    assert result["edges_kept"] > 0

    edge = (
        in_memory_session.query(RelationLocal)
        .filter_by(source_corp="096770", target_corp="000660", source_type="dart_filing")
        .one_or_none()
    )
    assert edge is not None
    assert edge.relation_type == "dart_filing"
    assert "기  타" in edge.detail  # SK하이닉스는 "기타" 카테고리 소속
    assert edge.bsns_year == 2025


def test_apply_governance_idempotent_on_rerun(in_memory_session):
    _seed_registry(in_memory_session)
    apply_governance(session=in_memory_session, sections=_one_section())
    rows1 = sorted(
        (e.source_corp, e.target_corp, e.detail)
        for e in in_memory_session.query(RelationLocal).all()
    )
    apply_governance(session=in_memory_session, sections=_one_section())
    rows2 = sorted(
        (e.source_corp, e.target_corp, e.detail)
        for e in in_memory_session.query(RelationLocal).all()
    )
    assert len(rows1) == len(rows2)
    assert rows1 == rows2


def test_apply_governance_skips_notes_for_unregistered_filer(in_memory_session):
    """자기 자신(공시 회사)의 ticker를 못 찾으면 그 노트는 건너뛴다."""
    result = apply_governance(session=in_memory_session, sections=_one_section())
    assert result["no_ticker"] == 1
    assert result["edges_kept"] == 0
