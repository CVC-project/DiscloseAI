# -*- coding: utf-8 -*-
"""build_galaxy_lite_index.py — dossier/data/galaxy_lite_*.json 을 스캔해 galaxy_lite_index.json 생성.

골든 매니페스트(build_galaxy_index.py → galaxy_index.json)의 lite 판본.
v2 오버레이(bundle.jsx)가 두 매니페스트를 함께 fetch해 '현금 은하수' 탭을 판정한다:
  - 골든 보유 티커 → galaxy.html      (둘 다 있으면 골든 우선)
  - lite 보유 티커 → galaxy_lite.html
새 lite 완주 시 이 스크립트만 재실행하면 UI에 자동 등록된다 (하드코딩 0 — V-054 계보).

실행: python integration/dossier/build_galaxy_lite_index.py
"""

from __future__ import annotations

import glob
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")
_OUT = os.path.join(_DATA, "galaxy_lite_index.json")


def build() -> tuple[list[dict[str, str]], list[tuple[str, str]]]:
    """(매니페스트 등재분, 미완주로 제외한 것) — 제외분은 호출부가 눈에 보이게 출력한다."""
    entries: list[dict[str, str]] = []
    skipped: list[tuple[str, str]] = []
    for p in sorted(glob.glob(os.path.join(_DATA, "galaxy_lite_*.json"))):
        base = os.path.basename(p)
        if base == "galaxy_lite_index.json":
            continue
        t = base[len("galaxy_lite_") : -len(".json")]
        try:
            G = json.load(open(p, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        corp = G.get("corp") or {}
        std = G.get("std_ref") or {}
        # **완주 정의 = 델타 카드 + '눈여겨볼 곳' 1장 이상.** 델타만 있는 반제품을 매니페스트에
        # 올리면 사용자에겐 빈 섹션이 그냥 '없는 화면'으로 보인다 — 탭을 켜는 기준은 완주로 둔다.
        if not corp.get("ticker") or not G.get("cards"):
            continue
        if not G.get("notes"):
            skipped.append((t, corp.get("name", "")))
            continue
        entries.append(
            {
                "ticker": t,
                "name": corp.get("name", ""),
                "cluster": corp.get("cluster", ""),
                "std_ticker": std.get("ticker", ""),
                "std_name": std.get("name", ""),
                "notes": len(G.get("notes") or []),
            }
        )
    manifest = {
        "tickers": [e["ticker"] for e in entries],
        "count": len(entries),
        "entries": entries,
        "note": "galaxy lite(표준-델타) 탭 활성 티커 — build_galaxy_lite_index.py가 생성. "
        "등재 기준 = 델타 카드 + 눈여겨볼 곳 1장 이상(완주). 골든(galaxy_index.json)과 겹치면 골든이 우선.",
    }
    json.dump(manifest, open(_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return entries, skipped


if __name__ == "__main__":
    es, sk = build()
    # 콘솔이 cp949인 윈도우에서 em dash 등 비cp949 문자를 print하면 크래시한다(FN-001 계보) — ASCII 구분자 사용
    print(f"galaxy_lite_index.json 생성: {len(es)}개")
    for e in es:
        print(f"  {e['ticker']} {e['name']} / 표준 {e['std_name']}({e['std_ticker']}) / 주목할점 {e['notes']}장")
    if sk:
        # 조용히 빠지면 '왜 탭이 안 켜지지'로 시간을 쓴다 — 제외분은 항상 이유와 함께 보인다
        print(f"미등재(눈여겨볼 곳 0장 = 미완주) {len(sk)}개: " + ", ".join(f"{t} {n}" for t, n in sk))
