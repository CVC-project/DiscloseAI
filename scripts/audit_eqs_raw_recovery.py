"""Quality-gate raw DART document.xml recovery before EQS production merge.

This script does not change production panels.  It creates a review manifest
that separates records with internally consistent statement values from records
that still need source-table or accounting review.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


BALANCE_TOLERANCE = 0.02


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _balance_gap(year: dict[str, Any]) -> float | None:
    assets = year.get("total_assets")
    liabilities = year.get("total_liabilities")
    equity = year.get("total_equity")
    if not all(value is not None for value in (assets, liabilities, equity)) or not assets:
        return None
    return abs(assets - liabilities - equity) / max(abs(assets), 1.0)


def _m1_ready(years: list[dict[str, Any]]) -> bool:
    recent = years[-3:]
    if len(recent) != 3:
        return False
    values = [(item.get("operating_income"), item.get("operating_cashflow")) for item in recent]
    return all(operating_income is not None and cashflow is not None for operating_income, cashflow in values) and sum(
        operating_income for operating_income, _ in values
    ) > 0


def _m2_ready(years: list[dict[str, Any]], industry_code: str | None) -> bool:
    if (industry_code or "")[:2] in {"64", "65", "66"}:
        return False
    if len(years) < 2:
        return False
    previous, current = years[-2:]
    previous_receivable = previous.get("accounts_receivable")
    current_receivable = current.get("accounts_receivable")
    return bool(
        previous.get("revenue")
        and current.get("revenue")
        and previous_receivable not in (None, 0)
        and current_receivable is not None
    )


def _m3_ready(years: list[dict[str, Any]]) -> bool:
    if not years:
        return False
    latest = years[-1]
    return latest.get("total_liabilities") is not None and (latest.get("total_equity") or 0) > 0


def _m4_ready(years: list[dict[str, Any]]) -> bool:
    margins = [
        item["operating_income"] / item["revenue"]
        for item in years[-3:]
        if item.get("revenue") not in (None, 0) and item.get("operating_income") is not None
    ]
    return len(margins) >= 3


def _m5_ready(years: list[dict[str, Any]]) -> bool:
    if len(years) < 3:
        return False
    return (years[-3].get("total_equity") or 0) > 0 and (years[-1].get("total_equity") or 0) > 0


def audit_company(company: dict[str, Any]) -> dict[str, Any]:
    years = sorted(company.get("years", []), key=lambda item: item.get("year", 0))
    source_by_year = {item.get("year"): item for item in company.get("report_sources", [])}
    blocking: list[str] = []
    review: list[str] = []
    gaps: dict[str, float] = {}

    year_numbers = [item.get("year") for item in years]
    if len(year_numbers) != len(set(year_numbers)):
        blocking.append("duplicate_year")
    if len(years) < 3:
        blocking.append("fewer_than_3_recovered_years")

    for year in years:
        year_number = year.get("year")
        source = source_by_year.get(year_number)
        if source is None:
            blocking.append(f"{year_number}:missing_report_source")
        elif (source.get("field_coverage") or 0) < 3:
            blocking.append(f"{year_number}:low_source_coverage")
        elif not source.get("xml_file"):
            blocking.append(f"{year_number}:missing_xml_file")
        elif str(source.get("xml_file")).endswith("_00760.xml"):
            # _00760 denotes a separate-financial-statement XML. A filename
            # without either suffix is not enough evidence to call the source
            # non-consolidated, so it is not flagged.
            review.append(f"{year_number}:separate_financial_statement_xml")

        gap = _balance_gap(year)
        if gap is not None:
            gaps[str(year_number)] = round(gap, 6)
            if gap > BALANCE_TOLERANCE:
                blocking.append(f"{year_number}:balance_equation_gap={gap:.2%}")

        revenue = year.get("revenue")
        assets = year.get("total_assets")
        if revenue is not None and assets not in (None, 0) and abs(revenue / assets) > 20:
            review.append(f"{year_number}:revenue_to_assets_outlier")

    metric_ready = {
        "M1": _m1_ready(years),
        "M2": _m2_ready(years, company.get("industry_code")),
        "M3": _m3_ready(years),
        "M4": _m4_ready(years),
        "M5": _m5_ready(years),
    }
    status = "hold" if blocking else "auto_pass"
    return {
        "corp_code": company.get("corp_code"),
        "stock_code": company.get("stock_code"),
        "corp_name": company.get("corp_name"),
        "industry_code": company.get("industry_code"),
        "recovered_years": year_numbers,
        "status": status,
        "blocking_reasons": blocking,
        "review_flags": review,
        "balance_equation_gaps": gaps,
        "module_input_eligibility": metric_ready,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = _load(args.input)
    records = [audit_company(company) for company in payload.get("companies", [])]
    summary = {
        "companies": len(records),
        "auto_pass": sum(record["status"] == "auto_pass" for record in records),
        "hold": sum(record["status"] == "hold" for record in records),
        "module_input_eligibility": {
            name: sum(record["module_input_eligibility"][name] for record in records)
            for name in ("M1", "M2", "M3", "M4", "M5")
        },
        "blocking_reason_counts": dict(
            Counter(reason for record in records for reason in record["blocking_reasons"])
        ),
        "review_flag_counts": dict(
            Counter(flag.split(":", 1)[-1] for record in records for flag in record["review_flags"])
        ),
    }
    result = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "method": "raw recovery quality gate; no production merge performed",
        "balance_equation_tolerance": BALANCE_TOLERANCE,
        "summary": summary,
        "companies": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
