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


# ── 공백 패딩·한자 촌수 (2026-07-30, CPA 표본 검수에서 발견) ──────────────────
#
# 공시는 표 칸 폭을 맞추려 **이름과 relate 양쪽에 글자 사이 공백**을 넣는다
# (`이   진` / `본     인` / `최 대 주 주` / `등 기 임 원`). 공백을 접기만 하면
# `본 인` != `본인`이라 어휘 전체가 불일치해 **사람이 비상장법인으로** 분류됐다 —
# 실측 310건. 일부 공시는 촌수를 한자로 적는다(`子`·`妻`·`兄`) — 실측 92건.

@pytest.mark.parametrize(
    "surface,relate",
    [
        ("이   진", "(子)"),              # 양지사 실측 — CPA 표본 28번
        ("주 홍", "최대주주"),
        ("박 효 정", "본     인"),
        ("이 천 기", "미등기 임원"),
        ("최 원", "본     인"),
        ("최 석", "친 인 척"),
        ("남 지 현", "제 수"),
        ("류 시 영", "회      장"),
        ("이 혁", "계열사 대표"),
        ("손 욱", "등 기 임 원"),
        ("김정태", "최대주주 兄"),          # 한자 촌수
        ("이혜리", "자(姉)"),
        ("이효원", "부(父)"),
        ("노영희", "최대주주 妻"),
    ],
)
def test_space_padded_and_cjk_kinship_are_person(surface, relate):
    """⚠️ 회귀 박제: 공백 패딩된 이름·relate와 한자 촌수를 사람으로 인식해야 한다.
    판정은 여전히 relate가 개인을 가리킬 때만 성립한다(사명 뒤집기 경로 아님)."""
    assert classify(surface, relate, surname_fallback=True) == KIND_PERSON


@pytest.mark.parametrize(
    "surface,relate",
    [
        ("롯데물산", "자회사"),
        ("티모넷", "매출처"),
        ("어떤법인", "임원이 지배하는 법인"),
        ("성우물산", "모회사"),
    ],
)
def test_space_strip_does_not_flip_corporations(surface, relate):
    """⚠️ 공백 제거를 넣어도 법인 신호 우선(후속14 오류 8)이 깨지지 않아야 한다."""
    assert classify(surface, relate, surname_fallback=True) == KIND_PRIVATE_CORP


@pytest.mark.parametrize(
    "label", ["주요 주주", "임원 등", "임직원 등", "주 주", "임 직 원"],
)
def test_space_padded_aggregate_labels_are_noise(label):
    """묶음 라벨은 특정 실체가 아니다 — 공백을 넣어 적어도 잡음으로 걸러야 한다."""
    assert is_noise(label) == "aggregate_token"


# ── 각주 서술 문장 (2026-07-30 후속18, 실측 49건) ────────────────────────────

@pytest.mark.parametrize("text", [
    "(주)KG프레시는 당기 중 (주)KG에프앤비(구, KG할리스에프앤비)에 흡수합병 되었습니다.",
    "연결회사는 2025년 1월 2일 (주)화인어프라이언스의 지분을 취득하여 관계기업으로 편입되었습니다.",
    "공정거래위원회가 지정한 대규모기업집단계열회사는 한국채택국제회계기준 제1024호 문단10에서 규정하는",
    "당기 중 OCIM SDN. BHD.에서 OCI TerraSus Sdn. Bhd.로 상호를 변경하였습니다.",
    "(주)KG아이씨티는 최상위지배기업의 특수관계자가 지배력을 행사하는 기업입니다.",
    "(주)한국특강의 경우 당기 중 전환사채 처분이 완료되어",
    "KG에코솔루션(주)로 사명변경하였습니다.",
    "500주를 모두 취득하게 되어 제2대 주주와의 주주 간 계약은 종료되었습니다(주석 38 참조).",
])
def test_footnote_sentences_are_noise(text):
    """⚠️ 회귀 박제: 각주 서술 문장이 법인 표지(㈜·주식회사)를 품어 기존 게이트를
    통과했다. 서술 표지로 잡는다."""
    assert is_noise(text) == "sentence_form"


@pytest.mark.parametrize("name", [
    # ⚠️ 길이로 판정하면 실존 외국 사명이 잘린다(전부 실측 노드)
    "HYUNDAI MOTOR GROUP INNOVATION CENTER IN SINGAPORE PTE. LTD.",
    "ASSAN HANIL OTOMOTIV SANAYI VE TICARET ANONIM SIRKETI",
    "Sichuan Kelun-Doosan Biotechnology Company Limited",
    "타임폴리오 코스닥벤처 The Unique 대체투자3호 전문투자형 사모투자신탁",
    "㈜세미콜론명동위탁관리부동산투자회사 (舊㈜디디아이명동엔위탁관리부동산투자회사)",
    "Korea Electric Power Corporation for Maintenance Company",
    "百愛樂(GUANGZHOU)體育用品有限公司 (백애락(GUANGZHOU)체육용품유한공사)",
])
def test_long_real_company_names_survive_sentence_gate(name):
    """⚠️ 서술 표지 게이트가 장문 실존 사명을 잡아서는 안 된다."""
    assert is_noise(name) is None


# ── 표시명 정리 (2026-07-30 후속18 — 각주 885엣지 · 회전 조각 51엣지) ─────────

