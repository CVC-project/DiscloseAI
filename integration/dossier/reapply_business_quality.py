"""One-off: re-apply business_card_quality.normalize_business_payload() to
already-built business_<ticker>.json files in place.

Used when the raw DART summary source (modules/disclosure/data/fulltext/) is
not available locally but the built business_<ticker>.json files are (e.g. a
fresh worktree that only has the committed output, not the uncommitted
source). Preserves the 48 hand-curated tickers while refreshing all other
companies from their extracted DART business-section data.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from business_card_quality import COMPANY_OVERRIDES, normalize_business_payload  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "integration" / "dossier" / "data"
MANIFEST = ROOT / "integration" / "data" / "business_images_manifest.json"
PRODUCT_SEGMENTS = OUT_DIR / "product_service_segments.json"


def curated_tickers() -> set[str]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {item["stock_code"] for item in data["items"]}


def product_segments_by_corp() -> dict[str, list[dict]]:
    if not PRODUCT_SEGMENTS.exists():
        return {}
    data = json.loads(PRODUCT_SEGMENTS.read_text(encoding="utf-8"))
    return {
        str(corp_code).zfill(8): segments
        for corp_code, segments in data.items()
        if isinstance(segments, list)
    }


def main() -> int:
    curated = curated_tickers()
    product_segments = product_segments_by_corp()
    changed = 0
    unchanged = 0
    errors = 0
    for path in sorted(OUT_DIR.glob("business_*.json")):
        if path.name == "business_index.json":
            continue
        ticker = path.stem.replace("business_", "")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {path.name}: {exc}")
            errors += 1
            continue
        corp_code = str(payload.get("corp_code") or "").zfill(8)
        has_authoritative_segments = bool(product_segments.get(corp_code))
        # Keep manually curated cards only when there is no new structured
        # II.2 table to supersede them. The table is the source of truth.
        if ticker in curated and ticker not in COMPANY_OVERRIDES and not has_authoritative_segments:
            continue
        if has_authoritative_segments:
            snippets = payload.setdefault("snippets", {})
            snippets["product_service_segments"] = product_segments[corp_code]
            snippets["segment_breakdown"] = product_segments[corp_code]
        new_payload = normalize_business_payload(payload)
        new_text = json.dumps(new_payload, ensure_ascii=False, indent=2) + "\n"
        old_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if new_text != old_text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
        else:
            unchanged += 1
    print(
        json.dumps(
            {"changed": changed, "unchanged": unchanged, "errors": errors},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
