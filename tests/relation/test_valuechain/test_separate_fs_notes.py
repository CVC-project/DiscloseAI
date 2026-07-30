"""별도(개별)재무제표 주석 출처 표기 — 리더 판정 2026-07-30 (후속12 '그룹 합산' 선례 준용).

report 섹셔너가 마크업 변종을 읽게 되면서 `section_key`가 2종이 됐다:
`III.3.연결주석`(연결) · `III.5.별도주석`(**연결 미작성사**의 개별재무제표 주석).
연결 미작성사는 종속기업이 없어 내부거래 제거 문제가 성립하지 않지만, 금액 근거가
연결 기준이 아니라는 사실은 화면에 남아야 한다 → 표기에 `별도`를 명시한다.
"""

from __future__ import annotations

from modules.relation.storage.models import (
    CompanyNode,
    CompanyRegistry,
    RelationLocal,
    ValueChainEdge,
)
from modules.relation.valuechain.extract.related_party import (
    SEPARATE_FS_MARK,
    SEPARATE_FS_SECTION_KEY,
    apply,
    is_separate_fs_section,
)

# 연결 미작성사(신라섬유 유형)의 개별주석 — 행=거래유형·열=상대회사명
_NOTE_MD = "\n".join(
    [
        "| 특수관계자 거래 |",
        "| 당기 | (단위 : 백만원) |",
        "|  | 전체 특수관계자 |",
        "|  | 유의적인 영향력을 행사하는 회사 |",
        "|  | 삼성전자㈜ |",
        "| 매출 등, 특수관계자거래 | 1,234 |",
        "| 매입 등, 특수관계자거래 | 567 |",
    ]
)


def _section(section_key: str) -> dict:
    return {
        "rcept_no": "20990101000009",
        "title": "특수관계자 거래",
        "text_md": _NOTE_MD,
        "text_html": "",
        "section_key": section_key,
        "corp_code8": "00073570",
        "fiscal_year": 2025,
    }


def _seed(session):
    session.add(CompanyRegistry(corp_code="00126380", ticker="005930",
                                name_current="삼성전자", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00073570", ticker="000990",
                                name_current="보고사", market="KOSPI"))
    session.add(CompanyNode(corp_code="00126380", corp_name="삼성전자", ticker="005930"))
    session.add(CompanyNode(corp_code="00073570", corp_name="보고사", ticker="000990"))
    session.commit()


def test_is_separate_fs_section_reads_section_key():
    assert is_separate_fs_section({"section_key": SEPARATE_FS_SECTION_KEY})
    assert not is_separate_fs_section({"section_key": "III.3.연결주석"})
    assert not is_separate_fs_section({})  # 키 없는 옛 호출부는 연결 취급


def test_separate_fs_edge_is_marked_in_provenance(in_memory_session):
    session = in_memory_session
    _seed(session)

    result = apply(session=session, sections=[_section(SEPARATE_FS_SECTION_KEY)])

    edges = session.query(ValueChainEdge).filter_by(source_kind="rp_note").all()
    assert edges, "별도주석에서도 엣지가 나와야 한다"
    assert all(SEPARATE_FS_MARK in (e.provenance or "") for e in edges)
    assert result["separate_fs"] == len(edges)
    # ⚠️ rl-string "이름:타입:detail" 3분할 계약(FN-010) — 마커에 콜론 금지
    assert all(":" not in SEPARATE_FS_MARK for _ in edges)


def test_consolidated_edge_is_not_marked(in_memory_session):
    session = in_memory_session
    _seed(session)

    result = apply(session=session, sections=[_section("III.3.연결주석")])

    edges = session.query(ValueChainEdge).filter_by(source_kind="rp_note").all()
    assert edges
    assert all(SEPARATE_FS_MARK not in (e.provenance or "") for e in edges)
    assert result["separate_fs"] == 0


def test_governance_detail_marks_separate_fs(in_memory_session):
    """지배구조 경로도 같은 마커를 detail에 남긴다(그룹 합산과 동일 처리)."""
    from modules.relation.valuechain.extract.related_party import apply_governance

    session = in_memory_session
    _seed(session)
    html = (
        "<table><tr><th>구분</th><th>회사명</th><th>소재지</th></tr>"
        "<tr><td>유의적인 영향력을 행사하는 회사</td><td>삼성전자㈜</td><td>대한민국</td></tr>"
        "</table>"
    )
    sec = _section(SEPARATE_FS_SECTION_KEY)
    sec["text_md"] = ""
    sec["text_html"] = html

    apply_governance(session=session, sections=[sec], prune=False)

    rows = session.query(RelationLocal).filter_by(source_type="dart_filing").all()
    if rows:  # 파서가 이 표 형태를 잡았을 때만 표기를 검사(억지 매칭 금지)
        assert all(f"({SEPARATE_FS_MARK})" in (r.detail or "") for r in rows)


def test_edge_detail_keeps_marker_after_category_normalization():
    """정규화가 마커를 삼키면 화면에서 사라진다 — 그룹 합산과 같은 함정."""
    from modules.relation.universe.export import _edge_detail

    class _E:
        ratio = None
        group_name = None
        relation_type = "dart_filing"
        detail = f"사업보고서 주석: 대규모기업집단 소속회사 ({SEPARATE_FS_MARK})"

    assert f"({SEPARATE_FS_MARK})" in _edge_detail(_E())
