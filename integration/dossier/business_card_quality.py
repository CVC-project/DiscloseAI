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
    (
        ("산전", "PRENATAL"),
        "business_image_local_healthcare.svg",
        "Local visual",
    ),
    (
        ("암검사", "암스크린", "CANCER"),
        "business_image_local_pharma.svg",
        "Local visual",
    ),
    (
        ("유전희귀", "희귀유전", "유전체", "GENETIC"),
        "business_image_local_instrument.svg",
        "Local visual",
    ),
    (
        ("건강검진", "검진", "CHECKUP"),
        "business_image_local_medical_device.svg",
        "Local visual",
    ),
    (
        ("면제품", "라면", "당면", "국수", "NOODLE"),
        "business_image_food_noodle.svg",
        "Local visual",
    ),
    (
        ("양념", "소스", "카레", "케찹", "케첩", "마요네즈", "SAUCE"),
        "business_image_food_sauce.svg",
        "Local visual",
    ),
    (
        (
            "농수산",
            "참치",
            "가공식품",
            "간편식",
            "만두",
            "김치",
            "햇반",
            "PACKAGED",
            "CANNED",
        ),
        "business_image_food_packaged.svg",
        "Local visual",
    ),
    (
        ("스낵", "제과", "과자", "비스킷", "쿠키", "SNACK"),
        "business_image_food_snack.svg",
        "Local visual",
    ),
    (
        ("음료", "생수", "먹는샘물", "주스", "BEVERAGE"),
        "business_image_food_beverage.svg",
        "Local visual",
    ),
    (
        ("주류", "소주", "맥주", "막걸리", "와인", "주정", "ALCOHOL"),
        "business_image_local_alcohol.svg",
        "Local visual",
    ),
    (
        ("소재식품", "설탕", "밀가루", "식용유", "원당", "유지", "INGREDIENT"),
        "business_image_food_ingredient.svg",
        "Local visual",
    ),
    (("사료", "축산", "FEED"), "business_image_food_feed.svg", "Local visual"),
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

