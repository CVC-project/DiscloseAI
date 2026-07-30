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


# ══ 2026-07-29 전수 검증에서 잡은 파이프라인 오류 — 회귀 박제 (반복 금지) ══════

def test_upsert_keeps_higher_ratio_on_key_collision(in_memory_session):
    """⚠️ order-dependent 사고 박제: DART hyslrSttus는 **주식 종류마다 별도 행**을 준다.
    무조건 덮어쓰면 응답 순서에 따라 우선주(0.71%)가 보통주(34.0%)를 이기고,
    이어 kifrs가 5% 미만으로 판정해 **최대주주 엣지를 통째로 삭제**한다
    (실측: 계양전기←해성산업 34%, DL←㈜대림 48.27%가 화면에서 사라짐)."""
    from modules.relation.storage.models import RelationRaw

    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00000001", ticker="012200",
                                name_current="계양전기", market="KOSPI"))
    session.add(CompanyRegistry(corp_code="00000002", ticker="004890",
                                name_current="해성산업", market="KOSPI"))
    # 보통주 34.0% 먼저, 우선주 0.71% 나중 — 순서대로 들어와도 34.0이 남아야 한다
    for ratio in (34.0, 0.71):
        session.add(RelationRaw(
            source_name="해성산업", target_name="계양전기", relate="최대주주",
            ratio=ratio, source_type="hyslrSttus", bsns_year=2025,
        ))
    session.commit()

    transform_filters.apply(session=session)
    edge = (session.query(RelationLocal)
            .filter_by(source_corp="004890", target_corp="012200").one())
    assert edge.ratio == 34.0, "우선주 행이 보통주 최대주주 지분을 덮어씀"


def test_self_loop_edges_are_dropped(in_memory_session):
    """⚠️ 회귀 박제: 자사주·최대주주 본인 행이 A→A 엣지가 되면
    "KG스틸의 관계기업 = KG스틸 39.97%"가 화면에 뜬다(실측 36건)."""
    from modules.relation.storage.models import RelationRaw

    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00000003", ticker="016380",
                                name_current="KG스틸", market="KOSPI"))
    session.add(RelationRaw(
        source_name="KG스틸", target_name="KG스틸", relate="최대주주",
        ratio=39.97, source_type="hyslrSttus", bsns_year=2025,
    ))
    session.commit()

    result = transform_filters.apply(session=session)
    assert session.query(RelationLocal).count() == 0
    assert result["dropped_self_loop"] == 1


def test_stock_kind_in_name_column_is_rejected(in_memory_session):
    """⚠️ 회귀 박제: DART 응답 컬럼 밀림(445090 에이직랜드) — 주주명 칸에 '보통주'가
    들어온다. 노드로 만들면 '보통주'라는 주주가 생긴다."""
    from modules.relation.storage.models import RelationRaw

    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00000004", ticker="445090",
                                name_current="에이직랜드", market="KOSDAQ"))
    session.add(RelationRaw(
        source_name="보통주", target_name="에이직랜드", relate="최대주주",
        ratio=23.67, source_type="hyslrSttus", bsns_year=2025,
    ))
    session.commit()

    result = transform_filters.apply(session=session)
    assert result["dropped_stock_kind_row"] == 1
    assert session.query(RelationLocal).count() == 0


def test_equity_lineages_are_deduped_into_one_edge(in_memory_session):
    """⚠️ 회귀 박제: 지분 2원천(hyslr·otrCpr)은 **같은 사실의 두 기록**이다.
    source_type을 dedupe 키에 그대로 두면 둘 다 살아남아 같은 관계에 서로 다른
    지분율·연도가 한 화면에 뜬다(실측 366건 — 유한양행→이뮨온시아 76.9% + 65.93%)."""
    from modules.relation.storage.queries import latest_relation_local_edges

    session = in_memory_session
    session.add(RelationLocal(source_corp="000100", target_corp="424870",
                              relation_type="subsidiary", ratio=76.9,
                              source_type="otrCprInvstmntSttus", bsns_year=2024,
                              status="active"))
    session.add(RelationLocal(source_corp="000100", target_corp="424870",
                              relation_type="subsidiary", ratio=65.93,
                              source_type="hyslrSttus", bsns_year=2025,
                              status="active"))
    session.commit()

    edges = latest_relation_local_edges(session)
    pair = [e for e in edges if e.source_corp == "000100"]
    assert len(pair) == 1, "같은 관계가 두 번 표시됨"
    assert pair[0].bsns_year == 2025, "최신 연도가 채택돼야 함"


