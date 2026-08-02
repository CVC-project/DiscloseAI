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


# ── rp_note VCE도 생산자가 prune한다 (2026-07-30, dangling 112건 발견) ────────

def test_apply_prunes_stale_rp_note_edges(in_memory_session):
    """⚠️ 회귀 박제: apply()에 prune이 없어 과거 코드 세대가 만든 rp_note VCE가
    남고, **이미 삭제된 비상장 노드 uid를 가리키는 dangling 참조 112건**이 누적됐다
    (전수 검증에서 발견). transform/CLAUDE.md "prune은 생산자 소관"의 rp_note 판.
    """
    from modules.relation.storage.models import ValueChainEdge
    from modules.relation.valuechain.extract.related_party import apply

    session = in_memory_session
    session.add(ValueChainEdge(
        src_corp="x_deadbeefdead", dst_corp="00126380", edge_type="supply",
        tier="T1", source_kind="rp_note", rcept_no="20200101000001",
        provenance="stale", amount=1.0, as_of=2020, status="active"))
    # 다른 원천(공급계약)은 이 함수 소관이 아니므로 건드리지 않아야 한다
    session.add(ValueChainEdge(
        src_corp="005930", dst_corp="000660", edge_type="customer",
        tier="T1", source_kind="supply_contract", rcept_no="20200101000002",
        provenance="keep", amount=1.0, as_of=2020, status="active"))
    session.commit()

    result = apply(session=session, sections=[], prune=True)

    kinds = {e.source_kind for e in session.query(ValueChainEdge).all()}
    assert result["pruned_stale"] == 1
    assert kinds == {"supply_contract"}, "타 원천 prune 금지(소유권 경계)"


def test_apply_partial_run_does_not_prune(in_memory_session):
    """부분 주입 실행(테스트·증분)은 스캔 밖 행을 지우면 안 된다 —
    apply_governance와 동일 규율(dart_filing 소실 사고의 교훈)."""
    from modules.relation.storage.models import ValueChainEdge
    from modules.relation.valuechain.extract.related_party import apply

    session = in_memory_session
    session.add(ValueChainEdge(
        src_corp="005930", dst_corp="000660", edge_type="supply", tier="T1",
        source_kind="rp_note", rcept_no="20200101000003", provenance="x",
        amount=1.0, as_of=2020, status="active"))
    session.commit()

    result = apply(session=session, sections=[])   # prune 미지정 = 부분 주입
    assert result["pruned_stale"] == 0
    assert session.query(ValueChainEdge).count() == 1


# ── 뭉침 칸 분할을 비상장 노드 생성 前으로 (2026-07-30, 후속 14 잔여 2) ───────

def _unlisted_names(session) -> set[str]:
    from modules.relation.storage.models import UnlistedNode
    return {r.name_raw for r in session.query(UnlistedNode).all()}