# A company can legitimately have several cards in the same broad industry.
# Do not render those cards with an identical fallback image: pick the next
# stable local visual when a more specific keyword did not select one.
KIND_IMAGE_VARIANTS: dict[str, list[tuple[str, str]]] = {
    "bank": [
        ("business_image_local_bank.svg", "Local visual"),
        ("business_image_local_card.svg", "Local visual"),
        ("business_image_local_finance_hold.svg", "Local visual"),
    ],
    "securities": [
        ("business_image_local_securities.svg", "Local visual"),
        ("business_image_local_finance_hold.svg", "Local visual"),
        ("business_image_local_cloud.svg", "Local visual"),
    ],
    "insurance": [
        ("business_image_local_insurance.svg", "Local visual"),
        ("business_image_local_healthcare.svg", "Local visual"),
        ("business_image_local_finance_hold.svg", "Local visual"),
    ],
    "chip": [
        ("business_image_local_semiconductor_part.svg", "Local visual"),
        ("business_image_local_semiconductor_pkg.svg", "Local visual"),
        ("business_image_local_silicon_part.svg", "Local visual"),
        ("business_image_local_probe.svg", "Local visual"),
    ],
    "battery": [
        ("business_image_local_battery.svg", "Local visual"),
        ("business_image_local_chemical.svg", "Local visual"),
        ("business_image_local_electrode_ring.svg", "Local visual"),
    ],
    "auto": [
        ("business_image_local_auto_part.svg", "Local visual"),
        ("business_image_local_tire.svg", "Local visual"),
        ("business_image_local_machinery.svg", "Local visual"),
    ],
    "ship": [
        ("business_image_local_ship.svg", "Local visual"),
        ("business_image_local_offshore.svg", "Local visual"),
        ("business_image_local_machinery.svg", "Local visual"),
    ],
    "bio": [
        ("business_image_local_pharma.svg", "Local visual"),
        ("business_image_local_healthcare.svg", "Local visual"),
        ("business_image_local_instrument.svg", "Local visual"),
        ("business_image_local_medical_device.svg", "Local visual"),
    ],
    "display": [
        ("business_image_local_display.svg", "Local visual"),
        ("business_image_local_electronic_part.svg", "Local visual"),
        ("business_image_local_crystal.svg", "Local visual"),
    ],
    "telecom": [
        ("business_image_local_network.svg", "Local visual"),
        ("business_image_local_cable.svg", "Local visual"),
        ("business_image_local_software.svg", "Local visual"),
    ],
    "power": [
        ("business_image_local_power.svg", "Local visual"),
        ("business_image_local_cable.svg", "Local visual"),
        ("business_image_local_safety.svg", "Local visual"),
    ],
    "platform": [
        ("business_image_local_software.svg", "Local visual"),
        ("business_image_local_content.svg", "Local visual"),
        ("business_image_local_cloud.svg", "Local visual"),
    ],
    "material": [
        ("business_image_local_chemical.svg", "Local visual"),
        ("business_image_local_steel.svg", "Local visual"),
        ("business_image_local_rubber.svg", "Local visual"),
    ],
    "consumer": [
        ("business_image_local_convenience.svg", "Local visual"),
        ("business_image_local_cosmetics.svg", "Local visual"),
        ("business_image_local_retail.svg", "Local visual"),
    ],
    "service": [
        ("business_image_local_software.svg", "Local visual"),
        ("business_image_local_mro.svg", "Local visual"),
        ("business_image_local_default_a.svg", "Local visual"),
        ("business_image_local_default_b.svg", "Local visual"),
    ],
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
    "용역기간",
    "판매금액",
    "연구부문",
    "개발부문",
    "연구개발",
    "기술개발",
    "임상시험",
    "전자상거래 활성화",
    "출처:",
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
    (
        ("면제품", "라면", "당면", "국수"),
        "consumer",
        "NOODLE",
    ),
    (
        ("양념", "소스", "카레", "케찹", "케첩", "마요네즈"),
        "consumer",
        "SAUCE",
    ),
    (
        ("농수산", "참치", "가공식품", "간편식", "만두", "김치", "햇반"),
        "consumer",
        "CANNED",
    ),
    (("스낵", "제과", "과자", "비스킷", "쿠키"), "consumer", "SNACK"),
    (("음료", "생수", "먹는샘물", "주스"), "consumer", "BEVERAGE"),
    (("주류", "소주", "맥주", "막걸리", "와인", "주정"), "consumer", "ALCOHOL"),
    (
        ("소재식품", "설탕", "밀가루", "식용유", "원당", "유지"),
        "consumer",
        "INGREDIENT",
    ),
    (("사료", "축산"), "consumer", "FEED"),
    (("소재", "화학", "정유", "철강", "금속"), "material", "MAT"),
]


