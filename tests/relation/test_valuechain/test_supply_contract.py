"""단일판매ㆍ공급계약체결 T1 파서 테스트 — 실제 DART 공시 문서 2건 기반(2026-07-21 수집).

- anonymous 픽스처(그린광학, rcept 20260630901538): 계약상대방이 업종 설명으로
  비공개("방산 솔루션 공급 업체") — entity linking 실패 케이스.
- named 픽스처(아티스트스튜디오, rcept 20260630901559): 계약상대방이 실제 법인명
  ("스튜디오에스 주식회사") — entity linking 성공 케이스.
"""

from __future__ import annotations

from pathlib import Path

from modules.relation.storage.models import CompanyRegistry, LinkFailQueue, ValueChainEdge
from modules.relation.valuechain.extract.supply_contract import apply, parse_filing_html

FIXTURES = Path(__file__).parent.parent / "fixtures"
ANONYMOUS_HTML = (FIXTURES / "valuechain_supply_contract_anonymous.html").read_text(
    encoding="utf-8"
)
NAMED_HTML = (FIXTURES / "valuechain_supply_contract_named.html").read_text(encoding="utf-8")


def test_parse_named_filing_extracts_counterparty_amount_and_year():
    parsed = parse_filing_html(NAMED_HTML, fallback_year=1999)
    assert parsed["counterparty"] == "스튜디오에스 주식회사"
    # 이 픽스처는 확정/총액 계약금액이 모두 "-"라 금액 없음, 계약(수주)일자로 연도만 확인
    assert parsed["as_of"] == 2026


def test_parse_anonymous_filing_extracts_amount_but_generic_counterparty():
    parsed = parse_filing_html(ANONYMOUS_HTML, fallback_year=1999)
    assert parsed["amount"] == 4_746_484_750
    assert parsed["as_of"] == 2026
    # 실제 법인명이 아니라 업종 설명 — 값 자체는 추출되지만 링킹은 실패해야 정상
    assert parsed["counterparty"] == "방산 솔루션 공급 업체"


def test_apply_creates_edge_for_linked_counterparty(in_memory_session):
    in_memory_session.add(
        CompanyRegistry(
            corp_code="00990819",
            ticker="900001",
            name_current="아티스트스튜디오",
            market="KOSDAQ",
        )
    )
    in_memory_session.add(
        CompanyRegistry(
            corp_code="01234567",
            ticker="900002",
            name_current="스튜디오에스",
            market="KOSDAQ",
        )
    )
    in_memory_session.commit()

    filings = [
        {
            "rcept_no": "20260630901559",
            "corp_code": "00990819",
            "corp_name": "아티스트스튜디오",
            "rcept_dt": "20260630",
            "html": NAMED_HTML,
        }
    ]
    result = apply(session=in_memory_session, filings=filings)

    assert result["filings_scanned"] == 1
    assert result["edges_kept"] == 1

    edge = (
        in_memory_session.query(ValueChainEdge)
        .filter_by(src_corp="00990819", dst_corp="01234567", edge_type="customer")
        .one_or_none()
    )
    assert edge is not None
    assert edge.tier == "T1"
    assert edge.source_kind == "supply_contract"
    assert edge.as_of == 2026


def test_apply_skips_edge_and_logs_no_match_for_anonymous_counterparty(in_memory_session):
    in_memory_session.add(
        CompanyRegistry(
            corp_code="00677486", ticker="900003", name_current="그린광학", market="KOSDAQ"
        )
    )
    in_memory_session.commit()

    filings = [
        {
            "rcept_no": "20260630901538",
            "corp_code": "00677486",
            "corp_name": "그린광학",
            "rcept_dt": "20260630",
            "html": ANONYMOUS_HTML,
        }
    ]
    result = apply(session=in_memory_session, filings=filings)

    assert result["filings_scanned"] == 1
    assert result["edges_kept"] == 0
    assert result["link_failed"] == 1

    assert in_memory_session.query(ValueChainEdge).count() == 0
    fail = (
        in_memory_session.query(LinkFailQueue)
        .filter_by(surface_form="방산 솔루션 공급 업체")
        .one_or_none()
    )
    assert fail is not None


def test_apply_idempotent_on_rerun(in_memory_session):
    in_memory_session.add(
        CompanyRegistry(
            corp_code="00990819", ticker="900001", name_current="아티스트스튜디오", market="KOSDAQ"
        )
    )
    in_memory_session.add(
        CompanyRegistry(
            corp_code="01234567", ticker="900002", name_current="스튜디오에스", market="KOSDAQ"
        )
    )
    in_memory_session.commit()
    filings = [
        {
            "rcept_no": "20260630901559",
            "corp_code": "00990819",
            "corp_name": "아티스트스튜디오",
            "rcept_dt": "20260630",
            "html": NAMED_HTML,
        }
    ]

    apply(session=in_memory_session, filings=filings)
    rows1 = [(e.src_corp, e.dst_corp, e.amount) for e in in_memory_session.query(ValueChainEdge)]
    apply(session=in_memory_session, filings=filings)
    rows2 = [(e.src_corp, e.dst_corp, e.amount) for e in in_memory_session.query(ValueChainEdge)]

    assert len(rows1) == len(rows2) == 1
    assert rows1 == rows2
