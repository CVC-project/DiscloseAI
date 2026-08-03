"""Quality rules for full-market business cards.

The full-market generator starts from imperfect DART summary snippets. This
module removes accounting/table artifacts, applies a small number of
company-specific corrections, and attaches stable local representative images
so the business tab never falls back to empty placeholder visuals.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


IMG = "../data/business_images/"


IMAGE_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("HBM", "고대역폭"), "business_image_df7b448e6d568266.jpg", "Wikimedia Commons"),
    (
        ("CIS", "이미지센서", "카메라모듈"),
        "business_image_025006447be31665.jpg",
        "Wikimedia Commons",
    ),
    (
        ("MLCC", "적층세라믹", "콘덴서"),
        "business_image_76a8c8f5ba93d5d3.avif",
        "Unsplash",
    ),
    (
        # NAND는 SSD보다 먼저 검사한다 — "NAND"만 있고 "SSD"는 없는 세그먼트(예: 순수
        # 낸드 플래시 사업부)가 SSD 완제품 사진을 받지 않게. "SSD"·"스토리지"는 SSD
        # 완제품 사진, "NAND"·"낸드"는 반도체 칩 사진으로 갈라 같은 회사 카드 4장 중
        # 두 장이 동일 사진이 되는 문제(예: 파두)를 없앤다.
        ("NAND", "낸드"),
        "business_image_6d132f7d0cd45102.jpg",
        "Wikimedia Commons",
    ),
    (
        ("SSD", "스토리지"),
        "business_image_b24ab2723180c79f.jpg",
        "Wikimedia Commons",
    ),
    (("DRAM", "메모리"), "business_image_10774ca82ea41202.jpg", "Wikimedia Commons"),
    (
        # VC·PE·여신전문금융업·신기술사업투자조합 — 전부 예전엔 companies의 sector
        # 텍스트("기타 금융업" 등)까지 내려가 "은행" 이미지 하나로 수렴했다(미래에셋벤처투자
        # 사례). 세그먼트 제목 자체에서 먼저 걸리도록 은행/증권 규칙보다 앞에 둔다.
        # 짧은 "VC"를 단독 키워드로 두면 안 된다 — SEGMENT_EXPLAIN의 PE 설명 캡션 안에
        # "VC보다"라는 문구가 들어있어, PE 카드가 이 규칙에 먼저 걸려 VC 이미지를 받는
        # 자기 충돌이 있었다(PE와 동일하게 "VC부문" 단위로만 매칭).
        ("VC부문", "VC 부문", "벤처캐피탈", "벤처투자조합", "벤처투자"),
        "business_image_ceca6180c78be87d.jpg",
        "Wikimedia Commons",
    ),
    (
        ("PE부문", "PE 부문", "사모펀드", "프라이빗에쿼티", "바이아웃", "구조조정투자"),
        "business_image_6967bb0f468d4e39.jpg",
        "Wikimedia Commons",
    ),
    (
        ("신기술사업투자조합", "신기술조합", "신기술금융", "신기술투자조합"),
        "business_image_6ac978585d526517.jpg",
        "Wikimedia Commons",
    ),
    (
        ("여신전문금융업", "할부금융", "시설대여", "리스업", "신기술사업금융업"),
        "business_image_10d17beeb61d4b0e.jpg",
        "Wikimedia Commons",
    ),
    (
        ("반도체", "웨이퍼", "Foundry", "파운드리", "Probe", "검사장치"),
        "business_image_63ecaf002e77f353.jpg",
        "Wikimedia Commons",
    ),
    (
        ("OLED", "디스플레이", "패널"),
        "business_image_d41fecd0a3904c17.jpg",
        "Wikimedia Commons",
    ),
    (
        ("스마트폰", "Galaxy", "TV", "모니터", "생활가전", "네트워크시스템"),
        "business_image_141eab6519656e30.jpg",
        "Wikimedia Commons",
    ),
    (
        ("디지털 콕핏", "카오디오", "포터블 스피커", "Harman"),
        "business_image_8b1b40ffeb79bd60.jpg",
        "Wikimedia Commons",
    ),
    (
        ("자동차", "완성차", "전기차", "하이브리드", "모빌리티"),
        "business_image_3918919e2e6dfce9.avif",
        "Unsplash",
    ),
    (
        ("전장부품", "자동차부품", "차량 전장"),
        "business_image_e310d326cafd0fb3.jpg",
        "Wikimedia Commons",
    ),
    (
        ("배터리", "2차전지", "양극재", "음극재", "전해액"),
        "business_image_d2545c8e29d092d8.avif",
        "Unsplash",
    ),
    (
        ("조선", "선박", "LNG", "해양", "플랜트"),
        "business_image_5184e050831a4460.avif",
        "Unsplash",
    ),
    (
        ("FM", "PM", "시설관리", "자산관리", "부동산 시설", "건물관리"),
        "business_image_d205f8d7b04d385e.avif",
        "Unsplash",
    ),
    (
        ("보안", "시큐리티", "경비", "출동", "통합보안", "보안SI"),
        "business_image_281a9ea62f3d74e6.avif",
        "Unsplash",
    ),
    (
        ("물류", "배송", "택배", "창고", "운송"),
        "business_image_3078a83d5189713b.avif",
        "Unsplash",
    ),
    (
        ("할인점", "트레이더스", "이마트", "소매", "유통", "마트", "슈퍼", "편의점"),
        "business_image_33f95df49fba7bd7.jpg",
        "Wikimedia Commons",
    ),
    (
        ("스타벅스", "커피", "음료", "식음료", "외식", "푸드"),
        "business_image_c346f28a524bc889.avif",
        "Unsplash",
    ),
    (
        ("온라인", "SSG", "이커머스", "커머스", "플랫폼"),
        "business_image_c346f28a524bc889.avif",
        "Unsplash",
    ),
    (
        ("호텔", "리조트", "객실", "레저", "여행"),
        "business_image_d205f8d7b04d385e.avif",
        "Unsplash",
    ),
    (
        ("항공", "엔진", "우주", "방산", "미사일", "레이더"),
        "business_image_1805fba8159acac6.avif",
        "Unsplash",
    ),
    (
        ("은행", "대출", "예금", "금융"),
        "business_image_6d251c6de8f8e995.jpg",
        "Wikimedia Commons",
    ),
    (
        ("증권", "브로커리지", "투자", "운용"),
        "business_image_c1540b930934e19f.avif",
        "Unsplash",
    ),
    (
        ("보험", "손해보험", "생명보험", "보장"),
        "business_image_837140a1a79dbc33.jpg",
        "Wikimedia Commons",
    ),
    (
        ("바이오", "의약품", "제약", "CDMO", "임상", "백신"),
        "business_image_88477d76a420ca8a.avif",
        "Unsplash",
    ),
    (
        ("화학", "소재", "정유", "철강", "금속", "원재료"),
        "business_image_c5e03278f3aee100.jpg",
        "Wikimedia Commons",
    ),
    (
        ("전력", "발전", "송전", "전선", "OPGW", "케이블"),
        "business_image_93b560bdbc084531.jpg",
        "Wikimedia Commons",
    ),
    (
        ("통신", "광케이블", "광섬유", "네트워크", "무선"),
        "business_image_ca24250faeb63812.avif",
        "Unsplash",
    ),
    (
        ("게임", "콘텐츠", "미디어", "광고"),
        "business_image_7a64e307a92ba431.avif",
        "Unsplash",
    ),
    (
        ("식품", "담배", "화장품", "생활"),
        "business_image_c346f28a524bc889.avif",
        "Unsplash",
    ),
]


KIND_IMAGE: dict[str, tuple[str, str]] = {
    "bank": ("business_image_6d251c6de8f8e995.jpg", "Wikimedia Commons"),
    "securities": ("business_image_c1540b930934e19f.avif", "Unsplash"),
    "insurance": ("business_image_837140a1a79dbc33.jpg", "Wikimedia Commons"),
    "chip": ("business_image_63ecaf002e77f353.jpg", "Wikimedia Commons"),
    "battery": ("business_image_d2545c8e29d092d8.avif", "Unsplash"),
    "auto": ("business_image_3918919e2e6dfce9.avif", "Unsplash"),
    "ship": ("business_image_5184e050831a4460.avif", "Unsplash"),
    "bio": ("business_image_88477d76a420ca8a.avif", "Unsplash"),
    "display": ("business_image_d41fecd0a3904c17.jpg", "Wikimedia Commons"),
    "telecom": ("business_image_ca24250faeb63812.avif", "Unsplash"),
    "power": ("business_image_93b560bdbc084531.jpg", "Wikimedia Commons"),
    "platform": ("business_image_c346f28a524bc889.avif", "Unsplash"),
    "material": ("business_image_c5e03278f3aee100.jpg", "Wikimedia Commons"),
    "consumer": ("business_image_c346f28a524bc889.avif", "Unsplash"),
    "service": ("business_image_d205f8d7b04d385e.avif", "Unsplash"),
}


BAD_TITLE_PARTS = (
    "기타부문",
    "기타 사업",
    "기타",
    "주요 사업",
    "사업",
    "서비스",
    "제품",
    "내부거래",
    "금융보증계약",
    "계약자산",
    "매출채권",
    "리스부채",
    "사용권자산",
    "영업부문",
    "보고부문",
    "연결조정",
    "조정",
)

CUSTOMER_LIST_PARTS = (
    "삼성전자, SK하이닉스",
    "삼성전자",
    "SK하이닉스",
    "삼성디스플레이",
    "윈팩",
    "LG전자",
    "현대차",
    "기아",
    "Apple",
    "NVIDIA",
    "TSMC",
    "Micron",
    "Intel",
    "Qualcomm",
)


# 세그먼트 제목이 이 키워드 중 하나를 포함하면, 그 캡션을 "무엇인지 + 무엇으로
# 돈을 버는지" 설명으로 항상 덮어쓴다. VC/PE/신기술사업투자조합/여신전문금융업 같은
# 업종 용어는 사업보고서 원문 desc가 있어도("사업보고서상 주요 사업부문" 등) 초보
# 투자자에게는 뜻 자체가 안 와닿아서, 원문 유무와 무관하게 항상 설명으로 교체한다.
SEGMENT_EXPLAIN: list[tuple[tuple[str, ...], str]] = [
    (
        ("VC부문", "벤처캐피탈", "벤처투자조합", "창업투자"),
        "VC(벤처캐피탈)는 성장 가능성이 큰 스타트업·벤처기업의 지분을 사들이는 사업입니다. "
        "투자한 기업이 커져서 상장하거나 다른 곳에 팔릴 때 지분을 되팔아 남기는 차익이 주 수익원입니다.",
    ),
    (
        ("PE부문", "PE 부문", "사모펀드", "프라이빗에쿼티", "바이아웃", "구조조정투자"),
        "PE(사모펀드)는 비상장 기업이나 회사 지분을 인수해 경영을 개선한 뒤 되팔아 차익을 남기는 사업입니다. "
        "VC보다 더 자리잡은 기업을, 더 큰 금액으로 다루는 경우가 많습니다.",
    ),
    (
        ("신기술사업투자조합", "신기술조합", "신기술투자조합", "신기술금융"),
        "신기술사업투자조합은 여러 투자자의 자금을 모아 신기술을 가진 기업에 투자하는 조합입니다. "
        "조합이 투자한 기업의 가치가 오르면 지분을 팔아 조합원들이 수익을 나눠 갖습니다.",
    ),
    (
        ("여신전문금융업", "할부금융", "시설대여업", "리스업", "신기술사업금융업"),
        "여신전문금융업은 금융당국 인가를 받아 대출·할부금융·리스(시설대여) 등을 제공하는 사업입니다. "
        "빌려준 돈에 붙는 이자와 수수료가 주 수익원입니다.",
    ),
]


def explain_segment_caption(title: str) -> str | None:
    text = _text(title)
    for words, explain in SEGMENT_EXPLAIN:
        if any(word in text for word in words):
            return explain
    return None


_DEDUPE_SUFFIXES = ("사업부문", "사업부", "부문", "사업")


def _core_title(title: str) -> str:
    # "SSD"와 "SSD사업"처럼 접미사만 다른 사실상 동일한 제목을 같은 키로 묶기 위한 정규화.
    t = _text(title)
    for suf in _DEDUPE_SUFFIXES:
        if t.endswith(suf) and len(t) > len(suf):
            return t[: -len(suf)].strip()
    return t


def dedupe_by_title(
    items: list[dict[str, Any]], *, title_key: str, desc_key: str
) -> list[dict[str, Any]]:
    """이름만 다르고 내용이 같은 항목(예: "SSD" / "SSD사업")을 하나로 합친다.

    구분해도 사용자에게 실익이 없는 카드(같은 이미지, 같은 사업)가 두 번 나오는
    문제(예: 파두)를 근본적으로 줄인다. 짧은 제목·더 긴 설명을 우선한다.
    """
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in items:
        title = _text(item.get(title_key))
        core = _core_title(title)
        if not core:
            continue
        key = core.lower()
        if key not in merged:
            merged[key] = dict(item)
            order.append(key)
            continue
        existing = merged[key]
        if len(title) < len(_text(existing.get(title_key))):
            existing[title_key] = item.get(title_key)
        if len(_text(item.get(desc_key))) > len(_text(existing.get(desc_key))):
            existing[desc_key] = item.get(desc_key)
        # 둘 중 하나라도 실제 매출비중 수치가 있으면 보존한다(segment_breakdown 전용 필드).
        if (
            existing.get("revenue_share") is None
            and item.get("revenue_share") is not None
        ):
            existing["revenue_share"] = item.get("revenue_share")
    return [merged[k] for k in order]


COMPANY_OVERRIDES: dict[str, list[dict[str, str]]] = {
    "012750": [
        {
            "title": "시큐리티",
            "caption": "출동경비, 영상보안, 디지털 보안 서비스를 제공합니다.",
            "kind": "service",
            "visual": "SECURITY",
        },
        {
            "title": "인프라 서비스",
            "caption": "건물 시설관리(FM)와 자산관리(PM)로 부동산 운영을 돕습니다.",
            "kind": "service",
            "visual": "FM/PM",
        },
        {
            "title": "보안SI",
            "caption": "기업·시설에 필요한 통합보안 시스템을 구축합니다.",
            "kind": "service",
            "visual": "SI",
        },
    ],
    "139480": [
        {
            "title": "할인점",
            "caption": "이마트 점포를 중심으로 식품·생활용품을 판매합니다.",
            "kind": "consumer",
            "visual": "MART",
        },
        {
            "title": "트레이더스",
            "caption": "창고형 매장으로 대용량 상품과 자체 브랜드를 판매합니다.",
            "kind": "consumer",
            "visual": "TRADERS",
        },
        {
            "title": "전문점·푸드",
            "caption": "노브랜드, 스타벅스 등 연결 자회사의 유통·식음료 사업이 포함됩니다.",
            "kind": "consumer",
            "visual": "FOOD",
        },
        {
            "title": "온라인·물류",
            "caption": "SSG 등 온라인 판매와 물류 역량이 오프라인 유통을 보완합니다.",
            "kind": "platform",
            "visual": "ONLINE",
        },
    ],
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _image_path(filename: str) -> str:
    return IMG + filename


def is_bad_card(card: dict[str, Any]) -> bool:
    title = _text(card.get("title"))
    caption = _text(card.get("caption"))
    combined = f"{title} {caption}"
    if not title:
        return True
    # BAD_TITLE_PARTS는 순수 substring이 아니라 접두/접미 일치로 본다 — "사업"·"제품"·"서비스"
    # 처럼 짧고 흔한 항목을 순수 포함으로 걸면 "신기술사업투자조합"(가운데에 "사업"이 있을
    # 뿐인 정상 세그먼트)처럼 특정 업종 용어가 통째로 카드에서 사라진다.
    if any(
        title == part or title.startswith(part) or title.endswith(part)
        for part in BAD_TITLE_PARTS
    ):
        return True
    if any(part in combined for part in CUSTOMER_LIST_PARTS):
        return True
    if re.fullmatch(r"[\d.,%()/*\- ]+", title):
        return True
    return False


def choose_image(card: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str]:
    card_text = " ".join(
        [
            _text(card.get("title")),
            _text(card.get("caption")),
            _text(card.get("visual")),
        ]
    )
    lower = card_text.lower()
    for words, filename, source in IMAGE_RULES:
        if any(word.lower() in lower for word in words):
            return _image_path(filename), source
    sector_text = f"{_text(payload.get('sector'))} {_text(payload.get('display_category'))}".lower()
    for words, filename, source in IMAGE_RULES:
        if any(word.lower() in sector_text for word in words):
            return _image_path(filename), source
    kind = _text(card.get("kind"))
    filename, source = KIND_IMAGE.get(kind, KIND_IMAGE["service"])
    return _image_path(filename), source


def attach_images(
    cards: list[dict[str, Any]], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for card in cards:
        clean = dict(card)
        image, source = choose_image(clean, payload)
        clean["image"] = image
        clean["image_source"] = source
        result.append(clean)
    return result


def fallback_cards(payload: dict[str, Any]) -> list[dict[str, str]]:
    sector = _text(payload.get("sector") or payload.get("display_category"))
    if "소매" in sector or "유통" in sector:
        return COMPANY_OVERRIDES["139480"]
    if "경비" in sector or "경호" in sector or "보안" in sector:
        return COMPANY_OVERRIDES["012750"]
    if "금융" in sector or "은행" in sector:
        return [
            {
                "title": "금융 서비스",
                "caption": "예금, 대출, 수수료 등 금융 서비스를 제공합니다.",
                "kind": "bank",
                "visual": "BANK",
            },
            {
                "title": "투자·운용",
                "caption": "자산 운용과 투자 수익이 실적에 영향을 줍니다.",
                "kind": "securities",
                "visual": "AUM",
            },
        ]
    if "반도체" in sector:
        return [
            {
                "title": "반도체",
                "caption": "메모리, 시스템반도체, 장비·소재 관련 사업을 봅니다.",
                "kind": "chip",
                "visual": "CHIP",
            },
            {
                "title": "부품·소재",
                "caption": "공정에 투입되는 부품과 소재가 실적에 영향을 줍니다.",
                "kind": "chip",
                "visual": "PARTS",
            },
        ]
    fallback_title = sector if sector else "핵심 서비스"
    return [
        {
            "title": fallback_title,
            "caption": f"{fallback_title}을 중심으로 매출을 만듭니다.",
            "kind": "service",
            "visual": "BUSINESS",
        }
    ]


def normalize_business_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(payload)
    ticker = str(data.get("stock_code") or "").zfill(6)
    if ticker in COMPANY_OVERRIDES:
        cards = [dict(card) for card in COMPANY_OVERRIDES[ticker]]
    else:
        cards = [
            dict(card)
            for card in data.get("business_cards", [])
            if isinstance(card, dict) and not is_bad_card(card)
        ]
        if len(cards) < 2:
            cards = cards + [
                dict(card)
                for card in fallback_cards(data)
                if card.get("title") not in {c.get("title") for c in cards}
            ]
    cards = dedupe_by_title(cards, title_key="title", desc_key="caption")
    for card in cards:
        explain = explain_segment_caption(card.get("title"))
        if explain:
            card["caption"] = explain
    data["business_cards"] = attach_images(cards[:4], data)

    snippets = data.get("snippets")
    if isinstance(snippets, dict):
        breakdown = [
            seg
            for seg in snippets.get("segment_breakdown", [])
            if isinstance(seg, dict)
            and not any(part in _text(seg.get("name")) for part in BAD_TITLE_PARTS)
        ]
        breakdown = dedupe_by_title(breakdown, title_key="name", desc_key="desc")
        for seg in breakdown:
            explain = explain_segment_caption(seg.get("name"))
            if explain:
                seg["desc"] = explain
        snippets["segment_breakdown"] = breakdown
        if ticker == "139480":
            snippets["overview"] = (
                "이마트는 할인점과 트레이더스 같은 오프라인 유통, 전문점·푸드, "
                "온라인·물류를 함께 운영하는 종합소매 기업입니다."
            )
            snippets["investor_note"] = snippets["overview"]
        if ticker == "012750":
            snippets["overview"] = (
                "에스원은 출동경비와 디지털 보안, 건물 시설관리(FM)·자산관리(PM), "
                "보안SI를 함께 제공하는 보안·인프라 서비스 기업입니다."
            )
            snippets["investor_note"] = snippets["overview"]

    return data