COMPANY_OVERRIDES: dict[str, list[dict[str, str]]] = {
    "340450": [
        {
            "title": "산전검사",
            "caption": "임신 전·임신 중 유전질환 위험을 확인하는 유전자 검사 서비스입니다.",
            "kind": "bio",
            "visual": "PRENATAL",
        },
        {
            "title": "암검사",
            "caption": "유전체 분석을 바탕으로 암 위험과 관련 변이를 살피는 검사 서비스입니다.",
            "kind": "bio",
            "visual": "CANCER",
        },
        {
            "title": "유전희귀질환 검사",
            "caption": "희귀 유전질환의 원인을 찾기 위해 유전자·유전체를 분석하는 서비스입니다.",
            "kind": "bio",
            "visual": "GENETIC",
        },
        {
            "title": "건강검진",
            "caption": "유전체 정보를 활용해 건강 위험을 살피는 검진 서비스입니다.",
            "kind": "bio",
            "visual": "CHECKUP",
        },
    ],
    "317770": [
        {
            "title": "바이오인식 솔루션",
            "caption": "지문 등록·인증에 쓰이는 스캐너와 인증 디바이스를 공급합니다.",
            "kind": "service",
            "visual": "SECURITY",
        },
        {
            "title": "전자문서 솔루션",
            "caption": "문서 스캔과 전자문서 처리에 필요한 장비·솔루션을 제공합니다.",
            "kind": "service",
            "visual": "DOCUMENT",
        },
    ],
    "446540": [
        {
            "title": "2차전지 충방전용 핀",
            "caption": "배터리 셀의 충전·방전 검사 장비에 들어가는 접촉 부품입니다.",
            "kind": "battery",
            "visual": "BATTERY",
        },
        {
            "title": "반도체 테스트용 핀",
            "caption": "반도체 전기검사 과정에서 칩과 검사 장비를 연결하는 접촉 부품입니다.",
            "kind": "chip",
            "visual": "PROBE",
        },
    ],
    "004370": [
        {
            "title": "라면",
            "caption": "신라면·짜파게티 등 봉지면과 용기면을 제조·판매하는 주력 사업입니다.",
            "kind": "consumer",
            "visual": "NOODLE",
        },
        {
            "title": "스낵",
            "caption": "새우깡·꿀꽈배기 등 과자류를 제조·판매합니다.",
            "kind": "consumer",
            "visual": "SNACK",
        },
        {
            "title": "음료",
            "caption": "백산수 등 생수·음료 제품을 제조·판매합니다.",
            "kind": "consumer",
            "visual": "BEVERAGE",
        },
    ],
    "280360": [
        {
            "title": "제과·스낵",
            "caption": "빼빼로·가나·꼬깔콘 등 과자와 초콜릿 제품을 제조·판매합니다.",
            "kind": "consumer",
            "visual": "SNACK",
        },
        {
            "title": "빙과",
            "caption": "월드콘·설레임 등 아이스크림과 빙과 제품을 제조·판매합니다.",
            "kind": "consumer",
            "visual": "FOOD",
        },
        {
            "title": "유가공·베이커리",
            "caption": "유제품과 빵 등 제과 외 식품 제품군을 함께 운영합니다.",
            "kind": "consumer",
            "visual": "FOOD",
        },
    ],
    "007310": [
        {
            "title": "면제품류",
            "caption": "라면, 당면, 국수처럼 오뚜기의 대표적인 면류 제품을 제조·판매합니다.",
            "kind": "consumer",
            "visual": "NOODLE",
        },
        {
            "title": "양념소스류",
            "caption": "카레, 케첩, 마요네즈, 소스류처럼 가정식 조리에 쓰이는 제품군입니다.",
            "kind": "consumer",
            "visual": "SAUCE",
        },
        {
            "title": "농수산가공품류",
            "caption": "참치캔과 즉석식품 등 저장·간편식 수요에 연결되는 가공식품입니다.",
            "kind": "consumer",
            "visual": "CANNED",
        },
    ],
    "097950": [
        {
            "title": "식품사업",
            "caption": "햇반, 만두, 김치, 간편식 등 국내외 소비자 식품 브랜드가 주력입니다.",
            "kind": "consumer",
            "visual": "FOOD",
        },
        {
            "title": "소재식품",
            "caption": "설탕, 밀가루, 식용유 등 식품 제조와 외식 원가에 연결되는 기초 식품 소재를 공급합니다.",
            "kind": "consumer",
            "visual": "INGREDIENT",
        },
        {
            "title": "바이오·FNT",
            "caption": "아미노산, 조미소재, 영양 소재처럼 글로벌 식품·사료 산업에 쓰이는 바이오 소재를 판매합니다.",
            "kind": "bio",
            "visual": "BIO",
        },
        {
            "title": "사료·축산",
            "caption": "사료와 축산 사업은 곡물 가격과 글로벌 축산 수요 영향을 함께 받습니다.",
            "kind": "consumer",
            "visual": "FEED",
        },
    ],
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
            "caption": "반도체 칩을 조립하고 전기적으로 검사하는 후공정 서비스를 제공합니다.",
            "kind": "chip",
            "visual": "PKG",
        },
        {
            "title": "반도체 소재·소모품",
            "caption": "식각 장비에 쓰이는 Si-Parts·SiC-Parts 같은 교체형 공정 부품을 공급합니다.",
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
    if any(part in clean for part in ("매출", "제품매출", "테스트 매출")):
        return False
    if clean == "제조":
        return False
    if clean in {"용역", "제품외", "상품외", "제조외", "임대외", "투자외"}:
        return False
    if any(part == clean for part in GENERIC_PRODUCT_PARTS):
        return False
    if re.fullmatch(r"제?\s*\d+\s*기", clean):
        return False
    if clean in {"비고", "품목", "구분", "분류", "내용", "번호", "합계", "총계"}:
        return False
    if re.fullmatch(r"[\d.,%()/*\- ]+", clean):
        return False
    return True


FOOD_CATEGORY_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (("국내식품제조유통",), "국내 식품", "consumer", "FOOD"),
    (("해외식품제조유통",), "해외 식품", "consumer", "FOOD"),
    (("건강케어",), "건강기능식품", "consumer", "HEALTH"),
    (("식품서비스유통",), "급식·외식", "consumer", "FOOD"),
    (("면스낵",), "라면·스낵", "consumer", "NOODLE"),
    (
        ("라면", "탕면", "사발면", "볶음면", "짜파게티", "너구리", "면제품"),
        "라면",
        "consumer",
        "NOODLE",
    ),
    (
        (
            "스낵",
            "제과",
            "과자",
            "비스킷",
            "쿠키",
            "크래커",
            "초코파이",
            "새우깡",
            "꿀꽈배기",
        ),
        "스낵·제과",
        "consumer",
        "SNACK",
    ),
    (
        ("음료", "생수", "먹는샘물", "주스", "사이다", "콜라", "백산수"),
        "음료",
        "consumer",
        "BEVERAGE",
    ),
    (
        (
            "소주",
            "맥주",
            "막걸리",
            "약주",
            "탁주",
            "청주",
            "와인",
            "주정",
            "에탄올",
            "복분자",
            "위스키",
        ),
        "주류",
        "consumer",
        "ALCOHOL",
    ),
    (
        (
            "건강기능식품",
            "건강식품",
            "오메가",
            "유산균",
            "프로바이오틱스",
            "콜라겐",
            "콘드로이친",
        ),
        "건강기능식품",
        "consumer",
        "HEALTH",
    ),
    (("사료", "프리믹스", "사료첨가제"), "사료", "consumer", "FEED"),
    (
        ("축산", "양돈", "양계", "가금", "육가공", "돼지고기", "닭고기"),
        "축산·육가공",
        "consumer",
        "FEED",
    ),
    (("펫푸드", "반려동물", "PET부문"), "펫푸드", "consumer", "FEED"),
    (
        ("소스", "카레", "케찹", "케첩", "마요네즈", "조미", "장류", "간장"),
        "양념·소스",
        "consumer",
        "SAUCE",
    ),
    (
        ("간편식", "즉석식품", "냉동식품", "냉동", "가공식품", "도시락"),
        "가공식품·간편식",
        "consumer",
        "CANNED",
    ),
    (
        ("설탕", "밀가루", "식용유", "전분당", "소재식품", "식품소재"),
        "소재식품",
        "consumer",
        "INGREDIENT",
    ),
    (("빵", "제빵", "베이커리", "냉동생지"), "베이커리", "consumer", "FOOD"),
    (("빙과", "아이스크림"), "빙과", "consumer", "FOOD"),
    (("유제품", "유가공", "우유", "발효유", "치즈"), "유제품", "consumer", "FOOD"),
    (
        ("식품첨가물", "특수효소", "조미액", "카라기난"),
        "식품소재·첨가물",
        "consumer",
        "INGREDIENT",
    ),
    (("급식", "컨세션", "외식", "푸드서비스"), "급식·외식", "consumer", "FOOD"),
    (("식자재", "식품 유통", "식품유통"), "식품유통", "consumer", "FOOD"),
    (
        ("두부", "콩나물", "신선식품", "계란", "액상계란"),
        "신선·가공식품",
        "consumer",
        "FOOD",
    ),
    (("식용색소",), "식품소재·첨가물", "consumer", "INGREDIENT"),
]


