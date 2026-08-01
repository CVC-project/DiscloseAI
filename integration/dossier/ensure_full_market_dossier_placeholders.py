"""Ensure every company in integration/data/companies_index.json has dossier files.

For companies without collected DART summary or EQS panel, create explicit
N/A placeholders. This keeps the full-market galaxy UI from showing iframe
404 errors while still making data gaps transparent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
COMPANIES_INDEX = ROOT / "integration" / "data" / "companies_index.json"
DATA_DIR = ROOT / "integration" / "dossier" / "data"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def make_business(row: dict[str, Any]) -> dict[str, Any]:
    ticker = str(row.get("t") or "")
    name = str(row.get("n") or ticker)
    sector = str(row.get("s") or "사업")
    return {
        "rank": None,
        "name": name,
        "stock_code": ticker,
        "corp_code": None,
        "grade": None,
        "total": None,
        "market_cap": None,
        "last_price": None,
        "ttm_per": None,
        "dart_url": "#",
        "latest_year": None,
        "history": [],
        "modules": [],
        "percentile": {},
        "report": {"name": "사업보고서 수집 대기", "date": "", "rcept_no": ""},
        "snippets": {
            "overview": f"{name}은 현재 통합 화면의 전 상장사 목록에는 포함되어 있지만, 로컬 DART 사업보고서 요약 데이터가 아직 연결되지 않았습니다.",
            "segment_breakdown": [],
            "products": [],
            "investor_note": "사업보고서 원문 수집 또는 종목코드 매핑을 보강하면 이 영역에 회사별 사업 요약이 표시됩니다.",
        },
        "business_cards": [
            {
                "title": sector,
                "caption": "사업보고서 요약 데이터가 아직 없어 업종 기준 임시 카드로 표시합니다.",
                "kind": "service",
                "visual": "DATA",
            }
        ],
        "custom_report_ideas": [
            {
                "title": "데이터 수집 대기",
                "value": "사업보고서 요약 미연결",
                "fact": "전 상장사 행성 목록에는 포함되어 있으나, DART 사업보고서 요약 JSON이 아직 생성되지 않은 기업입니다.",
                "view": "추가 수집 후 회사별 제품·서비스와 사업현황 요약을 연결할 수 있습니다.",
            }
        ],
        "sector": sector,
        "display_category": sector,
        "badge_label": sector[:12],
        "_placeholder": True,
    }


def make_firm(row: dict[str, Any]) -> dict[str, Any]:
    ticker = str(row.get("t") or "")
    name = str(row.get("n") or ticker)
    sector = str(row.get("s") or "미분류")
    return {
        "corp": {"name": name, "code": None, "industry": sector, "year_count": 0},
        "years": [],
        "eqs": {
            "total": None,
            "grade": "N/A",
            "excluded": ["no_financial_panel"],
            "modules": [],
            "method": "not_available",
        },
        "ratios": {"year": None, "values": {}, "labels": {}},
        "industry": {"sector": sector, "n_companies": 0, "averages": {}, "members": []},
        "summary": [
            "DART 표준 재무 패널이 아직 연결되지 않았습니다.",
            "EQS/F-EQS는 재무제표 데이터 확보 후 산출됩니다.",
            "전 상장사 UI에서 빈 화면이 뜨지 않도록 N/A placeholder로 표시합니다.",
        ],
        "highlights": [],
        "glossary": {},
        "_hdr": {
            "corp_name": name,
            "corp_code": ticker,
            "year_range": "N/A",
            "total": None,
            "grade": "N/A",
        },
        "_placeholder": True,
    }


def main() -> int:
    rows = load_json(COMPANIES_INDEX)
    made_business = 0
    made_firm = 0
    for row in rows:
        ticker = str(row.get("t") or "")
        if not ticker:
            continue
        business_path = DATA_DIR / f"business_{ticker}.json"
        firm_path = DATA_DIR / f"firm_{ticker}.json"
        if not business_path.exists():
            dump_json(business_path, make_business(row))
            made_business += 1
        if not firm_path.exists():
            dump_json(firm_path, make_firm(row))
            made_firm += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companies_index_count": len(rows),
        "created_business_placeholders": made_business,
        "created_firm_placeholders": made_firm,
    }
    dump_json(DATA_DIR / "dossier_placeholder_index.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
