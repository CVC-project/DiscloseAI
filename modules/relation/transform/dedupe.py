"""양방향 지분 엣지 중복 제거.

같은 (source, target, relation_type) 쌍에 여러 ratio가 있을 수 있음.
A→B와 B→A 양쪽에서 같은 지분 사실이 수집되는 경우도 포함.
higher ratio 선택 + 양방향 중복 제거.

ftc_group과 K-IFRS 지분 엣지는 relation_type이 달라서 **레이어 공존 유지** (교육 목적).
"""

from __future__ import annotations

import logging
from collections import defaultdict

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal

logger = logging.getLogger(__name__)

# K-IFRS 지분 유형 (ownership 레이어, 양방향 중복 제거 대상)
_OWNERSHIP_TYPES = {"subsidiary", "associate", "investment", "ownership"}


def apply() -> dict:
    """RelationLocal의 K-IFRS 지분 엣지에 대해 양방향 중복 제거.

    규칙:
      1. ownership 계열 엣지를 (min_ticker, max_ticker) 쌍 + relation_type별로 묶음
      2. 같은 쌍에 여러 ratio → higher ratio만 유지
      3. ftc_group·dart_filing·manual 엣지는 건드리지 않음 (공존)

    Returns: {'kept': int, 'removed': int}
    """
    session = get_local_session()
    kept = 0
    removed = 0
    try:
        ownership_edges = (
            session.query(RelationLocal)
            .filter(RelationLocal.relation_type.in_(list(_OWNERSHIP_TYPES)))
            .all()
        )

        # (min_ticker, max_ticker, relation_type) → [RelationLocal, ...]
        groups: dict[tuple, list[RelationLocal]] = defaultdict(list)
        for e in ownership_edges:
            pair = tuple(sorted([e.source_corp, e.target_corp]))
            key = (pair[0], pair[1], e.relation_type)
            groups[key].append(e)

        # 각 그룹에서 higher ratio만 남기고 나머지 삭제
        for key, edges in groups.items():
            if len(edges) == 1:
                kept += 1
                continue
            # ratio 내림차순 정렬 (None은 뒤로)
            edges.sort(
                key=lambda e: (e.ratio if e.ratio is not None else -1), reverse=True
            )
            # 첫 번째 유지, 나머지 삭제
            for e in edges[1:]:
                session.delete(e)
                removed += 1
            kept += 1

        session.commit()
    finally:
        session.close()

    logger.info(f"dedupe 결과: kept {kept}쌍, removed {removed}건")
    return {"kept": kept, "removed": removed}