# These rules intentionally describe a *business group*, not a customer name,
# a single SKU, or an accounting-table row.  They are applied after the food
# rules and before the raw DART label is used as a final fallback.
BUSINESS_CATEGORY_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (
        ("반도체 패키징", "패키징 및 테스트", "패키지 테스트", "후공정"),
        "반도체 패키징·테스트",
        "chip",
        "CHIP",
    ),
    (
        (
            "Si-Parts",
            "SiC-Parts",
            "Silicon Parts",
            "실리콘부품",
            "웨이퍼",
            "식각부품",
            "반도체 소재",
            "반도체 재료",
            "공정소모품",
        ),
        "반도체 소재·소모품",
        "chip",
        "PARTS",
    ),
    (
        ("반도체 장비", "식각장비", "증착장비", "세정장비", "검사장비", "테스트 장비"),
        "반도체 장비",
        "chip",
        "EQUIP",
    ),
    (("HBM", "DRAM", "NAND", "SSD", "메모리"), "메모리 반도체", "chip", "MEMORY"),
    (
        ("Foundry", "파운드리", "시스템반도체", "모바일AP", "이미지센서"),
        "시스템반도체",
        "chip",
        "CHIP",
    ),
    (("OLED", "디스플레이 패널", "디스플레이"), "디스플레이", "display", "OLED"),
    (("카메라모듈", "카메라 모듈"), "카메라모듈", "chip", "CAM"),
    (("MLCC", "적층세라믹", "콘덴서"), "전자부품", "chip", "MLCC"),
    (("PCB", "인쇄회로기판", "기판"), "전자부품·기판", "chip", "PCB"),
    (("전장", "자동차 전자", "차량용 전자"), "전장부품", "auto", "AUTO"),
    (("완성차", "승용차", "SUV", "상용차"), "완성차", "auto", "AUTO"),
    (("전기차", "하이브리드", "EV"), "전기차·하이브리드", "auto", "EV"),
    (("파워트레인", "엔진", "변속기"), "구동계 부품", "auto", "PARTS"),
    (("배터리 셀", "이차전지 셀", "2차전지 셀"), "배터리 셀", "battery", "CELL"),
    (
        ("양극재", "음극재", "전해액", "분리막", "배터리 소재"),
        "배터리 소재",
        "battery",
        "MATERIAL",
    ),
    (("배터리 장비", "충방전", "전극공정"), "배터리 장비", "battery", "EQUIP"),
    (("의약품", "신약", "원료의약품", "제약"), "의약품", "bio", "PHARMA"),
    (
        ("CDMO", "위탁개발", "위탁생산", "바이오의약품 생산"),
        "바이오의약품 위탁개발·생산",
        "bio",
        "CDMO",
    ),
    (("바이오시밀러",), "바이오시밀러", "bio", "BIO"),
    (("진단", "분자진단", "체외진단"), "진단·분석", "bio", "DIAGNOSTIC"),
    (("의료기기", "의료용 기기", "치과", "임플란트"), "의료기기", "bio", "MEDICAL"),
    (("클라우드", "데이터센터"), "클라우드·데이터센터", "service", "CLOUD"),
    (("보안", "시큐리티", "정보보호", "인증"), "보안 솔루션", "service", "SECURITY"),
    (("시스템통합", "SI", "시스템 구축"), "시스템 구축·통합", "service", "SI"),
    (("소프트웨어", "솔루션", "SaaS"), "소프트웨어·솔루션", "service", "SOFTWARE"),
    (("플랫폼", "커머스", "모빌리티"), "플랫폼 서비스", "platform", "PLATFORM"),
    (("게임", "게임소프트웨어"), "게임", "platform", "GAME"),
    (("은행", "예금", "대출", "여신"), "은행", "bank", "BANK"),
    (("증권", "브로커리지", "위탁매매", "IB"), "증권", "securities", "SECURITIES"),
    (("보험", "보험료", "손해보험", "생명보험"), "보험", "insurance", "INSURANCE"),
    (("자산운용", "펀드", "운용자산"), "자산운용", "securities", "AUM"),
    (("할인점", "마트", "대형마트"), "대형마트", "consumer", "MART"),
    (("백화점", "면세점"), "백화점·면세점", "consumer", "RETAIL"),
    (("온라인몰", "전자상거래", "이커머스"), "온라인 유통", "platform", "ONLINE"),
    (("건축", "건설", "주택"), "건축·주택", "service", "CONSTRUCTION"),
    (("토목", "플랜트"), "토목·플랜트", "service", "CONSTRUCTION"),
    (("태양광", "풍력", "신재생"), "신재생에너지", "power", "RENEWABLE"),
    (("발전", "송전", "변압기", "전력"), "전력기기·발전", "power", "POWER"),
    (("선박", "LNG선", "탱커", "컨테이너선"), "상선", "ship", "SHIP"),
    (("해양플랜트", "해양", "오프쇼어"), "해양·플랜트", "ship", "OFFSHORE"),
    (("특수선", "방산", "항공", "미사일"), "방산·항공", "ship", "DEFENSE"),
    (("정유", "석유화학", "기초화학", "정밀화학"), "화학소재", "material", "CHEMICAL"),
    (("철강", "강관", "철근", "선재"), "철강", "material", "STEEL"),
]


