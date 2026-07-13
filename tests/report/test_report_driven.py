# -*- coding: utf-8 -*-
"""R6.9 보고서 기반 원칙 회귀 — 골든이 아니라 그 회사 사업보고서가 구조를 정의한다.

방향A: 회사에 없는 항목(예: 플랫폼사의 cogs)은 골든에 있어도 '누락'으로 요구되지 않아야 한다
       (0/— 표시 강제 금지).
방향B: 회사 데이터에 근거 없는 dive가 존재하면(골든 흉내 0-표시) FAIL이어야 한다.
방향C: 회사 고유 신규 dive(골든 universe 밖)는 커버리지 위반이 아니다 — 원장 new-dive 라우팅과 짝.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modules.report import check_golden as cg  # noqa: E402

_DATA = cg._DATA
FIXTURE = os.path.join(_DATA, "galaxy_zztest_rd.json")


def _base():
    """SK 골든을 복제해 가상 회사 픽스처로 사용."""
    with open(os.path.join(_DATA, "galaxy_000660.json"), encoding="utf-8") as f:
        return json.load(f)


def _run(G):
    with open(FIXTURE, "w", encoding="utf-8") as f:
        json.dump(G, f, ensure_ascii=False)
    try:
        # 픽스처는 reports.db에 없음 → 원장(§7)은 자동 스킵, 커버리지·정합 규칙만 검사됨
        G["corp"]["rcept_no"] = "00000000000000"
        with open(FIXTURE, "w", encoding="utf-8") as f:
            json.dump(G, f, ensure_ascii=False)
        return cg.check("zztest_rd")
    finally:
        os.remove(FIXTURE)


def test_direction_a_absent_item_not_required():
    """cogs가 보고서에 없는 회사(플랫폼형) — k3·k4 dive가 없어도 '누락' 갭이 없어야 한다."""
    G = _base()
    for key in ("cogs", "gross"):
        G["series"].pop(key, None)
    for k in ("k3", "k4"):
        G["dives"].pop(k, None)
    # 근거 없어진 패널 행·잔재도 제거(순수 방향A 검증)
    G["panels"]["B"] = [r for r in G["panels"]["B"] if r["row"] not in ("is-cogs", "is-grossprofit")]
    gaps = _run(G)
    bad = [g for g in gaps if "'k3'" in g or "'k4'" in g]
    assert not bad, f"보고서에 없는 항목을 골든 기준으로 요구: {bad}"


def test_direction_b_unfounded_dive_fails():
    """cogs가 없는데 k3 dive가 존재(0-표시 흉내) — '근거 없음' FAIL이어야 한다."""
    G = _base()
    G["series"].pop("cogs", None)
    G["series"].pop("gross", None)
    assert "k3" in G["dives"]  # dive는 남겨둠
    gaps = _run(G)
    assert any("'k3'" in g and "근거 없음" in g for g in gaps), \
        f"근거 없는 dive를 통과시킴 (0-표시 위험): {[g for g in gaps if 'k3' in g]}"


def test_direction_c_novel_dive_allowed():
    """회사 고유 신규 dive(예: 콘텐츠자산) — universe 밖이므로 커버리지 위반이 아니어야 한다."""
    G = _base()
    G["dives"]["contentasset"] = {
        "z": "D", "zc": "steel", "en": "CONTENT ASSETS", "name": "콘텐츠자산",
        "amt": "1.0조", "raw_mn": 1000000, "color_key": "steel", "row": "bs-content",
        "what": ["이 회사 고유의 [1.0조] 자산이에요.", "보고서 주석에 근거한 신규 항목이에요 — [5년]째 상각 중이에요."],
        "links": [{"t": "BS", "row": "bs-assets", "txt": "자산총계의 일부예요", "a": "176.1"}],
        "lnote": "", "why": {"sub": "신규", "body": ["회사 고유 항목이에요."], "viz": None},
        "five": {"skip": "골든 외 신규 항목 — 시계열 매핑 전이에요."},
    }
    gaps = _run(G)
    bad = [g for g in gaps if "contentasset" in g and "커버리지" in g]
    assert not bad, f"회사 고유 신규 dive를 커버리지 위반으로 처리: {bad}"


def test_both_goldens_still_pass():
    """원칙 전환 후에도 두 골든은 PASS."""
    assert cg.check("000660") == []
    assert cg.check("005930") == []
