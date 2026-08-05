"""One-off: inject audit_opinion/KAM/emphasis into business_<ticker>.json.

Source: modules/disclosure/data/disclosure.db's company_summary table, which
this worktree does not have populated (the full-market disclosure summary
work landed on a different, still-unmerged branch). Reads it from an
explicit --db-path instead so this stays a local, non-committed data pull —
the *output* (business_<ticker>.json with an added "audit" field) is what
gets committed, not the source DB.

Usage:
  python integration/dossier/inject_audit_summary.py --db-path <path to disclosure.db>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "integration" / "dossier" / "data"
MASTER_PATH = OUT_DIR / "company_master.json"
MANIFEST = ROOT / "integration" / "data" / "business_images_manifest.json"


def curated_tickers() -> set[str]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {item["stock_code"] for item in data["items"]}


def ticker_by_corp_code() -> dict[str, str]:
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    out = {}
    for row in master.get("companies", []):
        cc = row.get("corp_code")
        t = row.get("ticker")
        if cc and t:
            out[str(cc).zfill(8)] = str(t).zfill(6)
    return out


def load_audit_by_corp(db_path: str) -> dict[str, dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT corp_code, audit_opinion, kam, emphasis FROM company_summary")
    out: dict[str, dict] = {}
    for row in cur.fetchall():
        corp_code = str(row["corp_code"] or "").zfill(8)
        opinion = (row["audit_opinion"] or "").strip()
        try:
            kam = json.loads(row["kam"] or "[]")
        except Exception:  # noqa: BLE001
            kam = []
        try:
            emphasis = json.loads(row["emphasis"] or "[]")
        except Exception:  # noqa: BLE001
            emphasis = []
        if not opinion and not kam and not emphasis:
            continue
        out[corp_code] = {
            "opinion": opinion or "확인불가",
            "kam": kam if isinstance(kam, list) else [],
            "emphasis": emphasis if isinstance(emphasis, list) else [],
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True)
    args = parser.parse_args()

    curated = curated_tickers()
    corp_to_ticker = ticker_by_corp_code()
    audit_by_corp = load_audit_by_corp(args.db_path)
    ticker_to_corp = {}
    for corp_code, ticker in corp_to_ticker.items():
        ticker_to_corp.setdefault(ticker, corp_code)

    written = 0
    missing = 0
    skipped_curated = 0
    for path in sorted(OUT_DIR.glob("business_*.json")):
        if path.name == "business_index.json":
            continue
        ticker = path.stem.replace("business_", "")
        if ticker in curated:
            skipped_curated += 1
            continue
        corp_code = ticker_to_corp.get(ticker)
        audit = audit_by_corp.get(corp_code) if corp_code else None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if audit:
            payload["audit"] = audit
            written += 1
        else:
            payload.pop("audit", None)
            missing += 1
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "written_with_audit": written,
                "missing_audit": missing,
                "skipped_curated": skipped_curated,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
