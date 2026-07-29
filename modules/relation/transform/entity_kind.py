"""비상장 상대방의 유형 분류 (U5-a — universe/UNLISTED_PLAN.md §1).

상장사 링킹에 실패한 상대 표기를 화면 범례(NODE TYPOLOGY) 5종 중 하나로 가른다.
**노드로 만들 가치가 없는 잡음**(빈칸·집계 라벨·거래항목명·법인격 조각)은 여기서
먼저 걸러 낸다 — 영향 조사(UNLISTED_NODE_IMPACT.md)에서 실측한 게이트의 승격판이다.

⚠️ 앵커-로컬 원칙(리더 확정): 이 모듈은 **문자열 하나를 보고 유형만 판정**한다.
다른 회사 공시의 같은 이름과 병합하거나 전역 실체를 만들지 않는다 — 그래서
동명이인·동명법인 판단 자체가 필요 없다(설계상 위험 소멸).
"""

from __future__ import annotations

import re

# ── 유형 (화면 범례와 1:1) ──────────────────────────────────────────────────
KIND_PRIVATE_CORP = "private_corp"   # 비상장법인
KIND_PERSON = "person"               # 개인
KIND_COOP_FUND = "coop_fund"         # 조합·펀드
KIND_PUBLIC_ORG = "public_org"       # 공공기관

ALL_KINDS = (KIND_PRIVATE_CORP, KIND_PERSON, KIND_COOP_FUND, KIND_PUBLIC_ORG)

# ── 잡음 (노드로 만들지 않음) ───────────────────────────────────────────────
# 실측 근거: 지분 경로에서 빈칸/'계' 8,504 · 거래항목 147 · 카테고리 37,
# 주석 경로에서 카테고리 439 · 거래항목 537이 걸렸다.
_EMPTY_TOKENS = {"", "-", "−", "―", "계", "합계", "소계", "총계", "n/a", "na"}
_CATEGORY_WORDS = (
    "특수관계자", "관계기업", "공동기업", "종속기업", "지배기업", "기업집단",
    "계열회사", "경영진", "영향력", "공동지배", "합계", "소계",
)
_TXN_ITEM_WORDS = (
    "거래", "매출", "매입", "수익", "비용", "자산", "부채", "채권", "채무",
    "구매", "판매", "대여", "차입", "상환", "출자금", "배당", "급여", "보상",
    "잔액", "대손", "미수", "미지급", "선급", "선수",
)
# 외국 법인명이 "Co., Ltd." 콤마로 쪼개졌을 때 남는 조각
_SUFFIX_FRAGMENTS = {
    "llc", "ltd", "ltd.", "inc", "inc.", "l.p.", "lp", "co.", "co", "corp",
    "corp.", "gmbh", "s.a.", "sa", "pte", "pte.", "b.v.", "bv", "n.v.", "nv",
    "s.r.o.", "sarl", "sas", "plc", "ag", "kk", "주식회사", "㈜", "(주)",
}

# ── 유형 판별 어휘 ──────────────────────────────────────────────────────────
_COOP_FUND_WORDS = (
    "조합", "펀드", "신탁", "공제", "투자회사", "사모", "벤처투자", "인베스트먼트",
    "리츠", "유동화전문", "제이차", "기금", "fund", "trust", "partners l.p.",
)
_PUBLIC_ORG_WORDS = (
    "공단", "공사", "진흥원", "연구원", "재단", "협회", "학교", "대학교", "정부",
    "조달청", "국민연금", "예금보험", "산업은행", "수출입은행", "중소벤처기업",
)
# 법인격 표지 — 있으면 개인이 아니다
_CORP_MARKS = re.compile(
    r"㈜|\(주\)|주식회사|유한회사|합자회사|합명회사|유한책임회사|"
    r"\bLtd\b|\bInc\b|\bLLC\b|\bLLP\b|\bGmbH\b|\bS\.A\b|\bN\.V\b|\bB\.V\b|"
    r"\bPte\b|\bCorp\b|\bCo\b|\bCompany\b|\bLimited\b|\bPLC\b|\bAG\b|"
    r"s\.r\.o|SARL|SAS|은행|증권|보험|캐피탈|홀딩스|파트너스|산업|전자|화학|건설|"
    # ★2026-07-29: 금융·부동산 계열 사명이 거래어휘 게이트에 삼켜졌다(실측 103건 —
    # 삼성자산운용·KB자산운용·신한자산신탁 등 100% 자회사가 통째로 사라짐).
    # '자산운용'의 '자산'이 _TXN_ITEM_WORDS에 걸리는데 법인 표지로는 인식되지 않았다.
    r"자산운용|자산신탁|투자신탁|자산개발|인베스트먼트|거래소|리츠|에셋|"
    r"금융|카드|저축|리스|벤처스|테크놀로지|시스템즈?|네트웍스|솔루션즈?",
    re.IGNORECASE,
)
_KOREAN_PERSON_RE = re.compile(r"^[가-힣]{2,4}$")
_RRN_RE = re.compile(r"\d{6}\s*-\s*\d{7}")

