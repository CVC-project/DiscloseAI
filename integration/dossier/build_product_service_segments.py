"""Build the structured product/service source used by full-market cards.

Usage example (raw reports can live outside this worktree):
  python integration/dossier/build_product_service_segments.py \
    --fulltext-dir ..\\DiscloseAI\\modules\\disclosure\\data\\fulltext
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from modules.disclosure.product_service_parser import extract_product_service_segments


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fulltext-dir",
        type=Path,
        default=ROOT / "modules" / "disclosure" / "data" / "fulltext",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "integration"
        / "dossier"
        / "data"
        / "product_service_segments.json",
    )
    args = parser.parse_args()

    records: dict[str, list[dict[str, Any]]] = {}
    scanned = 0
    for path in sorted(args.fulltext_dir.glob("*/*/parsed.json")):
        try:
            parsed = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        scanned += 1
        corp_code = str(parsed.get("corp_code") or path.parent.parent.name).zfill(8)
        segments = extract_product_service_segments(parsed)
        if segments:
            records[corp_code] = segments

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(
        json.dumps(
            {"scanned": scanned, "with_product_table": len(records)}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
