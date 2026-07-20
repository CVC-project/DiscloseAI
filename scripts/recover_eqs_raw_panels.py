"""Recover EQS financial panels from DART document.xml when the standard API has no data.

The OpenDART ``fnlttSinglAcntAll`` endpoint is preferred for normal collection.
This script is a deliberately separate recovery path: it downloads annual business
reports or consolidated audit reports, extracts the XML tables, and writes a
reviewable checkpoint file. Recovered panels are not merged into the production
EQS input until their coverage has been reviewed.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.collector import _get, fetch_company_industry, fetch_corp_codes
from modules.financial.eqs.types import FirmYear


DEFAULT_MISSING = ROOT / "modules" / "financial" / "data" / "eqs_v3_missing_panels.json"
DEFAULT_OUTPUT = ROOT / "modules" / "financial" / "data" / "eqs_v3_raw_recovered_panels.json"


def _normalise_label(value: str) -> str:
    return re.sub(r"[\s0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ().·-]", "", value).lower()


def _amount(value: str) -> float | None:
    value = value.strip().replace(",", "")
    if not value or value in {"-", "--"}:
        return None
    negative = value.startswith("(") and value.endswith(")")
    value = value.strip("()")
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        return None
    result = float(value)
    return -result if negative else result


def _row_cells(row) -> list[str]:
    return [cell.get_text(" ", strip=True) for cell in row.find_all(["TH", "TD"], recursive=False)]


def _table_rows(table) -> list[list[str]]:
    return [cells for tr in table.find_all("TR") if (cells := _row_cells(tr))]


def _statement_amount_column(rows: list[list[str]]) -> int:
    """Return the current-period amount column for a statement table.

    DART statement tables commonly put a ``주석`` column between the account
    label and current-period amount. Treating the first numeric cell as an
    amount therefore turns a note reference such as ``24, 39`` into ``2439``.
    Prefer an explicit current-period header, otherwise skip the note column.
    """
    for cells in rows[:5]:
        labels = [_normalise_label(cell) for cell in cells]
        for index, label in enumerate(labels):
            if index and any(token in label for token in ("당기", "당분기", "현재기", "currentperiod")):
                return index
        for index, label in enumerate(labels):
            if "주석" in label or label == "note":
                return index + 1
    return 1


def _match_value(
    rows: list[list[str]], patterns: tuple[str, ...], amount_column: int
) -> float | None:
    for cells in rows:
        label = _normalise_label(cells[0])
        if any(pattern in label for pattern in patterns):
            if len(cells) > amount_column:
                value = _amount(cells[amount_column])
                if value is not None:
                    return value
    return None


def _best_table(tables, required: tuple[tuple[str, ...], ...]):
    """Find the table containing the most statement-specific rows."""
    best = None
    best_score = 0
    for table in tables:
        rows = _table_rows(table)
        labels = [_normalise_label(cells[0]) for cells in rows]
        score = sum(any(any(pattern in label for pattern in group) for label in labels) for group in required)
        if score > best_score:
            best, best_score = (table, rows), score
    return best if best_score == len(required) else (None, [])


BALANCE_REQUIRED = (("자산총계",), ("부채총계",), ("자본총계",))
INCOME_REQUIRED = (("영업이익", "영업손익"), ("당기순이익", "당기순손익", "당기순손실"))
CASHFLOW_REQUIRED = (("영업활동으로인한현금흐름",),)


def _extract_from_xml(path: Path, year: int) -> tuple[FirmYear, int]:
    """Extract a single-year panel from one DART XML file and return coverage."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(text, "lxml-xml")
    tables = soup.find_all("TABLE")
    balance, balance_rows = _best_table(tables, BALANCE_REQUIRED)
    income, income_rows = _best_table(tables, INCOME_REQUIRED)
    cashflow, cashflow_rows = _best_table(tables, CASHFLOW_REQUIRED)

    item = FirmYear(year=year)
    if balance:
        amount_column = _statement_amount_column(balance_rows)
        item.total_assets = _match_value(balance_rows, ("자산총계",), amount_column)
        item.total_liabilities = _match_value(balance_rows, ("부채총계",), amount_column)
        item.total_equity = _match_value(balance_rows, ("자본총계",), amount_column)
        item.accounts_receivable = _match_value(
            balance_rows, ("매출채권", "외상매출금"), amount_column
        )
        item.contract_assets = _match_value(
            balance_rows, ("계약자산", "미청구공사"), amount_column
        )
    if income:
        amount_column = _statement_amount_column(income_rows)
        item.revenue = _match_value(
            income_rows, ("매출액", "영업수익", "보험수익", "수익"), amount_column
        )
        item.operating_income = _match_value(
            income_rows, ("영업이익", "영업손익"), amount_column
        )
        item.net_income = _match_value(
            income_rows, ("당기순이익", "당기순손익", "당기순손실"), amount_column
        )
    if cashflow:
        amount_column = _statement_amount_column(cashflow_rows)
        item.operating_cashflow = _match_value(
            cashflow_rows, ("영업활동으로인한현금흐름",), amount_column
        )
    coverage = sum(
        value is not None
        for value in (
            item.revenue,
            item.operating_income,
            item.net_income,
            item.operating_cashflow,
            item.total_assets,
            item.total_liabilities,
            item.total_equity,
        )
    )
    return item, coverage


