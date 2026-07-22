"""수집된 전 상장사 패널에서 EQS v3 업종 보정 JSON을 생성한다."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.eqs.calibration import build_calibration
from scripts.collect_eqs_v3_panels import DEFAULT_OUT, load_panels


DEFAULT_CALIBRATION = ROOT / "modules" / "financial" / "data" / "eqs_v3_calibration.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panels", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--min-peers", type=int, default=20)
    args = parser.parse_args()

    panels = list(load_panels(args.panels).values())
    if not panels:
        raise SystemExit(f"패널 데이터가 없습니다: {args.panels}")
    calibration = build_calibration(panels, min_peers=args.min_peers)
    payload = calibration.as_dict() | {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "panel_count": len(panels),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"보정값 {len(calibration.profiles)}개 생성: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