# hyslrSttus `relate` 필드 판정 어휘.
#
# ★2026-07-29 2차 수정(검증 에이전트가 잡음): 1차 수정에서 1자 관계어를 substring으로
# 매칭했더니 **법인이 개인으로 뒤집혔다** — `자회사`에 '자', `모회사`에 '모',
# `제휴사`에 '제', `매출처`에 '처'·'매'가 걸려 롯데물산·롯데상사·성우물산·티모넷이
# person이 됐다. `임원이 지배하는 법인`은 '임원'에 걸려 **relate가 명시적으로 '법인'인데**
# 개인이 됐다. → ① 법인 신호를 **먼저** 차단하고 ② 1자 어휘는 **완전일치**로만 본다.
_CORP_RELATIONS = (
    "법인", "회사", "계열", "자회사", "모회사", "관계사", "제휴", "거래처",
    "매출처", "매입처", "출자", "투자",
)
# 여러 글자라 오탐 위험이 낮은 것 — substring 매칭 허용
_PERSONAL_RELATIONS = (
    "본인", "최대주주", "친인척", "친족", "인척", "배우자", "자녀", "특수관계인",
    "대표이사", "사내이사", "사외이사", "감사", "임원", "며느리", "사위", "조카",
    "친척", "형제", "자매", "부인",
)
# 1자 어휘 — **완전일치만**. substring으로 쓰면 위 사고가 재발한다.
_PERSONAL_RELATIONS_EXACT = {"자", "부", "모", "제", "매", "형", "손", "처", "녀", "남"}

# 한국 성씨(상위 40). `relate`가 개인/법인 어느 쪽 신호도 아닐 때(예: '기타'·'-')
# **3자 이름에 한해** 개인의 보조 신호로 쓴다.
# ⚠️ 단독으로도, 4자에도 쓰면 안 된다 — 고려아연·강원랜드·유한양행이 전부 성씨로
#    시작한다(검증 에이전트 실측: 실존 사명 35개 중 28개가 person으로 뒤집힘).
_KOREAN_SURNAMES = (
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서",
    "신", "권", "황", "안", "송", "류", "전", "홍", "고", "문", "양", "손", "배",
    "백", "허", "유", "남", "심", "노", "하", "곽", "성", "차", "주", "우", "구", "민",
)


# 관계어의 **끝 명사**가 주체를 결정한다(한국어 어순). '지배회사의 등기임원'은
# 회사가 아니라 **임원(사람)**이고, '임원이 지배하는 법인'은 임원이 아니라 **법인**이다.
# ★3차 수정: substring만 보면 앞쪽 수식어에 걸려 428건이 뒤집혔다(실측).
_PERSON_HEADS = (
    "임원", "이사", "감사", "본인", "친인척", "친족", "인척", "배우자", "자녀",
    "특수관계인", "며느리", "사위", "조카", "친척", "형제", "자매", "부인", "최대주주",
)
_CORP_HEADS = ("회사", "법인", "계열", "조합", "펀드", "재단", "단체")


