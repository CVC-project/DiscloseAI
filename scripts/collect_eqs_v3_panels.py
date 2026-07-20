"""전 상장사 EQS v3 보정용 최근 3개년 재무 패널 수집.

기본 실행은 50개사만 수집한다. ``--limit 0``을 명시해야 전체 상장사를
수집하므로, DART 일일 호출 한도를 실수로 소진하지 않는다. 중간 결과는 매 회사
처리 뒤 저장되어 다음 실행에서 이어받는다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.collector import (
    fetch_company_industry,
    fetch_corp_codes,
    fetch_panel,
)
from modules.financial.eqs.types import FirmPanel, FirmYear


DEFAULT_OUT = ROOT / "modules" / "financial" / "data" / "eqs_v3_panels.json"
DEFAULT_LISTED_TICKERS = ROOT / "modules" / "financial" / "data" / "krx_listed_tickers.json"


def _panel_to_dict(panel: FirmPanel) -> dict:
    return {
        "corp_code": panel.corp_code,
        "corp_name": panel.corp_name,
        "industry_code": panel.industry_code,
        "years": [asdict(year) for year in panel.years],
    }


def _panel_from_dict(raw: dict) -> FirmPanel:
    return FirmPanel(
        corp_code=raw["corp_code"],
        corp_name=raw.get("corp_name"),
        industry_code=raw.get("industry_code"),
        years=[FirmYear(**year) for year in raw.get("years", [])],
    )


def load_panels(path: Path) -> dict[str, FirmPanel]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["corp_code"]: _panel_from_dict(item)
        for item in raw.get("panels", [])
    }


def load_attempted_codes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return set(raw.get("attempted_corp_codes", []))


def load_listed_tickers(path: Path) -> set[str]:
    """Load a KIND-derived current-listing universe, never DART history alone."""
    if not path.exists():
        raise FileNotFoundError(
            f"Current KRX ticker cache not found: {path}. "
            "Run scripts/fetch_krx_listed_tickers.py first."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    tickers = {str(code).zfill(6) for code in raw.get("tickers", [])}
    valid = {code for code in tickers if len(code) == 6 and code.isdigit()}
    if not valid:
        raise ValueError(f"No valid six-digit listed tickers in {path}")
    return valid


def load_excluded_tickers(path: Path | None) -> set[str]:
    """Load an explicit, reversible stock-code exclusion list when supplied."""
    if path is None:
        return set()
    if not path.exists():
        raise FileNotFoundError(f"Exclusion file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    codes = {
        str(company.get("stock_code", "")).zfill(6)
        for company in raw.get("companies", [])
    }
    return {code for code in codes if len(code) == 6 and code.isdigit()}


def save_panels(
    path: Path,
    panels: dict[str, FirmPanel],
    years: range,
    attempted_codes: set[str],
) -> None:
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "years": list(years),
        "attempted_corp_codes": sorted(attempted_codes),
        "panels": [_panel_to_dict(panel) for panel in panels.values()],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year-end", type=int, default=2025)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--limit", type=int, default=50, help="0이면 전체 상장사")
    parser.add_argument(
        "--stock-codes",
        help="Comma-separated six-digit stock codes. Useful for validation or retries.",
    )
    parser.add_argument(
        "--retry-empty",
        action="store_true",
        help="Retry companies that were contacted but had no usable annual panel.",
    )
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--listed-tickers-file",
        type=Path,
        default=DEFAULT_LISTED_TICKERS,
        help="KIND-derived JSON cache from fetch_krx_listed_tickers.py.",
    )
    parser.add_argument(
        "--exclude-file",
        type=Path,
        help="Optional JSON exclusion list. Excluded tickers are not collected or retried.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    args = parse_args()
    years = range(args.year_end - args.years + 1, args.year_end + 1)
    existing = load_panels(args.output)
    attempted = load_attempted_codes(args.output)
    current_tickers = load_listed_tickers(args.listed_tickers_file)
    excluded_tickers = load_excluded_tickers(args.exclude_file)
    listed = [
        corp
        for corp in fetch_corp_codes()
        if (
            corp.stock_code
            and corp.stock_code in current_tickers
            and corp.stock_code not in excluded_tickers
        )
    ]
    selected_codes = {
        code.strip().zfill(6)
        for code in (args.stock_codes or "").split(",")
        if code.strip()
    }
    if selected_codes:
        targets = [corp for corp in listed if corp.stock_code in selected_codes]
        found_codes = {corp.stock_code for corp in targets}
        missing_codes = selected_codes - found_codes
        if missing_codes:
            raise SystemExit(f"Unknown stock code(s): {', '.join(sorted(missing_codes))}")
    else:
        targets = [
            corp
            for corp in listed
            if corp.corp_code not in existing
            and (args.retry_empty or corp.corp_code not in attempted)
        ]
    if args.limit:
        targets = targets[: args.limit]

    print(
        f"대상 {len(targets)}개 / 기존 {len(existing)}개 / "
        f"연도 {years.start}~{years.stop - 1} / 제외 {len(excluded_tickers)}개"
    )
    for index, corp in enumerate(targets, 1):
        completed = False
        try:
            industry_code = fetch_company_industry(corp.corp_code)
            panel = fetch_panel(
                corp.corp_code,
                years,
                corp_name=corp.corp_name,
                industry_code=industry_code,
                sleep_sec=args.sleep,
            )
            if panel.years:
                existing[corp.corp_code] = panel
            completed = True
            print(
                f"[{index}/{len(targets)}] {corp.corp_name}: "
                f"{len(panel.years)}년, KSIC={industry_code or '-'}"
            )
        except Exception as exc:  # 한 기업 실패가 배치를 멈추지 않도록
            print(f"[{index}/{len(targets)}] {corp.corp_name}: 실패 {type(exc).__name__}")
        finally:
            if completed:
                attempted.add(corp.corp_code)
            save_panels(args.output, existing, years, attempted)
    print(f"완료: {args.output} ({len(existing)}개 패널)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
