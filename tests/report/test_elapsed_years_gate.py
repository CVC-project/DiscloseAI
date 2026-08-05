# -*- coding: utf-8 -*-
"""V-112 C 승격 회귀 — 경과연수 서술("N년 만에")의 창 길이 검산 (2026-08-06).

숫자는 전부 원문에 있고 **세는 방식만** 틀리는 계열이라 브래킷 화이트리스트(§2)도
항등식(§4)도 못 잡는다. V-102ⓑ(추세 서술)·V-104(e)(기준연도 혼용)에 이어 하이브에서
**"5년 만에 플러스"가 3곳**에 퍼진 것이 3회째라 게이트로 승격했다(fin FY21이 이미
[+2.23조]라 4년 만이 맞다).

계약: `N년 만에`는 두 뜻으로 쓰인다.
  ⓐ "N년 만에 **처음/첫**" — 창 안에 한 번도 없던 일. N == 창 길이(5)가 정당하다.
  ⓑ "N년 만에 (다시) X" — 마지막으로 X였던 게 N년 전. 그 연도가 창 안에 있어야
     재도출되므로 **N ≤ 창-1(4)**. 하이브가 여기서 틀렸다.
→ N ≥ 창 길이인데 `처음`·`첫` 표지가 인접하지 않으면 갭.

⚠️ `N년 내리|연속|내내`의 series 재계수는 **게이트로 기각**했다(2026-08-06 `--all` 실측
9본 9건이 전부 정당한 불일치 — 런이 말단이 아님 / 서술 지표가 five.key와 다름 / 부호 반대).
"""
import glob
import json
import os
import re

import pytest

from modules.report import check_golden as CG

_DATA = os.path.join("integration", "dossier", "data")


def _goldens():
    return sorted(
        p for p in glob.glob(os.path.join(_DATA, "galaxy_*.json"))
        if os.path.basename(p) != "galaxy_index.json"
    )


def _blob(d):
    return " ".join(t for t in CG._texts(d) if isinstance(t, str))


@pytest.mark.parametrize("path", _goldens())
def test_elapsed_years_within_window(path):
    """전 골든의 'N년 만에'가 창 길이 안에서 재도출 가능한지."""
    g = json.load(open(path, encoding="utf-8"))
    span = max(
        [len(a) for a in (g.get("series") or {}).values() if isinstance(a, list)] or [5]
    )
    bad = []
    for k, d in (g.get("dives") or {}).items():
        b = _blob(d)
        for m in re.finditer(r"(\d+)년\s*만에", b):
            ctx = b[max(0, m.start() - 40): m.end() + 30]
            if int(m.group(1)) >= span and not re.search(r"처음|첫", ctx):
                bad.append(f"{k}: {m.group(0)} — {b[max(0, m.start() - 25): m.end() + 25]}")
    assert not bad, f"{os.path.basename(path)}: {bad}"


def test_gate_detects_overcounted_claim():
    """게이트가 하이브 사고 형태를 실제로 FAIL로 잡는지(음성 테스트)."""
    span, pat = 5, re.compile(r"(\d+)년\s*만에")

    def hit(text):
        m = pat.search(text)
        ctx = text[max(0, m.start() - 40): m.end() + 30]
        return int(m.group(1)) >= span and not re.search(r"처음|첫", ctx)

    # 사고 당시 문장(fin FY21이 이미 플러스라 '4년 만에'가 맞다)
    assert hit("올해는 [+0.19조]가 들어와 5년 만에 방향이 플러스로 뒤집혔어요.")
    # 정정본
    assert not hit("올해는 [+0.19조]가 들어와 4년 만에 방향이 플러스로 뒤집혔어요.")
    # 정당한 ⓐ 용법 — 창 전체에 한 번도 없던 일
    assert not hit("올해 [5.49조]에 머물러 5년 만에 처음으로 걸음을 멈췄어요.")
    assert not hit("불황에 손상·평가손실이 겹쳐 5년 만에 첫 적자를 냈어요.")


def test_consecutive_run_recount_stays_rejected():
    """'N년 내리' 재계수를 게이트에 되살리지 말 것 — 9본 9건이 정당한 불일치였다."""
    src = open(os.path.join("modules", "report", "check_golden.py"), encoding="utf-8").read()
    body = src[src.index("# ── 19)"):]
    assert "년\\s*(?:내리" not in body and "내리|연속|내내" not in body.split("⚠️")[0], (
        "§19가 '내리/연속/내내' 재계수를 강제하고 있다 — 기존 골든 9본이 거짓 양성으로 깨진다"
    )