def _relate_signal(relate: str | None) -> str:
    """relate 필드가 가리키는 것 — 'corp' | 'person' | 'neutral'.

    판정 순서: ① 끝 명사(주체) → ② 명시적 법인 어휘 → ③ 1자 완전일치 → ④ 개인 어휘.
    """
    # ★개행·닫는 괄호가 끝 명사 판정을 막는다: 원문이 '특수관계인' + 개행 +
    # '(계열회사 임원)'이면 끝이 '임원)'이라 endswith에 안 걸리고, 앞의 '계열회사'가
    # 먼저 잡혀 사람이 법인으로 뒤집혔다(실측). 공백 접기 + 닫는 괄호 제거로 해소.
    r = re.sub(r"\s+", " ", (relate or "")).strip().rstrip(")]） ")
    if not r:
        return "neutral"
    # ① 끝 명사 — 가장 강한 신호
    for head in _PERSON_HEADS:
        if r.endswith(head):
            return "person"
    for head in _CORP_HEADS:
        if r.endswith(head):
            return "corp"
    # ② 명시적 법인 어휘(끝에 없어도 '매출처'·'거래처'처럼 통째로 법인을 뜻하는 것)
    if any(w in r for w in _CORP_RELATIONS):
        return "corp"
    # ③ 1자 어휘는 완전일치만 (substring이면 '자회사'의 '자'에 걸린다)
    if r in _PERSONAL_RELATIONS_EXACT:
        return "person"
    # ④ 나머지 개인 어휘
    if any(w in r for w in _PERSONAL_RELATIONS):
        return "person"
    return "neutral"


# ★2026-07-29 전수 검사에서 발견한 사각지대 — 위 규칙을 통과했지만 노드가 되면
# 안 되는 표기들(실측 31건). 각각 실물이 근거다.
# ★2026-07-29 2차: `%`·괄호·대시가 빠져 있어 `23.99%`·`(4,891,807)`·`--`가 통과했다.
# 실제 화면에 **숫자가 회사 노드로 그려지고 진짜 회사명은 detail에만** 있었다
# (JW중외제약 n='(4,891,807)' detail='JW홀딩스㈜'). 거버넌스 파서의 열 밀림 산물.
_NUMERIC_ONLY_RE = re.compile(r"^[\d,.\s%()\-–—~]+$")
_ORPHAN_MARKER_RE = re.compile(r"^\d+\s*\)$")                     # '2)' — 각주 번호만
_FOOTNOTE_PREFIX_RE = re.compile(r"^(?:주|\*|note)\s*\d*\s*\)")   # '주1) (주)훼미모드'
_GROUP_TOTAL_RE = re.compile(r"등\s*(?:기타\s*)?\d+\s*개\s*사")     # '㈜A 등 기타 104개사'
_UNIT_HEADER_RE = re.compile(r"^\(?\s*단위\s*[:：]")                # '(단위: 원)' — 표 머리글
_AGGREGATE_TOKENS = {"자기주식", "자사주", "기타개인", "우리사주조합", "소액주주",
                     "기타주주", "국민연금", "기타법인"}


def is_noise(surface: str) -> str | None:
    """노드로 만들면 안 되는 표기인가 — 잡음이면 사유, 아니면 None."""
    s = (surface or "").strip()
    if s.lower() in _EMPTY_TOKENS:
        return "empty_or_total"
    if s.lower().strip(".") in _SUFFIX_FRAGMENTS or s.lower() in _SUFFIX_FRAGMENTS:
        return "suffix_fragment"
    if len(s) < 2:
        return "too_short"
    if _NUMERIC_ONLY_RE.match(s):
        return "numeric_only"          # 숫자·지분율·금액 — 표 셀이 밀려 들어온 것
    if _ORPHAN_MARKER_RE.match(s):
        return "orphan_marker"         # '2)' — 각주 번호만
    if _UNIT_HEADER_RE.match(s):
        return "unit_header"           # '(단위: 원)' — 표 머리글
    if _FOOTNOTE_PREFIX_RE.match(s):
        return "footnote_prefix"       # '주1) ...' — 각주 번호가 이름 앞에 붙은 행
    if s in _AGGREGATE_TOKENS:
        return "aggregate_token"       # 자기주식·기타개인 등 — 특정 실체가 아님
    if _GROUP_TOTAL_RE.search(s):
        return "group_total"           # '등 기타 104개사' — 개별 법인이 아닌 집계
    # ★법인 표지가 있으면 카테고리 라벨로 보지 않는다 — '㈜글로우원과 종속기업'(94.6%),
    # '우리산업(주)와 그 종속기업'(39.5%)처럼 **집계 접미어가 붙은 실존 법인**이
    # 통째로 잡음 처리되던 문제(실측 9건). 접미어 제거는 strip_group_aggregate 소관.
    if any(w in s for w in _CATEGORY_WORDS) and not _CORP_MARKS.search(s):
        return "category_label"
    # 거래 항목명: 법인 표지가 전혀 없으면서 거래 어휘를 포함
    if any(w in s for w in _TXN_ITEM_WORDS) and not _CORP_MARKS.search(s):
        return "txn_item"
    return None


