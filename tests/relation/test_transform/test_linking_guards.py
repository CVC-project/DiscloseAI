"""엔티티 링킹 방어층 회귀 테스트 (FN-013 — HMM 오링킹 사고 재발 방지).

사업보고서 추출의 정확성은 교육 서비스의 신뢰 기반(리더 지정 Key 요건).
여기 케이스들은 실제 발생한 사고의 박제다 — 다음 확장(전 상장사 재수집·T2 확장)에서
이 테스트가 깨지면 같은 사고가 재발한다는 뜻이므로 절대 삭제·완화하지 말 것.

방어 5층 (transform/CLAUDE.md "엔티티 링킹 방어 5층" 조문 참조):
  L1 모호 약칭 게이트 + 실존 상장사명 화이트리스트   (filters.is_ambiguous_abbrev)
  L2 쌍 단위 블록리스트                              (data/link_blocklist.csv)
  L3 ratio sanity (>100% 오파싱 차단)                (filters.apply otrCpr 분기)
  L4 50%+ 교차검증 스캔 → CPA 검수 리스트            (수동 루프 — 자동화 아님)
  L5 LinkFailQueue → 수동 별칭/블록 확정 (M2)        (storage.LinkFailQueue)
"""

from __future__ import annotations

import pytest

from modules.relation.common.names import NAME_ALIASES, normalize_company_name
from modules.relation.transform.filters import (
    is_ambiguous_abbrev,
    load_link_blocklist,
)


# ── L1: 모호 약칭 게이트 ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        # 실사고: 현대차 사업보고서의 해외 생산법인 약칭 무리 — 게이트 대상
        ("HMM", True),
        ("HMA", True),
        ("HMI", True),
        ("GMC", True),
        # 정식 사명이 약칭 형태인 실존 상장사도 형태상으로는 게이트 대상
        # (통과 여부는 ticker_map 화이트리스트가 결정 — apply() 내부)
        ("KT", True),
        ("NAVER", True),
        ("POSCO", True),
        # 게이트 비대상: 한글 포함·정식 법인 표기·긴 영문
        ("HD현대", False),
        ("(주)하림", False),
        ("HMM오션서비스", False),
        ("Hyundai Motor Manufacturing", False),
        ("삼성전자", False),
        ("", False),
    ],
)
def test_ambiguous_abbrev_gate(raw, expected):
    assert is_ambiguous_abbrev(raw) == expected


# ── L2: 쌍 단위 블록리스트 ──────────────────────────────────────────────────

def test_blocklist_contains_confirmed_mislinks():
    """CPA 검수 1차(2026-07-28)로 확정된 오링킹 쌍이 블록리스트에 남아 있어야 한다."""
    bl = load_link_blocklist()
    # 실사고 원형: 현대차 → HMM (해외법인 약칭 → 상장 해운사)
    assert ("005380", "011200") in bl
    # 유형 대표: 한글 동명 비상장 (DS단석 '하이브 주식회사' → 엔터 하이브)
    assert ("017860", "352820") in bl
    # 유형 대표: 구사명 충돌 (금호에이치티 '풍전약품(주)' → 당시 에스씨엠생명과학)
    assert ("214330", "298060") in bl
    # 유형 대표: 수치 오파싱 (영풍 → 시그네틱스 710651%)
    assert ("000670", "033170") in bl
    assert len(bl) >= 16


# ── 구사명 별칭 (registry name_current 시차 보정) ───────────────────────────

def test_former_name_alias_resolves_to_current():
    """구사명은 별칭으로 현재 사명에 흡수 — 과거 연도 공시 링킹의 시차 보정."""
    assert normalize_company_name("에스씨엠생명과학") == normalize_company_name("풍전약품")
    # 별칭 사전 자체에 등재돼 있는지 (실수로 지우면 여기서 잡힘)
    assert "에스씨엠생명과학" in NAME_ALIASES


# ── L3: ratio sanity 규칙 문서화 테스트 ────────────────────────────────────

