"""특수관계자 주석 T1 파서 단위 테스트 — 삼성전자 실제 공시 샘플 기반.

fixture는 shared/data/reports.db에서 실측 추출한 원본 마크다운(2026-07-21) —
합성 데이터가 아니라 실제 DART XBRL→마크다운 변환 산출물의 편차(계층 헤더 콜스팬
소실, 합계 표 병존)를 그대로 반영한다.
"""

from __future__ import annotations

from pathlib import Path

from modules.relation.valuechain.extract.related_party import parse_note

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "valuechain_related_party_sample.txt"
)


def _parse_fixture() -> list[dict]:
    return parse_note(FIXTURE.read_text(encoding="utf-8"))


def test_extracts_current_period_sales_amount():
    results = _parse_fixture()
    sales = {
        r["counterparty"]: r["amount"]
        for r in results
        if r["direction"] == "customer" and r["label"].startswith("매출 등")
    }
    assert sales["삼성에스디에스㈜"] == 110_512 * 1_000_000
    assert sales["삼성물산㈜"] == 10_604 * 1_000_000


def test_extracts_current_period_purchase_amount():
    results = _parse_fixture()
    purchases = {
        r["counterparty"]: r["amount"]
        for r in results
        if r["direction"] == "supply" and r["label"].startswith("매입 등")
    }
    assert purchases["삼성에스디에스㈜"] == 2_218_940 * 1_000_000
    assert purchases["㈜에스원"] == 561_277 * 1_000_000


def test_skips_prior_period_values():
    """전기(104,837) 값은 결과에 없어야 한다 — 당기(110,512)만 포함."""
    results = _parse_fixture()
    amounts = {r["amount"] for r in results}
    assert 104_837 * 1_000_000 not in amounts
    assert 110_512 * 1_000_000 in amounts


def test_excludes_aggregate_other_columns():
    """'기타 관계기업 및 공동기업' 등 집계 컬럼은 상대회사가 아니므로 제외."""
    results = _parse_fixture()
    assert all(not r["counterparty"].startswith("기타") for r in results)


def test_excludes_non_transaction_labels():
    """비유동자산 매입/처분(자산 취득)·채권/채무 잔액은 상거래 매출/매입이 아니므로 제외."""
    results = _parse_fixture()
    assert all("비유동자산" not in r["label"] for r in results)
    assert all(r["label"].startswith(("매출", "매입")) for r in results)


def test_excludes_aggregate_totals_table():
    """'...공시, 합계' 표의 리프 헤더(관계기업 및 공동기업 등)를 상대회사로 오인하지 않는다."""
    results = _parse_fixture()
    counterparties = {r["counterparty"] for r in results}
    assert "관계기업 및 공동기업" not in counterparties
    assert "대규모기업집단" not in counterparties
    assert "그 밖의 특수관계자" not in counterparties


def test_excludes_non_trade_sections():
    """특수관계자 자금거래(현금출자) 표는 매출/매입 라벨이 없어 자연히 제외된다."""
    results = _parse_fixture()
    labels = {r["label"] for r in results}
    assert not any("현금출자" in label for label in labels)


def test_empty_or_none_input_returns_empty_list():
    assert parse_note(None) == []
    assert parse_note("") == []
    assert parse_note("아무 표도 없는 일반 서술문입니다.") == []
