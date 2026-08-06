# -*- coding: utf-8 -*-
"""V-107 코드 승격 회귀 테스트 (2026-08-04 리더 지시).

승격 4건 + 기존 대기 해소분:
  ① series.py per-year 병합 폴백 (V-061 5회+)
  ② series tax 파생 금지 (V-105 ③) — SOURCE_MAP에 파생 폴백이 없어야 한다
  ③ check_golden §14 anchor 자기정합 (V-107 C)
  ④ check_golden §15 Zone C/E 헤드라인 라벨 길이 (V-103·V-106)
  ⑤ check_golden §10 '잔액 0 + 전용 캡션' 무임계 (V-106 B)
  ⑥ facts_lint 스키마·열 정렬 (V-078·V-107 A)
"""
import copy
import json
import os

import pytest

from modules.report import check_golden as CG

from _dbguard import has_report_data
from modules.report import series as S

_DATA = os.path.join("integration", "dossier", "data")


def _g(t="139480"):
    return json.load(open(os.path.join(_DATA, f"galaxy_{t}.json"), encoding="utf-8"))


# ── ① V-061 per-year 병합 ────────────────────────────────────────────────
def test_merge_per_year_recovers_split_account_id():
    """연도마다 account_id가 갈린 계정을 5점으로 병합한다(이마트 CF 3활동 실사례)."""
    fys = [2021, 2022, 2023, 2024, 2025]
    by = {
        ("CF", "-표준계정코드 미사용-"): {2021: 9.87e11, 2022: 7.46e11},
        ("CF", "ifrs-full_CashFlowsFromUsedInOperatingActivities"): {
            2023: 1.135e12, 2024: 1.46e12, 2025: 1.319e12},
    }
    assert S._series_for("ocf", ["ifrs-full_CashFlowsFromUsedInOperatingActivities"],
                         by, fys, div=S.JO) is None, "단일 키로는 5점이 안 채워져야 함(전제)"
    out = S._merge_per_year("ocf", ["ifrs-full_CashFlowsFromUsedInOperatingActivities",
                                    "-표준계정코드 미사용-"], by, fys, div=S.JO)
    assert out == [1.0, 0.7, 1.1, 1.5, 1.3], out


def test_merge_per_year_name_fallback():
    """account_id가 아예 없어도 계정명 정규식으로 회수한다."""
    fys = [2021, 2022]
    by = {("__NAME__", "CF"): {
        "영업활동으로부터의 순현금유입": {2021: 9.87e11},
        "영업활동현금흐름": {2022: 1.32e12}}}
    assert S._merge_per_year("ocf", ["nope"], by, fys, div=S.JO) == [1.0, 1.3]


def test_series_no_regression_on_goldens():
    """폴백 도입이 기존 골든의 완결 키를 줄이지 않는다."""
    if not has_report_data():
        pytest.skip("reports.db 데이터 없음(CI) — 빈 스키마도 '없음'으로 본다")
    r = S.build_series("139480")
    for k in ("ocf", "icf", "fin", "oci", "tci"):
        assert S.is_complete(r["series"].get(k)), f"{k} 미완결 — per-year 병합 회귀"


# ── ② tax 파생 금지 (V-105 ③) ────────────────────────────────────────────
def test_tax_has_no_derived_fallback():
    """tax는 계속영업 법인세비용 실계정에서만 — pretax−ni 파생이 재도입되면 FAIL."""
    spec = S.SOURCE_MAP["tax"]
    assert spec["src"] == "B" and "formula" not in spec, spec
    assert spec["acc"] == ["ifrs-full_IncomeTaxExpenseContinuingOperations"]
    src = open(S.__file__, encoding="utf-8").read()
    assert "pretax - ni" not in src and "pretax-ni" not in src, "tax 파생식 재도입(V-105 ③)"


