"""특수관계자 주석 "구분/특수관계자명" 거버넌스 카테고리 표 파서 테스트.

fixture는 SK이노베이션 실제 공시(2026-07-22 수집, rcept 20260316000827)의
전체 노트 원문 — 거래금액 표 앞에 이 카테고리 표가 먼저 등장하는 실제 구조를
그대로 반영한다(sectioner의 평문 중복 렌더링 포함).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.relation.storage.models import CompanyRegistry, RelationLocal
from modules.relation.valuechain.extract.related_party import (
    apply_governance,
    parse_governance_carryforward,
    parse_governance_categories,
    parse_governance_html_rows,
    parse_governance_transaction_header,
    parse_governance_wide_row,
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
FIXTURE_ROTEM = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_hyundai_rotem.txt"
)
FIXTURE_KTNG = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_ktng.html"
)
FIXTURE_SAMSUNG_ELEC = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_samsung_electronics.html"
)
FIXTURE_DOOSAN = (
    Path(__file__).parent.parent
    / "fixtures"
    / "valuechain_related_party_governance_doosan.html"
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


def test_parses_wide_row_variant():
    """현대로템 실제 공시(2026-07-22 수집, rcept 20250321001612) — 카테고리가
    컬럼 헤더, 상대회사명이 그 아래 단일 데이터 행인 와이드 1행형."""
    results = parse_governance_wide_row(FIXTURE_ROTEM.read_text(encoding="utf-8"))
    assert {"category": "지배기업", "counterparty": "현대자동차㈜"} in results
    assert {"category": "관계기업", "counterparty": "하이스테이션㈜"} in results
    assert {"category": "그 밖의 특수관계자", "counterparty": "기아㈜"} in results
    assert {"category": "그 밖의 특수관계자", "counterparty": "현대제철㈜"} in results
    # "전체 특수관계자"/"특수관계자" 보일러플레이트 행은 카테고리로 오인되지 않아야 함
    categories = {r["category"] for r in results}
    assert "전체 특수관계자" not in categories
    assert categories == {"지배기업", "관계기업", "그 밖의 특수관계자"}


def test_wide_row_returns_empty_when_title_absent():
    assert parse_governance_wide_row("아무 관련 없는 텍스트") == []
    assert parse_governance_wide_row(None) == []


def test_wide_row_bails_out_safely_on_unexpected_shape():
    """LIG디펜스앤에어로스페이스류 — 제목은 같지만 표 구조가 달라(카테고리 헤더 행이
    아예 없음) 억지 매칭하지 않고 빈 결과를 반환해야 한다."""
    malformed = (
        "| 회사와 주요 거래 또는 채권ㆍ채무가 있는 특수관계자 현황에 대한 공시 |\n"
        "| 전체 특수관계자 | 특수관계자 | 지배기업 | (주)엘아이지 |  |\n"
    )
    assert parse_governance_wide_row(malformed) == []


def test_parses_html_rows_variant():
    """KT&G 실제 공시(2026-07-22 수집, rcept 20260318001422) — text_md 평탄화로는
    rowspan 정보가 유실돼 안전하게 못 읽던 행=개별회사형. 원본 text_html(ROWSPAN
    보존)을 직접 파싱하면 카테고리/회사명 위치가 항상 고정돼 모호성이 없다."""
    results = parse_governance_html_rows(
        FIXTURE_KTNG.read_text(encoding="utf-8")
    )
    by_name = {r["counterparty"]: r["category"] for r in results}
    assert by_name["(주)라이트팜텍"] == "관계기업"
    assert by_name["코람코반포프로젝트금융투자(주)"] == "관계기업"  # rowspan 캐리포워드
    assert by_name["케이비KT&G신성장1호펀드"] == "관계기업"  # 관계기업 그룹 마지막 행
    assert by_name["코람코유럽코어전문투자형사모부동산투자신탁제3-2호"] == "공동기업"
    assert by_name["지엘광진도시개발(주)"] == "기타"
    assert by_name["(주)코크렙제36호위탁관리부동산투자회사"] == "기타"
    # 회사명 칸에 카테고리 라벨("기타")이 그대로 들어간 캐치올 행은 스킵돼야 함
    assert "기타" not in by_name


def test_html_rows_returns_empty_when_no_matching_table():
    assert parse_governance_html_rows("<table><tr><th>foo</th></tr></table>") == []
    assert parse_governance_html_rows(None) == []


def test_parses_transaction_header_variant():
    """삼성전자 실제 공시(2026-07-22 수집, rcept 20260310002820) — 별도 거버넌스
    리스팅 표가 없고, 거래금액 표의 COLSPAN 카테고리 헤더 + 리프 회사명 헤더에
    정보가 인코딩돼 있는 경우. text_html의 COLSPAN을 grid로 복원해 짝짓는다."""
    results = parse_governance_transaction_header(
        FIXTURE_SAMSUNG_ELEC.read_text(encoding="utf-8")
    )
    by_name = {r["counterparty"]: r["category"] for r in results}
    assert by_name["삼성에스디에스㈜"] == "관계기업 및 공동기업"
    assert by_name["삼성전기㈜"] == "관계기업 및 공동기업"
    assert by_name["삼성물산㈜"] == "그 밖의 특수관계자"
    assert by_name["삼성이앤에이㈜"] == "대규모기업집단"
    assert by_name["㈜에스원"] == "대규모기업집단"
    # "기타 관계기업 및 공동기업" 같은 집계 컬럼은 특정 법인이 아니므로 제외
    assert not any(name.startswith("기타") for name in by_name)


def test_transaction_header_returns_empty_when_no_matching_table():
    assert parse_governance_transaction_header("<table><tr><th>foo</th></tr></table>") == []
    assert parse_governance_transaction_header(None) == []


def test_parses_carryforward_variant():
    """두산 실제 공시(2026-07-22 수집, rcept 20260323000945) — 구분/당기말/전기말/
    비고 4컬럼, 카테고리가 ROWSPAN으로 그룹 첫 행에만 붙는 캐리포워드형. 당기말
    컬럼만 채택하고(스냅샷 원칙) "-"(당기 중 이탈) 행은 스킵해야 한다."""
    results = parse_governance_carryforward(
        FIXTURE_DOOSAN.read_text(encoding="utf-8")
    )
    by_name = {r["counterparty"]: r["category"] for r in results}
    assert by_name["PT. SEGARA AKASA"] == "관계기업"
    assert by_name["마스턴일반사모부동산투자신탁제98호"] == "관계기업"  # ROWSPAN 캐리포워드
    assert by_name["Sichuan Kelun-Doosan Biotechnology Company Limited"] == "공동기업"
    assert by_name["두산연강재단"] == "기타특수관계자"
    assert by_name["중앙대학교 등"] == "기타특수관계자"
    # 당기말="-"(당기 중 이탈, 전기말에만 존재)인 하이창원㈜은 스킵돼야 함
    assert "하이창원㈜" not in by_name
    # 전기말="-"(당기 신규 취득)인 우리지붕형태양광일반사모특별자산투자신탁 1호는 당기말 기준 포함
    assert "우리지붕형태양광일반사모특별자산투자신탁 1호" in by_name


def test_carryforward_returns_empty_when_no_matching_table():
    assert parse_governance_carryforward("<table><tr><th>foo</th></tr></table>") == []
    assert parse_governance_carryforward(None) == []


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


# ── 콤마 나열형 회사명 분할 (2026-07-29 실측 — 71표기에 상장사 116건 묻힘) ──

def test_split_multi_counterparties_basic():
    from modules.relation.valuechain.extract.related_party import (
        split_multi_counterparties,
    )
    assert split_multi_counterparties("기아㈜, 현대제철㈜, 현대글로비스㈜") == [
        "기아㈜", "현대제철㈜", "현대글로비스㈜",
    ]
    # 분리 지점이 없으면 빈 리스트 (원문 링킹을 그대로 쓰게)
    assert split_multi_counterparties("삼성전자") == []
    assert split_multi_counterparties("") == []


# ⚠️ 아래 두 테스트는 **HTML 기반 파서 경로**(행=개별회사형)를 쓴다.
# text_md의 "구분/특수관계자명" 경로는 parse_governance_categories가 이미 콤마를
# 분리하므로 apply_governance의 신규 분할 코드를 타지 않는다 — 실제로 놓치고 있던
# 건 HTML 파서 3종이 통째로 넘기는 칸이므로 그 경로로 검증해야 의미가 있다.
def _html_rows_note(company_cell: str) -> str:
    """parse_governance_html_rows가 인식하는 최소 표(소재지·소유지분율 앵커)."""
    return (
        "<TABLE><TR><TH>구분</TH><TH>회사명</TH><TH>소재지</TH><TH>소유지분율</TH></TR>"
        f"<TR><TE>관계기업</TE><TE>{company_cell}</TE><TE>한국</TE><TE>20%</TE></TR>"
        "</TABLE>"
    )


def test_apply_governance_recovers_companies_from_comma_list(in_memory_session):
    """HTML 파서가 통째로 넘긴 콤마 나열 칸에서 개별 상장사를 회수한다."""
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00164779", ticker="000660",
                                name_current="SK하이닉스", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930",
                                name_current="삼성전자", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000003", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("SK하이닉스, 삼성전자"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = apply_governance(session=session, sections=sections, prune=False)

    targets = {r.target_corp for r in session.query(RelationLocal)
               .filter_by(source_type="dart_filing").all()}
    assert targets == {"000660", "005930"}
    assert result["edges_kept"] == 2


def test_apply_governance_prefers_whole_string_over_split(in_memory_session):
    """⚠️ 원문이 링킹되면 분할하지 않는다 — 콤마를 품은 사명을 쪼개 잃지 않기 위함.

    '가나, 다라 주식회사'가 그대로 registry에 있으면 분할 없이 그 회사로 붙어야 한다
    (분할하면 '가나'·'다라'가 되어 원 회사를 잃는다).
    """
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00999999", ticker="999999",
                                name_current="가나, 다라 주식회사", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00888888", ticker="888888",
                                name_current="가나", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000004", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("가나, 다라 주식회사"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    apply_governance(session=session, sections=sections, prune=False)

    rows = session.query(RelationLocal).filter_by(source_type="dart_filing").all()
    assert [r.target_corp for r in rows] == ["999999"], "원문 링킹을 우선해야 함"


# ── 그룹 집계 표현 (2026-07-29 리더 판정: 붙이되 "그룹 합산" 명시) ──────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("엘지디스플레이㈜와 종속기업", "엘지디스플레이㈜"),
        ("㈜엘지씨엔에스와 그 종속기업", "㈜엘지씨엔에스"),
        ("엘지전자㈜와 그 종속 및 공동기업", "엘지전자㈜"),
        ("삼성전자(주) 및 그 종속기업", "삼성전자(주)"),
        ("삼성물산㈜ 등", "삼성물산㈜"),
        ("SK바이오사이언스(주) 등 SK기업집단 계열회사", "SK바이오사이언스(주)"),
    ],
)
def test_strip_group_aggregate(raw, expected):
    from modules.relation.valuechain.extract.related_party import strip_group_aggregate
    assert strip_group_aggregate(raw) == expected


@pytest.mark.parametrize("name", ["삼성전자", "한국전구체 주식회사", "㈜씨텍", "현대종속기업개발"])
def test_normal_names_are_not_stripped(name):
    """⚠️ 회귀 박제: 집계 꼬리는 연결어(및·와·과·등) 뒤에 올 때만 인정한다.
    '현대종속기업개발'처럼 '종속기업'을 품은 정상 사명을 깎으면 안 된다."""
    from modules.relation.valuechain.extract.related_party import strip_group_aggregate
    assert strip_group_aggregate(name) is None


def test_apply_governance_marks_group_aggregate(in_memory_session):
    """집계 표현은 대표사로 붙되 detail에 '그룹 합산'이 명시돼야 한다."""
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930",
                                name_current="삼성전자", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000005", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("삼성전자(주) 및 그 종속기업"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = apply_governance(session=session, sections=sections, prune=False)

    row = session.query(RelationLocal).filter_by(source_type="dart_filing").one()
    assert row.target_corp == "005930"
    assert "그룹 합산" in row.detail
    assert ":" not in row.detail.split("사업보고서 주석:")[1], "rl-string 3분할 계약 보호"
    assert result["group_aggregate"] == 1


def test_apply_governance_no_mark_for_plain_name(in_memory_session):
    """평이한 사명은 마커가 붙지 않는다(집계로 오인 금지)."""
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930",
                                name_current="삼성전자", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000006", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("삼성전자"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = apply_governance(session=session, sections=sections, prune=False)
    row = session.query(RelationLocal).filter_by(source_type="dart_filing").one()
    assert "그룹 합산" not in row.detail
    assert result["group_aggregate"] == 0
