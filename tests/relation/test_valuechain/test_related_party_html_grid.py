"""계층 헤더 거래금액 표 파서(parse_note_html_grid) 테스트 — U-확대 2026-07-29.

배경: 전 상장사 확대 실측에서 거래금액 0건 노트 856건 중 **464건이 "라벨은 인식되는데
셀 수가 안 맞아" 스킵**된 것으로 드러났다. 원인은 새 표 변형이 아니라 markdown 평탄화의
COLSPAN 유실 — 같은 표를 원본 text_html로 읽으면 모든 행이 균일 폭으로 정렬된다.

fixture 3종은 실제 공시(기간 마커 소표 + 대상 표만 추려 보존):
  포스코퓨처엠 20260312000826 — 1단 라벨·21열
  기아         20250313001390 — 2단 라벨(수익거래/재화의 판매…)·27열 + 카테고리 집계 컬럼
  삼성전자     20240312000736 — 1단 라벨·16열 + 하위분해 없는 실제 법인(삼성엔지니어링·에스원)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.relation.valuechain.extract.related_party import (
    _is_category_column,
    parse_note_html_grid,
)

FIX = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


@pytest.fixture
def posco() -> list[dict]:
    return parse_note_html_grid(_load("valuechain_rp_amount_grid_posco_future_m.html"))


@pytest.fixture
def kia() -> list[dict]:
    return parse_note_html_grid(_load("valuechain_rp_amount_grid_kia.html"))


@pytest.fixture
def samsung() -> list[dict]:
    return parse_note_html_grid(_load("valuechain_rp_amount_grid_samsung_electronics.html"))


# ── 기본 추출 정확성 (원문 대조) ────────────────────────────────────────────

def test_posco_extracts_amounts_with_unit_normalized(posco):
    """단위(천원) 정규화 + 방향 판정. 원문: (주)포스코 재화의 판매 888,295,990천원."""
    hit = [r for r in posco if r["counterparty"] == "(주)포스코"
           and r["direction"] == "customer"]
    assert len(hit) == 1
    assert hit[0]["amount"] == 888_295_990 * 1_000


def test_posco_purchase_direction(posco):
    """매입 라벨은 supply — 원문: ZHEJIANG HUAYOU-POSCO ESM 재화의 매입 16,315천원."""
    hit = [r for r in posco if r["counterparty"] == "ZHEJIANG HUAYOU-POSCO ESM"]
    assert [(h["direction"], h["amount"]) for h in hit] == [("supply", 16_315 * 1_000)]


def test_samsung_both_directions_for_same_counterparty(samsung):
    """같은 상대에 매출·매입이 모두 있으면 둘 다 별도 항목으로 나온다."""
    sds = {r["direction"]: r["amount"] for r in samsung
           if r["counterparty"] == "삼성에스디에스㈜"}
    assert sds == {"customer": 202_810 * 1_000_000, "supply": 1_984_263 * 1_000_000}


def test_kia_two_level_label_uses_sublabel(kia):
    """2단 라벨 표(수익거래 > 재화의 판매로 인한 수익)는 **세부 라벨** 금액을 쓴다.

    원문 기아: 현대자동차㈜ 수익거래 총계 731,394 / 그중 재화의 판매 664,913 (백만원).
    총계를 잡으면 이중계상이므로 세부 값이 나와야 한다.
    """
    hit = [r for r in kia if r["counterparty"] == "현대자동차㈜"
           and r["direction"] == "customer"]
    assert len(hit) == 1
    assert hit[0]["amount"] == 664_913 * 1_000_000
    assert hit[0]["label"].startswith("재화의 판매로 인한 수익")


def test_kia_group_total_row_not_double_counted(kia):
    """그룹 합계 행(라벨 셀이 전부 '수익거래')은 세부 행이 있으면 스킵 — 이중계상 방지."""
    assert not any(r["label"] == "수익거래" for r in kia)
    assert not any(r["label"] == "비용거래" for r in kia)


# ── 집계 컬럼 배제 (허위 노드 방지 — FN-013 계열 방어) ──────────────────────

def test_category_columns_excluded(kia):
    """카테고리명이 ROWSPAN으로 회사명 칸에 내려온 집계 컬럼은 법인이 아니다."""
    names = {r["counterparty"] for r in kia}
    assert "그 밖의 특수관계자" not in names
    assert not any("대규모기업집단" in n for n in names)
    assert not any(n.startswith("기타") for n in names)


def test_real_companies_without_subbreakdown_are_kept(samsung):
    """⚠️ 회귀 박제: 삼성엔지니어링㈜·㈜에스원은 하위 분해가 없어 카테고리 행과 같은
    칸에 나타나지만 **실제 법인**이다. "캐리다운=집계"로 판정하면 이 4건이 소실된다
    (구현 중 실제 발생 → 어휘 기반 판정으로 교체). 구조가 아니라 어휘로 거른다."""
    names = {r["counterparty"] for r in samsung}
    assert "삼성엔지니어링㈜" in names
    assert "㈜에스원" in names


@pytest.mark.parametrize(
    "name,expected",
    [
        ("그 밖의 특수관계자", True),
        ("대규모기업집단 계열회사  (*)", True),
        ("관계기업 및 공동기업 합계", True),
        ("당해 기업이나 당해 기업의 지배기업의 주요 경영진", True),
        ("삼성엔지니어링㈜", False),
        ("㈜에스원", False),
        ("포스코홀딩스(주)", False),
        ("Hyundai Motor America", False),
    ],
)
def test_is_category_column_vocabulary(name, expected):
    assert _is_category_column(name) is expected


# ── 안전성: 억지 매칭 금지 ─────────────────────────────────────────────────

def test_returns_empty_on_none_or_unrelated_html():
    assert parse_note_html_grid(None) == []
    assert parse_note_html_grid("") == []
    assert parse_note_html_grid("<table><tr><th>foo</th></tr></table>") == []


def test_skips_prior_period_tables():
    """기간 마커가 '전기'인 표는 스킵 — 전년도 보고서의 당기 블록에서 이미 잡힌다."""
    html = _load("valuechain_rp_amount_grid_samsung_electronics.html").replace(
        "당기", "전기"
    )
    assert parse_note_html_grid(html) == []


def test_no_amount_cells_yields_nothing():
    """금액이 전부 비거나 '-'면 항목을 만들지 않는다."""
    html = (
        "<table><tr><td>당기</td><td>(단위 : 백만원)</td></tr></table>"
        "<table><tr><th></th><th>삼성전자㈜</th></tr>"
        "<tr><td>매출 등</td><td>-</td></tr></table>"
    )
    assert parse_note_html_grid(html) == []