def is_food_business_sector(sector: str) -> bool:
    return any(
        word in sector
        for word in ("식품", "음식료", "음료", "사료", "농수산", "주정", "주류")
    )


def is_immaterial_revenue_share(value: Any) -> bool:
    """Return true below 1%, accepting ratio or percentage storage."""
    try:
        share = float(value)
    except (TypeError, ValueError):
        return False
    return share < (0.01 if 0 <= share <= 1 else 1.0)


def is_redundant_category(title: str, existing: set[str]) -> bool:
    """Avoid a narrow product card after its reported combined segment."""
    tokens = {token.strip() for token in title.split("·") if token.strip()}
    for current in existing:
        current_tokens = {
            token.strip() for token in current.split("·") if token.strip()
        }
        if (
            tokens
            and current_tokens
            and (tokens <= current_tokens or current_tokens <= tokens)
        ):
            return True
    return False


def canonical_business_category(
    name: str, sector: str, context: str = "", *, is_segment: bool = False
) -> tuple[str, str, str] | None:
    """Collapse product and brand names into investor-readable business groups."""
    clean = _text(name).strip(" .,/·")
    if not is_good_product_name(clean):
        return None
    food_sector = is_food_business_sector(sector)
    if food_sector:
        haystack = f"{clean} {context}"
        for keywords, title, kind, visual in FOOD_CATEGORY_RULES:
            if any(keyword.lower() in haystack.lower() for keyword in keywords):
                return title, kind, visual
        if is_segment and any(
            word in clean
            for word in ("골프장", "기계설비", "물류", "포장", "임대", "태양광")
        ):
            segment_title = re.sub(r"\s*(?:사업)?부문$", "", clean).strip()
            kind, visual = infer_kind_visual(f"{segment_title} {context}", sector)
            return segment_title, kind, visual
        # An unmatched food product is usually a brand, table heading, or legal entity.
        return None
    haystack = f"{clean} {context}"
    for keywords, title, kind, visual in BUSINESS_CATEGORY_RULES:
        if any(keyword.lower() in haystack.lower() for keyword in keywords):
            return title, kind, visual
    kind, visual = infer_kind_visual(f"{clean} {context}", sector)
    return clean, kind, visual


