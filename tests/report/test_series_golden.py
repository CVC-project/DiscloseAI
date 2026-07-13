"""G2 series.py 회귀 — 삼성 골든 대조 (PHASE4_PLAN G2 DoD).

코드 파생 가능 키(A|B|D)는 galaxy_005930.json series와 ±0.06조(eps ±1원) 일치해야 한다.
N(주석 의존: rnd·dsOp)·영year 결측(buyback·dep)은 의도적 미완성이라 제외.
reports.db(fs_account)가 비어 있으면(backfill 전) skip — DART 키로 재현 가능한 로컬 정본.
"""
import json
import os
import sqlite3

import pytest

from modules.report.series import build_series

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DB = os.path.join(_ROOT, "modules", "report", "data", "reports.db")
_GOLDEN = os.path.join(_ROOT, "integration", "dossier", "data", "galaxy_005930.json")

# 코드가 채워야 하는 키(주석·영year 의존 제외)
CODE_KEYS = [
    "revenue", "cogs", "gross", "sgna", "op", "pretax", "tax", "ni", "oci",
    "ocf", "icf", "capex", "fin", "div", "cash", "assets", "debt", "equity", "eps",
]


def _has_fs_data() -> bool:
    if not os.path.exists(_DB):
        return False
    con = sqlite3.connect(_DB)
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM fs_account WHERE ticker='005930'"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()
    return n > 0


pytestmark = pytest.mark.skipif(
    not _has_fs_data(), reason="reports.db fs_account 미적재 (Phase 3 backfill 필요)"
)


@pytest.fixture(scope="module")
def golden():
    with open(_GOLDEN, encoding="utf-8") as f:
        return json.load(f)["series"]


@pytest.fixture(scope="module")
def computed():
    return build_series("005930")["series"]


@pytest.mark.parametrize("key", CODE_KEYS)
def test_series_matches_golden(key, golden, computed):
    gv = golden[key]
    mv = computed.get(key)
    assert mv is not None, f"{key} 계산 결과 없음 (골든={gv})"
    assert len(mv) == 5, f"{key} 5점 아님: {mv}"
    tol = 1 if key == "eps" else 0.06
    for i, (a, b) in enumerate(zip(mv, gv)):
        assert abs(a - b) <= tol, f"{key}[{i}] 계산 {a} vs 골든 {b} (허용 ±{tol})"


def test_note_keys_incomplete():
    """rnd·dsOp는 주석 추출(Phase4) 전까지 미완성이어야 한다(five=skip 대상)."""
    r = build_series("005930")
    assert "rnd" in r["incomplete"]
    assert "dsOp" in r["incomplete"]
