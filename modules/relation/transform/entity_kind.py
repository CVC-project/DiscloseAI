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
    r"s\.r\.o|SARL|SAS|은행|증권|보험|캐피탈|홀딩스|파트너스|산업|전자|화학|건설",
    re.IGNORECASE,
)
_KOREAN_PERSON_RE = re.compile(r"^[가-힣]{2,4}$")
_RRN_RE = re.compile(r"\d{6}\s*-\s*\d{7}")

# hyslrSttus relate 필드의 개인 관계어 (filters.PERSONAL_RELATIONS 준용·확장)
_PERSONAL_RELATIONS = (
    "본인", "친인척", "친족", "인척", "배우자", "자녀", "자", "부", "모",
    "형제", "자매", "손", "임원", "특수관계인",
)


def is_noise(surface: str) -> str | None:
    """노드로 만들면 안 되는 표기인가 — 잡음이면 사유, 아니면 None."""
    s = (surface or "").strip()
    if s.lower() in _EMPTY_TOKENS:
        return "empty_or_total"
    if s.lower().strip(".") in _SUFFIX_FRAGMENTS or s.lower() in _SUFFIX_FRAGMENTS:
        return "suffix_fragment"
    if len(s) < 2:
        return "too_short"
    if any(w in s for w in _CATEGORY_WORDS):
        return "category_label"
    # 거래 항목명: 법인 표지가 전혀 없으면서 거래 어휘를 포함
    if any(w in s for w in _TXN_ITEM_WORDS) and not _CORP_MARKS.search(s):
        return "txn_item"
    return None


def upsert_unlisted_node(
    session, anchor_corp: str, name_raw: str, relate: str | None, provenance: str
) -> str | None:
    """비상장 상대 표기 → UnlistedNode upsert 후 uid 반환. 잡음이면 None.

    앵커-로컬: (anchor_corp, name_raw) 조합이 키다. 다른 앵커의 같은 이름과 병합하지
    않는다 — 전역 실체가 없으므로 동명 판정 문제가 발생하지 않는다(UNLISTED_PLAN §2).
    """
    from modules.relation.storage.models import UnlistedNode, unlisted_uid

    name = (name_raw or "").strip()
    if is_noise(name):
        return None
    uid = unlisted_uid(anchor_corp, name)
    row = session.query(UnlistedNode).filter_by(uid=uid).one_or_none()
    kind = classify(name, relate)
    if row:
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
                first_seen=provenance,
                status="active",
            )
        )
    return uid


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


def classify(surface: str, relate: str | None = None) -> str:
    """비상장 상대 표기 → kind. 잡음 여부는 호출 전에 is_noise()로 거른다.

    relate: hyslrSttus의 관계 필드(있으면 개인 판정의 1차 근거).

    판정 순서는 **신호의 강도 순**이다:
      ① 주민번호(결정적) → ② relate 관계어 + 개인명 형태 → ③ 조합·펀드 어휘
      → ④ 공공기관 어휘 → ⑤ 무표지 2~4자 한글(가장 약한 휴리스틱) → ⑥ 비상장법인
    ⚠️ ⑤를 어휘 판정보다 앞에 두면 '조달청'(3자 한글)이 개인으로 분류된다 —
    구현 중 실측으로 잡은 순서 버그(회귀 테스트로 박제).
    """
    s = (surface or "").strip()

    if _RRN_RE.search(s):
        return KIND_PERSON
    has_corp_mark = bool(_CORP_MARKS.search(s))
    if (
        relate
        and any(kw in relate for kw in _PERSONAL_RELATIONS)
        and not has_corp_mark
        and _KOREAN_PERSON_RE.match(s)
    ):
        return KIND_PERSON

    if any(w in s for w in _COOP_FUND_WORDS) or any(
        w in s.lower() for w in ("fund", "trust")
    ):
        return KIND_COOP_FUND
    if any(w in s for w in _PUBLIC_ORG_WORDS):
        return KIND_PUBLIC_ORG

    if not relate and _KOREAN_PERSON_RE.match(s) and not has_corp_mark:
        # relate가 없어도 2~4자 한글 단독은 개인으로 본다(filters 기존 휴리스틱 준용).
        # 오분류 비용은 '개인 링'으로 표시되는 것뿐 — 허위 관계를 만들지 않는다.
        return KIND_PERSON
    return KIND_PRIVATE_CORP
