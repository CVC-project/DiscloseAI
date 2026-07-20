"""Apply all-KRX EQS v3 scores to an existing company subset export.

The prototype already contains display metadata such as market cap, DART links,
and financial history. This script only replaces the EQS fields with scores
calibrated against the full listed-company KSIC universe and writes a separate
comparison file for review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MODULE_LABELS = {
    "M1": "현금이익률",
    "M2": "매출 회수 건전성",
    "M3": "부채 건전성",
    "M4": "본업 안정성",
    "M5": "자본 성장성",
}

DEFAULT_METHOD = "v3_all_krx_percentile_financial_short_history_2021_2025"


def score_map(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["corp_code"]: item for item in payload.get("results", [])}


def current_module_scores(record: dict) -> dict[str, float | None]:
    modules = record.get("modules", {})
    if not isinstance(modules, dict):
        return {}
    return {
        name: module.get("score") if isinstance(module, dict) else None
        for name, module in modules.items()
    }


def module_payload(result: dict) -> dict[str, dict]:
    return {
        module["name"]: {
            "label": MODULE_LABELS[module["name"]],
            "score": module["score"],
            "note": module["note"],
            "weight": module.get("weight", 1.0),
        }
        for module in result["modules"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--comparison-output", type=Path, required=True)
    parser.add_argument("--method", default=DEFAULT_METHOD)
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    scores = score_map(args.scores)
    missing = [record.get("name", record.get("corp_code", "unknown")) for record in records if record.get("corp_code") not in scores]
    if missing:
        raise SystemExit(f"Missing full-market scores for: {', '.join(missing)}")

    comparison: list[dict] = []
    for record in records:
        result = scores[record["corp_code"]]
        old_total = record.get("total")
        old_modules = current_module_scores(record)
        new_modules = module_payload(result)
        comparison.append(
            {
                "name": record.get("name"),
                "corp_code": record["corp_code"],
                "previous_total": old_total,
                "v3_total": result["total"],
                "delta": (
                    round(result["total"] - old_total, 1)
                    if isinstance(result["total"], (int, float)) and isinstance(old_total, (int, float))
                    else None
                ),
                "previous_modules": old_modules,
                "v3_modules": {name: module["score"] for name, module in new_modules.items()},
            }
        )
        record["modules"] = new_modules
        record["total"] = result["total"]
        record["grade"] = result["grade"]
        record["industry_code"] = result["industry_code"]
        record["eqs_method"] = args.method
        record["eqs_excluded"] = result["excluded"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    args.comparison_output.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Exported {len(records)} records: {args.output}")
    print(f"Comparison: {args.comparison_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
