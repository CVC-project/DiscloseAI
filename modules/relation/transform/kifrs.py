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


def apply(session=None) -> dict:
    """RelationLocal의 지분 엣지(source_type=hyslrSttus/otrCprInvstmntSttus)에 대해
    ratio로 relation_type 재분류.

    ftc_group·dart_filing·manual 엣지는 건드리지 않음.

    ★2026-07-29 수정(적대적 검증에서 발견): <5% 지분을 **삭제**하면 "지분을 처분했다"는
    사실 자체가 사라진다. 그러면 최신 연도 행이 없어져 D13 신선도 규칙이 **처분 직전
    연도**를 최신으로 골라 **끝난 관계를 현재 관계로 부활**시킨다.
      실측: SK→에스케이머티리얼즈그룹포틴 화면 75% 종속 / 2025 공시 0.0%
            윤성에프앤씨→프라이믹스윤성 화면 45% 관계기업 / 2025 공시 0.0%
      규모: 화면 지분엣지의 31.2%(10,383건)가 앵커 최신 공시연도보다 오래됐고,
            그중 1,985건은 더 최신 공시가 <5%(사실상 처분)를 명시했다.
    → 삭제 대신 **status='terminated'로 기록**한다(D7 "저장은 전 연도 보존" 원칙과도
      부합). 화면 제외는 queries.latest_relation_local_edges가 담당한다.

    session: 주입 시 그 세션 사용(테스트용 — 닫지 않음). None이면 로컬 relation.db.

    Returns: {'classified': int, 'dropped_below_5pct': int}
    """
    owns_session = session is None
    if owns_session:
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
                # 삭제가 아니라 "관계 종료" 기록 — 위 docstring 참조
                r.status = "terminated"
                dropped += 1
            else:
                r.relation_type = rtype
                classified += 1
        session.commit()
    finally:
        if owns_session:
            session.close()
    logger.info(f"K-IFRS 분류: {classified}개 (dropped<5%: {dropped}개)")
    return {"classified": classified, "dropped_below_5pct": dropped}
