"""KOSPI 48에 EQS v2 일괄 산출 → eqs_data.json 갱신.

실행:
    PYTHONIOENCODING=utf-8 python scripts/run_eqs_v2.py
"""

from __future__ import annotations

import sys

from modules.financial.batch import (
    KOSPI_TOP_50,
    build_per_firm_dashboards,
    build_sector_stats,
    collect_batch,
    export_for_frontend,
    persist_to_db,
    summarize,
)
from modules.financial.dashboard import build_dashboard, build_ranking_dashboard
from modules.financial.translator import extract_highlights, translate_all


def main() -> int:
    print(f"[v2] universe: {len(KOSPI_TOP_50)}개 종목")
    records = collect_batch(KOSPI_TOP_50, range(2021, 2026), sleep_sec=0.1)

    summary = summarize(records)
    print("\n=== Summary ===")
    print(f"  total: {summary['total_count']}, success: {summary['success_count']}, fail: {summary['fail_count']}")
    print(f"  grade dist: {summary['grade_distribution']}")
    print(f"  module means: {summary['module_means']}")
    print(f"  avg total: {summary['avg_total']}")

    out_path = export_for_frontend(records)
    print(f"\n[export] {out_path}")

    db_info = persist_to_db(records)
    print(f"[db persist] financial_local: written={db_info['written']} skipped={db_info['skipped']}")

    sector_info = build_sector_stats(records)
    print(f"[sectors] {sector_info}")

    # 1) 50기업 비교 대시보드 (kospi50_ranking.html)
    rank_path = build_ranking_dashboard(records, year_range="2021-2025")
    print(f"[ranking] {rank_path}")

    # 2) 단일기업 dashboard 샘플 — 삼성전자
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

    # 3) 47개 기업 단독 dashboard (firm_<ticker>.html) — 통합 대시보드 오버레이용
    dash_info = build_per_firm_dashboards(records)
    print(f"[per-firm dashboards] written={dash_info['written']} skipped={dash_info['skipped']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
