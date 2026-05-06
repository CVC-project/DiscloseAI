"""SQLite → NetworkX MultiDiGraph 구축.

MultiDiGraph 선택 이유: 같은 (source, target) 쌍에 relation_type이 다른 엣지가
공존해야 함 (예: ftc_group + subsidiary).

상세 스키마는 modules/relation/graph/CLAUDE.md 참조.
"""

from __future__ import annotations

import logging
import math

import networkx as nx

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyNode, RelationLocal

logger = logging.getLogger(__name__)


def _scale_size(market_cap_eok: float) -> float:
    """시가총액(억원) → 프로토타입 호환 sz (0.5 ~ 3.5).

    제곱근 스케일 사용: 삼성전자 12.6M억 → ~3.5, 한국항공우주 0.18M억 → ~0.9.
    """
    if market_cap_eok <= 0:
        return 0.5
    sz = math.sqrt(market_cap_eok / 100000) * 0.3 + 0.5
    return max(0.5, min(3.5, sz))


def build_graph() -> nx.MultiDiGraph:
    """CompanyNode + RelationLocal → nx.MultiDiGraph.

    노드 속성:
      id = ticker (노드 id, 프로토타입 호환 't')
      n = corp_name (프로토타입 호환)
      t = ticker
      s = sector (sectors 키)
      sz = market_cap / 10000 (조 단위 표시 크기)
      mc = "{시총/10000}조"
      group = group_name
      is_target = True

    엣지 속성 (MultiDiGraph, key=relation_type으로 멀티엣지 구분):
      relation_type
      ratio (nullable)
      detail
      source_type
      bsns_year
    """
    G = nx.MultiDiGraph()
    session = get_local_session()
    try:
        # 노드 추가
        for node in session.query(CompanyNode).all():
            cap = node.market_cap or 0
            sz = _scale_size(cap)
            # mc 표시 문자열 — 시가총액 억원 → 조원
            mc_trillion = cap / 10000
            if mc_trillion >= 100:
                mc = f"{int(mc_trillion)}조"
            elif mc_trillion >= 10:
                mc = f"{mc_trillion:.0f}조"
            else:
                mc = f"{mc_trillion:.1f}조"
            G.add_node(
                node.ticker,
                n=node.corp_name,
                t=node.ticker,
                s=node.sector or "기타",
                sz=sz,
                mc=mc,
                group=node.group_name,
                is_target=bool(node.is_target),
            )

        # 엣지 추가 — MultiDiGraph에서 key=relation_type으로 멀티엣지
        for e in session.query(RelationLocal).all():
            if e.source_corp not in G or e.target_corp not in G:
                continue  # 노드 없으면 스킵 (안전장치)
            G.add_edge(
                e.source_corp,
                e.target_corp,
                key=f"{e.relation_type}_{e.id}",  # 같은 (s,t,rt) 여러 개일 수 있으니 id 포함
                relation_type=e.relation_type,
                ratio=e.ratio,
                detail=e.detail,
                source_type=e.source_type,
                bsns_year=e.bsns_year,
            )
    finally:
        session.close()

    logger.info(
        f"MultiDiGraph 구축: 노드 {G.number_of_nodes()}, 엣지 {G.number_of_edges()}"
    )
    return G
