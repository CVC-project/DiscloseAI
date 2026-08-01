"""Build integration/data/eqs_summary.json from full-market firm_<ticker>.json.

The v2 loader enriches universe nodes from this compact file. firm_<ticker>.json
remains the detailed source for the EQS iframe; this script only creates the
small index used by the main galaxy UI.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIRM_DIR = ROOT / "integration" / "dossier" / "data"
OUT_PATH = ROOT / "integration" / "data" / "eqs_summary.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def module_map(eqs: dict[str, Any]) -> dict[str, Any]:
    return {m.get("name"): m for m in (eqs.get("modules") or []) if m.get("name")}


def latest_year(years: list[dict[str, Any]]) -> dict[str, Any]:
    if not years:
        return {}
    return sorted(years, key=lambda y: y.get("year") or 0)[-1]


def to_eok(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) / 100_000_000, 1)
    except (TypeError, ValueError):
        return None


def build_row(path: Path) -> dict[str, Any] | None:
    ticker = path.stem.replace("firm_", "")
    data = load_json(path)
    corp = data.get("corp") or {}
    eqs = data.get("eqs") or {}
    years = data.get("years") or []
    latest = latest_year(years)
    modules = module_map(eqs)

    if eqs.get("total") is None:
        return None

    row = {
        "ticker": ticker,
        "corp_code": corp.get("code"),
        "corp_name": corp.get("name"),
        "year": latest.get("year"),
        "quarter": None,
        "revenue": to_eok(latest.get("revenue")),
        "operating_income": to_eok(latest.get("operating_income")),
        "net_income": to_eok(latest.get("net_income")),
        "total_assets": to_eok(latest.get("total_assets")),
        "total_liabilities": to_eok(latest.get("total_liabilities")),
        "total_equity": to_eok(latest.get("total_equity")),
        "operating_cashflow": to_eok(latest.get("operating_cashflow")),
        "market_cap": None,
        "dart_url": None,
        "industry_code": corp.get("industry"),
        "is_financial": str(eqs.get("method") or "").startswith("feqs_"),
        "eqs_total": eqs.get("total"),
        "eqs_grade": eqs.get("grade"),
        "eqs_method": eqs.get("method"),
        "eqs_excluded": eqs.get("excluded") or [],
        "eqs_modules": modules,
        "eqs_module_notes": {k: v.get("note") for k, v in modules.items() if isinstance(v, dict)},
    }
    for key in ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]:
        row[f"eqs_{key.lower()}"] = (modules.get(key) or {}).get("score")
    return row


def main() -> int:
    rows = []
    financial = 0
    for path in sorted(FIRM_DIR.glob("firm_*.json")):
        row = build_row(path)
        if row is None:
            continue
        if row["is_financial"]:
            financial += 1
        rows.append(row)

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "integration/dossier/data/firm_<ticker>.json",
            "count": len(rows),
            "financial_feqs_count": financial,
            "non_financial_eqs_count": len(rows) - financial,
        },
        "data": rows,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