def sector_type(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, dict):
        source = " ".join(
            [
                _text(payload.get("sector")),
                _text(payload.get("display_category")),
                _text(payload.get("name")),
            ]
        )
    else:
        source = _text(payload)
    if any(word in source for word in ("금융", "은행", "증권", "보험")):
        return "finance"
    if any(word in source for word in ("식품", "음식료", "농수산", "가공식품", "음료")):
        return "food"
    if any(word in source for word in ("반도체", "전자부품", "정밀기기")):
        return "semiconductor"
    if any(word in source for word in ("소매", "유통", "마트", "백화점")):
        return "retail"
    if any(word in source for word in ("경비", "경호", "보안")):
        return "security"
    return "general"


def card_sector_mismatch(card: dict[str, Any], payload: dict[str, Any]) -> bool:
    combined = f"{_text(card.get('title'))} {_text(card.get('caption'))}"
    stype = sector_type(payload)
    if stype == "food":
        return any(
            word in combined
            for word in (
                "항공",
                "항공기",
                "방산",
                "데이터센터",
                "전력",
                "금융보증",
                "B2B전자결제",
                "신기술사업금융",
                "증권",
                "위탁매매",
                "IB",
            )
        )
    if stype == "semiconductor":
        return any(word in combined for word in ("현금", "B2B전자결제", "금융보증"))
    if stype == "finance":
        return any(
            word in combined
            for word in ("항공", "항공기", "방산", "데이터센터", "식품", "반도체")
        )
    if stype == "retail":
        return any(
            word in combined for word in ("방산", "항공기", "금융보증", "반도체 패키징")
        )
    return False


def infer_kind_visual(text: str, sector: str = "") -> tuple[str, str]:
    haystack = f"{text} {sector}"
    for words, kind, visual in PRODUCT_KIND_RULES:
        if any(word.lower() in haystack.lower() for word in words):
            return kind, visual
    return "service", "BUSINESS"


