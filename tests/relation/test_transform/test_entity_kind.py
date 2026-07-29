"""비상장 상대방 유형 분류기 테스트 (U5-a).

표기는 전부 **실제 공시에서 관측된 문자열**이다(영향 조사 unlisted_impact.py 산출 상위 +
강원랜드·케어젠 추적에서 확인). 휴리스틱이라 완벽할 수 없으므로, 여기서 지키는 것은
두 가지다: ① 잡음을 노드로 만들지 않는다 ② 오분류의 비용이 '표시 형태'에 그치고
허위 관계를 만들지 않는다(앵커-로컬이라 병합 사고가 구조적으로 불가).
"""

from __future__ import annotations

import pytest

from modules.relation.storage.models import unlisted_uid
from modules.relation.transform.entity_kind import (
    KIND_COOP_FUND,
    KIND_PERSON,
    KIND_PRIVATE_CORP,
    KIND_PUBLIC_ORG,
    classify,
    is_noise,
)


# ── 잡음 게이트 (노드로 만들지 않음) ────────────────────────────────────────

@pytest.mark.parametrize(
    "surface,reason",
    [
        ("", "empty_or_total"),
        ("-", "empty_or_total"),
        ("계", "empty_or_total"),
        ("합계", "empty_or_total"),
        # 외국 법인명 콤마 분리 잔재 (실측: LLC 224회·Ltd. 216회·Inc. 114회)
        ("LLC", "suffix_fragment"),
        ("Ltd.", "suffix_fragment"),
        ("L.P.", "suffix_fragment"),
        # 카테고리 라벨 (실측: '특수관계자' 8,005회)
        ("특수관계자", "category_label"),
        ("전체 특수관계자  합계", "category_label"),
        ("그 밖의 특수관계자", "category_label"),
        # 거래 항목명 (실측: '전력거래 등' 1,777회·'자산과 부채' 408회)
        ("전력거래 등", "txn_item"),
        ("자산과 부채", "txn_item"),
        ("REC구매 등", "txn_item"),
    ],
)
def test_noise_is_rejected(surface, reason):
    assert is_noise(surface) == reason


@pytest.mark.parametrize(
    "surface",
    [
        "㈜하이원파트너스",
        "한국광해광업공단",
        "정용지",
        "Caregen Biopharma Inc.",
        "SK에코플랜트(주)",
        "소프트웨어공제조합",
        "(주)대한송유관공사",
    ],
)
def test_real_entities_pass_noise_gate(surface):
    assert is_noise(surface) is None


def test_company_with_txn_word_is_not_noise():
    """⚠️ 회귀 박제: 거래 어휘를 품었어도 법인 표지가 있으면 잡음이 아니다.
    '(주)대한송유관공사'의 '송유관'은 거래어가 아니지만, 예컨대 '자산관리㈜' 류가
    txn_item으로 잘못 걸리면 실제 법인을 통째로 잃는다."""
    assert is_noise("삼성자산운용㈜") is None
    assert is_noise("케이비부동산신탁 주식회사") is None


# ── 유형 판별 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "surface,relate,expected",
    [
        # 개인 — 케어젠 최대주주 실측
        ("정용지", "본인", KIND_PERSON),
        ("정연우", "최대주주의 자녀", KIND_PERSON),
        ("김은미", "특수관계인", KIND_PERSON),
        ("홍길동", None, KIND_PERSON),            # relate 없어도 2~4자 한글 단독
        # 공공기관 — 강원랜드 최대주주 실측
        ("한국광해광업공단", None, KIND_PUBLIC_ORG),
        ("국민연금공단", None, KIND_PUBLIC_ORG),
        ("조달청", None, KIND_PUBLIC_ORG),
        # 조합·펀드 — 실측 상위(건설공제조합 29회·소프트웨어공제조합 30회)
        ("소프트웨어공제조합", None, KIND_COOP_FUND),
        ("건설공제조합", None, KIND_COOP_FUND),
        ("카카오그로스해킹펀드", None, KIND_COOP_FUND),
        ("마스턴일반사모부동산투자신탁제98호", None, KIND_COOP_FUND),
        # 비상장법인 — 강원랜드·케어젠 자회사 실측
        ("㈜하이원파트너스", None, KIND_PRIVATE_CORP),
        ("㈜키즈라라", None, KIND_PRIVATE_CORP),
        ("Caregen Biopharma Inc.", None, KIND_PRIVATE_CORP),
        ("SK에코플랜트(주)", None, KIND_PRIVATE_CORP),
        ("Kia Slovakia s.r.o.", None, KIND_PRIVATE_CORP),
    ],
)
def test_classify(surface, relate, expected):
    assert classify(surface, relate) == expected


def test_corp_mark_beats_person_shape():
    """⚠️ 법인격 표지가 있으면 이름이 짧아도 개인이 아니다 — '㈜대웅'을 개인으로
    분류하면 화면에 개인 링으로 그려진다."""
    assert classify("㈜대웅", None) == KIND_PRIVATE_CORP
    assert classify("대웅제약(주)", "본인") == KIND_PRIVATE_CORP


def test_classify_always_returns_valid_kind():
    """분류 실패 시 폴백은 가장 중립적인 private_corp — 빈 값이 나오면 안 된다."""
    from modules.relation.transform.entity_kind import ALL_KINDS

    for s in ["알 수 없는 무언가", "XYZ Holdings", "第一物産"]:
        assert classify(s, None) in ALL_KINDS


# ── uid: 앵커 스코프 (연관성 없음의 코드 표현) ─────────────────────────────

def test_uid_is_deterministic():
    assert unlisted_uid("035250", "㈜하이원파트너스") == unlisted_uid(
        "035250", "㈜하이원파트너스"
    )


def test_uid_is_anchor_scoped():
    """⚠️ 회귀 박제: 같은 이름이라도 앵커가 다르면 다른 노드다(리더 확정 —
    "별개 노드로 처리하고 연관성을 찾지 말 것"). 여기가 같아지면 전역 병합이
    되살아나 동명 사고가 재발한다."""
    assert unlisted_uid("035250", "소프트웨어공제조합") != unlisted_uid(
        "214370", "소프트웨어공제조합"
    )


def test_uid_prefix_never_collides_with_ticker():
    """RelationLocal.source_corp에 ticker와 uid가 섞여 들어가므로 형태가 갈려야 한다."""
    uid = unlisted_uid("035250", "㈜하이원파트너스")
    assert uid.startswith("x_")
    assert not uid[:6].isdigit()


def test_short_korean_org_is_not_person():
    """⚠️ 회귀 박제(구현 중 실측 버그): '조달청'은 3자 한글이라 개인명 형태와 겹친다.
    무표지 2~4자 한글 휴리스틱을 어휘 판정보다 **앞에** 두면 공공기관이 개인으로
    분류된다 — 판정 순서는 신호 강도 순이어야 한다."""
    assert classify("조달청", None) == KIND_PUBLIC_ORG
    assert classify("한국은행", None) == KIND_PRIVATE_CORP  # 은행=법인 표지
