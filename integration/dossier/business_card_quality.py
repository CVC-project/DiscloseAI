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
    "B2B전자결제",
    "제품매출",
    "테스트 매출",
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

GENERIC_PRODUCT_PARTS = (
    "기타",
    "기타부문",
    "기타 제품",
    "사업보고서상",
    "주요 사업부문",
    "고객사",
    "거래처",
)

PRODUCT_KIND_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("Si-Parts", "SiC-Parts", "Electrode", "Ring", "반도체", "웨이퍼", "식각"),
        "chip",
        "CHIP",
    ),
    (("DRAM", "NAND", "HBM", "SSD", "메모리"), "chip", "MEMORY"),
    (("OLED", "디스플레이", "패널"), "display", "OLED"),
    (("배터리", "전지", "양극재", "음극재", "전해액"), "battery", "BATTERY"),
    (("자동차", "완성차", "전기차", "하이브리드", "부품"), "auto", "AUTO"),
    (("선박", "LNG", "해양", "플랜트", "엔진"), "ship", "SHIP"),
    (("은행", "대출", "예금"), "bank", "BANK"),
    (("증권", "투자", "운용", "자산관리"), "securities", "AUM"),
    (("보험", "보장", "손해보험", "생명보험"), "insurance", "INS"),
    (("바이오", "제약", "CDMO", "임상", "백신"), "bio", "BIO"),
    (("통신", "네트워크", "광케이블", "무선"), "telecom", "NET"),
    (("전력", "발전", "송전", "케이블", "OPGW"), "power", "POWER"),
    (("게임", "플랫폼", "콘텐츠", "광고"), "platform", "APP"),
    (("소재", "화학", "정유", "철강", "금속"), "material", "MAT"),
]