def product_caption(name: str, sector: str, overview: str) -> str:
    if any(word in name for word in ("면제품", "라면", "당면", "국수")):
        return "라면, 당면, 국수처럼 반복 구매가 많은 면류 제품군입니다."
    if any(
        word in name for word in ("양념", "소스", "카레", "케찹", "케첩", "마요네즈")
    ):
        return "가정식 조리와 외식 수요에 함께 쓰이는 소스·조미 제품군입니다."
    if any(
        word in name
        for word in ("농수산", "참치", "가공식품", "간편식", "만두", "김치", "햇반")
    ):
        return "저장식품과 간편식처럼 소비자 식탁에 바로 닿는 가공식품입니다."
    if any(
        word in name
        for word in ("소재식품", "설탕", "밀가루", "식용유", "원당", "유지")
    ):
        return "다른 식품을 만드는 데 들어가는 기초 소재라 원재료 가격 영향을 받습니다."
    if any(word in name for word in ("사료", "축산", "F&C")):
        return "곡물 가격과 축산 수요에 영향을 받는 사료·축산 사업입니다."
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


def normalize_caption_endings(value: object) -> str:
    """Collapse accidental repeated Korean sentence endings in card copy."""
    text = _text(value)
    return re.sub(
        r"(입니다|합니다|됩니다|있습니다|였습니다)\s*[.!。]?\s*\1(?:\s*[.!。])?",
        r"\1.",
        text,
    )


def cards_from_report_terms(payload: dict[str, Any]) -> list[dict[str, str]]:
    snippets = (
        payload.get("snippets") if isinstance(payload.get("snippets"), dict) else {}
    )
    sector = _text(payload.get("sector") or payload.get("display_category"))
    overview = (
        _text(snippets.get("overview")) + " " + _text(snippets.get("segment_finance"))
    )
    segment_candidates: list[tuple[str, str, bool]] = []
    product_candidates: list[tuple[str, str, bool]] = []
    # The II.2 revenue table is authoritative. Never mix free-text section
    # headings with it: that was the source of false cards like 연구부문.
    product_service_segments = snippets.get("product_service_segments", [])
    source_segments = (
        product_service_segments
        if isinstance(product_service_segments, list) and product_service_segments
        else snippets.get("segment_breakdown", [])
    )
    for seg in source_segments:
        if isinstance(seg, dict):
            name = _text(seg.get("name"))
            desc = _text(seg.get("desc"))
            if is_immaterial_revenue_share(seg.get("revenue_share")):
                continue
            if is_good_product_name(name):
                segment_candidates.append((name, desc, True))
    for product in snippets.get("products", []):
        if isinstance(product, str) and is_good_product_name(product):
            product_candidates.append((product.strip(), "", False))

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidates in (segment_candidates, product_candidates):
        for name, local_context, is_segment in candidates:
            category = canonical_business_category(
                name, sector, local_context, is_segment=is_segment
            )
            if category is None:
                continue
            title, kind, visual = category
            if title in seen or is_redundant_category(title, seen):
                continue
            candidate_card = {
                "title": title,
                "caption": local_context,
                "kind": kind,
                "visual": visual,
            }
            if card_sector_mismatch(candidate_card, payload):
                continue
            seen.add(title)
            caption = (
                local_context
                if local_context and len(local_context) <= 90
                else product_caption(title, sector, overview)
            )
            result.append(
                {
                    "title": title,
                    "caption": caption,
                    "kind": kind,
                    "visual": visual,
                }
            )
            if len(result) >= 4:
                break
        if result:
            break
    return result


def _first_unused_image(
    candidates: list[tuple[str, str]], used_images: set[str]
) -> tuple[str, str]:
    for filename, source in candidates:
        image = _image_path(filename)
        if image not in used_images:
            return image, source
    filename, source = candidates[0]
    return _image_path(filename), source


def choose_image(
    card: dict[str, Any], payload: dict[str, Any], used_images: set[str]
) -> tuple[str, str]:
    card_text = " ".join(
        [
            _text(card.get("title")),
            _text(card.get("caption")),
            _text(card.get("visual")),
        ]
    )
    lower = card_text.lower()
    candidates: list[tuple[str, str]] = []
    for words, filename, source in IMAGE_RULES:
        if any(word.lower() in lower for word in words):
            candidates.append((filename, source))
    sector_text = (
        f"{_text(payload.get('sector'))} " f"{_text(payload.get('display_category'))}"
    ).lower()
    for words, filename, source in IMAGE_RULES:
        if any(word.lower() in sector_text for word in words):
            candidates.append((filename, source))
    kind = _text(card.get("kind"))
    candidates.extend(KIND_IMAGE_VARIANTS.get(kind, []))
    candidates.append(KIND_IMAGE.get(kind, KIND_IMAGE["service"]))
    return _first_unused_image(candidates, used_images)


