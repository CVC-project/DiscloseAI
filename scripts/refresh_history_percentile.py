"""기존 시가총액을 보존한 채 DART만 재수집 → history+percentile 포함 JSON 재생성.

배경: ``run_eqs_v2.py``는 yfinance 호출(시가총액)이 8~10분 소요되므로
시계열·백분위 추가 검증용 빠른 재실행 경로 제공.

실행:
    PYTHONIOENCODING=utf-8 PYTHONPATH=. python scripts/refresh_history_percentile.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from modules.financial.batch import (
    KOSPI_TOP_50,
    build_sector_stats,
    collect_batch,
    export_for_frontend,
    persist_to_db,
    summarize,
)
from modules.financial.dashboard import build_dashboard, build_ranking_dashboard
from modules.financial.translator import extract_highlights, translate_all

EQS_JSON = Path("docs/prototype/eqs_data.json")


def _load_market_caps() -> dict:
    """기존 eqs_data.json에서 corp_code → market_cap 맵 로드."""
    if not EQS_JSON.exists():
        return {}
    try:
        rows = json.loads(EQS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        r["corp_code"]: r.get("market_cap")
        for r in rows
        if r.get("corp_code") and r.get("market_cap") is not None
    }


def main() -> int:
    cap_map = _load_market_caps()
    print(f"[cache] preserved market caps: {len(cap_map)} firms")

    print(f"[v2] universe: {len(KOSPI_TOP_50)}개 종목 — yfinance 비활성화")
    records = collect_batch(
        KOSPI_TOP_50,
        range(2021, 2026),
        sleep_sec=0.1,
        fetch_market_caps=False,
    )

    # 기존 시총을 records에 주입 (yfinance 생략으로 None인 필드 복구)
    for r in records:
        if r.corp and r.market_cap is None:
            r.market_cap = cap_map.get(r.corp.corp_code)

    summary = summarize(records)
    print("\n=== Summary ===")
    print(
        f"  total: {summary['total_count']}, success: {summary['success_count']}, fail: {summary['fail_count']}"
    )
    print(f"  grade dist: {summary['grade_distribution']}")

    out_path = export_for_frontend(records)
    print(f"\n[export] {out_path}")

    db_info = persist_to_db(records)
    print(f"[db persist] financial_local: written={db_info['written']} skipped={db_info['skipped']}")

    sector_info = build_sector_stats(records)
    print(f"[sectors] {sector_info}")

    rank_path = build_ranking_dashboard(records, year_range="2021-2025")
    print(f"[ranking] {rank_path}")

    samsung = next((r for r in records if r.display_name == "삼성전자"), None)
    if samsung and samsung.panel and samsung.eqs:
        latest = samsung.panel.latest()
        if latest is not None:
            single_path = build_dashboard(
                samsung.panel,
                samsung.eqs,
                translate_all(latest),
                extract_highlights(samsung.panel),
            )
            print(f"[firm dashboard] {single_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