def upsert_unlisted_node(
    session, anchor_corp: str, name_raw: str, relate: str | None, provenance: str,
    allow_person: bool = True, surname_fallback: bool = False,
) -> str | None:
    """비상장 상대 표기 → UnlistedNode upsert 후 uid 반환. 잡음이면 None.

    앵커-로컬: (anchor_corp, name_raw) 조합이 키다. 다른 앵커의 같은 이름과 병합하지
    않는다 — 전역 실체가 없으므로 동명 판정 문제가 발생하지 않는다(UNLISTED_PLAN §2).
    """
    from modules.relation.storage.models import UnlistedNode, unlisted_uid

    # ★표시용 공백 정규화(2026-07-29): 원문 충실은 **문자**에 대한 것이고, 개행·연속
    # 공백은 표기가 아니라 원문 표 레이아웃의 잔재다. 그대로 두면 ego 2,933건이
    # 줄바꿈이 낀 이름으로 렌더된다(예: 'Beijing HYUNDAI TRANSYS' + 개행 + 'Transmission').
    name = re.sub(r"\s+", " ", (name_raw or "")).strip()
    if is_noise(name):
        return None
    uid = unlisted_uid(anchor_corp, name)
    row = session.query(UnlistedNode).filter_by(uid=uid).one_or_none()
    kind = classify(name, relate, allow_person=allow_person,
                    surname_fallback=surname_fallback)
    if row:
        # ★같은 (앵커, 이름)에 여러 relate가 올 수 있다(연도·행마다 표기가 다름).
        # 마지막 것으로 덮으면 순서 의존이 되고 relate_raw와 kind가 어긋난다.
        # → **개인 신호가 가장 강하다**: 한 번이라도 '임원·본인·최대주주'로 적혔으면
        #   그 상대는 사람이다(법인이 그렇게 적히지 않는다). 결정적·순서 독립.
        prev_sig = _relate_signal(row.relate_raw)
        new_sig = _relate_signal(relate)
        if prev_sig != "person" and new_sig == "person":
            row.relate_raw = relate
            row.kind = kind
        elif prev_sig == "person":
            pass                      # 이미 개인 확정 — 유지
        else:
            row.relate_raw = relate
            row.kind = kind
        row.status = "active"
        # 같은 법인의 표기 변형이 여러 번 오면 **가장 깔끔한 것**을 화면에 쓴다
        # (각주·개행이 붙은 긴 변형보다 원형이 읽기 좋다). 원문 보존 원칙과 양립 —
        # 셋 다 원문이고 그중 하나를 고르는 것뿐이다.
        if len(name) < len(row.name_raw or ""):
            row.name_raw = name
    else:
        session.add(
            UnlistedNode(
                uid=uid,
                anchor_corp=anchor_corp,
                name_raw=name,
                kind=kind,
                relate_raw=relate,      # 분류 입력 보존 — 없으면 kind를 사후 감사할 수 없다
                first_seen=provenance,
                status="active",
            )
        )
    return uid


def reconcile_unlisted_kinds(session) -> int:
    """저장된 kind를 **재산출값으로 확정** — 감사 가능성 보장. 갱신 건수 반환.

    ⚠️ 왜 필요한가: 같은 (앵커, 이름) 노드가 여러 생산자·여러 행에서 upsert되는데,
    분류 입력(relate·경로)이 행마다 다르면 최종 저장값이 **실행 순서에 따라 달라진다**
    (실측: '윤정'이 앵커 464500에선 person, 425420에선 private_corp — 같은 relate인데도).
    산출물을 사후 검증할 수 없으면 오분류를 발견할 방법도 없다.
    → 파이프라인 끝에서 **저장된 입력(relate_raw·first_seen)으로 다시 계산**해 확정한다.
      이후 "저장 kind == classify(저장 입력)"가 불변식이 되어 전수 감사가 가능해진다.
    """
    from modules.relation.storage.models import UnlistedNode

    changed = 0
    for row in session.query(UnlistedNode).all():
        path = row.first_seen or ""
        expect = classify(
            row.name_raw,
            row.relate_raw,
            allow_person=not path.startswith("otrCpr"),
            surname_fallback=path.startswith("hyslrSttus"),
        )
        if row.kind != expect:
            row.kind = expect
            changed += 1
    return changed


