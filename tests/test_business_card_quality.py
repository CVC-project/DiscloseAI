from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "integration"
    / "dossier"
    / "business_card_quality.py"
)
SPEC = importlib.util.spec_from_file_location("business_card_quality", MODULE_PATH)
assert SPEC and SPEC.loader
QUALITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALITY)


def test_nongshim_override_uses_business_categories() -> None:
    payload = {"stock_code": "004370", "sector": "기타 식품 제조업"}
    result = QUALITY.normalize_business_payload(payload)
    assert [card["title"] for card in result["business_cards"]] == [
        "라면",
        "스낵",
        "음료",
    ]


def test_food_brands_are_collapsed_into_categories() -> None:
    payload = {
        "stock_code": "999999",
        "sector": "기타 식품 제조업",
        "snippets": {
            "products": ["신라면", "안성탕면", "새우깡", "백산수"],
            "segment_breakdown": [],
        },
        "business_cards": [
            {"title": "신라면", "caption": "과거 세부 제품 카드"}
        ],
    }
    result = QUALITY.normalize_business_payload(payload)
    assert [card["title"] for card in result["business_cards"]] == [
        "라면",
        "스낵·제과",
        "음료",
    ]


def test_duplicate_sentence_endings_are_collapsed() -> None:
    assert (
        QUALITY.normalize_caption_endings("유전자 검사 서비스입니다.입니다")
        == "유전자 검사 서비스입니다."
    )


def test_report_segments_take_priority_and_period_headers_are_rejected() -> None:
    payload = {
        "stock_code": "999998",
        "sector": "기타 식품 제조업",
        "snippets": {
            "products": ["제 9기", "제8기", "비스킷"],
            "segment_breakdown": [
                {"name": "제과", "desc": "과자류 제조·판매"},
                {"name": "음료", "desc": "음료 제조·판매"},
            ],
        },
        "business_cards": [],
    }
    result = QUALITY.normalize_business_payload(payload)
    titles = [card["title"] for card in result["business_cards"]]
    assert titles[:2] == ["스낵·제과", "음료"]
    assert "제 9기" not in titles
    assert "제8기" not in titles


def test_revenue_share_accepts_ratio_and_percentage_units() -> None:
    assert QUALITY.is_immaterial_revenue_share(0.001)
    assert not QUALITY.is_immaterial_revenue_share(0.3034)
    assert not QUALITY.is_immaterial_revenue_share(0.5)
    assert not QUALITY.is_immaterial_revenue_share(3.4)


def test_food_segments_with_manufacturing_are_kept_and_brands_do_not_duplicate() -> None:
    payload = {
        "stock_code": "999997",
        "sector": "기타 식품 제조업",
        "snippets": {
            "segment_breakdown": [
                {
                    "name": "국내식품제조유통 부문",
                    "desc": "두부·생면 등 국내 식품 제조·유통",
                    "revenue_share": 0.477,
                },
                {
                    "name": "면스낵",
                    "desc": "라면과 스낵",
                    "revenue_share": 0.4,
                },
            ],
            "products": ["신라면"],
        },
        "business_cards": [],
    }
    result = QUALITY.normalize_business_payload(payload)
    titles = [card["title"] for card in result["business_cards"]]
    assert titles == ["국내 식품", "라면·스낵"]


def test_reported_semiconductor_segments_replace_stale_customer_cards() -> None:
    payload = {
        "stock_code": "999996",
        "sector": "반도체 제조업",
        "snippets": {
            "segment_breakdown": [
                {"name": "반도체 패키징 및 테스트", "desc": "후공정 서비스"},
                {"name": "반도체 재료", "desc": "Si-Parts와 SiC-Parts"},
            ]
        },
        "business_cards": [
            {"title": "삼성전자, SK하이닉스", "caption": "과거 고객사 카드"},
            {"title": "판매금액", "caption": "표 제목"},
        ],
    }
    result = QUALITY.normalize_business_payload(payload)
    assert [card["title"] for card in result["business_cards"]] == [
        "반도체 패키징·테스트",
        "반도체 소재·소모품",
    ]


def test_financial_report_segments_use_financial_business_groups() -> None:
    payload = {
        "stock_code": "999995",
        "sector": "기타 금융업",
        "snippets": {
            "segment_breakdown": [
                {"name": "은행", "desc": "예금과 대출"},
                {"name": "자산운용", "desc": "펀드 운용"},
            ]
        },
        "business_cards": [],
    }
    result = QUALITY.normalize_business_payload(payload)
    assert [card["title"] for card in result["business_cards"]] == [
        "은행",
        "자산운용",
    ]


def test_product_service_table_wins_over_research_and_development_headings() -> None:
    payload = {
        "stock_code": "214450",
        "sector": "의료용 물질 및 의약품 관련제품 제조업",
        "snippets": {
            "segment_breakdown": [
                {"name": "연구부문", "desc": "잘못 추출된 본문 제목"},
                {"name": "개발부문", "desc": "잘못 추출된 본문 제목"},
            ],
            "product_service_segments": [
                {"name": "의약품", "revenue_share": 0.154},
                {"name": "의료기기", "revenue_share": 0.586},
                {"name": "화장품", "revenue_share": 0.246},
            ],
        },
    }
    result = QUALITY.normalize_business_payload(payload)
    assert [card["title"] for card in result["business_cards"]] == [
        "의약품",
        "의료기기",
        "화장품",
    ]


def test_gcg_genome_uses_service_categories_and_comparative_history() -> None:
    result = QUALITY.normalize_business_payload(
        {
            "stock_code": "340450",
            "sector": "자연과학 및 공학 연구개발업",
            "latest_year": {
                "year": 2025,
                "revenue": 31533860809,
                "operating_income": 1235615079,
                "net_income": 4044351288,
            },
        }
    )

    assert [card["title"] for card in result["business_cards"]] == [
        "산전검사",
        "암검사",
        "유전희귀질환 검사",
        "건강검진",
    ]
    assert len({card["image"] for card in result["business_cards"]}) == 4
    assert [item["year"] for item in result["history"]] == [2023, 2024, 2025]
