# -*- coding: utf-8 -*-
"""V-099 CF 운전자본 분리 게이트(check_golden --strict §13) 회귀.

원칙: 현금흐름표 **본표에 '영업활동으로 인한 자산·부채의 변동' 집계 라인이 별도로 있는 회사만**
cf-wc 행 분리를 강제한다. 없는 회사에는 강제하지 않는다(R6.9 — 없는 근거로 행을 만들지 않는다).

이 테스트가 지키는 것: ① 게이트가 실제로 발화하는가(무력한 no-op 방지)
② 근거 없는 회사에까지 번지지 않는가(과잉 강제 방지).
로컬 reports.db가 없으면(CI) 전부 skip — 게이트 자체가 DB 근거 기반이라 판정 불가.
"""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modules.report import check_golden as cg  # noqa: E402

_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(cg.__file__))),
    "..",
    "shared",
    "data",
    "reports.db",
)
pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.abspath(_DB)), reason="로컬 reports.db 없음(CI)"
)

WITH_LINE = "005930"  # 본표에 WC 집계 라인 보유(삼성 T0, −9.61조) — 분리 강제 대상
NO_LINE = "010130"  # 본표에 집계 라인 없음(고려아연) — 강제 대상 아님


def _load(ticker):
    with open(
        os.path.join(cg._DATA, f"galaxy_{ticker}.json"), encoding="utf-8"
    ) as f:
        return json.load(f)


def _cf_gaps(ticker, G):
    return [g for g in cg._check_strict(ticker, G, G.get("dives", {})) if "[CF운전자본]" in g]


def _rows(G):
    return [r for z in G.get("panels", {}) for r in G["panels"][z]]


def test_baseline_no_gap():
    """무변경 골든 2본은 §13 갭 0 — 캘리브레이션."""
    assert _cf_gaps(WITH_LINE, _load(WITH_LINE)) == []
    assert _cf_gaps(NO_LINE, _load(NO_LINE)) == []


def test_gate_fires_when_wc_row_removed():
    """본표에 집계 라인이 있는데 cf-wc 행을 없애면(= cf-noncash 뭉뚱그림) FAIL이어야 한다."""
    G = copy.deepcopy(_load(WITH_LINE))
    for z in G["panels"]:
        G["panels"][z] = [r for r in G["panels"][z] if r.get("row") != "cf-wc"]
    gaps = _cf_gaps(WITH_LINE, G)
    assert gaps and "cf-wc 행 없음" in gaps[0], f"뭉뚱그림을 통과시킴: {gaps}"


def test_gate_fires_on_value_mismatch():
    """cf-wc 값이 본표 집계 라인과 어긋나면(부호·집계 오류) FAIL이어야 한다."""
    G = copy.deepcopy(_load(WITH_LINE))
    for r in _rows(G):
        if r.get("row") == "cf-wc":
            r["v"] = "+9.6"  # 부호 반전
    gaps = _cf_gaps(WITH_LINE, G)
    assert gaps and "본표" in gaps[0], f"부호 반전을 통과시킴: {gaps}"


def test_no_force_without_statement_line():
    """본표에 집계 라인이 없는 회사는 cf-wc 행이 없어도 갭이 없어야 한다(과잉 강제 방지)."""
    G = copy.deepcopy(_load(NO_LINE))
    assert not any(r.get("row") == "cf-wc" for r in _rows(G))  # 원래 없음
    assert _cf_gaps(NO_LINE, G) == []


def test_double_label_flagged():
    """cf-wc 행이 있는데 cf-noncash 라벨도 '운전자본'을 포함하면 이중 표기로 FAIL."""
    G = copy.deepcopy(_load(WITH_LINE))
    for r in _rows(G):
        if r.get("row") == "cf-noncash":
            r["name"] = "조정 (현금 안 나간 비용·운전자본 변동)"
    gaps = _cf_gaps(WITH_LINE, G)
    assert any("이중 표기" in g for g in gaps), f"이중 표기를 통과시킴: {gaps}"