COMPANY_OVERRIDES: dict[str, list[dict[str, str]]] = {
    "000440": [
        {

            "title": "유류판매",

            "caption": "주유소와 대리점 채널을 통해 일반유·LPG 등 에너지 제품을 판매합니다.",

            "kind": "material",

            "visual": "OIL",

        },
        {

            "title": "부대 용역",

            "caption": "유류 판매와 함께 발생하는 부대 서비스 수익을 더합니다.",

            "kind": "service",

            "visual": "SERVICE",

        },
        {

            "title": "부동산 임대",

            "caption": "보유 지점 부동산 임대수익이 보조 수익원으로 붙습니다.",

            "kind": "service",

            "visual": "RENT",

        },
        {

            "title": "태양광 발전",

            "caption": "종속회사를 통해 태양광 전기발전 사업도 함께 운영합니다.",

            "kind": "power",

            "visual": "SOLAR",

        },
    ],
    "012790": [
        {

            "title": "의약품 제조",

            "caption": "일반·전문·동물용 의약품과 위탁생산 제품을 다품종으로 만듭니다.",

            "kind": "bio",

            "visual": "PHARMA",

        },
        {

            "title": "기능성 화장품",

            "caption": "제약 기술을 바탕으로 팜트리 브랜드 화장품을 판매합니다.",

            "kind": "consumer",

            "visual": "COSMETIC",

        },
        {

            "title": "건강기능식품",

            "caption": "비타민 등 건강기능식품이 의약품 외 제품군을 보완합니다.",

            "kind": "consumer",

            "visual": "HEALTH",

        },
        {

            "title": "의약외품",

            "caption": "마스크 등 생활 방역·위생 관련 제품을 함께 취급합니다.",

            "kind": "bio",

            "visual": "MED",

        },
    ],
    "166090": [
        {
            "title": "Si-Parts",
            "caption": "반도체 전공정 중 에칭(식각) 장비 안에서 웨이퍼를 깎는 데 쓰이는 실리콘 소모성 부품입니다.",
            "kind": "chip",
            "visual": "Si",
        },
        {
            "title": "SiC-Parts",
            "caption": "고온·플라즈마 환경을 견디는 실리콘카바이드 부품으로, 식각 공정 장비의 소모품 성격이 큽니다.",
            "kind": "chip",
            "visual": "SiC",
        },
        {
            "title": "Electrode·Ring",
            "caption": "전극과 링처럼 반도체 식각 장비에 반복 투입되는 부품을 고객 주문에 맞춰 공급합니다.",
            "kind": "chip",
            "visual": "PARTS",
        },
    ],
    "067310": [
        {
            "title": "반도체 패키징·테스트",
            "caption": "반도체 칩을 제품으로 쓸 수 있게 포장하고 검사하는 후공정 서비스입니다.",
            "kind": "chip",
            "visual": "PKG",
        },
        {
            "title": "반도체 재료·Si-Parts",
            "caption": "식각 장비에 들어가는 실리콘·실리콘카바이드 소모성 부품을 공급합니다.",
            "kind": "chip",
            "visual": "Si",
        },
        {
            "title": "반도체 공정소모품",
            "caption": "고객사의 공정 장비에서 반복 교체되는 부품이라 설비투자와 가동률 영향을 받습니다.",
            "kind": "chip",
            "visual": "PARTS",
        },
    ],
    "131290": [
        {
            "title": "Probe Card",
            "caption": "웨이퍼 위 반도체 칩이 정상 작동하는지 검사할 때 쓰는 핵심 테스트 부품입니다.",
            "kind": "chip",
            "visual": "PROBE",
        },
        {
            "title": "Interface Board",
            "caption": "검사장비와 반도체 칩 사이의 신호를 연결해주는 테스트용 기판입니다.",
            "kind": "chip",
            "visual": "BOARD",
        },
        {
            "title": "Contact Probe",
            "caption": "칩과 검사장비를 전기적으로 접촉시켜 불량 여부를 확인하는 미세 접촉 부품입니다.",
            "kind": "chip",
            "visual": "PROBE",
        },
        {
            "title": "Interposer",
            "caption": "고성능 반도체 테스트 과정에서 신호 전달을 보조하는 정밀 부품입니다.",
            "kind": "chip",
            "visual": "TEST",
        },
    ],
    "003030": [
        {

            "title": "강관 계열사",

            "caption": "세아제강 등 강관 사업 계열의 실적과 배당 흐름을 함께 보는 지주회사입니다.",

            "kind": "material",

            "visual": "PIPE",

        },
        {

            "title": "지주·투자",

            "caption": "자회사 지분가치와 배당수익이 기업가치의 중심입니다.",

            "kind": "securities",

            "visual": "HOLD",

        },
    ],
    "011150": [
        {

            "title": "수산가공식품",

            "caption": "어묵·맛살 등 수산가공 제품 판매가 핵심입니다.",

            "kind": "consumer",

            "visual": "FOOD",

        },
        {

            "title": "식품 유통",

            "caption": "대형 유통채널과 식품 고객사 공급망이 매출에 연결됩니다.",

            "kind": "consumer",

            "visual": "RETAIL",

        },
    ],
    "093050": [
        {

            "title": "패션 브랜드",

            "caption": "의류와 잡화 브랜드 판매가 핵심 사업입니다.",

            "kind": "consumer",

            "visual": "FASHION",

        },
        {

            "title": "유통 채널",

            "caption": "오프라인 매장과 온라인몰을 함께 운영합니다.",

            "kind": "platform",

            "visual": "ONLINE",

        },
    ],
    "106190": [
        {

            "title": "원료의약품",

            "caption": "의약품 생산에 쓰이는 원료의약품을 제조·판매합니다.",

            "kind": "bio",

            "visual": "API",

        },
        {

            "title": "제약 소재",

            "caption": "고객 제약사의 생산 계획과 수출 수요가 실적에 연결됩니다.",

            "kind": "bio",

            "visual": "PHARMA",

        },
    ],
    "153890": [
        {

            "title": "전기전자 부품",

            "caption": "전자제품 제조에 들어가는 부품을 공급합니다.",

            "kind": "service",

            "visual": "PARTS",

        },
        {

            "title": "부품 제조",

            "caption": "고객사 생산량과 제품 교체 수요가 매출에 영향을 줍니다.",

            "kind": "service",

            "visual": "MFG",

        },
    ],
    "253450": [
        {

            "title": "드라마 제작",

            "caption": "방송·OTT용 드라마 콘텐츠를 기획하고 제작합니다.",

            "kind": "platform",

            "visual": "CONTENT",

        },
        {

            "title": "콘텐츠 유통",

            "caption": "방영권·판권·해외 판매가 매출에 연결됩니다.",

            "kind": "platform",

            "visual": "IP",

        },
    ],
    "365660": [
        {

            "title": "모바일 헬스케어",

            "caption": "병원·환자용 모바일 서비스를 제공하는 헬스케어 플랫폼입니다.",

            "kind": "platform",

            "visual": "HEALTH",

        },
        {

            "title": "의료 데이터 서비스",

            "caption": "병원 시스템과 환자 서비스를 연결하는 디지털 솔루션을 운영합니다.",

            "kind": "platform",

            "visual": "DATA",

        },
    ],
    "387690": [
        {

            "title": "의료·전자 부품",

            "caption": "의료기기와 전자제품에 쓰이는 부품·장비를 공급합니다.",

            "kind": "service",

            "visual": "MED",

        },
        {

            "title": "정밀 장비",

            "caption": "고객사 제품 개발과 생산 일정에 맞춰 장비·부품 매출이 발생합니다.",

            "kind": "service",

            "visual": "EQUIP",

        },
    ],
    "439960": [
        {

            "title": "로봇 제품",

            "caption": "산업 현장과 서비스 영역에 쓰이는 로봇 제품을 개발합니다.",

            "kind": "service",

            "visual": "ROBOT",

        },
        {

            "title": "자동화 솔루션",

            "caption": "공장·물류 자동화 수요가 사업 확장에 연결됩니다.",

            "kind": "service",

            "visual": "AUTO",

        },
    ],
    "466100": [
        {

            "title": "로봇 소프트웨어",

            "caption": "로봇을 움직이고 관리하는 소프트웨어 플랫폼을 제공합니다.",

            "kind": "platform",

            "visual": "ROBOT",

        },
        {

            "title": "로봇 관제",

            "caption": "여러 로봇을 한 화면에서 운영·관리하는 관제 솔루션이 핵심입니다.",

            "kind": "platform",

            "visual": "CONTROL",

        },
    ],
    "477850": [
        {

            "title": "산업 AI 플랫폼",

            "caption": "제조·산업 데이터를 분석해 설비와 공정 의사결정을 돕는 AI 솔루션입니다.",

            "kind": "platform",

            "visual": "AI",

        },
        {

            "title": "AI 운영 솔루션",

            "caption": "기업이 AI 모델을 배포하고 관리하는 소프트웨어를 제공합니다.",

            "kind": "platform",

            "visual": "MLOPS",

        },
    ],
    "493330": [
        {

            "title": "DI-KIT",

            "caption": "재난·안전 분야에서 쓰이는 탐지·대응 장비 제품입니다.",

            "kind": "service",

            "visual": "SAFETY",

        },
        {

            "title": "안전 장비",

            "caption": "소방·안전 현장의 장비 수요가 매출에 연결됩니다.",

            "kind": "service",

            "visual": "FIRE",

        },
    ],
    "950250": [
        {

            "title": "검사 장비",

            "caption": "산업 현장에서 소재와 부품을 검사하는 장비 사업을 봅니다.",

            "kind": "service",

            "visual": "TEST",

        },
        {

            "title": "장비 솔루션",

            "caption": "고객사 품질관리와 생산 공정에 연결되는 솔루션을 제공합니다.",

            "kind": "service",

            "visual": "EQUIP",

        },
    ],
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
    if "사업보고서상 주요 사업부문" in caption:
        return True
    if caption == "사업보고서의 주요 제품·서비스 문단에서 확인되는 사업입니다.":
        return True
    if any(part == title for part in GENERIC_PRODUCT_PARTS):
        return True
    if re.fullmatch(r"[\d.,%()/*\- ]+", title):
        return True
    return False


def is_good_product_name(name: str) -> bool:
    clean = _text(name).strip(" .,/·")
    if len(clean) < 2 or len(clean) > 32:
        return False
    if any(part in clean for part in CUSTOMER_LIST_PARTS):
        return False
    if any(part == clean or clean.startswith(part + " ") for part in BAD_TITLE_PARTS):
        return False
    if any(part in clean for part in ("매출", "제품매출", "테스트 매출", "제조")):
        return False
    if any(part == clean for part in GENERIC_PRODUCT_PARTS):
        return False
    if re.fullmatch(r"[\d.,%()/*\- ]+", clean):
        return False
    return True


def infer_kind_visual(text: str, sector: str = "") -> tuple[str, str]:
    haystack = f"{text} {sector}"
    for words, kind, visual in PRODUCT_KIND_RULES:
        if any(word.lower() in haystack.lower() for word in words):
            return kind, visual
    return "service", "BUSINESS"


def product_caption(name: str, sector: str, overview: str) -> str:
    if any(word in name for word in ("Si-Parts", "SiC-Parts", "Electrode", "Ring")):
        return "반도체 식각 공정 장비에 들어가는 교체·소모성 부품입니다."
    if any(word in name for word in ("DRAM", "NAND", "HBM", "SSD")):
        return "데이터 저장과 AI 서버 수요에 연결되는 메모리 제품입니다."
    if "OPGW" in name or "광케이블" in name:
        return "전력망과 통신망 인프라에 쓰이는 케이블 제품입니다."
    if "LNG" in name or "선박" in name:
        return "조선·해양 프로젝트 매출을 만드는 핵심 제품군입니다."
    if "보험" in sector:
        return "보험료 수입과 손해율이 실적을 좌우하는 금융 서비스입니다."
    if "금융" in sector or "은행" in sector:
        return "이자이익과 수수료 수익을 만드는 금융 서비스입니다."
    if "반도체" in sector:
        return "반도체 공정과 고객사 투자 흐름에 연결되는 제품입니다."
    if "자동차" in sector:
        return "완성차 생산·판매와 부품 공급망에 연결되는 사업입니다."
    if "전자부품" in sector or "전자제품" in sector:
        return "전자제품과 반도체·디스플레이 생산 과정에 들어가는 부품·장비 사업입니다."
    if "통신" in sector:
        return "통신망 구축과 데이터 전송 인프라에 연결되는 제품·서비스입니다."
    if "소매" in sector or "유통" in sector:
        return "소비자에게 상품을 판매해 매출을 만드는 유통 사업입니다."
    if overview:
        return "사업보고서에서 주요 제품·서비스로 확인되는 항목입니다."
    return f"{name}을 중심으로 매출을 만듭니다."


def cards_from_report_terms(payload: dict[str, Any]) -> list[dict[str, str]]:
    snippets = (
        payload.get("snippets") if isinstance(payload.get("snippets"), dict) else {}
    )
    sector = _text(payload.get("sector") or payload.get("display_category"))
    overview = (
        _text(snippets.get("overview")) + " " + _text(snippets.get("segment_finance"))
    )
    names: list[str] = []
    for product in snippets.get("products", []):
        if isinstance(product, str) and is_good_product_name(product):
            names.append(product.strip())
    for seg in snippets.get("segment_breakdown", []):
        if isinstance(seg, dict):
            name = _text(seg.get("name"))
            desc = _text(seg.get("desc"))
            if is_good_product_name(name):
                names.append(name)
            for token in re.split(r"[,/·ㆍ]", desc):
                token = token.strip()
                if is_good_product_name(token):
                    names.append(token)

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        kind, visual = infer_kind_visual(f"{name} {overview}", sector)
        result.append(
            {
                "title": name,
                "caption": product_caption(name, sector, overview),
                "kind": kind,
                "visual": visual,
            }
        )
        if len(result) >= 4:
            break
    return result


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
    sector_text = (
        f"{_text(payload.get('sector'))} "
        f"{_text(payload.get('display_category'))}"
    ).lower()
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
        report_cards = cards_from_report_terms(data)
        cards = [dict(card) for card in report_cards]
        existing_titles = {c.get("title") for c in cards}
        cards = cards + [
            dict(card)
            for card in data.get("business_cards", [])
            if isinstance(card, dict)
            and not is_bad_card(card)
            if card.get("title") not in existing_titles
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
