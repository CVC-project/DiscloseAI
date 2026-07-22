"""Score collected financial panels with a persisted EQS v3 calibration table."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.eqs.calibration import load_calibration
from modules.financial.eqs.score import compute_eqs
from scripts.collect_eqs_v3_panels import DEFAULT_OUT, load_panels


DEFAULT_CALIBRATION = ROOT / "modules" / "financial" / "data" / "eqs_v3_calibration.json"
DEFAULT_RESULTS = ROOT / "modules" / "financial" / "data" / "eqs_v3_scores.json"


def result_to_dict(result) -> dict:
    return {
        "corp_code": result.corp_code,
        "corp_name": result.corp_name,
        "industry_code": result.industry_code,
        "total": result.total,
        "grade": result.grade,
        "excluded": result.excluded,
        "modules": [
            {
                "name": module.name,
                "score": module.score,
                "raw": module.raw,
                "note": module.note,
                "weight": module.weight,
            }
            for module in result.modules
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panels", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()

    panels = list(load_panels(args.panels).values())
    calibration = load_calibration(args.calibration)
    results = [result_to_dict(compute_eqs(panel, calibration)) for panel in panels]
    results.sort(key=lambda item: (item["total"] is None, -(item["total"] or 0)))

    payload = {
        "schema_version": 1,
        "method": "eqs_v3_industry_percentile",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "panel_count": len(panels),
        "calibration_profile_count": len(calibration.profiles),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    scored = sum(item["total"] is not None for item in results)
    print(f"Scored {scored}/{len(results)} panels: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
