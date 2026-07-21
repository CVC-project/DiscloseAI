"""universe/export.py — 연도별 rl 중복 회귀 테스트 (2026-07-22).

graph/build.py와 같은 근본 원인(RelationLocal이 (pair, source_type)당 여러
bsns_year 행을 갖는 게 정상, U-D13)을 storage/queries.py의 공용 헬퍼로
공유하는지 검증. 세션 주입(in_memory_session)으로 격리.
"""

from __future__ import annotations

from modules.relation.storage.models import CompanyRegistry, RelationLocal
from modules.relation.universe import export


def _seed(session):
    session.add(
        CompanyRegistry(
            corp_code="00267250", ticker="267250", name_current="HD현대",
            market="KOSPI", sector_id="indust", universe_tier="named400",
            universe_rank=1, market_cap_krw=1_000_000_000_000,
        )
    )
    session.add(
        CompanyRegistry(
            corp_code="00009540", ticker="009540", name_current="HD한국조선해양",
            market="KOSPI", sector_id="indust", universe_tier="named400",
            universe_rank=2, market_cap_krw=1_000_000_000_000,
        )
    )
    for year, ratio in [(2022, 37.22), (2023, 37.20), (2024, 37.18)]:
        session.add(
            RelationLocal(
                source_corp="267250", target_corp="009540", relation_type="associate",
                ratio=ratio, detail=f"{ratio}%", source_type="otrCprInvstmntSttus",
                bsns_year=year,
            )
        )
    session.commit()


def test_export_universe_json_dedupes_multi_year_named_rl(in_memory_session, tmp_path):
    _seed(in_memory_session)
    payload = export.export_universe_json(
        in_memory_session, output_path=tmp_path / "universe.json"
    )
    hd = next(n for n in payload["named"] if n["t"] == "267250")
    assert hd["rl"] == ["HD한국조선해양:associate:37.18%"]


def test_export_ego_files_dedupes_multi_year_governance(in_memory_session, tmp_path):
    _seed(in_memory_session)
    result = export.export_ego_files(in_memory_session, output_dir=tmp_path)
    assert result["written"] == 2
    import json

    ego = json.loads((tmp_path / "267250.json").read_text("utf-8"))
    gov = ego["layers"]["governance"]
    assert len(gov) == 1
    assert gov[0]["detail"] == "37.18%"
