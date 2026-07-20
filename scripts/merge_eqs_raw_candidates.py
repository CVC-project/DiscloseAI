"""Create a reviewable EQS panel set with quality-gated raw DART recovery data."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.collect_eqs_v3_panels import _panel_from_dict, _panel_to_dict, load_panels


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_mergeable(audit_record: dict) -> bool:
    """Keep source-table anomalies out of the automatic candidate merge."""
    if audit_record.get("status") != "auto_pass":
        return False
    return not any(
        str(flag).endswith("revenue_to_assets_outlier")
        for flag in audit_record.get("review_flags", [])
    )


def is_partial_current_eligible(audit_record: dict) -> bool:
    """Allow current one/two-year panels only for M2/M3 partial scoring.

    M1, M4 and M5 each require a three-year history. M2 and M3 do not, so a
    company with a structurally verified 2024-2025 source can still receive a
    clearly partial EQS result. Old one-year records are deliberately excluded:
    they do not describe the 2025 investment state.
    """
    if audit_record.get("blocking_reasons") != ["fewer_than_3_recovered_years"]:
        return False
    years = audit_record.get("recovered_years", [])
    if not years or max(years) < 2025:
        return False
    ready = audit_record.get("module_input_eligibility", {})
    if not (ready.get("M2") or ready.get("M3")):
        return False
    return not any(
        str(flag).endswith("revenue_to_assets_outlier")
        for flag in audit_record.get("review_flags", [])
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-panels", type=Path, required=True)
    parser.add_argument("--raw-panels", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--include-partial-current",
        action="store_true",
        help="Also merge verified 2024-2025 M2/M3-only candidates.",
    )
    args = parser.parse_args()

    base_payload = load_json(args.base_panels)
    merged = load_panels(args.base_panels)
    raw_by_code = {
        item["corp_code"]: item for item in load_json(args.raw_panels).get("companies", [])
    }
    audit_records = load_json(args.audit).get("companies", [])

    added: list[dict] = []
    added_partial: list[dict] = []
    skipped_existing: list[str] = []
    skipped_quality: list[str] = []
    for record in audit_records:
        code = record.get("corp_code")
        full_candidate = is_mergeable(record)
        partial_candidate = args.include_partial_current and is_partial_current_eligible(record)
        if not full_candidate and not partial_candidate:
            skipped_quality.append(code)
            continue
        if code in merged:
            skipped_existing.append(code)
            continue
        raw = raw_by_code.get(code)
        if raw is None:
            skipped_quality.append(code)
            continue
        panel = _panel_from_dict(raw)
        merged[code] = panel
        target = added if full_candidate else added_partial
        target.append(
            {
                "corp_code": code,
                "stock_code": raw.get("stock_code"),
                "corp_name": raw.get("corp_name"),
                "recovered_years": [item.year for item in panel.years],
            }
        )

    output = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "years": base_payload.get("years", []),
        "attempted_corp_codes": sorted(
            set(base_payload.get("attempted_corp_codes", [])) | set(merged)
        ),
        "method": "standard OpenDART panels plus raw DART XML candidates that passed structural quality gates",
        "panels": [_panel_to_dict(panel) for panel in merged.values()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "generated_at": output["generated_at"],
        "base_panel_count": len(load_panels(args.base_panels)),
        "merged_panel_count": len(merged),
        "added_raw_candidate_count": len(added),
        "added_partial_current_candidate_count": len(added_partial),
        "added_raw_candidates": added,
        "added_partial_current_candidates": added_partial,
        "skipped_existing_count": len(skipped_existing),
        "skipped_quality_count": len(skipped_quality),
        "skipped_quality_corp_codes": skipped_quality,
        "policy": (
            "auto_pass only; revenue_to_assets_outlier remains manual hold"
            + ("; verified current M2/M3-only panels included" if args.include_partial_current else "")
        ),
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("base_panel_count", "merged_panel_count", "added_raw_candidate_count", "added_partial_current_candidate_count", "skipped_quality_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
