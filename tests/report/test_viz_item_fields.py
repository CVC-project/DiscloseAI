# -*- coding: utf-8 -*-
"""V-112 회귀 — viz_data 원소 **내부 필드**까지 검사하는 게이트 (2026-08-05).

실사고(하이브 352820 완전성 감사): `k6`이 `why.viz="vBubbles"`에 `viz_data.segs=[{l,v,p}]`를
넣었는데 렌더러(`integration/dossier/galaxy.html` `vBubbles`)는 `{l,rev,op}`를 읽는다.
`Math.sqrt(s.rev)` → `Math.sqrt(undefined)` = NaN이 되어 cx/r/x/y가 전부 NaN으로 찍히며
**차트 박스가 통째로 공백**으로 렌더됐다(콘솔 에러 21건).

종전 `VIZ_SCHEMA` 게이트는 상위 키(`segs`)가 list인지만 봐서 이 사고를 그대로 통과시켰다
— R6.3-7의 '빈 박스 사고 방지' 취지를 상위 키 한 겹으로만 지키고 있었던 셈이다.
`VIZ_ITEM_FIELDS`는 렌더러가 실제로 읽는 필드 이름에서 뽑았다.
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


@pytest.mark.parametrize("path", _goldens())
def test_viz_item_fields_present(path):
    """전 골든의 viz_data 원소가 렌더러가 읽는 필드를 갖췄는지."""
    g = json.load(open(path, encoding="utf-8"))
    cards = list(g.get("dives", {}).items()) + [
        (a.get("n", "?"), a) for a in (g.get("appendix") or [])
    ]
    bad = []
    for key, d in cards:
        w = d.get("why") or {}
        viz = w.get("viz")
        if viz not in CG.VIZ_ITEM_FIELDS:
            continue
        top = CG.VIZ_SCHEMA[viz][0]
        need = CG.VIZ_ITEM_FIELDS[viz]
        for i, it in enumerate((w.get("viz_data") or {}).get(top) or []):
            miss = need - set(it) if isinstance(it, dict) else need
            if miss:
                bad.append(f"{key}.{viz}.{top}[{i}] 누락 {sorted(miss)}")
    assert not bad, f"{os.path.basename(path)}: {bad}"


def test_gate_detects_wrong_field_names():
    """게이트가 필드명 불일치를 실제로 FAIL로 잡는지(음성 테스트)."""
    need = CG.VIZ_ITEM_FIELDS["vBubbles"]
    assert need == {"l", "rev", "op"}
    # 사고 당시 데이터 형태
    bad_item = {"l": "음악", "v": 3.07, "p": 0.16}
    assert need - set(bad_item) == {"rev", "op"}
    # 정상 형태(삼성 T0 k2와 동형)
    ok_item = {"l": "DS 반도체", "rev": 130.1, "op": 24.9}
    assert not (need - set(ok_item))


def test_every_viz_kind_has_item_contract():
    """스칼라형(vPuddle)을 뺀 모든 viz 종류가 내부 필드 계약을 갖는다."""
    listy = {k for k, (_, t) in CG.VIZ_SCHEMA.items() if t is list}
    assert listy == set(CG.VIZ_ITEM_FIELDS), (
        f"계약 없는 viz: {sorted(listy - set(CG.VIZ_ITEM_FIELDS))}"
    )
