"""행=회사·열=기간 레이아웃 파서 (`parse_note_company_rows`) — 2026-07-31 신설.

배경(전수 실측): 섹셔닝 확장으로 특수관계자 주석이 1,550→11,302로 열렸는데 거래금액
파싱은 +5.7%뿐이었다. 최신연도 미파싱 중 **거래 라벨이 있는데 미파싱**인 1,320건을
파서의 실제 단계 함수로 귀속했더니 1,146건(87%)이 한 형태였다 — `당기`가 마커 블록
(`| 당기 | (단위 : 백만원) |`)이 아니라 **열 헤더**에 있는 레이아웃.

fixture는 전부 **실공시 발췌**(파일 첫 줄에 rcept_no 명시). 합성 데이터 금지.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.relation.valuechain.extract.related_party import (
    parse_note,
    parse_note_company_rows,
)

FIX = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def silla():
    return parse_note_company_rows(_load("valuechain_rp_company_rows_basic_silla.txt"))


@pytest.fixture(scope="module")
def eaglevet():
    return parse_note_company_rows(_load("valuechain_rp_company_rows_carry_eaglevet.txt"))


@pytest.fixture(scope="module")
def nhn():
    return parse_note_company_rows(_load("valuechain_rp_company_rows_sum_nhn.txt"))


def _one(items, name, direction=None):
    hits = [i for i in items if i["counterparty"] == name
            and (direction is None or i["direction"] == direction)]
    assert len(hits) == 1, f"{name}/{direction}: {len(hits)}건 — {hits}"
    return hits[0]


# ── 기본형: `| 특수관계자명 | 거래내용 | 당기 | 전기 |` ─────────────────────

def test_basic_period_column_extracts_current_only(silla):
    """원문: `| (주)조흥 | 매출 등 | 12,000 | - |` (단위: 천원)."""
    assert len(silla) == 2
    assert _one(silla, "(주)조흥")["amount"] == 12_000 * 1_000
    assert _one(silla, "춘강문화장학재단")["amount"] == 18_000 * 1_000
    assert {i["direction"] for i in silla} == {"customer"}


def test_balance_table_is_excluded_entirely(silla):
    """⚠️ 회귀 박제: 같은 노트의 `(3) …채권ㆍ채무내역` 표는 헤더가 `당기말|전기말`이다.
    **당기말은 잔액이지 거래액이 아니다** — 행 라벨 필터만 믿지 말고 표 전체를 배제한다.
    원문 임차보증금 60,000천원이 결과에 섞이면 실패."""
    assert 60_000 * 1_000 not in {i["amount"] for i in silla}


# ── 캐리다운: 회사 칸이 **소멸**한 행(빈 칸이 아니다) ───────────────────────

def test_carry_down_attributes_to_previous_company(eaglevet):
    """⚠️ 회귀 박제: `| 특수관계자 | 계정과목 | 당기 | 전기 |` 4열 표에서 두 번째
    거래 행은 `| 매입 | 23,230 | 20,414 |` **3칸**으로 온다(칸 자체가 소멸).
    좌측 패딩 없이 인덱스를 읽으면 전기값(20,414)을 당기값으로 오인한다."""
    assert _one(eaglevet, "메트로펫", "customer")["amount"] == 4_101_777 * 1_000
    assert _one(eaglevet, "메트로펫", "supply")["amount"] == 23_230 * 1_000
    assert _one(eaglevet, "Eaglevet (U) Limited")["amount"] == 3_341_006 * 1_000


# ── 합산: 같은 (회사, 방향)의 계정과목 다행 ────────────────────────────────

def test_same_company_direction_rows_are_summed(nhn):
    """⚠️ 회귀 박제: `_upsert_edge`는 UNIQUE(src,dst,type,as_of,rcept_no) **last-wins**라
    다건을 흘리면 마지막 행만 남아 과소계상된다. 파서가 합산해 1건으로 낸다."""
    e = _one(nhn, "엔에이치엔페이코㈜")
    assert e["label"] == "매출+매출원가"
    assert e["amount"] == 24_782_234 * 1_000
    keys = [(i["counterparty"], i["direction"]) for i in nhn]
    assert len(keys) == len(set(keys)), "(회사,방향) 중복 방출 금지"


# ── 모드 T: 2단 헤더(거래유형 × 기간) ──────────────────────────────────────

def test_two_tier_header_maps_transaction_type_to_current_period():
    """원문(에쓰비씨 2026): 상위 헤더가 거래유형, 다음 행이 전부 기간 토큰이다.

        | 특수관계구분 | 회사명 | 매출 | 기타수익 | 기타비용 | 자산취득 |
        | 당기 | 전기 | 당기 | 전기 | 당기 | 전기 | 당기 |
        | 기타 | 제일호…자산대부 | - | 540 | 61,941 | 19,671 | - | 2,926 | - |
        | 청림양계 | 300,385 | - | - | - | 9,786 | - | - |

    ⚠️ 회귀 박제: 라벨 열 수는 `데이터폭 − 서브헤더폭`으로, 거래유형 수는 서브헤더의
    `당기` 등장 횟수로 **결정적으로 역산**한다. 추측으로 열을 맞추면 금액이 엉뚱한
    상대·거래유형에 붙는다. 여기서는 매출(당기)만 어휘에 걸리므로 청림양계 1건.
    """
    items = parse_note_company_rows(_load("valuechain_rp_company_rows_twotier_sbc.txt"))
    assert len(items) == 1
    assert items[0] == {
        "counterparty": "청림양계",
        "direction": "customer",
        "amount": 300_385 * 1_000,
        "label": "매출",
    }


def test_two_tier_total_row_with_padded_spaces_is_dropped():
    """⚠️ 회귀 박제: `| 합  계 | 300,385 | … |` — 공시는 칸 폭을 맞추려 글자 사이를
    벌린다. 원문 그대로만 잡음 판정하면 `_EMPTY_TOKENS`(합계)를 빠져나간다."""
    items = parse_note_company_rows(_load("valuechain_rp_company_rows_twotier_sbc.txt"))
    assert not {i["counterparty"] for i in items} & {"합계", "합  계"}


# ── 잡음·배제 ──────────────────────────────────────────────────────────────

def test_shifted_total_rows_produce_no_noise_nodes():
    """⚠️ 회귀 박제: 서브헤더가 있어 헤더 폭과 데이터 폭이 어긋나는 표는 **합계 행**이
    회사명 칸에 `-`나 `19,948`을 밀어 넣는다(스윕 1회차 실측 10건).
    `entity_kind.is_noise`가 dash·수치·묶음 라벨(`임직원`)을 한 번에 거른다."""
    items = parse_note_company_rows(_load("valuechain_rp_company_rows_noise_achimhae.txt"))
    names = {i["counterparty"] for i in items}
    assert not (names & {"-", "19,948", "임직원", "합계", "합  계"})


def test_foreign_currency_table_is_excluded():
    """⚠️ 회귀 박제: `(단위: RMB)` 같은 외화는 배율을 모른다. `.get(u, 1)`로 넘기면
    **원화 금액인 것처럼 저장**된다 — 금액이 틀리느니 안 뽑는다(억지 매칭 금지)."""
    assert parse_note_company_rows(
        _load("valuechain_rp_company_rows_foreign_ccy.txt")) == []


# ── 안전성 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("md", [None, "", "표가 없는 평문입니다.", "| a | b |"])
def test_returns_empty_on_empty_or_unrelated(md):
    assert parse_note_company_rows(md) == []


def test_prior_period_substitution_yields_nothing():
    """`당기` 열이 사라지면 방출이 없어야 한다 — 기간 판정이 실제로 작동하는지."""
    md = _load("valuechain_rp_company_rows_basic_silla.txt").replace("당기", "전기")
    assert parse_note_company_rows(md) == []


def test_all_dash_amounts_yield_nothing():
    md = _load("valuechain_rp_company_rows_basic_silla.txt")
    md = md.replace("12,000", "-").replace("18,000", "-")
    assert parse_note_company_rows(md) == []


# ── 영역 불침범 (사슬 끝 배치의 실행 증거) ─────────────────────────────────

def test_does_not_claim_existing_marker_block_layout():
    """⚠️ 회귀 박제: 기존 `parse_note` 대상(마커 블록형)에 이 파서를 적용하면 []여야 한다.
    마커행 `| 당기 | (단위 : 백만원) |`이 헤더 후보로 잡히면 company_col==당기열 충돌로
    표를 포기하는 설계 — 두 파서의 영역이 겹치지 않음을 실행으로 확인한다."""
    md = _load("valuechain_related_party_sample.txt")
    assert parse_note(md), "이 fixture는 기존 파서 대상이어야 한다(전제 확인)"
    assert parse_note_company_rows(md) == []
