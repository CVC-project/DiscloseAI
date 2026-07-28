"""Synchronize V3 EQS results into the corporation dossier payloads.

The integration v2 map reads ``integration/data/eqs_summary.json``, while the
corporation dossier's EQS tab reads a separate ``integration/dossier/data/
firm_<ticker>.json`` payload.  Keep those two presentation paths aligned with
the canonical financial export.

Usage:
    python scripts/sync_dossier_eqs_v3.py          # update dossier payloads
    python scripts/sync_dossier_eqs_v3.py --check  # fail if they are stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "modules" / "financial" / "data" / "eqs_data.json"
DOSSIER_DIR = ROOT / "integration" / "dossier" / "data"


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _module_order(modules: dict) -> list[str]:
    names = list(modules)
    if all(name.startswith("F") for name in names):
        return sorted(names, key=lambda name: int(name[1:]) if name[1:].isdigit() else 99)
    return sorted(names, key=lambda name: int(name[1:]) if name[:1] == "M" and name[1:].isdigit() else 99)


def _v3_eqs(record: dict, existing: dict) -> dict:
    """Retain historical raw metrics, but replace the user-facing V3 result."""
    old_modules = {
        module.get("name"): module
        for module in (existing.get("eqs", {}).get("modules") or [])
        if isinstance(module, dict)
    }
    modules = []
    current_modules = record.get("modules") or {}
    for name in _module_order(current_modules):
        current = record["modules"].get(name, {})
        previous = old_modules.get(name, {})
        modules.append(
            {
                "name": name,
                "score": current.get("score"),
                "raw": previous.get("raw"),
                "note": current.get("note", ""),
            }
        )

    return {
        "total": record.get("total"),
        "grade": record.get("grade"),
        "excluded": record.get("eqs_excluded", []),
        "modules": modules,
        "method": record.get("eqs_method"),
    }


def _sync_payload(record: dict, payload: dict) -> bool:
    next_eqs = _v3_eqs(record, payload)
    next_header = {
        **(payload.get("_hdr") or {}),
        "corp_name": record["name"],
        "corp_code": record["corp_code"],
        "total": f"{record['total']:.1f}" if record.get("total") is not None else "-",
        "grade": record.get("grade") or "-",
    }
    changed = payload.get("eqs") != next_eqs or payload.get("_hdr") != next_header
    payload["eqs"] = next_eqs
    payload["_hdr"] = next_header
    return changed


def sync(*, check: bool) -> tuple[int, int, list[str]]:
    records = _load_json(SOURCE)
    by_ticker = {
        str(record["stock_code"]).zfill(6): record
        for record in records
        if record.get("stock_code")
    }
    changed = 0
    missing = []

    for path in sorted(DOSSIER_DIR.glob("firm_*.json")):
        ticker = path.stem.removeprefix("firm_")
        record = by_ticker.get(ticker)
        if record is None:
            missing.append(ticker)
            continue
        payload = _load_json(path)
        if _sync_payload(record, payload):
            changed += 1
            if not check:
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8",
                )

    return len(by_ticker), changed, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report stale dossier EQS data")
    args = parser.parse_args()
    source_count, changed, missing = sync(check=args.check)
    print(f"canonical={source_count}, stale_or_updated={changed}, unmatched={len(missing)}")
    if missing:
        print("unmatched tickers: " + ", ".join(missing))
    if args.check and (changed or missing):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
