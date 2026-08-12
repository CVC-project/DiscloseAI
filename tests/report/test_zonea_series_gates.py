# -*- coding: utf-8 -*-
"""V-111 A · V-112 B 승격 회귀 — Zone A 기초현금 정합 / series↔패널 정합 (2026-08-06).

둘 다 "각 절은 통과하는데 절과 절 **사이**를 아무도 안 보던" 구멍이다.

· V-111 A: `pbs-cash`(Zone A '작년 말 통장')에 **당기말** 현금을 넣었는데 표시 반올림이
  우연히 같아 `--strict` 16개 절이 전부 통과했다(크래프톤 259960).
  §5는 Zone A에 grp가 없어 미적용, §6은 그 값이 패널에 실존해 통과, §13은 `cf-begincash`만 본다.
· V-112 B: 차트를 그리는 `series`와 카드가 읽는 패널이 **다른 값을 가리킨 채** 통과했다
  (하이브 352820 `cash` FY25 — series 0.54 vs 패널 "0.53"). §4는 series끼리, §6은 패널끼리만 본다.

⚠️ 게이트 18은 **실계정 키만** 본다 — 파생키(`gross`·`tci`)는 이미 반올림된 값끼리 계산해
   실계정과 ±0.1 어긋나는 게 전 골든 11본에 퍼져 있고(2026-08-06 실측) 그 11본은 k4 산문이
   전부 옛 파생값을 인용한다. 근본 수리(`series.py`가 매출총이익 실계정 우선)는 별도 캐스케이드.
"""
import glob
import json
import os

import pytest

from modules.report import check_golden as CG

_DATA = os.path.join("integration", "dossier", "data")


def _goldens():
    return sorted(
        p for p in glob.glob(os.path.join(_DATA, "galaxy_*.json"))
        if os.path.basename(p) != "galaxy_index.json"
    )


def _rows(g):
    return {r.get("row"): r for z, rs in (g.get("panels") or {}).items() for r in (rs or [])}


@pytest.mark.parametrize("path", _goldens())
def test_zone_a_begin_cash_matches_cashflow(path):
    """Zone A 기초현금 == 현금흐름표 기초의 현금 (둘 다 있을 때)."""
    R = _rows(json.load(open(path, encoding="utf-8")))
    a, b = R.get("pbs-cash"), R.get("cf-begincash")
    if not (a and b) or a.get("raw_mn") is None or b.get("raw_mn") is None:
        pytest.skip("두 행 중 하나가 없다(삼성 T0 등) — 강제 대상 아님")
    assert a["raw_mn"] == b["raw_mn"], (
        f"{os.path.basename(path)} pbs-cash {a['raw_mn']:,} ≠ cf-begincash {b['raw_mn']:,}"
    )


@pytest.mark.parametrize("path", _goldens())
def test_series_last_matches_panel(path):
    """series 최종값이 패널 표시값과 같은 원값에서 나왔는지(series 소수 자릿수 기준)."""
    g = json.load(open(path, encoding="utf-8"))
    R, S = _rows(g), (g.get("series") or {})
    # V-117 — 표시 단위가 티커 속성이므로 환산 제수도 티커에서 읽는다(check_golden §18과 동식).
    #   `/1e6` 고정이면 억 표기 티커에서 1만 배 어긋나 항상 FAIL이다.
    udiv = {"조 원": 1e6, "억 원": 1e2}.get(
        (g.get("corp") or {}).get("unit_label", "조 원"), 1e6)
    bad = []
    for sk, rid in {
        "revenue": "is-revenue", "op": "is-opincome", "ni": "is-netincome",
        "ocf": "cf-op", "icf": "cf-inv", "fin": "cf-fin",
        "cash": "bs-cash", "assets": "bs-assets", "equity": "bs-equity",
    }.items():
        arr, row = S.get(sk), R.get(rid)
        if not (isinstance(arr, list) and arr and row) or row.get("raw_mn") is None:
            continue
        last = arr[-1]
        if not isinstance(last, (int, float)):
            continue
        dec = len(str(last).split(".")[1]) if "." in str(last) else 0
        if abs(round(row["raw_mn"] / udiv, dec) - last) > 10 ** -(dec + 2):
            bad.append(f"{sk}[-1]={last} vs {rid} {row['raw_mn'] / udiv:.{dec + 2}f}")
    assert not bad, f"{os.path.basename(path)}: {bad}"


def test_gate_18_excludes_derived_keys():
    """파생키는 게이트 대상 밖임을 못박는다(범위를 조용히 넓히면 11본이 깨진다)."""
    src = open(os.path.join("modules", "report", "check_golden.py"), encoding="utf-8").read()
    body = src[src.index("SERIES_ROW = {"):]
    body = body[: body.index("}")]
    for derived in ('"gross"', '"tci"'):
        assert derived not in body, f"파생키 {derived}가 SERIES_ROW에 들어왔다 — 11본 회귀 위험"
