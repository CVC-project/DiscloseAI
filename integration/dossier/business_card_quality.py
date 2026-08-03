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
        ("NAND", "SSD", "스토리지"),
        "business_image_b24ab2723180c79f.jpg",
        "Wikimedia Commons",
    ),
    (("DRAM", "메모리"), "business_image_10774ca82ea41202.jpg", "Wikimedia Commons"),
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
    if any(part in title for part in BAD_TITLE_PARTS):
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
    data["business_cards"] = attach_images(cards[:4], data)

    snippets = data.get("snippets")
    if isinstance(snippets, dict):
        snippets["segment_breakdown"] = [
            seg
            for seg in snippets.get("segment_breakdown", [])
            if isinstance(seg, dict)
            and not any(part in _text(seg.get("name")) for part in BAD_TITLE_PARTS)
        ]
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
