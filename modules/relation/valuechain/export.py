"""ValueChainEdge → valuechain.json export (valuechain PLAN.md §2.3, U-D9 계약 준용).

integration이 read-only fetch할 정적 JSON. status=superseded는 제외(active만).

schema: {"as_of": <최신 스냅샷 연도>, "edges": [...], "sector_io": [...]}

★ §2.3 표기의 실측 보정: 계약 예시는 최상위 "as_of" 하나만 보이지만, ValueChainEdge는
연도별 스냅샷을 삭제 대신 보존하므로(§2.2 as_of 주석 — "연도 스냅샷, 삭제 대신 보존")
서로 다른 연도의 엣지가 동시에 active일 수 있다. 최상위 as_of만으로는 이를 표현할
수 없으므로 edge별 as_of를 추가한다(§5.5 V-1 계약 체커가 이 형태를 고정할 예정).
"""

from __future__ import annotations

import json
from pathlib import Path

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry, SectorIOEdge, ValueChainEdge

_OUTPUT_PATH = Path(__file__).parent / "data" / "valuechain.json"


def export_json(output_path: Path | None = None, session=None) -> dict:
    """relation.db → valuechain.json(dict) 생성 + 파일 기록. dict를 그대로 반환."""
    owns_session = session is None
    if owns_session:
        session = get_local_session()

    try:
        sector_map = dict(
            session.query(CompanyRegistry.corp_code, CompanyRegistry.sector_id).all()
        )
        edges = []
        max_as_of = None
        for e in session.query(ValueChainEdge).filter_by(status="active").all():
            edges.append(
                {
                    "src": e.src_corp,
                    "dst": e.dst_corp,
                    "type": e.edge_type,
                    "tier": e.tier,
                    "amount": e.amount,
                    "as_of": e.as_of,
                    "src_sector": sector_map.get(e.src_corp),
                    "prov": e.provenance,
                }
            )
            if e.as_of is not None and (max_as_of is None or e.as_of > max_as_of):
                max_as_of = e.as_of

        sector_io = [
            {"src": s.src_sector, "dst": s.dst_sector, "flow": s.flow_amount}
            for s in session.query(SectorIOEdge).all()
        ]

        payload = {
            "as_of": str(max_as_of) if max_as_of is not None else None,
            "edges": edges,
            "sector_io": sector_io,
        }
    finally:
        if owns_session:
            session.close()

    path = output_path or _OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = export_json()
    print(f"valuechain.json 생성: {len(result['edges'])}건 엣지 (as_of={result['as_of']})")
