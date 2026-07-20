"""Classify listed companies missing from the standard DART financial endpoint."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.collector import _BASE, _get


def annual_reports(corp_code: str) -> tuple[str, list[dict]]:
    response = _get(
        f"{_BASE}/list.json",
        {
            "corp_code": corp_code,
            "bgn_de": "20200101",
            "pblntf_ty": "A",
            "last_reprt_at": "Y",
            "page_count": 100,
        },
    ).json()
    if response.get("status") != "000":
        return str(response.get("status", "unknown")), []

    reports = [
        {
            "report_name": item.get("report_nm"),
            "receipt_no": item.get("rcept_no"),
            "receipt_date": item.get("rcept_dt"),
        }
        for item in response.get("list", [])
        if "사업보고서" in str(item.get("report_nm", ""))
    ]
    return "000", reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sleep", type=float, default=0.15)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    diagnostics: list[dict] = []
    for index, company in enumerate(source.get("companies", []), 1):
        try:
            status, reports = annual_reports(company["corp_code"])
            classification = "annual_report_available" if reports else "no_annual_report_in_list_api"
            diagnostics.append(
                company
                | {
                    "list_api_status": status,
                    "classification": classification,
                    "annual_report_count": len(reports),
                    "latest_annual_report": reports[0] if reports else None,
                }
            )
        except Exception as exc:  # Keep the diagnostic batch going.
            diagnostics.append(company | {"classification": "lookup_error", "error": type(exc).__name__})
        print(f"[{index}/{len(source.get('companies', []))}] {company['stock_code']}")
        time.sleep(args.sleep)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(args.input),
        "companies": diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    available = sum(item["classification"] == "annual_report_available" for item in diagnostics)
    print(f"Annual report available: {available}/{len(diagnostics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