@pytest.mark.parametrize("raw,expected", [
    ("Iksuda Therapeutics Limited(*3)", "Iksuda Therapeutics Limited"),
    ("오상-케이넷 창업초기 투자조합(주7)", "오상-케이넷 창업초기 투자조합"),
    ("(주)프로젠(보통주)", "(주)프로젠"),
    ("(주)렉스필드컨트리클럽 (주1 참조)", "(주)렉스필드컨트리클럽"),
    # 원문 구분자 유실로 앞 회사의 'Co., Ltd'가 뒷 회사 앞에 붙은 조각 제거
    ("LTD.HWASEUNG VIETNAM CHEMICAL CO.", "HWASEUNG VIETNAM CHEMICAL CO."),
    ("Ltd.Zhe Jiang Dayimei Health Technology Co.",
     "Zhe Jiang Dayimei Health Technology Co."),
])
def test_clean_display_name_strips_annotation_and_orphan_suffix(raw, expected):
    from modules.relation.transform.entity_kind import clean_display_name
    assert clean_display_name(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    # ⚠️ 회귀 박제(2026-07-30 전수 스윕): 번호 없는 **맨뒤 별표**만 남는 각주가 있다.
    # `(*N)` 형태만 떼던 규칙을 빠져나가 화면에 별표가 그대로 노출됐다.
    ("키움문화벤처제1호투자조합*", "키움문화벤처제1호투자조합"),
    ("씨아이에스 (前씨아이솔리드 주식회사) *", "씨아이에스 (前씨아이솔리드 주식회사)"),
    ("㈜한국기업평가**", "㈜한국기업평가"),
])
def test_clean_display_name_strips_trailing_bare_asterisk(raw, expected):
    from modules.relation.transform.entity_kind import clean_display_name
    assert clean_display_name(raw) == expected


@pytest.mark.parametrize("text", [
    # ⚠️ 회귀 박제(2026-07-30 전수 스윕): 종결어미를 하나씩 열거하면 반드시 빠진다.
    # `있습니다`가 목록에 없어 이 11건이 노드로 만들어졌다(dart_filing 경로).
    "BLUE ONE NYC LLC가 100% 지분을 보유하고 있습니다.",
    "BLUE 31st STREET HOLDCO LLC가 100% 지분을 보유하고 있습니다.",
])
def test_holding_sentences_are_noise(text):
    assert is_noise(text) == "sentence_form"


@pytest.mark.parametrize("name", [
    # ⚠️ 원칙 ②: 일반 괄호는 신원 정보 — 떼면 HMM류 오링킹이 된다
    "DB(Philippines) Inc.",
    "百愛樂(GUANGZHOU)體育用品有限公司 (백애락(GUANGZHOU)체육용품유한공사)",
    # ⚠️ 접미어로 시작하는 것처럼 보이는 실존 사명은 건드리지 않는다
    "CoMo China Co.,Ltd.",
    "Samsung Electronics Co., Ltd.",
])
def test_clean_display_name_preserves_identity_parentheses(name):
    from modules.relation.transform.entity_kind import clean_display_name
    assert clean_display_name(name) == name


# ── 참조 무결성: 노드 없는 엣지도 정리한다 (2026-07-30 전수 스윕) ─────────────

def test_prune_removes_edges_pointing_at_missing_node(in_memory_session):
    """⚠️ 회귀 박제: 고아 노드(엣지 없는 노드)만 지우고 **반대 방향**은 안 지우고 있었다.

    표시명 규칙을 손질하면 reconcile이 노드를 병합·삭제하는데, 그 뒤에 생산자가 옛 uid로
    행을 다시 넣으면 참조가 끊긴 채 남는다(실측 1건: 023590 → x_07ccff2cb98d).
    화면에는 이미 안 보이므로 남겨두면 순수 오염이다.
    """
    from modules.relation.storage.models import RelationLocal, UnlistedNode, ValueChainEdge
    from modules.relation.transform.entity_kind import prune_orphan_unlisted_nodes

    s = in_memory_session
    s.add(UnlistedNode(uid="x_alive0000001", anchor_corp="005930",
                       name_raw="살아있는조합", kind="fund_partnership"))
    s.add(RelationLocal(source_corp="005930", target_corp="x_alive0000001",
                        source_type="otrCprInvstmntSttus", relation_type="investment",
                        bsns_year=2025))
    s.add(RelationLocal(source_corp="005930", target_corp="x_dead00000001",
                        source_type="otrCprInvstmntSttus", relation_type="investment",
                        bsns_year=2025))
    s.add(ValueChainEdge(src_corp="x_dead00000002", dst_corp="005930", edge_type="supply",
                         tier="T1", source_kind="rp_note", rcept_no="20250101000001",
                         provenance="x", amount=1.0, as_of=2025, status="active"))
    s.commit()

    removed = prune_orphan_unlisted_nodes(s)
    s.flush()

    rl = s.query(RelationLocal).all()
    assert removed == 2, "끊어진 참조 2건이 정리돼야 한다"
    assert [r.target_corp for r in rl] == ["x_alive0000001"], "살아있는 참조는 보존"
    assert s.query(ValueChainEdge).count() == 0
    assert s.query(UnlistedNode).count() == 1


def test_prune_keeps_listed_ticker_edges(in_memory_session):
    """상장 티커(6자리)는 UnlistedNode에 없는 게 정상 — 정리 대상이 아니다."""
    from modules.relation.storage.models import RelationLocal
    from modules.relation.transform.entity_kind import prune_orphan_unlisted_nodes

    s = in_memory_session
    s.add(RelationLocal(source_corp="005930", target_corp="000660",
                        source_type="hyslrSttus", relation_type="subsidiary",
                        bsns_year=2025))
    s.commit()

    assert prune_orphan_unlisted_nodes(s) == 0
    assert s.query(RelationLocal).count() == 1
