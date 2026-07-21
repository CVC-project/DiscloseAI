"""양방향 지분 엣지 중복 제거.

같은 (source, target, relation_type, bsns_year) 쌍에 여러 ratio가 있을 수 있음.
A→B와 B→A 양쪽에서 같은 지분 사실이 수집되는 경우도 포함.
higher ratio 선택 + 양방향 중복 제거.

ftc_group과 K-IFRS 지분 엣지는 relation_type이 달라서 **레이어 공존 유지** (교육 목적).

★U1 실측 버그 수정(2026-07-21): 그룹핑 키에 bsns_year가 빠져 있어 top50 단일연도
MVP 때는 잠복돼 있다가, 전 상장사 5개년 백필 도입 후 "같은 쌍의 서로 다른 연도
기록"까지 양방향 중복으로 오인해 무너뜨렸다(재현: 5개년 처리 시 최종 엣지가 1,088→
1,353으로 겨우 24%만 증가 — kifrs 분류 4,766건 중 71.6%가 dedupe에서 사라짐, 대부분
"같은 연도 아닌데 같은 쌍"이었음). RelationLocal의 UNIQUE 키도 bsns_year를 포함하므로
(U-D13) 이 함수의 그룹핑도 동일 키를 따라야 연도 스냅샷이 보존된다.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal

logger = logging.getLogger(__name__)

# K-IFRS 지분 유형 (ownership 레이어, 양방향 중복 제거 대상)
_OWNERSHIP_TYPES = {"subsidiary", "associate", "investment", "ownership"}


def apply(session=None) -> dict:
    """RelationLocal의 K-IFRS 지분 엣지에 대해 양방향 중복 제거.

    규칙:
      1. ownership 계열 엣지를 (min_ticker, max_ticker) 쌍 + relation_type + bsns_year별로 묶음
         (★연도까지 키에 포함 — 다른 연도는 별개 스냅샷, 중복 아님)
      2. 같은 쌍·같은 연도에 여러 ratio → higher ratio만 유지 (진짜 양방향 중복만)
      3. ftc_group·dart_filing·manual 엣지는 건드리지 않음 (공존)

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음). None이면 로컬 relation.db.

    Returns: {'kept': int, 'removed': int}
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()
    kept = 0
    removed = 0
    try:
        ownership_edges = (
            session.query(RelationLocal)
            .filter(RelationLocal.relation_type.in_(list(_OWNERSHIP_TYPES)))
            .all()
        )

        # (min_ticker, max_ticker, relation_type, bsns_year) → [RelationLocal, ...]
        groups: dict[tuple, list[RelationLocal]] = defaultdict(list)
        for e in ownership_edges:
            pair = tuple(sorted([e.source_corp, e.target_corp]))
            key = (pair[0], pair[1], e.relation_type, e.bsns_year)
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
        if owns_session:
            session.close()

    logger.info(f"dedupe 결과: kept {kept}쌍, removed {removed}건")
    return {"kept": kept, "removed": removed}