def attach_images(
    cards: list[dict[str, Any]], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    used_images: set[str] = set()
    for card in cards:
        clean = dict(card)
        image, source = choose_image(clean, payload, used_images)
        clean["image"] = image
        clean["image_source"] = source
        result.append(clean)
        used_images.add(image)
    return result


def fallback_cards(payload: dict[str, Any]) -> list[dict[str, str]]:
    sector = _text(payload.get("sector") or payload.get("display_category"))
    if "식품" in sector or "음식료" in sector or "농수산" in sector:
        return [
            {
                "title": "식품사업",
                "caption": "소비자 식품과 가공식품을 중심으로 매출을 만듭니다.",
                "kind": "consumer",
                "visual": "FOOD",
            },
            {
                "title": "소재식품",
                "caption": "식품 제조에 들어가는 원재료와 소재 제품을 공급합니다.",
                "kind": "consumer",
                "visual": "INGREDIENT",
            },
            {
                "title": "가공식품",
                "caption": "간편식과 저장식품처럼 반복 구매가 많은 제품군입니다.",
                "kind": "consumer",
                "visual": "CANNED",
            },
        ]
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
        sector = _text(data.get("sector") or data.get("display_category"))
        # Do not mix an authoritative report-derived business group with stale
        # cards from a previous heuristic.  The latter was the main source of
        # customer names, accounting labels, and unrelated categories.
        if not report_cards:
            for existing in data.get("business_cards", []):
                if not isinstance(existing, dict) or is_bad_card(existing):
                    continue
                category = canonical_business_category(
                    _text(existing.get("title")), sector, _text(existing.get("caption"))
                )
                if category is None:
                    continue
                title, kind, visual = category
                if title in existing_titles or is_redundant_category(
                    title, existing_titles
                ):
                    continue
                candidate = {
                    "title": title,
                    "caption": product_caption(title, sector, ""),
                    "kind": kind,
                    "visual": visual,
                }
                if card_sector_mismatch(candidate, data):
                    continue
                cards.append(candidate)
                existing_titles.add(title)
        if not cards:
            cards = cards + [
                dict(card)
                for card in fallback_cards(data)
                if card.get("title") not in {c.get("title") for c in cards}
            ]
    for card in cards:
        card["caption"] = normalize_caption_endings(card.get("caption"))
    data["business_cards"] = attach_images(cards[:4], data)

    # The 2025 annual report includes comparative 2024/2023 income-statement
    # values, but the original integrated payload retained only 2025. Keep the
    # report's comparative columns so the business tab does not claim they are
    # unavailable.
    if ticker == "340450":
        latest = (
            data.get("latest_year") if isinstance(data.get("latest_year"), dict) else {}
        )
        history = data.get("history") if isinstance(data.get("history"), list) else []
        by_year = {
            int(item.get("year")): item
            for item in history
            if isinstance(item, dict) and str(item.get("year", "")).isdigit()
        }
        by_year.update(
            {
                2023: {
                    "year": 2023,
                    "revenue": 27292051619,
                    "cogs": 13594981381,
                    "operating_income": 160076955,
                    "net_income": -550095144,
                },
                2024: {
                    "year": 2024,
                    "revenue": 25887798646,
                    "cogs": 14706763974,
                    "operating_income": -1233500726,
                    "net_income": -1256914171,
                },
                2025: latest,
            }
        )
        data["history"] = [by_year[year] for year in sorted(by_year)]
        data["custom_report_ideas"] = [
            {
                "title": "2025년 흑자 전환",
                "value": "매출 315억 · 영업이익 12억",
                "fact": "매출은 2024년 259억원에서 2025년 315억원으로 늘었고, 영업손실 12억원은 영업이익 12억원으로 전환했습니다.",
                "view": "검사 서비스 매출 성장과 본업 수익성 회복이 함께 나타났는지 보는 것이 핵심입니다.",
            },
            {
                "title": "유전체 검사 서비스 구성",
                "value": "암검사 · 산전검사 · 유전희귀질환 · 건강검진",
                "fact": "사업보고서의 주요 제품 및 서비스 표는 네 검사 서비스로 매출을 구분합니다.",
                "view": "단일 제품 판매가 아니라 검사 목적별 서비스 포트폴리오로 매출을 만드는 구조입니다.",
            },
        ]

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
