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
        # ★2026-07-29 계약 변경: relate 없이 이름만으로는 개인/법인을 못 가른다
        # ('오뚜기'·'하이브'도 성씨 3자다). 성씨 폴백은 **최대주주 명부 경로**에서만.
        ("홍길동", None, KIND_PRIVATE_CORP),
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


# ══ 2026-07-29 검증 에이전트가 잡은 오류 — 전부 회귀 박제 (반복 금지) ══════════

@pytest.mark.parametrize(
    "name",
    [
        # 실측: 금융지주 100% 자회사가 통째로 화면에서 사라졌다(103건).
        # '자산운용'의 '자산'이 거래어휘 게이트에 걸리는데 법인 표지로는 인식 안 됐다.
        "삼성자산운용", "KB자산운용", "신한자산신탁", "하나대체투자자산운용",
        "키움투자자산운용", "현대인베스트먼트자산운용", "롯데자산개발",
        "한국전력거래소", "대신자산신탁", "신영자산운용",
        # 집계 접미어가 붙은 실존 법인 — 접미어 제거는 strip_group_aggregate 소관
        "㈜글로우원과 종속기업", "우리산업(주)와 그 종속기업",
    ],
)
def test_real_financial_entities_are_not_noise(name):
    """⚠️ 회귀 박제: 거래 어휘를 품은 사명이 잡음으로 삼켜지면 100% 자회사가 소실된다."""
    assert is_noise(name) is None


@pytest.mark.parametrize(
    "name,relate,expected",
    [
        # 실측: relate에 개인 지표가 있는데 키워드 목록이 좁아 889명이 법인으로 그려졌다
        ("김기철", "최대주주", KIND_PERSON),
        ("장세욱", "대표이사", KIND_PERSON),
        ("정몽열", "본인", KIND_PERSON),
        ("황익준", "사내이사", KIND_PERSON),
        ("조유홍", "처", KIND_PERSON),
    ],
)
def test_person_relate_vocabulary_covers_observed_values(name, relate, expected):
    """⚠️ 회귀 박제: hyslrSttus.relate 실측 분포(최대주주 333·대표이사 80·처 14)를 커버."""
    assert classify(name, relate) == expected


@pytest.mark.parametrize("name", ["포스코", "엔씨켐", "대한사료", "동희오토", "정식품"])
def test_investment_targets_are_never_person(name):
    """⚠️ 회귀 박제: 타법인출자 대상은 **정의상 법인**이다(개인에게 출자하지 않는다).
    이름 형태만으로는 개인/법인을 가를 수 없으므로 경로가 알려줘야 한다."""
    assert classify(name, None, allow_person=False) == KIND_PRIVATE_CORP


@pytest.mark.parametrize(
    "name,reason",
    [
        ("284", "numeric_only"),          # 표 셀이 밀려 숫자만 들어옴
        ("(단위: 원)", "unit_header"),      # 표 머리글
        ("자기주식", "aggregate_token"),     # 특정 실체 아님
        ("우리사주조합", "aggregate_token"),
        ("주1) (주)훼미모드", "footnote_prefix"),
        ("㈜에이치비씨티 등 기타 104개사", "group_total"),
    ],
)
def test_noise_blind_spots_are_closed(name, reason):
    """⚠️ 회귀 박제: 전수 검사에서 통과해버렸던 사각지대 31건."""
    assert is_noise(name) == reason


# ══ 2026-07-29 2차 검증 — 1차 수정이 만든 회귀까지 박제 ═══════════════════════

@pytest.mark.parametrize(
    "name,relate",
    [
        # ⚠️ 1차 수정이 1자 관계어를 substring 매칭해 **법인을 개인으로 뒤집었다**
        ("롯데물산", "자회사"),      # '자'가 걸림
        ("롯데상사", "모회사"),      # '모'
        ("티모넷", "제휴사"),        # '제'
        ("성우물산", "매출처"),      # '처'·'매'
        ("다올테크", "임원이 지배하는 법인"),  # '임원' — relate가 명시적으로 '법인'인데
    ],
)
def test_corp_relate_signal_beats_person_keyword(name, relate):
    """⚠️ 회귀 박제: relate에 법인 신호가 있으면 **개인 키워드보다 우선**한다.
    1자 관계어는 완전일치로만 봐야 한다(substring 금지)."""
    assert classify(name, relate) == KIND_PRIVATE_CORP


@pytest.mark.parametrize(
    "name", ["고려아연", "강원랜드", "유한양행", "남양유업", "신도리코", "오뚜기"],
)
def test_four_char_company_names_are_not_person(name):
    """⚠️ 회귀 박제: 성씨 폴백을 4자까지 넓히면 실존 사명이 개인으로 뒤집힌다
    (검증 실측: 실존 사명 35개 중 28개). 폴백은 **3자 + 중립 relate**에 한정."""
    assert classify(name, None) == KIND_PRIVATE_CORP


@pytest.mark.parametrize(
    "name",
    ["23.99%", "(4,891,807)", "--", "2)", "13.00", "(23.99)"],
)
def test_numeric_cells_never_become_nodes(name):
    """⚠️ 회귀 박제: 거버넌스 파서 열 밀림으로 지분율·금액이 회사명 칸에 온다.
    화면에 **숫자가 회사 노드로** 그려지고 진짜 회사명은 detail에만 남았다
    (JW중외제약 n='(4,891,807)' detail='JW홀딩스㈜')."""
    assert is_noise(name) is not None


def test_corporate_registration_number_is_not_rrn():
    """⚠️ 회귀 박제: 법인등록번호(110111-4686139)는 주민번호와 형태가 같다.
    '(주)'가 붙어 있는데 개인으로 분류되던 문제(실측 9건)."""
    assert classify("(주)미툰앤노벨 (법인등록번호 : 110111-4686139)", None) == KIND_PRIVATE_CORP


@pytest.mark.parametrize(
    "relate,expected",
    [
        # ⚠️ 회귀 박제(3차): 한국어는 **끝 명사가 주체**다. substring만 보면
        # '지배회사의 등기임원'이 '회사' 때문에 법인이 돼 428건이 뒤집혔다.
        ("지배회사의 등기임원", KIND_PERSON),
        ("켐트로닉스 임원", KIND_PERSON),
        ("최대주주의 등기이사", KIND_PERSON),
        # 반대 방향도 지켜야 한다 — 앞에 '임원'이 있어도 끝이 '법인'이면 법인
        ("임원이 지배하는 법인", KIND_PRIVATE_CORP),
        ("임원이 지배하는 회사", KIND_PRIVATE_CORP),
        ("자회사", KIND_PRIVATE_CORP),
        ("매출처", KIND_PRIVATE_CORP),
    ],
)
def test_relate_head_noun_decides_subject(relate, expected):
    assert classify("김철수", relate) == expected
