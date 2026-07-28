"""Populate business-reader category fields for dossier JSON files.

The integration business tab reads top-level ``sector``, ``display_category``,
and ``badge_label`` fields. Some generated JSON files only kept the broader
EQS peer-group value under ``percentile._sector``, which made the deployed UI
fall back to "업종 미분류". This script restores the explicit business-category
contract for all local dossier business files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "integration" / "dossier" / "data"

CATEGORY_BY_STOCK: dict[str, tuple[str, str, str]] = {
    "005930": ("반도체/전자부품", "종합반도체", "종합반도체"),
    "000660": ("반도체/전자부품", "메모리반도체", "메모리"),
    "005380": ("자동차", "완성차", "자동차"),
    "373220": ("2차전지/배터리", "배터리셀", "배터리"),
    "012450": ("중공업/방산/전기장비", "방산·항공우주", "방산"),
    "402340": ("지주/복합기업", "투자지주", "지주"),
    "207940": ("바이오/제약", "바이오 CDMO", "CDMO"),
    "034020": ("중공업/방산/전기장비", "발전설비", "발전설비"),
    "105560": ("금융/보험", "금융업", "금융업"),
    "000270": ("자동차", "완성차", "자동차"),
    "329180": ("조선", "조선", "조선"),
    "032830": ("금융/보험", "생명보험", "보험"),
    "028260": ("지주/복합기업", "건설·상사 복합", "복합"),
    "055550": ("금융/보험", "금융업", "금융업"),
    "068270": ("바이오/제약", "바이오의약품", "바이오"),
    "009150": ("반도체/전자부품", "전자부품", "전자부품"),
    "006400": ("2차전지/배터리", "배터리", "배터리"),
    "042660": ("조선", "조선·방산", "조선"),
    "267260": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "006800": ("금융/보험", "증권업", "증권"),
    "012330": ("자동차", "자동차부품", "부품"),
    "010130": ("화학/정유/소재", "제련", "제련"),
    "086790": ("금융/보험", "금융업", "금융업"),
    "015760": ("통신/유틸리티/운송/기타", "전력", "전력"),
    "011200": ("통신/유틸리티/운송/기타", "해운", "해운"),
    "035420": ("인터넷/IT서비스", "플랫폼", "플랫폼"),
    "096770": ("화학/정유/소재", "에너지", "에너지"),
    "272210": ("중공업/방산/전기장비", "방산·ICT", "방산ICT"),
    "267250": ("지주/복합기업", "조선·정유 지주", "지주"),
    "298040": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "034730": ("지주/복합기업", "투자지주", "지주"),
    "316140": ("금융/보험", "금융업", "금융업"),
    "017670": ("통신/유틸리티/운송/기타", "통신", "통신"),
    "010140": ("조선", "조선해양", "조선"),
    "051910": ("화학/정유/소재", "화학·첨단소재", "화학"),
    "064350": ("중공업/방산/전기장비", "방산·철도", "방산철도"),
    "000810": ("금융/보험", "손해보험", "보험"),
    "000150": ("지주/복합기업", "지주·전자소재", "지주"),
    "035720": ("인터넷/IT서비스", "플랫폼", "플랫폼"),
    "079550": ("중공업/방산/전기장비", "방산", "방산"),
    "033780": ("통신/유틸리티/운송/기타", "담배·건기식", "소비재"),
    "009540": ("조선", "조선", "조선"),
    "010120": ("중공업/방산/전기장비", "전력기기", "전력기기"),
    "003670": ("2차전지/배터리", "배터리소재", "배터리소재"),
    "005490": ("화학/정유/소재", "철강·소재 지주", "소재"),
    "042700": ("반도체/전자부품", "반도체장비", "반도체장비"),
    "000720": ("통신/유틸리티/운송/기타", "건설", "건설"),
}


def category_for(row: dict[str, Any]) -> tuple[str, str, str]:
    stock_code = str(row.get("stock_code") or "").zfill(6)
    if stock_code in CATEGORY_BY_STOCK:
        return CATEGORY_BY_STOCK[stock_code]
    fallback = (row.get("percentile") or {}).get("_sector") or row.get("sector") or "사업"
    return str(fallback), str(fallback), "사업"


def main() -> int:
    updated = 0
    missing = []
    for path in sorted(DATA_DIR.glob("business_*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        sector, display_category, badge_label = category_for(row)
        before = (row.get("sector"), row.get("display_category"), row.get("badge_label"))
        row["sector"] = sector
        row["display_category"] = display_category
        row["badge_label"] = badge_label
        next_text = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        if (sector, display_category, badge_label) != before or path.read_text(encoding="utf-8") != next_text:
            path.write_text(next_text, encoding="utf-8")
            updated += 1
        if not row.get("display_category") or not row.get("sector") or not row.get("badge_label"):
            missing.append(path.name)
    print(f"updated={updated}")
    print(f"missing_category_fields={len(missing)}")
    if missing:
        for name in missing:
            print(f"- {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
