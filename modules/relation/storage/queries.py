"""RelationLocal 공용 조회 헬퍼 — 쿼리 1벌, 소비자 여러 곳(U-D2 원칙 준용).

U1 5개년 백필(2021~2024) 이후 같은 (source_corp, target_corp, source_type) 쌍이
bsns_year별로 별개 행으로 존재하는 게 정상(UNIQUE 키, U-D13) — 스냅샷 산출물
(graph_top50.json / universe.json / ego/<ticker>.json)은 최신 연도 1건만 반영해야
같은 관계가 연도 수만큼 중복 표기되지 않는다(2026-07-22 발견 회귀).
"""

from __future__ import annotations

from modules.relation.storage.models import RelationLocal


def latest_relation_local_edges(session, status: str = "active") -> list[RelationLocal]:
    """(source_corp, target_corp, source_type)별 최신 bsns_year 행만 반환.

    다른 source_type(예: hyslrSttus vs ftc)이 같은 쌍에 공존하는 것은 레이어
    공존 원칙(storage/CLAUDE.md)대로 그대로 유지 — dedupe하는 것은 "완전히 같은
    (pair, source_type)의 연도별 중복"뿐.
    """
    latest_by_key: dict[tuple[str, str, str | None], RelationLocal] = {}
    query = session.query(RelationLocal)
    if status is not None:
        query = query.filter(RelationLocal.status == status)
    for e in query.all():
        key = (e.source_corp, e.target_corp, e.source_type)
        current = latest_by_key.get(key)
        if current is None or (e.bsns_year or 0) > (current.bsns_year or 0):
            latest_by_key[key] = e
    return list(latest_by_key.values())
