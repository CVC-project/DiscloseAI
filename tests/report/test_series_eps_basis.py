# -*- coding: utf-8 -*-
"""V-109 코드 승격 회귀 — series ALT_NAME 확장 2건 (2026-08-04, 대한항공 003490).

① capex 계정명 변이 — `유형자산 및 투자부동산의 취득`(FY21~23) ↔ `유형자산의 취득`(FY24~25).
   회사가 스스로 한 줄로 공시한 설비투자 라인이라 병합이 정당(V-061 계열).
② eps 기준 혼용 차단 — `계속영업기본주당이익`은 **그 해 중단영업 EPS가 없거나 0일 때만**
   총 EPS와 같다. 한화에어로 012450 FY22 실측: 총 3,964 = 계속 3,223 + 중단 741.
   가드 없이 정규식만 넓히면 연도별로 총/계속이 섞여 V-105 ③(`pretax−ni` 파생)과 같은
   기준 혼용 사고가 난다 — `_eps_basis_ok()`가 연도별로 판정해 거부한다.
"""
import os

import pytest

from modules.report import series as S


# ── ① capex 계정명 변이 병합 ──────────────────────────────────────────────
def test_capex_merges_ppe_and_investment_property_caption():
    """`유형자산 및 투자부동산의 취득`도 capex로 회수한다(대한항공 FY21~23 실사례)."""
    fys = [2021, 2022, 2023, 2024, 2025]
    by = {
        ("__NAME__", "CF"): {
            "유형자산 및 투자부동산의 취득": {2021: -3.42965e11, 2022: -7.61763e11, 2023: 1.90852e12},
            "유형자산의 취득": {2024: 2.8941e12, 2025: 4.28914e12},
        }
    }
    out = S._merge_per_year("capex", ["nope"], by, fys, div=S.JO)
    assert out == [0.3, 0.8, 1.9, 2.9, 4.3], out  # ABS_KEYS로 부호 반전도 정규화


# ── ② eps 기준 혼용 차단 ──────────────────────────────────────────────────
def test_eps_accepts_continuing_when_no_discontinued():
    """중단영업 EPS가 없으면 계속영업 EPS = 총 EPS로 인정(대한항공 FY21·22)."""
    fys = [2021, 2022]
    by = {
        ("__NAME__", "CIS"): {
            "계속영업기본주당이익(손실)": {2021: 1743.0, 2022: 4787.0},
            "중단영업기본주당이익(손실)": {},  # 원문 None → _load_fs가 넣지 않는다
        }
    }
    assert S._merge_per_year("eps", ["nope"], by, fys, div=1) == [1743, 4787]


def test_eps_rejects_continuing_when_discontinued_exists():
    """중단영업 EPS가 실재하고 0이 아니면 계속영업 EPS를 총 EPS로 쓰지 않는다(한화 FY22)."""
    fys = [2022]
    by = {
        ("__NAME__", "CIS"): {
            "계속영업기본주당이익(손실)": {2022: 3223.0},
            "중단영업기본주당이익(손실)": {2022: 741.0},
        }
    }
    assert S._merge_per_year("eps", ["nope"], by, fys, div=1) is None

    # 총 EPS가 같은 해에 실재하면 그쪽을 쓴다(기준 혼용 없음)
    by[("__NAME__", "CIS")]["기본주당이익(손실)"] = {2022: 3964.0}
    assert S._merge_per_year("eps", ["nope"], by, fys, div=1) == [3964]


def test_eps_basis_guard_keeps_hanwha_incomplete():
    """실데이터 회귀 — 012450은 FY23~25가 계속영업 EPS뿐이라 eps 미완결이 정답이다."""
    if not os.path.exists(S._DB):
        pytest.skip("reports.db 없음(CI)")
    assert "eps" in S.build_series("012450")["incomplete"]


def test_003490_series_recovered():
    """대한항공은 capex·eps 둘 다 5점 완결(19/24 → 21/24)."""
    if not os.path.exists(S._DB):
        pytest.skip("reports.db 없음(CI)")
    r = S.build_series("003490")
    assert r["series"]["capex"] == [0.3, 0.8, 1.9, 2.9, 4.3]
    assert r["series"]["eps"] == [1743, 4787, 2866, 3566, 2133]
    assert set(r["incomplete"]) == {"buyback", "rnd", "dsOp"}