def _balance_equation_gap(item: FirmYear) -> float | None:
    """Return the relative assets = liabilities + equity gap when available."""
    values = (item.total_assets, item.total_liabilities, item.total_equity)
    if any(value is None for value in values) or not item.total_assets:
        return None
    return abs(item.total_assets - item.total_liabilities - item.total_equity) / max(
        abs(item.total_assets), 1.0
    )


def extract_year_from_directory(
    directory: Path, year: int, preferred_file: str | None = None
) -> tuple[FirmYear | None, str | None, int]:
    """Choose the most coherent financial-statement XML from a report ZIP.

    A DART ZIP can include correction notices and note tables which happen to
    contain the same labels as financial statements.  Prefer a table set that
    satisfies the accounting equation over raw field-count matches.
    """
    if preferred_file:
        preferred_path = directory / preferred_file
        if preferred_path.exists():
            preferred_item, preferred_coverage = _extract_from_xml(preferred_path, year)
            preferred_gap = _balance_equation_gap(preferred_item)
            if preferred_coverage >= 3 and (
                preferred_gap is None or preferred_gap <= 0.02
            ):
                return preferred_item, preferred_path.name, preferred_coverage
        else:
            preferred_item, preferred_coverage = None, 0

        candidate_paths = [preferred_path]
        candidate_paths.extend(sorted(directory.glob("*_00761.xml")))
        candidate_paths.extend(sorted(directory.glob("*_00760.xml")))
        # Preserve order while removing duplicates and files absent from this ZIP.
        candidates = list(dict.fromkeys(path for path in candidate_paths if path.exists()))
        if not candidates:
            candidates = sorted(directory.rglob("*.xml"))
    else:
        candidates = sorted(directory.rglob("*.xml"))
    best_item: FirmYear | None = None
    best_file: Path | None = None
    best_score = -1
    best_coverage = 0
    for path in candidates:
        item, coverage = _extract_from_xml(path, year)
        balance_gap = _balance_equation_gap(item)
        consistency_bonus = 0
        if balance_gap is not None:
            consistency_bonus = 1000 if balance_gap <= 0.02 else -1000
        consolidated_bonus = 1 if path.stem.endswith("_00761") else 0
        score = coverage * 10 + consistency_bonus + consolidated_bonus
        if score > best_score:
            best_item, best_file, best_score = item, path, score
            best_coverage = coverage
    if best_item is None:
        return None, None, 0
    return best_item, best_file.name if best_file else None, best_coverage


def _report_candidates(items: list[dict], year: int) -> list[dict]:
    """Return annual-report candidates, ordered by report type and recency.

    Some late correction filings have a DART list entry but no downloadable
    ``document.xml`` archive (status 014).  Keeping every suitable filing lets
    the caller fall back to the original annual report or audit report instead
    of discarding the whole company.
    """
    year_marker = f"({year}.12)"
    choices: list[tuple[int, dict]] = []
    for item in items:
        name = item.get("report_nm", "")
        if year_marker not in name:
            continue
        if "사업보고서" in name:
            choices.append((0, item))
        elif "연결감사보고서" in name:
            choices.append((1, item))
        elif "감사보고서" in name:
            choices.append((2, item))
    return [
        item
        for _, item in sorted(
            choices,
            key=lambda choice: (
                choice[0],
                -int(choice[1].get("rcept_dt", "0") or 0),
            ),
        )
    ]