def test_ratio_sanity_threshold_semantics():
    """>100%는 오파싱(주식수 혼입), 정확히 100%는 유효(상장 前 완전자회사).

    apply() 내부 분기라 여기서는 경계 의미만 박제 — 100.0은 통과, 100.01부터 차단.
    (실사고: 영풍→시그네틱스 710651.0 — 실지분 0.83%로 기준 미달이 정답이었음)
    """
    valid, invalid = 100.0, 710651.0
    assert not valid > 100
    assert invalid > 100


# ── prune 소유권 (2026-07-29 dart_filing 소실 사고 박제) ────────────────────
# 실사고: filters.apply()의 prune 스코프에 dart_filing이 들어 있어, 생산자
# (valuechain related_party.apply_governance — RelationLocal 직접 적재)가 만든
# 행 전체(115엣지·7개사)가 "RelationRaw에 없음=stale"로 transform 재실행 때마다
# 오인 삭제됐다. 아래 두 테스트가 깨지면 같은 소실이 재발한다는 뜻.

from modules.relation.storage.models import (  # noqa: E402
    CompanyRegistry,
    LinkFailQueue,
    RelationLocal,
    ValueChainEdge,
)
from modules.relation.transform import filters as transform_filters  # noqa: E402
from modules.relation.valuechain.extract.related_party import (  # noqa: E402
    apply as rp_apply,
    apply_governance,
)


def _seed_two_companies(session):
    session.add(
        CompanyRegistry(
            corp_code="00073570", ticker="096770",
            name_current="SK이노베이션", market="KOSPI",
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00164779", ticker="000660",
            name_current="SK하이닉스", market="KOSPI",
        )
    )
    session.commit()


def _dart_filing_row(**over):
    fields = dict(
        source_corp="096770", target_corp="000660",
        relation_type="dart_filing", source_type="dart_filing",
        ratio=None, detail="사업보고서 주석: 기타", bsns_year=2025, status="active",
    )
    fields.update(over)
    return RelationLocal(**fields)


def test_filters_prune_leaves_dart_filing_intact(in_memory_session):
    """transform 재실행(filters.apply)은 다른 생산자의 dart_filing 행을 지우면 안 된다."""
    _seed_two_companies(in_memory_session)
    in_memory_session.add(_dart_filing_row())
    in_memory_session.commit()

    result = transform_filters.apply(session=in_memory_session)  # RelationRaw 비어 있음

    survivors = (
        in_memory_session.query(RelationLocal)
        .filter_by(source_type="dart_filing").count()
    )
    assert survivors == 1, "filters prune이 dart_filing을 오인 삭제 — 소실 사고 재발"
    assert result["pruned_stale"] == 0


