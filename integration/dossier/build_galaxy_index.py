# -*- coding: utf-8 -*-
"""build_galaxy_index.py — dossier/data/galaxy_*.json 을 스캔해 galaxy_index.json 매니페스트 생성.

v2 오버레이(bundle.jsx)가 이 매니페스트를 fetch해 '현금 은하수' 탭 활성 티커를 판정한다
(하드코딩 GALAXY_TICKERS 대체 — 새 골든 추가 시 이 스크립트만 재실행하면 UI에 자동 등록).

실행: python -m integration.dossier.build_galaxy_index   (또는 이 파일 직접)
"""

from __future__ import annotations

import glob
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")
_OUT = os.path.join(_DATA, "galaxy_index.json")


def build() -> list[str]:
    tickers = []
    for p in sorted(glob.glob(os.path.join(_DATA, "galaxy_*.json"))):
        base = os.path.basename(p)
        if base == "galaxy_index.json":
            continue
        t = base[len("galaxy_") : -len(".json")]
        # 실제 렌더 가능한지 최소 확인(corp.ticker 존재)
        try:
            G = json.load(open(p, encoding="utf-8"))
            if (G.get("corp") or {}).get("ticker"):
                tickers.append(t)
        except (ValueError, OSError):
            continue
    manifest = {
        "tickers": tickers,
        "count": len(tickers),
        "note": "galaxy 탭 활성 티커 — build_galaxy_index.py가 생성. 새 골든 추가 시 재실행.",
    }
    json.dump(manifest, open(_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return tickers


if __name__ == "__main__":
    ts = build()
    print(f"galaxy_index.json 생성: {len(ts)}개 — {ts}")
