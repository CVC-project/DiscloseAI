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

# ★2026-07-30 표본 대조 결과 dart_filing을 컷 대상에서 **제외**한다.
#
# 왜: 연도 컷의 전제는 "최신 공시에 없으면 관계가 끝났다"인데, 이 전제는 **원천의
# 커버리지가 균일할 때만** 성립한다.
#   · 지분(hyslr·otrCpr) = DART 정형 API. 전 상장사·전 연도를 에러 0으로 수집했고
#     명세에서 빠지면 실제로 처분·해소다 → 전제 성립, 컷 유효.
#   · dart_filing(사업보고서 주석) = **파서 커버리지가 불균일**하다. 1,550노트 중
#     824노트가 미파싱이고, 파싱된 노트도 부분 성공이 흔하다. 그래서 "최신 연도에
#     없음"이 종료 근거가 되지 못한다.
# 실측(2026-07-30 표본 대조): 컷된 주석 엣지 1,374건 중 **746건(54%)이 최신 주석
# 본문에 상대가 그대로 있는데 파싱만 놓친 것**이었다 — 롯데이노베이트→롯데지주
# (지배기업!)·경동도시가스→경동나비엔·엘에스일렉트릭→E1 등 현재 관계 다수.
# **우리 커버리지 공백을 데이터 사실로 오독**하는 구조 — dart_filing 소실 사고(prune
# 소유권)·처분 부활과 같은 계열의 실수다.
#
# 프로젝트 원칙과의 정합: 후속14 오류1은 처분을 **명시적 근거**(최신 공시의 0%)로
# `status='terminated'` 기록해 처리했다 — **부재는 종료의 근거가 아니다**가 이미
# 확립된 선례다. 주석에 그 선례를 지키면 부재만으로 지울 수 없다.
# 대신 이제 detail에 연도가 찍히므로(UX-025) 낡은 근거는 `· 2023`으로 드러난다.
#
# 후속 과제: 주석 종료 판정은 **최신 주석 본문 확인**으로 해야 정확하다(부재 420건은
# 실제 종료). `apply_governance`가 노트 본문을 이미 들고 있으므로 생산자 단계에서
# `status='terminated'`를 기록하는 것이 옳은 위치 — 후속15의 prune 조문과 같은 사상.
_NO_REPORTER_CUT = {"ftc", "manual", "dart_filing"}


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

    # ★2026-07-30 표본 대조에서 수정 — 최신 연도는 **(보고사, 계보)별**로 구한다.
    # 1차 구현은 보고사별로만 구해 **원천을 섞었고**, 그 결과 자기 원천 기준으로는
    # 최신인 엣지가 다른 원천이 더 최신이라는 이유로 잘렸다(실측 376건):
    #   · LG이노텍 — 주석 최신 2023인데 지분이 2025 → 주석 2023 엣지 전량 컷
    #   · 에스디바이오센서 — 주석 2024(→바이오노트)가 지분 2025에 밀려 컷
    #   · SK리츠 — 주석 2026(비12월 결산)이 지분 2025보다 최신 → **지분 2025가** 컷
    # 원천마다 커버리지가 다르다(주석은 파서가 못 읽은 연도가 있고, 결산월이 다르면
    # 회계연도 자체가 어긋난다) — 한 원천의 최신 연도를 다른 원천의 기준으로 쓰면
    # **파서 커버리지 공백을 "관계 종료"로 오독**한다. D13 원문도 "보고사별 최신
    # **주석** 연도"로 원천을 명시하고 있다(계보별이 곧 조문 그대로의 해석).
    # 지분 2원천(hyslr·otrCpr)은 같은 사업보고서의 두 표이므로 한 계보로 묶는다.
    #
    # 최신 연도는 **전 status·전 연도**를 놓고 구한다 — active만 보면 그 보고사가
    # 올해 공시를 했는데 전량 terminated인 경우 최신 연도가 과거로 내려가 컷이 무력해진다.
    reporter_latest: dict[tuple[str, str], int] = {}
    for e in session.query(RelationLocal).all():
        r = _reporter_of(e)
        if r is None:
            continue
        key = (r, _lineage(e.source_type))
        y = e.bsns_year or 0
        if y > reporter_latest.get(key, 0):
            reporter_latest[key] = y

    out = []
    for e in edges:
        r = _reporter_of(e)
        if r is None:
            out.append(e)                      # ftc·manual — 연도 컷 비대상
            continue
        if (e.bsns_year or 0) >= reporter_latest.get((r, _lineage(e.source_type)), 0):
            out.append(e)
    return out
