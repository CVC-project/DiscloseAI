"""Reparse already-downloaded DART report ZIPs after recovery parser changes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from recover_eqs_raw_panels import extract_year_from_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    companies: list[dict] = []
    for company in source.get("companies", []):
        recovered_years: list[dict] = []
        sources: list[dict] = []
        for report in company.get("report_sources", []):
            year = int(report["year"])
            receipt_no = report["rcept_no"]
            directory = args.raw_dir / company["corp_code"] / f"{year}_{receipt_no}"
            item, xml_file, coverage = extract_year_from_directory(
                directory, year, preferred_file=report.get("xml_file")
            )
            if item and coverage >= 3:
                recovered_years.append(asdict(item))
            sources.append(report | {"xml_file": xml_file, "field_coverage": coverage})
        companies.append(
            {
                "corp_code": company["corp_code"],
                "corp_name": company.get("corp_name"),
                "stock_code": company.get("stock_code"),
                "industry_code": company.get("industry_code"),
                "years": recovered_years,
                "report_sources": sources,
            }
        )
        print(f"{company.get('corp_name')}: {len(recovered_years)} usable years")

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "method": "DART document.xml reparsed from existing downloaded ZIPs; review required before production merge",
        "companies": companies,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
