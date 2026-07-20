"""Summarise score changes between two EQS v3 score files."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path


def load_results(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["corp_code"]: item for item in payload.get("results", [])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    baseline = load_results(args.baseline)
    candidate = load_results(args.candidate)
    common = sorted(set(baseline) & set(candidate))
    deltas = []
    for code in common:
        before = baseline[code].get("total")
        after = candidate[code].get("total")
        if before is not None and after is not None:
            deltas.append(
                {
                    "corp_code": code,
                    "corp_name": candidate[code].get("corp_name"),
                    "before": before,
                    "after": after,
                    "delta": round(after - before, 1),
                }
            )
    new = [candidate[code] for code in sorted(set(candidate) - set(baseline))]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_results": len(baseline),
        "candidate_results": len(candidate),
        "common_results": len(common),
        "new_results": len(new),
        "baseline_scored": sum(item.get("total") is not None for item in baseline.values()),
        "candidate_scored": sum(item.get("total") is not None for item in candidate.values()),
        "common_scored_delta_count": len(deltas),
        "average_common_score_delta": round(statistics.mean(item["delta"] for item in deltas), 3) if deltas else None,
        "median_common_score_delta": round(statistics.median(item["delta"] for item in deltas), 3) if deltas else None,
        "largest_absolute_common_changes": sorted(deltas, key=lambda item: abs(item["delta"]), reverse=True)[:20],
        "new_company_scores": [
            {
                "corp_code": item["corp_code"],
                "corp_name": item.get("corp_name"),
                "total": item.get("total"),
                "grade": item.get("grade"),
                "excluded": item.get("excluded", []),
            }
            for item in new
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("candidate_results", "new_results", "candidate_scored", "average_common_score_delta")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
