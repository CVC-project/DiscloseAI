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


# ★2026-07-30 D13 신선도를 **지배구조로 확장** (리더 지적: "관계·밸류체인은 최근 기준 /
# 지배구조는 2025 기준"). 후속 8의 D13 채록·구현이 **밸류체인 원천 3종에서 끝나** 있었고
# (valuechain/freshness.py는 valuechain export 2곳에만 걸림) 지배구조에는 절대 연도 컷이
# 없었다 — `latest_relation_local_edges`는 **쌍별 최신**만 고르므로, 그 쌍을 마지막으로
# 공시한 해가 2020이면 2020 행이 그대로 "현재 관계"로 렌더됐다.
#   실측(2026-07-30): 화면 지배구조 대표엣지 36,321건 중 2023년 이하 4,320건(11.9%).
#   예) 넥스틴→Nextin Solutions LTD. 100%가 **2020년 공시 기준**으로 노출
#       (넥스틴의 최신 타법인출자 명세는 2025인데 그 법인이 더는 안 올라온다 = 처분·청산).
#
# 규칙 = **보고사별 최신 연도**(전역 연도 컷이 아니다). D13이 rp_note에 쓴 사상과 동일 —
# "2025 미제출사 불이익 없음". 실측상 상장 앵커 2,609사 중 2,605사가 최신 2025라
# 하드 2025 컷과 결과가 99.8% 같으면서, 아직 2025 공시가 없는 4개사의 지배구조 레이어가
# 통째로 비는 부작용만 피한다(리더 승인).
#
# **보고사(공시 주체)가 원천마다 다르다** — 여기가 틀리기 쉬운 지점:
#   · otrCprInvstmntSttus(타법인출자 명세) → **출자사 = source_corp**
#   · hyslrSttus(최대주주 현황)           → **피출자사 = target_corp** (자기 주주를 공시)
#   · dart_filing(사업보고서 주석)         → **보고사 = source_corp** (apply_governance가 그렇게 적재)
#   · ftc(공정위 지정)                    → 보고사가 기업이 아님(공정위 발표) → **컷 제외**
_REPORTER_IS_TARGET = {"hyslrSttus"}
_NO_REPORTER_CUT = {"ftc", "manual"}


def _reporter_of(e: RelationLocal) -> str | None:
    if e.source_type in _NO_REPORTER_CUT:
        return None
    corp = e.target_corp if e.source_type in _REPORTER_IS_TARGET else e.source_corp
    return None if (corp or "").startswith("x_") else corp   # 비상장은 보고 주체가 아님


def current_governance_edges(session, status: str = "active") -> list[RelationLocal]:
    """화면용 지배구조 엣지 — 쌍별 최신(위) + **보고사별 최신 연도** 컷.

    보고사가 그 해 공시에서 더 언급하지 않은 상대는 관계가 끝난 것으로 본다
    (처분·청산·특수관계 해소). 저장은 전 연도 보존(D7) — 컷은 **조회/export 단계만**.
    """
    edges = latest_relation_local_edges(session, status=status)

    # 보고사별 최신 연도는 **전 status·전 연도**를 놓고 구한다 — active만 보면 그 보고사가
    # 올해 공시를 했는데 전량 terminated인 경우 최신 연도가 과거로 내려가 컷이 무력해진다.
    reporter_latest: dict[str, int] = {}
    for e in session.query(RelationLocal).all():
        r = _reporter_of(e)
        if r is None:
            continue
        y = e.bsns_year or 0
        if y > reporter_latest.get(r, 0):
            reporter_latest[r] = y

    out = []
    for e in edges:
        r = _reporter_of(e)
        if r is None:
            out.append(e)                      # ftc·manual — 연도 컷 비대상
            continue
        if (e.bsns_year or 0) >= reporter_latest.get(r, 0):
            out.append(e)
    return out
