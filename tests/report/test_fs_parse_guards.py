"""fs_parse 방어 규칙 회귀 테스트 — **삭제·완화 금지**.

각 케이스는 P2 파일럿에서 실제로 터진 불일치를 되살려 넣은 것이다(FS_PARSE_PLAN §8.2).
게이트가 고무도장이 되지 않도록, 규칙을 되돌리면 반드시 빨간불이 나게 고정한다.
"""

from __future__ import annotations

import pytest

from modules.report.fs_parse import (
    NAME_EXCLUDE,
    SIGN_ABS,
    Row,
    norm_name,
    parse_amount,
    pick_account,
    select_core,
)


def _row(nm, amt, sj="CIS", code="", fs="CFS", col=0, order=0):
    return Row(fs_div=fs, sj_div=sj, account_id=code, account_nm=nm,
               amount=amt, col_kind=col, unit_scale=1.0, order=order)


# ── 계정명 정규화 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, want",
    [
        ("매출액(주6,32)", "매출액"),          # 주석 참조 — FY2023은 ACODE가 없어 치명적
        ("매출원가(주석 30)", "매출원가"),
        ("<P>영업이익(손실)</P>", "영업이익(손실)"),   # 계정 식별 괄호는 유지
        ("-당기순이익(손실)", "당기순이익(손실)"),      # 들여쓰기 불릿(두산)
        ("Ⅰ.유동자산", "유동자산"),
        ("연 결 재 무 상 태 표", "연결재무상태표"),    # 자간 벌린 캡션(금융업)
        ("수익(매출액)", "수익(매출액)"),
    ],
)
def test_norm_name(raw, want):
    assert norm_name(raw) == want


# ── 금액 파싱 ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, want",
    [
        ("8,099,147,815,086", 8099147815086.0),
        ("(478,201,170,293)", -478201170293.0),   # 괄호가 음수 정본
        ("△1,234", -1234.0),
        ("0", 0.0),                                # 0은 실제 보고값 — None 아님
        ("", None),                                # 빈 칸은 미발견 — 0으로 채우지 않는다
        ("-", None),
        ("해당사항없음", None),
    ],
)
def test_parse_amount(raw, want):
    assert parse_amount(raw) == want


# ── FN-025: 우선순위 정렬 후 최상위 1건 (first-wins 금지) ──────────────────────


def test_revenue_ignores_interest_income_even_when_it_comes_first():
    """카카오 오염의 원형 — 이자수익 행이 먼저 와도 매출을 밀어내면 안 된다."""
    rows = [
        _row("이자수익", 190_000_000_000, code="ifrs-full_RevenueFromInterest", order=0),
        _row("영업수익", 7_557_001_757_272, code="ifrs-full_Revenue", order=1),
    ]
    hit, rank = pick_account(rows, "revenue")
    assert hit.amount == 7_557_001_757_272
    assert rank == 1


def test_revenue_prefers_standard_code_over_name_order():
    """계정명만 맞는 앞 행보다 표준계정ID가 맞는 뒷 행이 이긴다."""
    rows = [
        _row("매출", 1_000, order=0),                                   # rank 3
        _row("영업수익", 9_999, code="ifrs-full_Revenue", order=1),      # rank 1
    ]
    hit, rank = pick_account(rows, "revenue")
    assert (hit.amount, rank) == (9_999, 1)


def test_revenue_name_guard_blocks_miscoded_interest_row():
    """원문 XBRL이 이자수익 행에 ifrs-full_Revenue를 잘못 붙여도 이름으로 막는다."""
    rows = [_row("이자수익", 5, code="ifrs-full_Revenue", order=0)]
    hit, _ = pick_account(rows, "revenue")
    assert hit is None
    assert "이자수익" in NAME_EXCLUDE["revenue"]


# ── 부정 이름 가드: 두산 000150 원문 XBRL 오태깅 ─────────────────────────────


def test_investing_cashflow_rejects_inflow_subtotal():
    """`투자활동으로 인한 현금유입액`에 순현금흐름 코드가 붙은 실측 케이스."""
    rows = [
        _row("투자활동으로 인한 현금흐름", -315_051_174_019, sj="CF", order=0),
        _row("투자활동으로 인한 현금유입액", 2_472_120_565_028, sj="CF",
             code="ifrs-full_CashFlowsFromUsedInInvestingActivities", order=1),
    ]
    hit, _ = pick_account(rows, "investing_cashflow")
    assert hit.amount == -315_051_174_019


# ── 재무제표 경계: 자본총계를 자본변동표에서 줍지 않는다 ──────────────────────


def test_total_equity_only_from_balance_sheet():
    rows = [
        _row("기말자본", 1, sj="SCE", code="ifrs-full_Equity", order=0),
        _row("자본총계", 2, sj="BS", code="ifrs-full_Equity", order=1),
    ]
    hit, _ = pick_account(rows, "total_equity")
    assert (hit.amount, hit.sj_div) == (2, "BS")


def test_net_income_not_taken_from_cashflow_statement():
    rows = [_row("당기순이익", 7, sj="CF", code="ifrs-full_ProfitLoss", order=0)]
    hit, _ = pick_account(rows, "net_income")
    assert hit is None


# ── 부호 정규화 · 파생 금지 · 열→연도 ────────────────────────────────────────


def test_cogs_sign_normalised_to_positive():
    """매출원가를 괄호로 싣는 회사(포스코·LG화학 등 실측 24건)를 DART 정본에 맞춘다."""
    rows = [_row("매출원가", -70_710_293_228_346, code="ifrs-full_CostOfSales")]
    out = select_core(rows, 2025)
    cogs = [d for d in out if d["account_key"] == "cogs"]
    assert cogs and cogs[0]["amount"] == 70_710_293_228_346
    assert "cogs" in SIGN_ABS


def test_missing_account_is_absent_not_zero():
    """원문에 합계 행이 없으면 **미발견** — 0으로 만들지 않는다."""
    rows = [_row("영업수익", 100, code="ifrs-full_Revenue")]
    keys = {d["account_key"] for d in select_core(rows, 2025)}
    assert keys == {"revenue"}


def test_column_to_fiscal_year_is_anchored_to_report_year():
    """당기·전기·전전기 → src_fy, src_fy-1, src_fy-2 (실측 161/161 정합)."""
    rows = [_row("영업수익", 10 + c, code="ifrs-full_Revenue", col=c, order=c)
            for c in (0, 1, 2)]
    got = {d["col_kind"]: d["fiscal_year"] for d in select_core(rows, 2025)}
    assert got == {0: 2025, 1: 2024, 2: 2023}
