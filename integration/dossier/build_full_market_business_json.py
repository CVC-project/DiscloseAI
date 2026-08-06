"""Build business_<ticker>.json files for the full listed-company dossier UI.

This is intentionally integration-only: it converts already-collected DART
business-report summaries into the JSON contract consumed by business.html.
Existing hand-curated 48 company files are preserved by default.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from business_card_quality import normalize_business_payload

ROOT = Path(__file__).resolve().parents[2]
FULLTEXT_DIR = ROOT / "modules" / "disclosure" / "data" / "fulltext"
OUT_DIR = ROOT / "integration" / "dossier" / "data"
MASTER_PATH = OUT_DIR / "company_master.json"
PRODUCT_SEGMENTS_PATH = OUT_DIR / "product_service_segments.json"


KIND_KEYWORDS = [
    ("bank", ["은행", "대출", "예금", "금융"]),
    ("securities", ["증권", "브로커리지", "투자"]),
    ("insurance", ["보험", "손해", "생명"]),
    ("chip", ["반도체", "DRAM", "NAND", "HBM", "Foundry", "웨이퍼"]),
    ("battery", ["배터리", "2차전지", "양극재", "음극재", "전해액"]),
    ("auto", ["자동차", "완성차", "전기차", "부품", "모빌리티"]),
    ("ship", ["조선", "선박", "LNG", "해양", "플랜트"]),
    ("bio", ["바이오", "의약품", "제약", "CDMO", "임상"]),
    ("display", ["디스플레이", "OLED", "패널"]),
    ("telecom", ["통신", "네트워크", "무선"]),
    ("platform", ["플랫폼", "커머스", "게임", "콘텐츠", "광고"]),
    ("power", ["전력", "발전", "에너지", "원전"]),
    ("material", ["화학", "소재", "철강", "금속", "정유"]),
    ("consumer", ["식품", "담배", "화장품", "생활"]),
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def clean_name(name: str | None) -> str:
    value = re.sub(r"^\(주\)|주식회사|\(주\)", "", str(name or "")).strip()
    return value or str(name or "").strip()


def compact(text: Any, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = re.sub(r"☞.*$", "", value).strip()
    if len(value) <= limit:
        return value
    cut = value[:limit]
    last = max(cut.rfind("습니다."), cut.rfind("입니다."), cut.rfind("다."))
    if last >= 80:
        return cut[: last + 2]
    return cut.rstrip(" ,·ㆍ-/") + "입니다."


def pct_share(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n > 1:
        n = n / 100.0
    if n < 0:
        return None
    return round(n, 4)


def choose_kind(text: str) -> str:
    for kind, words in KIND_KEYWORDS:
        if any(word.lower() in text.lower() for word in words):
            return kind
    return "service"


def visual_word(title: str, desc: str) -> str:
    text = f"{title} {desc}"
    for word in [
        "HBM",
        "DRAM",
        "NAND",
        "OLED",
        "EV",
        "LNG",
        "CDMO",
        "AI",
        "BANK",
        "CARD",
        "AUTO",
        "BIO",
        "SHIP",
    ]:
        if word in text.upper():
            return word
    token = re.split(r"[\s·ㆍ/(),]+", title.strip())[0]
    return token[:10] if token else "BUSINESS"


def build_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    segments = summary.get("segments") or []
    products = summary.get("products") or []
    cards: list[dict[str, Any]] = []

    for segment in segments[:4]:
        title = str(segment.get("name") or "").strip()
        desc = compact(segment.get("desc") or "", 84)
        if not title:
            continue
        text = f"{title} {desc}"
        cards.append(
            {
                "title": title,
                "caption": desc or "사업보고서에 표시된 주요 사업부문입니다.",
                "kind": choose_kind(text),
                "visual": visual_word(title, desc),
            }
        )

    if len(cards) < 2:
        for product in products[: 4 - len(cards)]:
            title = str(product or "").strip()
            if not title or any(c["title"] == title for c in cards):
                continue
            cards.append(
                {
                    "title": title,
                    "caption": f"{title} 관련 제품과 서비스를 통해 매출을 만듭니다.",
                    "kind": choose_kind(title),
                    "visual": visual_word(title, ""),
                }
            )

    return cards[:4]


def latest_summaries() -> dict[str, dict[str, Any]]:
    latest: dict[str, tuple[str, Path, dict[str, Any]]] = {}
    for path in FULLTEXT_DIR.glob("*/*/summary.json"):
        data = load_json(path)
        corp_code = str(data.get("corp_code") or path.parent.parent.name).zfill(8)
        rcept_no = str(data.get("rcept_no") or path.parent.name)
        current = latest.get(corp_code)
        if current is None or rcept_no > current[0]:
            latest[corp_code] = (rcept_no, path, data)
    return {corp: data for corp, (_, __, data) in latest.items()}


def master_by_corp() -> dict[str, dict[str, Any]]:
    master = load_json(MASTER_PATH)
    return {
        str(row["corp_code"]).zfill(8): row
        for row in master.get("companies", [])
        if row.get("corp_code")
    }


def product_segments_by_corp() -> dict[str, list[dict[str, Any]]]:
    if not PRODUCT_SEGMENTS_PATH.exists():
        return {}
    payload = load_json(PRODUCT_SEGMENTS_PATH)
    return {
        str(corp_code).zfill(8): value
        for corp_code, value in payload.items()
        if isinstance(value, list)
    }


def firm_by_ticker(ticker: str) -> dict[str, Any] | None:
    path = OUT_DIR / f"firm_{ticker}.json"
    if not path.exists():
        return None
    return load_json(path)


def report_payload(summary: dict[str, Any]) -> dict[str, str]:
    rcept_no = str(summary.get("rcept_no") or "")
    year = "2025.12"
    name = f"사업보고서 ({year})"
    return {
        "name": name,
        "date": str(summary.get("rcept_dt") or rcept_no[:8] or ""),
        "rcept_no": rcept_no,
    }


def build_custom_ideas(summary: dict[str, Any], category: str) -> list[dict[str, str]]:
    notes = compact(summary.get("investor_notes"), 520)
    highlights = summary.get("financial_highlights") or []
    parts = [h for h in highlights if isinstance(h, dict)]
    revenue = next((h for h in parts if "매출" in str(h.get("item", ""))), None)
    profit = next((h for h in parts if "영업이익" in str(h.get("item", ""))), None)
    debt = next((h for h in parts if "부채비율" in str(h.get("item", ""))), None)

    cards: list[dict[str, str]] = []
    if notes:
        cards.append(
            {
                "title": "사업보고서 핵심 요약",
                "value": compact(notes, 84),
                "fact": notes,
                "view": "제품명만 반복하지 않고, 회사가 어떤 사업으로 매출을 만드는지 먼저 읽으면 됩니다.",
            }
        )
    if revenue or profit:
        bits = []
        if revenue:
            bits.append(
                f"{revenue.get('item')}: {revenue.get('value')} ({revenue.get('yoy') or '전년 대비 정보 없음'})"
            )
        if profit:
            bits.append(
                f"{profit.get('item')}: {profit.get('value')} ({profit.get('yoy') or '전년 대비 정보 없음'})"
            )
        cards.append(
            {
                "title": "실적 변화",
                "value": " · ".join(bits[:2]),
                "fact": " / ".join(
                    filter(
                        None,
                        [
                            revenue and revenue.get("explain"),
                            profit and profit.get("explain"),
                        ],
                    )
                ),
                "view": "매출이 커졌는지와 본업 이익이 같이 좋아졌는지를 함께 보면 사업 흐름을 더 쉽게 볼 수 있습니다.",
            }
        )
    if debt:
        cards.append(
            {
                "title": "재무 부담",
                "value": f"{debt.get('item')}: {debt.get('value')}",
                "fact": str(debt.get("explain") or ""),
                "view": "성장 산업이어도 부채 부담이 크면 금리와 자금 조달 환경에 더 민감할 수 있습니다.",
            }
        )

    if not cards:
        cards.append(
            {
                "title": "회사 이해 포인트",
                "value": f"{category} 사업을 중심으로 요약했습니다.",
                "fact": compact(
                    summary.get("investor_notes")
                    or "사업보고서 요약 원천을 바탕으로 주요 사업과 제품을 정리했습니다.",
                    180,
                ),
                "view": "사업부문과 제품을 먼저 확인한 뒤, 실적과 재무제표를 이어서 보면 됩니다.",
            }
        )
    return cards[:3]


def build_business_json(
    summary: dict[str, Any], master: dict[str, Any]
) -> dict[str, Any]:
    ticker = str(master["ticker"]).zfill(6)
    firm = firm_by_ticker(ticker) or {}
    latest_year = None
    years = firm.get("years") or []
    if years:
        latest_year = years[-1]
    category = master.get("industry_name") or master.get("industry_code") or "사업"
    reported_segments = (
        summary.get("product_service_segments") or summary.get("segments") or []
    )
    segments = []
    for segment in reported_segments:
        if not isinstance(segment, dict):
            continue
        segments.append(
            {
                "name": str(segment.get("name") or "").strip(),
                "desc": compact(segment.get("desc") or "", 120),
                "revenue_share": pct_share(segment.get("revenue_share")),
            }
        )

    snippets = {
        "overview": compact(summary.get("investor_notes"), 900),
        "segment_finance": compact(summary.get("investor_notes"), 700),
        "segment_breakdown": [s for s in segments if s["name"]],
        "product_service_segments": [s for s in segments if s["name"]],
        "products": [
            str(p).strip() for p in (summary.get("products") or []) if str(p).strip()
        ][:12],
        "investor_note": compact(summary.get("investor_notes"), 700),
    }

    return {
        "rank": None,
        "name": clean_name(master.get("company_name") or summary.get("corp_name")),
        "stock_code": ticker,
        "corp_code": str(master["corp_code"]).zfill(8),
        "grade": (firm.get("eqs") or {}).get("grade"),
        "total": (firm.get("eqs") or {}).get("total"),
        "market_cap": None,
        "last_price": None,
        "ttm_per": None,
        "dart_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={summary.get('rcept_no')}",
        "latest_year": latest_year,
        "history": years,
        "modules": (firm.get("eqs") or {}).get("modules", []),
        "percentile": {},
        "report": report_payload(summary),
        "snippets": snippets,
        "business_cards": build_cards(summary),
        "custom_report_ideas": build_custom_ideas(summary, str(category)),
        "sector": category,
        "display_category": category,
        "badge_label": (master.get("industry_name") or str(category))[:12],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite-curated",
        action="store_true",
        help="Overwrite existing 48 curated business JSONs.",
    )
    args = parser.parse_args()

    summaries = latest_summaries()
    master = master_by_corp()
    product_segments = product_segments_by_corp()
    written = 0
    preserved = 0
    skipped = 0
    for corp_code, summary in sorted(summaries.items()):
        if product_segments.get(corp_code):
            summary = {
                **summary,
                "product_service_segments": product_segments[corp_code],
            }
        row = master.get(corp_code)
        if not row or not row.get("ticker"):
            skipped += 1
            continue
        ticker = str(row["ticker"]).zfill(6)
        out = OUT_DIR / f"business_{ticker}.json"
        if out.exists() and not args.overwrite_curated:
            preserved += 1
            continue
        payload = normalize_business_payload(build_business_json(summary, row))
        dump_json(out, payload)
        written += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_summary_count": len(summaries),
        "master_count": len(master),
        "written": written,
        "preserved_existing": preserved,
        "skipped_no_ticker": skipped,
    }
    dump_json(OUT_DIR / "business_index.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