def test_layer_coexistence_still_holds(in_memory_session):
    """⚠️ 위 dedupe가 과하면 안 된다 — ftc(계열)와 지분은 **다른 계보**라 공존한다
    (storage/CLAUDE.md 레이어 공존 원칙)."""
    from modules.relation.storage.queries import latest_relation_local_edges

    session = in_memory_session
    session.add(RelationLocal(source_corp="005930", target_corp="006400",
                              relation_type="investment", ratio=19.6,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    session.add(RelationLocal(source_corp="005930", target_corp="006400",
                              relation_type="ftc_group", ratio=None,
                              source_type="ftc", bsns_year=2025, status="active"))
    session.commit()

    edges = latest_relation_local_edges(session)
    assert len({e.source_type for e in edges}) == 2, "레이어 공존이 깨짐"


def test_common_shares_win_over_preferred(in_memory_session):
    """⚠️ 회귀 박제(적대적 검증): K-IFRS 지배력 판정은 **의결권** 기준이다.
    'higher ratio 채택'만 쓰면 우선주 29.91%가 보통주 7.55%를 이겨 지배력을
    과대표시한다(실측 428건 — 레이←㈜레이홀딩스)."""
    from modules.relation.storage.models import RelationRaw

    session = in_memory_session
    session.add(CompanyRegistry(corp_code="00000005", ticker="228670",
                                name_current="레이", market="KOSDAQ"))
    session.add(CompanyRegistry(corp_code="00000006", ticker="999001",
                                name_current="레이홀딩스", market="KOSDAQ"))
    for ratio, knd in ((7.55, "보통주"), (29.91, "우선주")):
        session.add(RelationRaw(source_name="레이홀딩스", target_name="레이",
                                relate="최대주주", ratio=ratio, stock_knd=knd,
                                source_type="hyslrSttus", bsns_year=2025))
    session.commit()

    transform_filters.apply(session=session)
    edge = (session.query(RelationLocal)
            .filter_by(source_corp="999001", target_corp="228670").one())
    assert edge.ratio == 7.55, "우선주가 의결권 지분을 덮어씀"


def test_disposed_stake_does_not_resurrect(in_memory_session):
    """⚠️ 회귀 박제(적대적 검증, 최중대): 지분을 처분해 최신 연도가 <5%가 되면
    그 관계는 **끝난 것**이다. <5%를 삭제하면 최신 행이 사라져 D13 신선도 규칙이
    **처분 직전 연도**를 최신으로 골라 끝난 관계를 현재처럼 되살린다
    (실측: SK→에스케이머티리얼즈그룹포틴 화면 75% 종속 / 2025 공시 0.0%)."""
    from modules.relation.storage.queries import latest_relation_local_edges
    from modules.relation.transform import kifrs

    session = in_memory_session
    session.add(RelationLocal(source_corp="034730", target_corp="x_abc",
                              relation_type="ownership", ratio=75.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2024,
                              status="active"))
    session.add(RelationLocal(source_corp="034730", target_corp="x_abc",
                              relation_type="ownership", ratio=0.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    session.commit()

    kifrs.apply(session=session)
    # 2025 행은 종료로 기록되고(삭제 아님), 그 쌍은 화면에서 빠진다
    assert (session.query(RelationLocal)
            .filter_by(bsns_year=2025).one().status == "terminated")
    shown = [e for e in latest_relation_local_edges(session)
             if e.source_corp == "034730"]
    assert shown == [], "처분한 지분이 화면에 부활함"


# ── D13 신선도 지배구조 확장 (2026-07-30, 리더 지적) ─────────────────────────
#
# 후속 8의 D13 채록·구현이 **밸류체인 원천 3종에서 끝나** 있었고 지배구조에는 절대
# 연도 컷이 없었다. `latest_relation_local_edges`는 쌍별 최신만 고르므로 그 쌍을
# 마지막으로 공시한 해가 2020이면 2020 행이 그대로 "현재 관계"로 렌더됐다
# (실측: 화면 지배구조 36,321건 중 2023년 이하 4,320건 = 11.9%.
#  예 — 넥스틴→Nextin Solutions LTD. 100%가 2020년 공시 기준으로 노출).

def test_governance_cut_drops_pair_the_reporter_stopped_disclosing(in_memory_session):
    """⚠️ 회귀 박제: 보고사가 최신 공시에서 더 언급하지 않은 상대는 화면에서 빠진다.

    넥스틴 실측 재현 — 타법인출자 명세(보고사=출자사)의 최신 연도는 2025인데
    Nextin Solutions는 2020에만 있다 = 처분·청산. 2020 행이 현재 관계가 되면 안 된다.
    """
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    # 보고사 넥스틴(348210)의 최신 타법인출자 = 2025 (다른 상대)
    session.add(RelationLocal(source_corp="348210", target_corp="005930",
                              relation_type="investment", ratio=6.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    # 2020에만 있는 상대 — 그 후 명세에서 사라짐
    session.add(RelationLocal(source_corp="348210", target_corp="x_nextinsol",
                              relation_type="subsidiary", ratio=100.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2020,
                              status="active"))
    session.commit()

    shown = {(e.target_corp, e.bsns_year) for e in current_governance_edges(session)}
    assert ("005930", 2025) in shown
    assert ("x_nextinsol", 2020) not in shown, "보고사가 더 안 올린 상대 = 현재 관계 아님"


def test_governance_cut_is_per_reporter_not_global_year(in_memory_session):
    """⚠️ 전역 연도 컷이 아니다(리더 승인) — 아직 2025 공시가 없는 회사의 지배구조가
    통째로 비면 안 된다. D13이 rp_note에 쓴 '2025 미제출사 불이익 없음'과 같은 사상."""
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    session.add(RelationLocal(source_corp="111111", target_corp="005930",
                              relation_type="investment", ratio=6.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    # 최신이 2024인 별개 보고사 — 전역 2025 컷이면 사라진다
    session.add(RelationLocal(source_corp="222222", target_corp="000660",
                              relation_type="associate", ratio=25.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2024,
                              status="active"))
    session.commit()

    shown = {(e.source_corp, e.bsns_year) for e in current_governance_edges(session)}
    assert ("222222", 2024) in shown, "2025 미제출사 불이익 금지"
    assert ("111111", 2025) in shown


def test_governance_cut_reporter_is_target_for_hyslr(in_memory_session):
    """⚠️ 보고사가 원천마다 다르다 — hyslrSttus(최대주주 현황)는 **피출자사가 보고사**다
    (자기 주주를 공시). source_corp(주주)를 보고사로 보면 컷이 엉뚱하게 걸린다."""
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    # 회사 333333이 2025에 주주 A를, 2020에 주주 B를 공시했다 → B는 이미 이탈
    session.add(RelationLocal(source_corp="x_holderA", target_corp="333333",
                              relation_type="subsidiary", ratio=55.0,
                              source_type="hyslrSttus", bsns_year=2025, status="active"))
    session.add(RelationLocal(source_corp="x_holderB", target_corp="333333",
                              relation_type="subsidiary", ratio=51.0,
                              source_type="hyslrSttus", bsns_year=2020, status="active"))
    session.commit()

    shown = {e.source_corp for e in current_governance_edges(session)}
    assert "x_holderA" in shown
    assert "x_holderB" not in shown


def test_governance_cut_exempts_ftc(in_memory_session):
    """공정위 계열 엣지는 보고 주체가 기업이 아니다(공정위 발표) → 연도 컷 비대상."""
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    session.add(RelationLocal(source_corp="005930", target_corp="006400",
                              relation_type="ftc_group", group_name="삼성",
                              source_type="ftc", bsns_year=2025, status="active"))
    session.add(RelationLocal(source_corp="005930", target_corp="000660",
                              relation_type="investment", ratio=5.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2020,
                              status="active"))
    session.commit()
    shown = {(e.target_corp, e.source_type) for e in current_governance_edges(session)}
    assert ("006400", "ftc") in shown


def test_edge_detail_carries_disclosure_year(in_memory_session):
    """지배구조 detail에 공시 연도가 붙는다(리더 지시). ⚠️ 콜론 금지 —
    rl-string '이름:타입:detail' 3분할 계약(FN-010)."""
    from modules.relation.universe.export import _edge_detail_with_year

    e = RelationLocal(source_corp="005930", target_corp="006400",
                      relation_type="subsidiary", ratio=19.9,
                      source_type="otrCprInvstmntSttus", bsns_year=2025)
    d = _edge_detail_with_year(e)
    assert d == "19.9% · 2025"
    assert ":" not in d


def test_governance_cut_is_per_lineage_not_per_company(in_memory_session):
    """⚠️ 회귀 박제: 최신 연도는 **(보고사, 계보)별**로 구한다.

    1차 구현이 보고사별로만 구해 원천을 섞었고, 자기 원천 기준으론 최신인 엣지가
    다른 원천이 더 최신이라는 이유로 잘렸다(실측 376건 — LG이노텍 주석 2023이
    지분 2025에 밀려 컷, SK리츠는 반대로 주석 2026이 지분 2025를 컷).
    원천마다 커버리지가 다르므로(주석 파서 공백·결산월 차이) 섞으면 **커버리지
    공백을 '관계 종료'로 오독**한다.
    """
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    # 보고사 011070: 지분은 2025까지, 주석은 2023이 최신
    session.add(RelationLocal(source_corp="011070", target_corp="005930",
                              relation_type="investment", ratio=5.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    session.add(RelationLocal(source_corp="011070", target_corp="034220",
                              relation_type="dart_filing", detail="사업보고서 주석: 기타",
                              source_type="dart_filing", bsns_year=2023, status="active"))
    session.commit()

    shown = {(e.target_corp, e.source_type) for e in current_governance_edges(session)}
    assert ("034220", "dart_filing") in shown, "주석 계보의 최신(2023)은 지분 2025에 밀리면 안 됨"
    assert ("005930", "otrCprInvstmntSttus") in shown


def test_governance_cut_note_year_ahead_does_not_cut_equity(in_memory_session):
    """SK리츠 실측 재현 — 비12월 결산으로 주석 회계연도(2026)가 지분(2025)보다
    앞서면, 섞어 계산하면 **지분이 잘린다**. 계보별이면 둘 다 살아야 한다."""
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    session.add(RelationLocal(source_corp="395400", target_corp="000660",
                              relation_type="dart_filing", detail="사업보고서 주석: 기타",
                              source_type="dart_filing", bsns_year=2026, status="active"))
    session.add(RelationLocal(source_corp="x_skholder", target_corp="395400",
                              relation_type="subsidiary", ratio=50.0,
                              source_type="hyslrSttus", bsns_year=2025, status="active"))
    session.commit()

    shown = {(e.source_corp, e.target_corp) for e in current_governance_edges(session)}
    assert ("395400", "000660") in shown
    assert ("x_skholder", "395400") in shown, "주석 2026이 지분 2025를 컷하면 안 됨"


def test_governance_cut_exempts_dart_filing_note_edges(in_memory_session):
    """⚠️ 회귀 박제: 주석(dart_filing)은 연도 컷 **비대상**이다.

    컷의 전제("최신 공시에 없으면 종료")는 원천 커버리지가 균일할 때만 성립한다.
    주석 파서는 1,550노트 중 824노트 미파싱 + 부분 성공이 흔해 전제가 깨진다 —
    실측: 컷된 주석 엣지 1,374건 중 **746건(54%)이 최신 주석 본문에 상대가 그대로
    있는데 파싱만 놓친 것**(롯데이노베이트→롯데지주=지배기업 등). 우리 커버리지
    공백을 데이터 사실로 오독하는 구조.
    지분(API·커버리지 균일)은 컷 유지 — 두 원천을 같이 취급하면 안 된다.
    """
    from modules.relation.storage.queries import current_governance_edges

    session = in_memory_session
    # 같은 보고사: 주석은 2023이 마지막 파싱, 2025 주석도 일부 파싱됨
    session.add(RelationLocal(source_corp="286940", target_corp="004990",
                              relation_type="dart_filing", detail="사업보고서 주석: 지배기업",
                              source_type="dart_filing", bsns_year=2024, status="active"))
    session.add(RelationLocal(source_corp="286940", target_corp="005930",
                              relation_type="dart_filing", detail="사업보고서 주석: 기타",
                              source_type="dart_filing", bsns_year=2025, status="active"))
    # 지분은 2025가 최신 → 2023 지분은 잘려야 한다(대조군)
    session.add(RelationLocal(source_corp="286940", target_corp="000660",
                              relation_type="investment", ratio=6.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2025,
                              status="active"))
    session.add(RelationLocal(source_corp="286940", target_corp="035420",
                              relation_type="investment", ratio=7.0,
                              source_type="otrCprInvstmntSttus", bsns_year=2023,
                              status="active"))
    session.commit()

    shown = {(e.target_corp, e.source_type) for e in current_governance_edges(session)}
    assert ("004990", "dart_filing") in shown, "주석 구연도는 파싱 공백일 수 있어 컷 금지"
    assert ("005930", "dart_filing") in shown
    assert ("000660", "otrCprInvstmntSttus") in shown
    assert ("035420", "otrCprInvstmntSttus") not in shown, "지분 구연도는 컷 유지"


def test_normalize_strips_leftover_separators_after_annotation_removal():
    """⚠️ 회귀 박제: 각주가 콤마로 나열되면 제거 후 **구분자만 남아** 정확일치가 깨진다.

    실측 사고 — 원문 `코오롱티슈진\n(주1),(주2),(주5)`가 `코오롱티슈진,,`으로 정규화돼
    링킹에 실패하고, 코오롱티슈진이 **상장 노드와 비상장 노드로 동시에** 화면에 나왔다
    (같은 회사·같은 지분율 39.27% / 39.3%).
    """
    from modules.relation.common.names import normalize_company_name

    assert normalize_company_name("코오롱티슈진\n(주1),(주2),(주5)") == "코오롱티슈진"
    assert normalize_company_name("㈜코오롱티슈진(주1)") == "코오롱티슈진"
    # ⚠️ 내부 콤마는 사명의 일부일 수 있으므로 보존 (양끝만 제거)
    assert "," in normalize_company_name("가나, 다라 주식회사")
    # ⚠️ 원칙 ②: 일반 괄호는 신원 정보 — 유지
    assert "(" in normalize_company_name("DB(Philippines) Inc.")
