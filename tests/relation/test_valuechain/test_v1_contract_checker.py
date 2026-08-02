"""하네스 V-1 계약 체커 — valuechain.json 확장분 (universe/PLAN.md §5.5).

related_party.py의 apply/export 테스트가 이미 다루는 스키마 형태·멱등 upsert·
superseded 제외에 더해, V-1이 요구하는 나머지 두 가지를 여기서 고정한다:
  - 참조 무결성: 모든 엣지의 src/dst corp_code가 CompanyRegistry에 실존
  - 멱등 export: export_json()을 연속 2회 호출해도 산출 JSON이 바이트 단위로 동일(diff 0)

세션 주입(in_memory_session)만 사용 — 실 relation.db는 건드리지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from modules.relation.storage.models import CompanyRegistry, ValueChainEdge
from modules.relation.valuechain import export
from modules.relation.valuechain.extract import related_party

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "valuechain_related_party_sample.txt"
)


def _seed_registry(session):
    session.add(
        CompanyRegistry(
            corp_code="00126380", ticker="005930", name_current="삼성전자",
            market="KOSPI", sector_id="semi",
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00164742", ticker="018260", name_current="삼성에스디에스",
            market="KOSPI", sector_id="it_service",
        )
    )
    session.commit()


def _one_section():
    return [
        {
            "rcept_no": "20250311000001",
            "title": "특수관계자와의 거래",
            "text_md": FIXTURE.read_text(encoding="utf-8"),
            "corp_code8": "00126380",
            "fiscal_year": 2024,
        }
    ]


def test_v1_referential_integrity_all_edge_endpoints_exist_in_registry(in_memory_session):
    """모든 ValueChainEdge endpoint가 **실존 노드**를 가리켜야 한다.

    ★U5 개정(2026-07-29): endpoint는 이제 두 종류다 —
      · corp_code(8자리) → CompanyRegistry에 존재해야 함
      · uid("x_" 접두) → UnlistedNode에 존재해야 함 (비상장·개인, 앵커-로컬)
    개정 전에는 "링킹 실패분은 엣지를 안 만든다"가 전제였으나, U5부터 실패분이
    비상장 노드로 살아난다. 불변식의 **의도**(dangling endpoint 금지)는 그대로 유지하고
    참조 대상만 두 테이블로 넓힌다.
    """
    from modules.relation.storage.models import UnlistedNode

    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    registry_codes = {
        c for (c,) in in_memory_session.query(CompanyRegistry.corp_code).all()
    }
    unlisted_uids = {u for (u,) in in_memory_session.query(UnlistedNode.uid).all()}
    known = registry_codes | unlisted_uids

    edges = in_memory_session.query(ValueChainEdge).all()
    assert len(edges) > 0, "테스트 전제 붕괴 — 엣지가 생성되지 않음"

    dangling = [
        (e.id, e.src_corp, e.dst_corp)
        for e in edges
        if e.src_corp not in known or e.dst_corp not in known
    ]
    assert dangling == [], f"참조 무결성 위반 — 실존하지 않는 endpoint: {dangling}"


def test_v1_unlisted_endpoints_are_anchor_scoped(in_memory_session):
    """⚠️ U5 회귀 박제: 비상장 endpoint는 uid 형태여야 하고, 그 노드의 anchor_corp는
    엣지의 상장 쪽 당사자여야 한다 — 앵커-로컬이 깨지면 전역 병합이 되살아난다."""
    from modules.relation.storage.models import UnlistedNode

    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    nodes = {u.uid: u for u in in_memory_session.query(UnlistedNode).all()}
    tickers = {
        c.corp_code: c.ticker
        for c in in_memory_session.query(CompanyRegistry).all()
    }
    for e in in_memory_session.query(ValueChainEdge).all():
        for endpoint, other in ((e.src_corp, e.dst_corp), (e.dst_corp, e.src_corp)):
            if endpoint.startswith("x_"):
                assert endpoint in nodes, f"uid인데 UnlistedNode 없음: {endpoint}"
                assert nodes[endpoint].anchor_corp == tickers.get(other), (
                    "앵커-로컬 위반 — 노드의 앵커가 상대 당사자와 불일치"
                )


def test_v1_no_duplicate_edges_on_same_natural_key(in_memory_session):
    """UNIQUE(src_corp, dst_corp, edge_type, as_of, rcept_no) 위반 없음 — DB 재실행 확인.

    _upsert_edge()가 갱신이 아니라 실수로 새 행을 추가하면 여기서 잡힌다(예:
    filter_by 키 불일치로 인한 조용한 중복 삽입).
    """
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())
    related_party.apply(session=in_memory_session, sections=_one_section())
    related_party.apply(session=in_memory_session, sections=_one_section())  # 3회 재실행

    edges = in_memory_session.query(ValueChainEdge).all()
    keys = [(e.src_corp, e.dst_corp, e.edge_type, e.as_of, e.rcept_no) for e in edges]
    assert len(keys) == len(set(keys)), f"자연키 중복 발견: {keys}"


def test_v1_export_idempotent_byte_identical(in_memory_session, tmp_path):
    """export_json()을 연속 2회 호출해도 산출 JSON이 바이트 단위로 동일해야 한다 (멱등 export, §5.5)."""
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    path1 = tmp_path / "vc_run1.json"
    path2 = tmp_path / "vc_run2.json"
    export.export_json(output_path=path1, session=in_memory_session)
    export.export_json(output_path=path2, session=in_memory_session)

    bytes1 = path1.read_bytes()
    bytes2 = path2.read_bytes()
    assert bytes1 == bytes2, "동일 DB 상태에서 export 2회 실행 결과가 바이트 단위로 다름"

    # 파서를 다시 돌려도(같은 입력 재실행) export 산출이 바뀌지 않아야 함 — 진짜 E2E 멱등
    related_party.apply(session=in_memory_session, sections=_one_section())
    path3 = tmp_path / "vc_run3.json"
    export.export_json(output_path=path3, session=in_memory_session)
    assert path3.read_bytes() == bytes1, "파서 재실행 후 export 결과가 달라짐 — E2E 멱등 위반"


def test_v1_edges_have_required_provenance_for_education_ui(in_memory_session):
    """교육 목적 근거 노출(§5 "근거 노출") — 모든 엣지가 provenance·rcept_no를 가져야 함."""
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    edges = in_memory_session.query(ValueChainEdge).all()
    assert len(edges) > 0
    for e in edges:
        assert e.provenance, f"엣지 {e.id}에 provenance 없음 — 교육용 근거 노출 불가"
        assert e.rcept_no, f"엣지 {e.id}에 rcept_no 없음 — 공시 추적 불가"
