# -*- coding: utf-8 -*-
"""build_report_source.py — 사업보고서 '원문 보기' 서빙 데이터 빌더 (integration 서빙 계층).

로직 정본은 modules/report/report_source.py (report 모듈 소유). 이 파일은 그걸 호출해
integration/dossier/data/report_<t>.json + report_index.json(매니페스트)을 쓰는 얇은 래퍼다.
(integration이 modules/report를 read-only import — 서빙 계층 예외 규약.)

실행:
  python integration/dossier/build_report_source.py 005930      # 한 기업
  python integration/dossier/build_report_source.py --all        # galaxy_*.json 전 기업
문서: modules/report/REPORT_SOURCE.md
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modules.report.report_source import build_report_data  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(_HERE, "data")


def build(ticker: str) -> None:
    data = build_report_data(ticker)
    out = os.path.join(_OUT_DIR, f"report_{ticker}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    ns = len(data["statements"])
    nn = len(data["notes"])
    kb = os.path.getsize(out) / 1024
    print(f"[{ticker}] report_{ticker}.json — 재무제표 {ns}본·주석 {nn}개·{kb:.0f}KB")


def write_index() -> None:
    """report_*.json 스캔 → report_index.json(원문 지원 티커 — galaxy.html이 fetch, 404 방지)."""
    ts = sorted(
        os.path.basename(p)[7:-5]
        for p in glob.glob(os.path.join(_OUT_DIR, "report_*.json"))
        if os.path.basename(p) != "report_index.json"
    )
    with open(os.path.join(_OUT_DIR, "report_index.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "tickers": ts,
                "note": "사업보고서 원문 지원 티커 — build_report_source.py 생성",
            },
            f,
            ensure_ascii=False,
        )
    print(f"  report_index.json — {len(ts)}개: {ts}")


def _golden_tickers() -> list[str]:
    return sorted(
        os.path.basename(p)[7:-5]
        for p in glob.glob(os.path.join(_OUT_DIR, "galaxy_*.json"))
        if os.path.basename(p) != "galaxy_index.json"
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--all":
        for t in _golden_tickers():
            try:
                build(t)
            except Exception as e:  # noqa: BLE001 — 데이터 없는 골든은 건너뛰고 계속
                print(f"[{t}] 건너뜀: {e}")
    else:
        build(args[0] if args else "005930")
    write_index()
