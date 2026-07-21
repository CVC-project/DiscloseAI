"""related_party.apply() 엔티티 링킹·멱등 upsert + export.export_json() 계약 테스트.

세션 주입(in_memory_session)으로 격리 — 실제 relation.db·reports.db는 건드리지 않는다
(test_idempotency.py와 동일 원칙, storage/CLAUDE.md·monkeypatch 사고 교훈 반영).
"""

from __future__ import annotations

import json
from pathlib import Path

from modules.relation.storage.models import (
    CompanyRegistry,
    LinkFailQueue,
    ValueChainEdge,
)
from modules.relation.valuechain import export
from modules.relation.valuechain.extract import related_party

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "valuechain_related_party_sample.txt"
)


def _seed_registry(session):
    session.add(
        CompanyRegistry(
            corp_code="00126380",
            ticker="005930",
            name_current="삼성전자",
            market="KOSPI",
            sector_id="semi",
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00164742",
            ticker="018260",
            name_current="삼성에스디에스",
            market="KOSPI",
            sector_id="it_service",
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00126186",
            ticker="006400",
            name_current="삼성SDI",
            market="KOSPI",
            sector_id="battery",
        )
    )
    session.commit()


def _one_section():
    return [
        {
            "rcept_no": "20250311000001",
            "title": "특수관계자와의 거래",
            "text_md": FIXTURE.read_text(encoding="utf-8"),
            "corp_code8": "00126380",  # 삼성전자 자신
            "fiscal_year": 2024,
        }
    ]


def test_apply_creates_edges_for_linked_counterparties(in_memory_session):
    _seed_registry(in_memory_session)
    result = related_party.apply(session=in_memory_session, sections=_one_section())

    assert result["notes_scanned"] == 1
    assert result["edges_kept"] > 0

    # 매출 등 → 삼성에스디에스가 고객(customer): src=삼성전자, dst=삼성에스디에스
    customer_edge = (
        in_memory_session.query(ValueChainEdge)
        .filter_by(src_corp="00126380", dst_corp="00164742", edge_type="customer")
        .one_or_none()
    )
    assert customer_edge is not None
    assert customer_edge.amount == 110_512 * 1_000_000
    assert customer_edge.tier == "T1"
    assert customer_edge.as_of == 2024

    # 매입 등 → 삼성에스디에스가 공급자(supply): src=삼성에스디에스, dst=삼성전자
    supply_edge = (
        in_memory_session.query(ValueChainEdge)
        .filter_by(src_corp="00164742", dst_corp="00126380", edge_type="supply")
        .one_or_none()
    )
    assert supply_edge is not None
    assert supply_edge.amount == 2_218_940 * 1_000_000


def test_apply_pushes_unmatched_counterparty_to_link_fail_queue(in_memory_session):
    """레지스트리에 없는 상대(삼성전기 등)는 LinkFailQueue에 쌓이고 엣지는 생성 안 됨."""
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    fail = (
        in_memory_session.query(LinkFailQueue)
        .filter_by(surface_form="삼성전기㈜")
        .one_or_none()
    )
    assert fail is not None
    assert fail.freq >= 1

    edge = (
        in_memory_session.query(ValueChainEdge)
        .filter(
            (ValueChainEdge.src_corp == "삼성전기")
            | (ValueChainEdge.dst_corp == "삼성전기")
        )
        .one_or_none()
    )
    assert edge is None


def test_apply_idempotent_on_rerun(in_memory_session):
    """동일 입력 재실행 → ValueChainEdge 행 수·내용 불변 (M4/D12 준용)."""
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())
    rows1 = sorted(
        (e.src_corp, e.dst_corp, e.edge_type, e.amount, e.as_of)
        for e in in_memory_session.query(ValueChainEdge).all()
    )

    related_party.apply(session=in_memory_session, sections=_one_section())
    rows2 = sorted(
        (e.src_corp, e.dst_corp, e.edge_type, e.amount, e.as_of)
        for e in in_memory_session.query(ValueChainEdge).all()
    )

    assert len(rows1) == len(rows2)
    assert rows1 == rows2


def test_export_json_contract_shape(in_memory_session, tmp_path):
    """export.export_json()가 §2.3 계약(edges[].src/dst/type/tier/amount/as_of) 충족."""
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    out_path = tmp_path / "valuechain.json"
    payload = export.export_json(output_path=out_path, session=in_memory_session)

    assert out_path.exists()
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk == payload

    assert payload["as_of"] == "2024"
    assert len(payload["edges"]) > 0
    for edge in payload["edges"]:
        assert set(edge.keys()) == {
            "src",
            "dst",
            "type",
            "tier",
            "amount",
            "as_of",
            "src_sector",
            "prov",
        }
        assert edge["tier"] == "T1"

    # src_sector가 CompanyRegistry.sector_id에서 채워졌는지 (삼성전자 src인 엣지)
    samsung_src_edges = [e for e in payload["edges"] if e["src"] == "00126380"]
    assert all(e["src_sector"] == "semi" for e in samsung_src_edges)


def test_export_json_excludes_superseded_edges(in_memory_session, tmp_path):
    _seed_registry(in_memory_session)
    related_party.apply(session=in_memory_session, sections=_one_section())

    edge = in_memory_session.query(ValueChainEdge).first()
    edge.status = "superseded"
    in_memory_session.commit()

    payload = export.export_json(output_path=tmp_path / "vc.json", session=in_memory_session)
    kept_ids = {(e["src"], e["dst"], e["type"], e["as_of"]) for e in payload["edges"]}
    assert (edge.src_corp, edge.dst_corp, edge.edge_type, edge.as_of) not in kept_ids