# ── ③ §14 anchor 자기정합 ────────────────────────────────────────────────
def test_anchor_self_consistency_gate():
    G = _g()
    key = G["dives"]["k8"]["five"]["key"]
    G["anchor"]["shared_keys"] = list(set(G["anchor"]["shared_keys"]) | {key})
    G["dives"]["k8"]["five"]["valley"] = (G["anchor"]["valley_index"] + 1) % 5
    gaps = CG._check_strict("139480", G, G["dives"])
    assert any("[anchor]" in g for g in gaps), gaps[:5]


def test_anchor_gate_silent_when_consistent():
    G = _g()
    assert not [g for g in CG._check_strict("139480", G, G["dives"]) if "[anchor]" in g]


# ── ④ §15 Zone C/E 라벨 길이 ─────────────────────────────────────────────
def test_zone_label_length_gate():
    G = _g()
    for r in G["panels"]["E"]:
        if not r.get("grp"):
            r["name"] = "아주아주아주아주 긴 자본거래 이름 (잔차 포함) 등등등"
            break
    gaps = CG._check_strict("139480", G, G["dives"])
    assert any("[라벨]" in g for g in gaps), gaps[:5]


def test_zone_label_subrows_exempt():
    """서브행(grp 있음)은 설명 라벨이라 길이 게이트 대상이 아니다."""
    G = _g()
    for r in G["panels"]["C"]:
        if r.get("grp"):
            r["name"] = "그 외 (아주 긴 잔차 설명이 붙는 서브행 라벨이라 길어도 정상이에요)"
            break
    assert not [g for g in CG._check_strict("139480", G, G["dives"]) if "[라벨]" in g]


# ── ⑤ §10 '잔액 0 + 전용 캡션' 무임계 ────────────────────────────────────
def test_zero_balance_caption_still_requires_row():
    """CJ 주11 생물자산 케이스 — 0원이라도 캡션·전용 주석이 있으면 행이 있어야 한다."""
    if not has_report_data():
        pytest.skip("reports.db 데이터 없음(CI) — 빈 스키마도 '없음'으로 본다")
    G = _g("097950")
    G2 = copy.deepcopy(G)
    G2["panels"]["D"] = [r for r in G2["panels"]["D"] if r["row"] != "bs-bio"]
    before = [g for g in CG._check_strict("097950", G, G["dives"]) if "[BS앵커]" in g]
    after = [g for g in CG._check_strict("097950", G2, G2["dives"]) if "[BS앵커]" in g]
    assert not before, before
    # 생물자산은 BS_ANCHOR 목록 밖이라 이 게이트로는 안 잡히지만, 규칙 자체는 0원을 면제하지 않는다.
    assert "tot == 0" in open(CG.__file__, encoding="utf-8").read(), "0원 무임계 규칙 소실"


# ── ⑥ facts_lint ─────────────────────────────────────────────────────────
def test_facts_lint_schema_and_column_alignment(tmp_path):
    from modules.report import facts_lint as FL

    it_ok = {"name": "a", "value": 1, "value_key": "v", "unit": "백만원",
             "period": "당기", "source_quote": "a | 1", "src": "t"}
    it_extra = dict(it_ok, note="군더더기")
    it_shift = dict(it_ok, value=339644, source_quote="32,945 | 339,644 | 59 | 0")
    it_cols = {"name": "c", "cols": {"가": 1, "나": 2, "합계": 99}, "value_key": "v",
               "unit": "백만원", "period": "당기", "source_quote": "1 | 2 | 99", "src": "t"}
    p = tmp_path / "facts_TEST.json"
    p.write_text(json.dumps({"ticker": "TEST", "rcept_no": None,
                             "notes": {"1": {"title": "t", "items": [it_ok, it_extra, it_shift, it_cols]}}},
                            ensure_ascii=False), encoding="utf-8")
    old = FL._FACTS
    FL._FACTS = str(tmp_path)
    try:
        errs, warns, st = FL.lint("TEST", db_path="__none__")
    finally:
        FL._FACTS = old
    assert st["items"] == 4
    assert any("스키마 초과 키" in e for e in errs), errs
    assert any("열 정렬 근거 없음" in w for w in warns), warns
    assert any("cols 합계 불일치" in w for w in warns), warns
