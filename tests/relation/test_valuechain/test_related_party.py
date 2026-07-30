"""특수관계자 주석 T1 파서 단위 테스트 — 삼성전자 실제 공시 샘플 기반.

fixture는 shared/data/reports.db에서 실측 추출한 원본 마크다운(2026-07-21) —
합성 데이터가 아니라 실제 DART XBRL→마크다운 변환 산출물의 편차(계층 헤더 콜스팬
소실, 합계 표 병존)를 그대로 반영한다.
"""

from __future__ import annotations

from pathlib import Path

from modules.relation.valuechain.extract.related_party import (
    parse_note,
    parse_note_transposed,
)

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "valuechain_related_party_sample.txt"
)
HYUNDAI_ROTEM_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_hyundai_rotem.txt"
)
LIG_TRANSPOSED_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_transposed_lig.html"
)
KIA_TRANSPOSED_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_transposed_kia.html"
)
HANWHA_SYSTEMS_TRANSPOSED_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_transposed_hanwha_systems.html"
)


def _parse_fixture() -> list[dict]:
    return parse_note(FIXTURE.read_text(encoding="utf-8"))


def _parse_hyundai_rotem_fixture() -> list[dict]:
    return parse_note(HYUNDAI_ROTEM_FIXTURE.read_text(encoding="utf-8"))


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


# --- 회귀: 현대로템(2026-07-22 실측) — "수익거래"/"비용거래" 라벨 + 마커 직후 평문 중복 ---


def test_hyundai_rotem_skips_plaintext_duplicate_between_marker_and_table():
    """마커 직후 빈 줄 대신 제목·기간·단위를 평문으로 반복하는 회사 — 결과가 0건이면 안 됨.

    실측 버그: _extract_period_blocks가 빈 줄만 스킵하고 평문 중복 줄은 스킵하지
    못해 전 회사 표가 0줄로 파싱되던 사고의 회귀 테스트.
    """
    results = _parse_hyundai_rotem_fixture()
    assert len(results) > 0


def test_hyundai_rotem_recognizes_suik_biyong_georae_labels():
    """"매출 등"/"매입 등"이 아니라 "수익거래"/"비용거래" 라벨도 customer/supply로 인식."""
    results = _parse_hyundai_rotem_fixture()
    directions = {r["direction"] for r in results}
    assert directions == {"customer", "supply"}


def test_hyundai_rotem_amounts_attributed_to_correct_counterparty():
    """2단 rowspan 하위분류 행(라벨 2개)에 의한 열 밀림으로 엉뚱한 상대에 금액이
    붙지 않아야 한다 — 헤더·데이터 셀 수가 정확히 일치하는 행만 채택하는 가드 확인.
    """
    results = _parse_hyundai_rotem_fixture()
    by_counterparty = {
        (r["counterparty"], r["direction"]): r["amount"] for r in results
    }
    # 현대제철 매출: 185,960,596천원 — 총계/매출거래 두 행 모두 이 값이 같아 가드
    # 통과 여부와 무관하게 항상 검증되지만, 기아(자릿수 편차 있는 행)로 오귀속되지
    # 않았는지가 핵심 — 기아 매출은 49,426,735천원(같은 열 순서 유지 확인)
    assert by_counterparty[("현대제철㈜", "customer")] == 185_960_596_000
    assert by_counterparty[("기아㈜", "customer")] == 49_426_735_000
    assert by_counterparty[("현대건설㈜", "supply")] == 34_279_000


def test_hyundai_rotem_zero_values_excluded():
    """0원 거래(예: 동북선도시철도 비용거래)는 엣지를 만들지 않는다."""
    results = _parse_hyundai_rotem_fixture()
    counterparties_supply = {
        r["counterparty"] for r in results if r["direction"] == "supply"
    }
    assert "동북선도시철도㈜" not in counterparties_supply
    assert parse_note("") == []
    assert parse_note("아무 표도 없는 일반 서술문입니다.") == []


# --- 전치(transposed)형: LIG디펜스앤에어로스페이스(2026-07-22 실측) ---
# parse_note()가 가정하는 "행=거래유형·열=상대회사명"의 정반대(행=상대회사명,
# 열=거래유형) — text_html의 ROWSPAN 카테고리를 그리드로 복원해 읽는다.


def _parse_lig_transposed_fixture() -> list[dict]:
    return parse_note_transposed(LIG_TRANSPOSED_FIXTURE.read_text(encoding="utf-8"))


def test_transposed_parses_correct_amounts():
    results = _parse_lig_transposed_fixture()
    by_counterparty = {
        (r["counterparty"], r["direction"]): r["amount"] for r in results
    }
    assert by_counterparty[("(주)엘아이지", "supply")] == 4_768_630_000
    assert by_counterparty[("엘아이지풍산프로테크(주)", "customer")] == 730_547_000
    assert by_counterparty[("엘아이지풍산프로테크(주)", "supply")] == 8_861_657_000


def test_transposed_excludes_receivable_payable_balance_columns():
    """"매출채권"/"매입채무"는 거래금액이 아니라 잔액이므로 제외돼야 한다."""
    results = _parse_lig_transposed_fixture()
    labels = {r["label"] for r in results}
    assert "매출채권" not in labels
    assert "매입채무" not in labels
    assert "기타채권" not in labels
    assert "기타채무" not in labels


def test_transposed_excludes_summary_row():
    """"전체 특수관계자" 합계 행은 개별 법인이 아니므로 counterparty로 잡히면 안 된다."""
    results = _parse_lig_transposed_fixture()
    counterparties = {r["counterparty"] for r in results}
    assert "전체 특수관계자" not in counterparties