def test_apply_governance_prunes_stale_dart_filing(in_memory_session):
    """dart_filing의 stale 정리는 생산자(apply_governance) 소관 — 전량 실행에서
    이번 파스에 안 나온 행만 정리하고, 이번 파스 산출 행은 남긴다."""
    _seed_two_companies(in_memory_session)
    # 예전 실행이 남긴 stale 행(이번 파스에는 없는 연도)
    in_memory_session.add(_dart_filing_row(bsns_year=2020, detail="사업보고서 주석: 관계기업"))
    in_memory_session.commit()

    note = (
        "| 특수관계자 |\n"
        "| 당기 | (단위 : 백만원) |\n"
        "\n"
        "| 구분 | 특수관계자명 |\n"
        "| 기타 | SK하이닉스 |\n"
    )
    sections = [{
        "rcept_no": "20260316000827", "title": "특수관계자",
        "text_md": note, "text_html": None,
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = apply_governance(session=in_memory_session, sections=sections, prune=True)

    rows = in_memory_session.query(RelationLocal).filter_by(source_type="dart_filing").all()
    assert result["edges_kept"] == 1
    assert result["pruned_stale"] == 1
    assert [(r.source_corp, r.target_corp, r.bsns_year) for r in rows] == [
        ("096770", "000660", 2025)
    ]


def test_apply_governance_partial_run_does_not_prune(in_memory_session):
    """부분 주입 실행(sections 지정, prune 미지정)은 스캔 밖 행을 지우면 안 된다."""
    _seed_two_companies(in_memory_session)
    in_memory_session.add(_dart_filing_row(bsns_year=2020))
    in_memory_session.commit()

    apply_governance(session=in_memory_session, sections=[], prune=None)

    survivors = (
        in_memory_session.query(RelationLocal)
        .filter_by(source_type="dart_filing").count()
    )
    assert survivors == 1


# ── T1 주석 경로의 L1·L2 (2026-07-29 전 상장사 확대 시 연결) ────────────────
# 확대 전에는 rp_note/dart_filing 링킹이 정규화 정확일치+L5뿐이었다 — otrCpr에서
# 실제로 났던 HMM 사고가 주석 경로에서도 그대로 날 수 있는 구조. 아래는 그 재현.

def _rp_note_md(counterparty: str) -> str:
    return (
        "| 특수관계자거래 |\n"
        "| 당기 | (단위 : 백만원) |\n"
        "\n"
        f"|  | {counterparty} |\n"
        "| 매출 등 | 100 |\n"
    )


def test_rp_note_l1_gate_queues_ambiguous_abbrev(in_memory_session):
    """영문 2~5자 단독 약칭(해외법인류)은 **상장사로 링킹되지 않는다** → 큐 + 비상장 노드.

    ★U5 개정(2026-07-29): 게이트에 걸린 표기를 이제 버리지 않고 **공시에 적힌 그대로**
    비상장 노드로 살린다('HMA'는 'HMA'로 표시). 지켜야 하는 본질은 그대로다 —
    **상장사에 붙지 않을 것**. 사고(FN-013)는 차단하면서 정보는 잃지 않는다.
    """
    from modules.relation.storage.models import UnlistedNode

    _seed_two_companies(in_memory_session)
    # 'HMA'가 등록사명과 정확 일치하는 회사는 registry에 없음 — 화이트리스트 미통과
    sections = [{
        "rcept_no": "20990101000001", "title": "특수관계자거래",
        "text_md": _rp_note_md("HMA"), "text_html": None,
        "corp_code8": "00073570", "fiscal_year": 2025,
    }]
    result = rp_apply(session=in_memory_session, sections=sections)

    assert result["l1_ambiguous_queued"] == 1
    queued = in_memory_session.query(LinkFailQueue).filter_by(surface_form="HMA").one()
    assert queued.freq == 1

    # 핵심 불변식: 어떤 상장사에도 붙지 않았다
    listed_codes = {"00073570", "00164779"}
    for e in in_memory_session.query(ValueChainEdge).all():
        endpoints = {e.src_corp, e.dst_corp}
        assert endpoints & listed_codes == {"00073570"}, "약칭이 상장사에 오링킹됨"

    # 정보는 살아 있다 — 원문 그대로 비상장 노드
    node = in_memory_session.query(UnlistedNode).filter_by(name_raw="HMA").one()
    assert node.anchor_corp == "096770"  # 앵커=보고사 SK이노베이션
    assert result["unlisted_nodes"] == 1


def test_rp_note_l2_blocklist_blocks_confirmed_pair(in_memory_session):
    """실사고 원형 재현: 현대차 주석에 'HMM' 표기 — L1 화이트리스트(실존 상장사
    정식명)는 통과하더라도 L2 쌍 블록리스트가 최종 차단해야 한다."""
    session = in_memory_session
    session.add(CompanyRegistry(
        corp_code="00164742", ticker="005380", name_current="현대자동차", market="KOSPI",
    ))
    session.add(CompanyRegistry(
        corp_code="00164645", ticker="011200", name_current="HMM", market="KOSPI",
    ))
    session.commit()

    sections = [{
        "rcept_no": "20990101000002", "title": "특수관계자거래",
        "text_md": _rp_note_md("HMM"), "text_html": None,
        "corp_code8": "00164742", "fiscal_year": 2025,
    }]
    result = rp_apply(session=session, sections=sections)

    assert result["edges_kept"] == 0
    assert result["l2_blocklisted"] == 1
    assert session.query(ValueChainEdge).count() == 0
