"""Phase 2e — graph/build + export 단위 테스트."""

from __future__ import annotations

import pytest

# networkx는 graph 빌드용 — 미설치 환경에서는 collection skip.
pytest.importorskip("networkx")

import json

from modules.relation.graph import build, export
from modules.relation.storage.models import CompanyNode, RelationLocal


def _seed_minimal(session):
    """5개 노드 + ftc_group 엣지 + ownership 엣지 시드."""
    nodes = [
        ("00126380", "삼성전자", "005930", 12627962, "반도체", "삼성"),
        ("00149655", "삼성물산", "028260", 488939, "건설", "삼성"),
        ("00877059", "삼성바이오로직스", "207940", 741118, "바이오", "삼성"),
        ("00126362", "삼성SDI", "006400", 413404, "2차전지", "삼성"),
        ("00164779", "SK하이닉스", "000660", 8039283, "반도체", "SK"),
    ]
    for corp_code, name, ticker, cap, sector, group in nodes:
        session.add(
            CompanyNode(
                corp_code=corp_code,
                corp_name=name,
                ticker=ticker,
                market_cap=cap,
                sector=sector,
                group_name=group,
                is_target=True,
            )
        )
    # 삼성 내 ftc_group 완전연결 C(4,2)=6
    samsung_tickers = ["005930", "028260", "207940", "006400"]
    for i, a in enumerate(samsung_tickers):
        for b in samsung_tickers[i + 1 :]:
            session.add(
                RelationLocal(
                    source_corp=a,
                    target_corp=b,
                    relation_type="ftc_group",
                    source_type="ftc",
                    group_name="삼성",
                    bsns_year=2025,
                )
            )
    # K-IFRS 지분: 삼성전자 → 삼성바이오로직스 31%, 삼성전자 → 삼성SDI 19.6%
    session.add(
        RelationLocal(
            source_corp="005930",
            target_corp="207940",
            relation_type="associate",
            ratio=31.2,
            detail="31.2%",
            source_type="otrCprInvstmntSttus",
            bsns_year=2024,
        )
    )
    session.add(
        RelationLocal(
            source_corp="005930",
            target_corp="006400",
            relation_type="investment",
            ratio=19.6,
            detail="19.6%",
            source_type="otrCprInvstmntSttus",
            bsns_year=2024,
        )
    )
    session.commit()


def test_build_graph_produces_multidigraph(in_memory_session, monkeypatch):
    monkeypatch.setattr(
        "modules.relation.graph.build.get_local_session",
        lambda: in_memory_session,
    )
    _seed_minimal(in_memory_session)
    G = build.build_graph()
    assert G.number_of_nodes() == 5
    # 6 ftc + 2 ownership = 8
    assert G.number_of_edges() == 8
    # MultiDiGraph — 같은 쌍에 relation_type 다른 엣지 공존
    edge_types_005930_207940 = {
        data["relation_type"] for _, _, data in G.out_edges("005930", data=True)
    }
    assert "ftc_group" in edge_types_005930_207940
    assert "associate" in edge_types_005930_207940


def test_export_json_schema(in_memory_session, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "modules.relation.graph.build.get_local_session",
        lambda: in_memory_session,
    )
    _seed_minimal(in_memory_session)

    out_path = tmp_path / "graph_test.json"
    export.export_json(out_path)

    data = json.loads(out_path.read_text("utf-8"))
    # 스키마 검증
    assert len(data) == 5
    for n in data:
        assert "n" in n and "t" in n and "s" in n and "rl" in n
        assert len(n["t"]) == 6
        assert isinstance(n["rl"], list)
        for r in n["rl"]:
            parts = r.split(":", 2)
            assert len(parts) == 3, f"rl 3-split 실패: {r}"

    # 삼성전자 노드 rl 확인
    sam = next(n for n in data if n["t"] == "005930")
    rl_types = set()
    for r in sam["rl"]:
        _, rt, _ = r.split(":", 2)
        rl_types.add(rt)
    # 삼성전자에서 나가는 엣지: ftc_group × 3 + associate 1 + investment 1
    assert "ftc_group" in rl_types
    assert "associate" in rl_types
    assert "investment" in rl_types


def test_build_graph_dedupes_multi_year_same_pair(in_memory_session, monkeypatch):
    """같은 (source_corp, target_corp, source_type)의 여러 연도 행은 최신 연도 1건만
    엣지로 반영해야 한다 (U1 5개년 백필 이후 발견된 회귀, 2026-07-22)."""
    monkeypatch.setattr(
        "modules.relation.graph.build.get_local_session",
        lambda: in_memory_session,
    )
    session = in_memory_session
    session.add(
        CompanyNode(
            corp_code="00126380", corp_name="삼성전자", ticker="005930",
            market_cap=12627962, sector="반도체", group_name="삼성", is_target=True,
        )
    )
    session.add(
        CompanyNode(
            corp_code="00877059", corp_name="삼성바이오로직스", ticker="207940",
            market_cap=741118, sector="바이오", group_name="삼성", is_target=True,
        )
    )
    for year, ratio in [(2021, 31.0), (2022, 31.1), (2023, 31.2), (2024, 31.22)]:
        session.add(
            RelationLocal(
                source_corp="005930",
                target_corp="207940",
                relation_type="associate",
                ratio=ratio,
                detail=f"{ratio}%",
                source_type="otrCprInvstmntSttus",
                bsns_year=year,
            )
        )
    session.commit()

    G = build.build_graph()
    edges = list(G.out_edges("005930", data=True))
    assert len(edges) == 1, f"연도별 중복이 dedupe 안 됨: {edges}"
    assert edges[0][2]["bsns_year"] == 2024
    assert edges[0][2]["ratio"] == 31.22