def _select_report(items: list[dict], year: int) -> dict | None:
    """Return the preferred annual-report candidate for diagnostics."""
    candidates = _report_candidates(items, year)
    return candidates[0] if candidates else None


def _download_report(rcept_no: str, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    zip_path = directory / f"{rcept_no}.zip"
    if not zip_path.exists() or zip_path.stat().st_size == 0:
        response = _get("https://opendart.fss.or.kr/api/document.xml", {"rcept_no": rcept_no})
        if response.content[:2] != b"PK":
            raise RuntimeError("document.xml did not return a ZIP archive")
        zip_path.write_bytes(response.content)
    if not any(directory.glob("*.xml")):
        with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as archive:
            archive.extractall(directory)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {item["corp_code"]: item for item in _load_json(path).get("companies", [])}


def _save_output(path: Path, companies: dict[str, dict]) -> None:
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "method": "DART document.xml table extraction; review required before production merge",
        "companies": list(companies.values()),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing-file", type=Path, default=DEFAULT_MISSING)
    parser.add_argument("--exclude-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--year-end", type=int, default=2025)
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="0 means all candidates")
    parser.add_argument("--corp-codes", help="Comma-separated DART corp codes for a focused validation run")
    parser.add_argument("--sleep", type=float, default=0.2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    excluded_codes: set[str] = set()
    if args.exclude_file:
        excluded_codes = {
            str(item.get("corp_code", ""))
            for item in _load_json(args.exclude_file).get("companies", [])
        }
    corp_index = {corp.corp_code: corp for corp in fetch_corp_codes()}
    requested = {code.strip() for code in (args.corp_codes or "").split(",") if code.strip()}
    if requested:
        target_codes = sorted(requested)
    else:
        missing = _load_json(args.missing_file).get("companies", [])
        target_codes = [item["corp_code"] for item in missing if item["corp_code"] not in excluded_codes]
    if args.limit:
        target_codes = target_codes[: args.limit]

    existing = _load_existing(args.output)
    years = list(range(args.year_end - args.years + 1, args.year_end + 1))
    print(f"raw recovery targets={len(target_codes)} years={years[0]}~{years[-1]}")
    for index, corp_code in enumerate(target_codes, 1):
        corp = corp_index.get(corp_code)
        if not corp:
            print(f"[{index}/{len(target_codes)}] {corp_code}: corp code missing")
            continue
        try:
            reports = _get(
                "https://opendart.fss.or.kr/api/list.json",
                {"corp_code": corp_code, "bgn_de": f"{years[0]}0101", "page_count": 100},
            ).json().get("list", [])
            recovered_years: list[dict] = []
            report_sources: list[dict] = []
            for year in years:
                candidates = _report_candidates(reports, year)
                if not candidates:
                    continue
                last_error: str | None = None
                for report in candidates:
                    receipt_no = report["rcept_no"]
                    directory = args.raw_dir / corp_code / f"{year}_{receipt_no}"
                    try:
                        _download_report(receipt_no, directory)
                        item, source_file, coverage = extract_year_from_directory(directory, year)
                    except Exception as exc:
                        last_error = f"{type(exc).__name__}: {exc}"
                        continue
                    if item and coverage >= 3:
                        recovered_years.append(asdict(item))
                    report_sources.append(
                        {
                            "year": year,
                            "rcept_no": receipt_no,
                            "report_nm": report.get("report_nm"),
                            "rcept_dt": report.get("rcept_dt"),
                            "xml_file": source_file,
                            "field_coverage": coverage,
                        }
                    )
                    break
                else:
                    report = candidates[0]
                    report_sources.append(
                        {
                            "year": year,
                            "rcept_no": report["rcept_no"],
                            "report_nm": report.get("report_nm"),
                            "rcept_dt": report.get("rcept_dt"),
                            "xml_file": None,
                            "field_coverage": 0,
                            "download_error": last_error,
                        }
                    )
                time.sleep(args.sleep)
            existing[corp_code] = {
                "corp_code": corp_code,
                "corp_name": corp.corp_name,
                "stock_code": corp.stock_code,
                "industry_code": fetch_company_industry(corp_code),
                "years": recovered_years,
                "report_sources": report_sources,
            }
            _save_output(args.output, existing)
            print(f"[{index}/{len(target_codes)}] {corp.corp_name}: {len(recovered_years)} usable years")
        except Exception as exc:
            print(f"[{index}/{len(target_codes)}] {corp.corp_name}: FAILED {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