def test_transposed_zero_amounts_excluded():
    """(주)엘아이지의 매출 등=0원은 엣지를 만들지 않는다."""
    results = _parse_lig_transposed_fixture()
    assert ("(주)엘아이지", "customer") not in {
        (r["counterparty"], r["direction"]) for r in results
    }


def test_transposed_returns_empty_when_no_matching_table():
    assert parse_note_transposed("<table><tr><th>foo</th></tr></table>") == []
    assert parse_note_transposed(None) == []


# --- 전치형 회귀: 기아(2026-07-22 실측) — 열 헤더가 "매출 등"이 아니라 "매출"
# (bare, 접미어 없음) 단독 라벨 + 제목·기간·단위가 한 표 2행에 함께 있는 형태 ---


def _parse_kia_transposed_fixture() -> list[dict]:
    return parse_note_transposed(KIA_TRANSPOSED_FIXTURE.read_text(encoding="utf-8"))


def test_kia_transposed_recognizes_bare_sale_purchase_labels():
    """"매출 등"이 아니라 "매출"(bare) 단독 라벨도 customer/supply로 인식해야 한다."""
    results = _parse_kia_transposed_fixture()
    by_counterparty = {
        (r["counterparty"], r["direction"]): r["amount"] for r in results
    }
    assert by_counterparty[("현대자동차㈜", "customer")] == 559_775 * 1_000_000
    assert by_counterparty[("현대자동차㈜", "supply")] == 653_348 * 1_000_000
    assert by_counterparty[("Hyundai Motor America", "customer")] == 191_408 * 1_000_000


def test_kia_transposed_excludes_other_income_and_purchase_columns():
    """"기타수익"/"기타매입"은 상거래 매출/매입이 아니므로 제외돼야 한다."""
    results = _parse_kia_transposed_fixture()
    labels = {r["label"] for r in results}
    assert "기타수익" not in labels
    assert "기타매입" not in labels


def test_kia_transposed_excludes_catchall_aggregate_row():
    """"유의적인 영향력을 행사하는 기타"처럼 "기타"로 끝나는 집계 캐치올 행은
    개별 법인이 아니므로 상대회사로 잡히면 안 된다."""
    results = _parse_kia_transposed_fixture()
    counterparties = {r["counterparty"] for r in results}
    assert "유의적인 영향력을 행사하는 기타" not in counterparties


def test_kia_transposed_handles_title_and_period_marker_in_one_table():
    """제목("특수관계자거래에 대한 공시")과 기간·단위("당기"/"(단위 : 백만원)")가
    별도 표가 아니라 한 표 2행에 같이 있는 경우도 기간 마커로 인식해야 한다
    (실측 버그: 이 경우 period가 끝내 설정되지 않아 결과가 항상 0건이었음)."""
    results = _parse_kia_transposed_fixture()
    assert len(results) > 0


def test_kia_transposed_zero_amounts_excluded():
    """Hyundai Motor Manufacturing Alabama,LLC의 매출=0원은 엣지를 만들지 않는다."""
    results = _parse_kia_transposed_fixture()
    assert ("Hyundai Motor Manufacturing Alabama,LLC", "customer") not in {
        (r["counterparty"], r["direction"]) for r in results
    }


# --- 전치형 회귀: 한화시스템(2026-07-22 실측) — 열 헤더가 "재화의 판매로 인한
# 수익, 특수관계자거래"/"재화의 매입, 특수관계자거래"(현대모비스 서술형 라벨과
# 동일 어휘군, 컬럼 헤더로 인코딩) ---


def _parse_hanwha_systems_transposed_fixture() -> list[dict]:
    return parse_note_transposed(
        HANWHA_SYSTEMS_TRANSPOSED_FIXTURE.read_text(encoding="utf-8")
    )


def test_hanwha_systems_transposed_recognizes_descriptive_labels():
    results = _parse_hanwha_systems_transposed_fixture()
    by_counterparty = {
        (r["counterparty"], r["direction"]): r["amount"] for r in results
    }
    assert by_counterparty[("한화에어로스페이스(주)", "customer")] == 148_447_645_000
    assert by_counterparty[("한화에어로스페이스(주)", "supply")] == 4_691_370_000


def test_hanwha_systems_transposed_excludes_other_sale_purchase_and_asset_columns():
    """"특수관계자 기타매출"/"특수관계자 기타매입"/"특수관계자거래, 자산증감"은
    상거래 매출/매입이 아니므로 제외돼야 한다."""
    results = _parse_hanwha_systems_transposed_fixture()
    labels = {r["label"] for r in results}
    assert "특수관계자 기타매출" not in labels
    assert "특수관계자 기타매입" not in labels
    assert "특수관계자거래, 자산증감" not in labels


def test_hanwha_systems_transposed_excludes_catchall_and_summary_rows():
    """"기타" 단독 행과 "전체 특수관계자 합계" 합계 행은 개별 법인이 아니다."""
    results = _parse_hanwha_systems_transposed_fixture()
    counterparties = {r["counterparty"] for r in results}
    assert "기타" not in counterparties
    assert "전체 특수관계자  합계" not in counterparties
    assert not any("합계" in c for c in counterparties)


def test_hanwha_systems_transposed_zero_sales_excluded():
    """㈜한화의 매출(재화의 판매로 인한 수익)=0원은 엣지를 만들지 않는다."""
    results = _parse_hanwha_systems_transposed_fixture()
    assert ("㈜한화", "customer") not in {
        (r["counterparty"], r["direction"]) for r in results
    }
