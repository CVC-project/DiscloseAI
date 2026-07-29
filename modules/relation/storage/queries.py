"""RelationLocal 공용 조회 헬퍼 — 쿼리 1벌, 소비자 여러 곳(U-D2 원칙 준용).

U1 5개년 백필(2021~2024) 이후 같은 (source_corp, target_corp, source_type) 쌍이
bsns_year별로 별개 행으로 존재하는 게 정상(UNIQUE 키, U-D13) — 스냅샷 산출물
(graph_top50.json / universe.json / ego/<ticker>.json)은 최신 연도 1건만 반영해야
같은 관계가 연도 수만큼 중복 표기되지 않는다(2026-07-22 발견 회귀).
"""

from __future__ import annotations

from modules.relation.storage.models import RelationLocal


# ★2026-07-29 수정(전수 불변식 검사에서 발견): 지분 2원천은 **같은 사실의 두 기록**이다.
# hyslrSttus(상대의 최대주주 현황에서 본 것)와 otrCprInvstmntSttus(자사의 타법인출자에서
# 본 것)는 같은 지분 관계를 양쪽에서 적은 것이라, source_type을 키에 그대로 두면 둘 다
# 살아남는다. 실제 사고: 유한양행→이뮨온시아가 **76.9%(otrCpr 2024)와 65.93%(hyslr 2025)로
# 한 화면에 동시 표기**됐다(366건). 연도가 다른데 화면엔 연도가 없어 사용자가 구분할 방법이
# 없다 — 같은 관계에 두 숫자를 보여주는 건 교육 서비스의 신뢰를 직접 깎는다.
#
# docstring이 말하던 "레이어 공존"은 **ftc(계열) vs 지분 vs dart_filing(주석)** 사이의
# 이야기지 지분 원천 2종 사이가 아니다. 그래서 지분 계보만 하나로 접는다.
# 채택 규칙: 최신 연도 우선 → 같은 연도면 higher ratio(transform/dedupe.py의 양방향
# 중복 관례와 동일).
_EQUITY_SOURCE_TYPES = {"hyslrSttus", "otrCprInvstmntSttus"}


def _lineage(source_type: str | None) -> str:
    """dedupe 계보 — 지분 2원천은 한 계보로 접고, 나머지는 source_type 그대로."""
    return "equity" if source_type in _EQUITY_SOURCE_TYPES else (source_type or "")


def latest_relation_local_edges(session, status: str = "active") -> list[RelationLocal]:
    """(source_corp, target_corp, 계보)별 대표 1건만 반환.

    계보 = 지분(hyslrSttus+otrCprInvstmntSttus 통합) / ftc / dart_filing / manual.
    레이어 공존 원칙(storage/CLAUDE.md)은 **계보 사이**에서 유지된다 — 같은 쌍에
    ftc_group과 지분 엣지가 함께 남는 것은 의도된 동작.
    """
    # ★2026-07-29: status 필터를 **먼저 걸면 안 된다**. 최신 연도 행이 terminated
    # (지분 처분)일 때 그 행이 빠지면 직전 연도 행이 "최신"이 되어 **끝난 관계가
    # 현재 관계로 부활**한다(적대적 검증에서 실측 1,985건). 그래서 전 status를 놓고
    # 쌍별 최신을 먼저 정한 뒤, 그 대표가 terminated면 그 쌍을 통째로 뺀다.
    latest_by_key: dict[tuple[str, str, str], RelationLocal] = {}
    for e in session.query(RelationLocal).all():
        key = (e.source_corp, e.target_corp, _lineage(e.source_type))
        current = latest_by_key.get(key)
        if current is None:
            latest_by_key[key] = e
            continue
        cy, ey = (current.bsns_year or 0), (e.bsns_year or 0)
        if ey > cy or (ey == cy and (e.ratio or 0) > (current.ratio or 0)):
            latest_by_key[key] = e
    if status is None:
        return list(latest_by_key.values())
    # 쌍의 **최신 상태**가 요청 status가 아니면 그 쌍은 화면에 없다(처분·정정 반영)
    return [e for e in latest_by_key.values() if e.status == status]
