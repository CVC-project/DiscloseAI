"""SQLite → NetworkX MultiDiGraph 구축.

MultiDiGraph 선택: 같은 (source, target) 쌍에 relation_type이 다른 엣지가 공존해야 함.
(예: ftc_group + subsidiary 둘 다 존재 가능)

상세 스키마는 modules/relation/graph/CLAUDE.md 참조.
"""

from __future__ import annotations


def build_graph():
    """CompanyNode + RelationLocal 조회 → nx.MultiDiGraph 반환.

    노드 속성: n(name), t(ticker), s(sector), sz(size), mc(market_cap), group
    엣지 속성: relation_type, ratio, detail, source_type, bsns_year
    """
    raise NotImplementedError("Phase 2e에서 구현")
