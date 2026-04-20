"""K-IFRS 1024호 기반 지분율 자동 분류.

임계값은 법정 기준 — 확정 상수로 정의. 변경 금지 (K-IFRS 개정 시에만 수정).
상세는 modules/relation/transform/CLAUDE.md 참조.
"""

from __future__ import annotations

import logging

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal

logger = logging.getLogger(__name__)

# K-IFRS 1024호 임계값 (% 단위)
SUBSIDIARY_THRESHOLD = 50.0  # > 50% → 지배기업-종속기업 (control)
ASSOCIATE_THRESHOLD = 20.0  # 20~50% → 관계기업 (significant influence)
INVESTMENT_THRESHOLD = 5.0  # 5~20% → 유의적 투자 (공시 의무)
# < 5% → 엣지 제외


def classify_ownership(ratio: float | None) -> str | None:
    """지분율(%) → 관계 유형.

    Returns:
        'subsidiary' (>50%) / 'associate' (20~50%) / 'investment' (5~20%) / None (<5%)

    경계값 규칙:
        - 50.01 → subsidiary / 50.0 → associate (> 50% 이면 지배)
        - 20.0 → associate (≥ 20% 이면 관계)
        - 5.0 → investment (≥ 5% 이면 유의적 투자)
        - 4.99 → None (엣지 제외)
        - None → None
    """
    if ratio is None:
        return None
    if ratio > SUBSIDIARY_THRESHOLD:
        return "subsidiary"
    if ratio >= ASSOCIATE_THRESHOLD:
        return "associate"
    if ratio >= INVESTMENT_THRESHOLD:
        return "investment"
    return None


def apply() -> dict:
    """RelationLocal의 지분 엣지(source_type=hyslrSttus/otrCprInvstmntSttus)에 대해
    ratio로 relation_type 재분류.

    ftc_group·dart_filing·manual 엣지는 건드리지 않음.
    <5% 지분은 엣지 자체를 삭제.

    Returns: {'classified': int, 'dropped_below_5pct': int}
    """
    session = get_local_session()
    classified = 0
    dropped = 0
    try:
        rows = (
            session.query(RelationLocal)
            .filter(
                RelationLocal.source_type.in_(["hyslrSttus", "otrCprInvstmntSttus"])
            )
            .all()
        )
        for r in rows:
            rtype = classify_ownership(r.ratio)
            if rtype is None:
                session.delete(r)
                dropped += 1
            else:
                r.relation_type = rtype
                classified += 1
        session.commit()
    finally:
        session.close()
    logger.info(f"K-IFRS 분류: {classified}개 (dropped<5%: {dropped}개)")
    return {"classified": classified, "dropped_below_5pct": dropped}
