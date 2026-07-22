"""Recalculate the existing KOSPI 48 export using EQS v3 percentile rules.

The export contains DART-derived time series plus each module's raw metric in
its note. This migration keeps the source business data unchanged and
reconstructs the five V3 inputs until the full listed-company panel is ready.
It can safely run again on a V3 output because it extracts the explicitly
labelled raw metric rather than the later peer-percentile explanation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.eqs.calibration import build_calibration
from modules.financial.eqs.score import compute_eqs
from modules.financial.eqs.types import FirmPanel, FirmYear


DEFAULT_INPUT = ROOT / "docs" / "prototype" / "eqs_data.json"
DEFAULT_OUTPUT = ROOT / "docs" / "prototype" / "eqs_data_v3.json"
DEFAULT_CALIBRATION = ROOT / "docs" / "prototype" / "eqs_v3_kospi48_calibration.json"
NUMBER = re.compile(r"[+-]?[0-9]+(?:[.][0-9]+)?")
M2_GAP = re.compile(r"차이 D=([+-]?[0-9]+(?:[.][0-9]+)?)%p")


def numbers(note: str) -> list[float]:
    return [float(value) for value in NUMBER.findall(note)]


def m2_gap(note: str) -> float:
    match = M2_GAP.search(note)
    if match is None:
        raise ValueError("Missing labelled M2 receivable gap")
    return float(match.group(1)) / 100.0


def history_value(record: dict, key: str, year: int) -> float:
    history = record["history"]
    position = history["years"].index(year)
    return float(history[key][position])


def is_financial(record: dict) -> bool:
    return record["modules"]["M2"].get("score") is None


def panel_from_record(record: dict) -> FirmPanel:
    modules = record["modules"]
    m3_numbers = numbers(modules["M3"]["note"])
    m5_numbers = numbers(modules["M5"]["note"])
    if not m3_numbers or not m5_numbers:
        raise ValueError(f"Missing raw M3/M5 metric: {record['name']}")

    debt_to_equity = m3_numbers[0] / 100.0
    equity_cagr = m5_numbers[0] / 100.0
    latest_equity = float(record["latest_year"]["total_equity"])
    if latest_equity <= 0 or equity_cagr <= -1:
        raise ValueError(f"Invalid equity metric: {record['name']}")

    equity_2023 = latest_equity / (1 + equity_cagr) ** 2
    equity_2024 = latest_equity / (1 + equity_cagr)
    years: list[FirmYear] = []
    for year, equity in ((2023, equity_2023), (2024, equity_2024), (2025, latest_equity)):
        revenue = history_value(record, "revenue", year)
        operating_income = history_value(record, "operating_income", year)
        operating_cashflow = history_value(record, "operating_cashflow", year)
        years.append(
            FirmYear(
                year=year,
                revenue=revenue,
                operating_income=operating_income,
                operating_cashflow=operating_cashflow,
                total_equity=equity,
            )
        )

    years[-1].total_liabilities = debt_to_equity * latest_equity
    if not is_financial(record):
        try:
            receivable_gap = m2_gap(modules["M2"]["note"])
        except ValueError as exc:
            raise ValueError(f"Missing raw M2 metric: {record['name']}") from exc
        revenue_growth = years[-1].revenue / years[-2].revenue - 1
        receivable_growth = revenue_growth + receivable_gap
        if receivable_growth <= -0.99:
            raise ValueError(f"Invalid M2 growth metric: {record['name']}")
        years[-2].accounts_receivable = 100.0
        years[-1].accounts_receivable = 100.0 * (1 + receivable_growth)

    return FirmPanel(
        corp_code=record["corp_code"],
        corp_name=record["name"],
        industry_code="64" if is_financial(record) else None,
        years=years,
    )


def module_payload(result) -> dict[str, dict]:
    labels = {
        "M1": "현금이익률",
        "M2": "매출 회수 건전성",
        "M3": "부채 건전성",
        "M4": "본업 안정성",
        "M5": "자본 성장성",
    }
    return {
        module.name: {"label": labels[module.name], "score": module.score, "note": module.note}
        for module in result.modules
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--calibration-output", type=Path, default=DEFAULT_CALIBRATION)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    panels = [panel_from_record(record) for record in source]
    # 전체 상장사 단계에서는 금융도 20개 이상을 요구한다. 이 파일럿에는 금융사가
    # 8개뿐이므로 비금융과 섞지 않고 금융 내부의 상대 비교만 허용한다.
    calibration = build_calibration(panels, min_peers=20, financial_min_peers=5)
    output: list[dict] = []
    for record, panel in zip(source, panels, strict=True):
        result = compute_eqs(panel, calibration)
        item = deepcopy(record)
        item["modules"] = module_payload(result)
        item["total"] = result.total
        item["grade"] = result.grade
        item["industry_code"] = panel.industry_code
        item["eqs_method"] = "v3_kospi48_market_percentile_pilot"
        item["eqs_excluded"] = result.excluded
        output.append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    calibration_payload = calibration.as_dict() | {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "KOSPI 48 pilot; finance-only peers (minimum 5), market fallback otherwise",
        "source": str(args.input),
        "panel_count": len(panels),
    }
    args.calibration_output.write_text(
        json.dumps(calibration_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Recalculated {len(output)} records: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