def test_split_runs_before_unlisted_node_creation(in_memory_session):
    """⚠️ 회귀 박제: 한 칸에 뭉친 법인은 **조각마다 노드**가 돼야 한다.

    수리 전에는 분할 조각 중 상장사만 회수하고 나머지는 버렸고, 하나도 안 붙으면
    칸 전체가 노드 1개가 됐다 — 노드 하나가 계열 전체를 대표하고 kind도 오분류됐다
    (실측: 한국전력공사 한 칸 3,662자·114개사).
    """
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.commit()

    cell = "한국수력원자력(주), 한국남동발전(주), 한국중부발전(주)"
    sections = [{
        "rcept_no": "20990101000010", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note(cell),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = apply_governance(session=session, sections=sections, prune=False)

    names = _unlisted_names(session)
    assert names == {"한국수력원자력(주)", "한국남동발전(주)", "한국중부발전(주)"}
    assert result["unlisted_nodes"] == 3
    assert result["edges_kept"] == 3, "칸 전체가 노드 1개로 뭉치면 안 됨"
    assert cell not in names, "뭉친 원문 전체가 노드가 되어선 안 됨"


def test_split_mixes_listed_and_unlisted_pieces(in_memory_session):
    """조각 중 상장사는 상장 노드로, 나머지는 비상장 노드로 — 이전에는 비상장
    조각이 통째로 버려졌다."""
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930",
                                name_current="삼성전자", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000011", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("삼성전자, ㈜미상장상대"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    apply_governance(session=session, sections=sections, prune=False)

    targets = {r.target_corp for r in session.query(RelationLocal)
               .filter_by(source_type="dart_filing").all()}
    assert "005930" in targets                      # 상장 조각
    assert _unlisted_names(session) == {"㈜미상장상대"}  # 비상장 조각도 보존
    assert len(targets) == 2


def test_whole_string_link_still_wins_over_split(in_memory_session):
    """⚠️ 원문 우선 불변 — 콤마를 품은 사명이 registry에 있으면 분할하지 않는다.
    (순서를 당기면서 이 방어가 깨지지 않았음을 박제)"""
    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00073570", ticker="096770",
                                name_current="SK이노베이션", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00999999", ticker="999999",
                                name_current="가나, 다라 주식회사", market="KOSPI"))
    session.commit()

    sections = [{
        "rcept_no": "20990101000012", "title": "특수관계자",
        "text_md": "", "text_html": _html_rows_note("가나, 다라 주식회사"),
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    apply_governance(session=session, sections=sections, prune=False)

    rows = session.query(RelationLocal).filter_by(source_type="dart_filing").all()
    assert [r.target_corp for r in rows] == ["999999"]
    assert _unlisted_names(session) == set(), "원문이 붙었으면 비상장 노드 생성 금지"


# ── 열 밀림 수리 (2026-07-30, 후속 14 잔여 1 — 앵커 7곳 실공시 fixture) ──────
#
# 증상: 지분율·금액이 회사명 칸으로 들어오고 진짜 회사명은 detail에만 남았다
# (리더가 본 화면: JW중외제약 노드 n='(4,891,807)' detail='JW홀딩스㈜').
# 잡음 게이트가 산물을 막고 있었을 뿐 근본 원인은 파서 3종의 **위치 가정**이었다.
# 전수 실측(1,550노트): 거버넌스 산출 9,491건 중 잡음 3,721 → 수리 후 8,580건 중 313.

FX = Path(__file__).parent.parent / "fixtures"
F_ILSHIN = FX / "valuechain_rp_gov_carry_ratio_ilshin.html"
F_HYUNDAICORP_H = FX / "valuechain_rp_gov_carry_ratio_hyundaicorp_h.html"
F_HL_DNI = FX / "valuechain_rp_gov_carry_ratio_hl_dni.html"
F_ISENS = FX / "valuechain_rp_gov_html_rows_isens.html"
F_JW_2025 = FX / "valuechain_rp_gov_txnheader_jw_2025.html"
F_JW_2024 = FX / "valuechain_rp_gov_txnheader_jw_2024.html"
F_APROGEN = FX / "valuechain_rp_gov_cat_parens_aprogen.txt"


def _by_name(results: list[dict]) -> dict[str, str]:
    return {r["counterparty"]: r["category"] for r in results}


def test_carryforward_reads_name_column_not_ratio_ilshin():
    """일신방직 실공시(rcept 20260318001204) — `구분|특수관계자명|주요 영업활동|
    소재지|당기말|전기말`. 당기말/전기말은 **지분율 하위 헤더**이므로 회사명은
    별도 칸에서 읽어야 한다(수리 전: '48.54%'·'24.28%'가 회사명으로 나왔다)."""
    results = parse_governance_carryforward(F_ILSHIN.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert by_name["㈜지오다노"] == "공동기업"
    assert by_name["하이젠알앤엠㈜"] == "관계기업"
    assert not any("%" in n for n in by_name), "지분율이 회사명이 되어선 안 됨"


def test_carryforward_ratio_style_skips_disposed_hyundaicorp_h():
    """현대코퍼레이션홀딩스 실공시(rcept 20260323001454) — 당기말 '-' / 전기말
    '23.72%'인 오픈더테이블(주)은 **당기 중 처분**이라 현재 관계로 노출하면 안 된다
    (후속14 오류1 '처분 부활'과 같은 사상)."""
    results = parse_governance_carryforward(F_HYUNDAICORP_H.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert by_name["현대코퍼레이션(주)"] == "관계기업"
    assert by_name["HYUNDAI MAO LEGACY CO., LTD.(*2,*4)"] == "공동기업"
    assert not any(n.startswith("오픈더테이블") for n in by_name), "처분분 부활 금지"
    assert not any("%" in n for n in by_name)


def test_carryforward_ratio_style_keeps_rows_without_ratio_hl_dni():
    """HL D&I 실공시(rcept 20250317000836) — 지분율이 양쪽 다 '-'인 행은 지분율이
    공시되지 않은 것일 뿐 **현재 특수관계자**이므로 유지한다. 반대로 당기말만 '-'인
    한라엔컴㈜(전기말 15.00, 당기 중 매각)은 스킵. 들여쓰기 불릿('- ')은 사명이
    아니므로 제거한다."""
    results = parse_governance_carryforward(F_HL_DNI.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert "에이치엘홀딩스 주식회사" in by_name
    assert "HL URIMAN, Inc." in by_name          # 당기말·전기말 모두 '-' → 유지
    assert "HL Transportation, LLC." in by_name  # 선행 불릿 제거됨
    assert not any(n.startswith("-") for n in by_name), "들여쓰기 불릿 잔존 금지"
    assert "한라엔컴(주)" not in by_name           # 당기 중 매각 → 스킵
    assert "발안남양도로(주)" in by_name            # 당기 신규(전기말 '-') → 유지
    assert not any(n.replace(".", "").isdigit() for n in by_name)


def test_html_rows_finds_name_column_by_header_isens():
    """아이센스 실공시(rcept 20260318001657) — `회사명|소유지분율(당기말·전기말)|
    소재지|결산월|업종`. 회사명이 소재지 **왼쪽 3칸**이라 '소재지-1' 위치 가정이
    통째로 밀렸다(수리 전: category='5.51%', counterparty='5.56%').
    카테고리는 표 안의 전폭 머리행('관계기업:')에서 온다."""
    results = parse_governance_html_rows(F_ISENS.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert by_name["(주)케어메디(*1)(*2)"] == "관계기업"
    assert by_name["신한-데브 헬스케어 투자조합 1호"] == "관계기업"
    assert not any("%" in n for n in by_name), "지분율이 회사명이 되어선 안 됨"
    assert "전기말" not in by_name and "회사명" not in by_name


def test_transaction_header_pairs_leaf_row_jw_2025():
    """JW중외제약 실공시(rcept 20260318001544) — 카테고리 층이 전부 보일러플레이트라
    기존 '위에서 건너뛰기'가 **한 층 아래로 지나쳐** 회사명이 카테고리, 금액이
    회사명이 됐다(리더가 본 화면: n='(4,891,807)' detail='JW홀딩스㈜')."""
    results = parse_governance_transaction_header(F_JW_2025.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert "JW홀딩스㈜" in by_name
    assert not any("," in n and n.strip("()").replace(",", "").isdigit() for n in by_name)
    assert "(4,891,807)" not in by_name


def test_transaction_header_pairs_leaf_row_with_total_column_jw_2024():
    """JW중외제약 실공시(rcept 20250318001192) — 반대 방향 실패. 합계 컬럼
    ('전체 특수관계자  합계')이 있으면 보일러플레이트 판정이 실패해 **한 층 위에서**
    멈췄다(수리 전: category='전체 특수관계자', counterparty='지배기업')."""
    results = parse_governance_transaction_header(F_JW_2024.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert by_name["JW홀딩스㈜"] == "지배기업"
    assert by_name["JW신약㈜"] == "특수관계자"
    assert by_name["JW생명과학㈜"] == "특수관계자"
    assert "지배기업" not in by_name, "K-IFRS 구분이 회사명이 되어선 안 됨"
    assert not any("합계" in n for n in by_name)


def test_categories_does_not_split_inside_parentheses_aprogen():
    """에이프로젠바이오로직스 실공시(rcept 20260320000881) — `㈜앱토크롬(구,
    ㈜에이피헬스케어)(*)`의 **괄호 안 콤마**를 쪼개 사명이 두 동으로 갈렸다
    (수리 전: '㈜앱토크롬(구' + '㈜에이피헬스케어)(*)'). 원칙 ②의 분할판."""
    results = parse_governance_categories(F_APROGEN.read_text(encoding="utf-8"))
    by_name = _by_name(results)
    assert by_name["㈜앱토크롬(구, ㈜에이피헬스케어)(*)"] == "관계기업"
    assert by_name["㈜앱튼"] == "관계기업"
    assert by_name["㈜지베이스"] == "지배기업의 최대주주"
    assert not any(n.endswith("(구") for n in by_name)
    # 공백이 앞에 붙은 콤마('에이프로젠아이앤씨㈜ ,지비티㈜')도 정상 분할
    assert "지비티㈜" in by_name


# ── 분할 규칙 1벌 (split_company_list) ──────────────────────────────────────

def test_split_company_list_keeps_parenthesised_comma():
    from modules.relation.valuechain.extract.related_party import split_company_list
    assert split_company_list("㈜앱토크롬(구, ㈜에이피헬스케어)(*), ㈜앱튼") == [
        "㈜앱토크롬(구, ㈜에이피헬스케어)(*)", "㈜앱튼",
    ]
    # 괄호 안 콤마뿐이면 분리 지점이 없다 — 통째로 원문 링킹에 맡긴다
    assert split_company_list("㈜에이피헬스케어(구.㈜에이프로젠헬스케어앤게임즈)(*1, 2)") == []


def test_split_company_list_rejoins_legal_suffix():
    """⚠️ 회귀 박제: 'Co., Ltd.'의 콤마를 쪼개면 'Ltd.' 조각이 노드 후보로 남는다
    (실측 261건이 suffix_fragment 잡음). 법인격 접미어만 남는 조각은 되붙인다."""
    from modules.relation.valuechain.extract.related_party import split_company_list
    assert split_company_list("HL (Suzhou) Logistics Co., Ltd., 신한벽지 주식회사") == [
        "HL (Suzhou) Logistics Co., Ltd.", "신한벽지 주식회사",
    ]
    assert split_company_list("Samsung Electronics Co., Ltd.") == []


@pytest.mark.parametrize("name", [
    "Kia Mexico, S.A. de C.V.",          # 토큰 열거로는 못 잡던 형태 (실측 소실 1건)
    "Samsung Electronics Co., Ltd.",
    "Delfi-Orion Pte. Ltd.",
])
def test_split_company_list_never_splits_single_foreign_name(name):
    """⚠️ 회귀 박제: 법인격 접미어를 토큰 목록으로 열거하면 미등록 형태에서 새는다
    ('S.A. de C.V.'). 형태 규칙(알파벳 8자 이하 + 점 포함)으로 막는다."""
    from modules.relation.valuechain.extract.related_party import split_company_list
    assert split_company_list(name) == []


@pytest.mark.parametrize("short_name", ["HMM", "KT", "LG"])
def test_split_company_list_does_not_absorb_short_real_names(short_name):
    """⚠️ 접미어 판정이 느슨하면 **실존 단독 사명이 앞 조각에 흡수**된다.
    점 없는 짧은 사명(HMM·KT)은 접미어로 보지 않는다 — FN-013 계열 위험."""
    from modules.relation.valuechain.extract.related_party import split_company_list
    assert split_company_list(f"㈜가나다, {short_name}") == ["㈜가나다", short_name]


def test_split_multi_counterparties_still_splits_plain_list():
    """기존 동작 보존 — 평이한 콤마 나열은 그대로 분할된다."""
    from modules.relation.valuechain.extract.related_party import (
        split_multi_counterparties,
    )
    assert split_multi_counterparties("한국수력원자력(주), 한국남동발전(주)") == [
        "한국수력원자력(주)", "한국남동발전(주)",
    ]


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