def prune_orphan_unlisted_nodes(session) -> int:
    """어떤 active 엣지도 참조하지 않는 UnlistedNode 삭제 → 삭제 건수.

    ⚠️ 소유권 설계: UnlistedNode는 filters(지분)·related_party(주석) 두 생산자가 함께
    만든다. source_type으로 스코프를 나누면 "둘 다 만든 행을 누가 지우나"가 모호해진다
    (dart_filing 소실 사고와 같은 구조). 그래서 **참조 무결성 기준**으로 정리한다 —
    노드는 자기를 가리키는 엣지가 있어야 존재한다. 생산자 누구든 실행 끝에 호출하면
    그 시점의 고아만 사라지므로 순서 의존이 없다.
    """
    from modules.relation.storage.models import (
        RelationLocal,
        UnlistedNode,
        ValueChainEdge,
    )

    referenced: set[str] = set()
    for src, dst in session.query(RelationLocal.source_corp, RelationLocal.target_corp):
        referenced.add(src)
        referenced.add(dst)
    for src, dst in session.query(ValueChainEdge.src_corp, ValueChainEdge.dst_corp):
        referenced.add(src)
        referenced.add(dst)

    removed = 0
    for row in session.query(UnlistedNode).all():
        if row.uid not in referenced:
            session.delete(row)
            removed += 1
    return removed


def classify(
    surface: str,
    relate: str | None = None,
    allow_person: bool = True,
    surname_fallback: bool = False,
) -> str:
    """비상장 상대 표기 → kind. 잡음 여부는 호출 전에 is_noise()로 거른다.

    relate: hyslrSttus의 관계 필드(있으면 개인 판정의 1차 근거).
    allow_person: **개인일 수 있는 원천인가**. 타법인출자(otrCpr)의 대상은 정의상
      항상 법인이다 — 개인에게 출자하지 않는다. 그런 경로는 False를 넘겨
      `포스코`·`엔씨켐`처럼 2~4자 한글 사명이 개인으로 분류되는 것을 원천 차단한다
      (2026-07-29 검증에서 발견 — 이름 형태만으로는 개인/법인을 가를 수 없다).

    판정 순서는 **신호의 강도 순**이다:
      ① 주민번호(결정적) → ② relate 관계어 + 개인명 형태 → ③ 조합·펀드 어휘
      → ④ 공공기관 어휘 → ⑤ 무표지 2~4자 한글(가장 약한 휴리스틱) → ⑥ 비상장법인
    ⚠️ ⑤를 어휘 판정보다 앞에 두면 '조달청'(3자 한글)이 개인으로 분류된다 —
    구현 중 실측으로 잡은 순서 버그(회귀 테스트로 박제).
    """
    s = (surface or "").strip()
    has_corp_mark = bool(_CORP_MARKS.search(s))
    signal = _relate_signal(relate)

    # ★법인등록번호(110111-4686139)는 주민번호와 형태가 같다 — 법인 표지가 있거나
    # '등록번호' 문구가 보이면 개인 분기를 타지 않는다(검증 실측 9건).
    if (
        allow_person
        and not has_corp_mark
        and "등록번호" not in s
        and _RRN_RE.search(s)
    ):
        return KIND_PERSON

    if allow_person and signal == "person" and not has_corp_mark and _KOREAN_PERSON_RE.match(s):
        return KIND_PERSON

    if any(w in s for w in _COOP_FUND_WORDS) or any(
        w in s.lower() for w in ("fund", "trust")
    ):
        return KIND_COOP_FUND
    if any(w in s for w in _PUBLIC_ORG_WORDS):
        return KIND_PUBLIC_ORG

    # 보조 신호: **최대주주 명부(hyslrSttus)에서만**, relate가 중립일 때, 3자+성씨.
    # ⚠️ 경로를 안 가르면 '오뚜기'·'하이브'처럼 성씨로 시작하는 3자 사명이 개인이 된다.
    # 최대주주 현황은 애초에 '사람 명부'라 이 폴백이 성립하지만, 주석·출자 경로는 아니다.
    if (
        allow_person
        and surname_fallback
        and signal == "neutral"
        and not has_corp_mark
        and _KOREAN_PERSON_RE.match(s)
        and (len(s) == 3 and s[0] in _KOREAN_SURNAMES)
    ):
        return KIND_PERSON
    return KIND_PRIVATE_CORP
