"""report 파이프라인 단위 테스트 — DART/LLM 무관 (CI는 이 부분만).

DART 의존 테스트는 skipif로 격리(Phase 3 백필에서 실데이터 검증).
"""

import os

import pytest

from modules.report import sectioner, series
from modules.report.db import get_local_session, init_local_db
from modules.report.models import FsAccount, ReportRaw


# ── 섹셔닝: 주석 번호 분할 ──
def test_split_notes_basic():
    html = "머리말\n주1. 일반사항 내용\n주16. 우발부채 내용\n주34. 후속사건"
    notes = sectioner._split_notes(html)
    keys = [n for n, _ in notes]
    assert keys == ["주1", "주16", "주34"]
    # 각 조각이 다음 주석 전까지
    assert "일반사항" in notes[0][1]
    assert "우발부채" in notes[1][1]


def test_split_notes_none():
    assert sectioner._split_notes("주석 번호가 없는 텍스트") == []


def test_to_md_table():
    html = "<p>서두</p><table><tr><th>계정</th><th>금액</th></tr><tr><td>매출</td><td>333</td></tr></table>"
    md = sectioner._to_md(html)
    assert "서두" in md
    assert "| 계정 | 금액 |" in md
    assert "| 매출 | 333 |" in md


# ── series: 5점 완결 판정 + 소스맵 ──
def test_is_complete():
    assert series.is_complete([1, 2, 3, 4, 5])
    assert not series.is_complete([1, 2, 3])  # 5점 미만
    assert not series.is_complete([1, 2, 3, 4, None])  # 비수치
    assert not series.is_complete("nope")


def test_source_map_covers_24_keys():
    expected = {
        "revenue",
        "cogs",
        "gross",
        "sgna",
        "op",
        "pretax",
        "tax",
        "ni",
        "oci",
        "ocf",
        "icf",
        "capex",
        "fin",
        "div",
        "buyback",
        "dep",
        "rnd",
        "cash",
        "assets",
        "debt",
        "equity",
        "dsOp",
        "eps",
        "tci",
    }
    assert set(series.SOURCE_MAP.keys()) == expected


def test_derived_keys_have_formula():
    for k in ("gross", "tci"):
        assert "formula" in series.SOURCE_MAP[k]


# ── DB 스키마 스모크 ──
def test_db_init_and_models():
    init_local_db()
    s = get_local_session()
    try:
        # 테이블 존재 + 쿼리 가능
        assert s.query(ReportRaw).count() >= 0
        assert s.query(FsAccount).count() >= 0
    finally:
        s.close()


def test_corps_csv_48():
    from modules.report.collector import load_corps

    corps = load_corps()
    assert len(corps) == 48
    assert all(len(c["ticker"]) == 6 and len(c["corp_code"]) == 8 for c in corps)
    assert any(c["ticker"] == "005930" for c in corps)  # 삼성전자


# ── DART 의존 (실API) — 키 있을 때만 ──
@pytest.mark.skipif(
    not os.getenv("DART_API_KEY"), reason="DART_API_KEY 없음 — 실API 스킵"
)
def test_dart_client_constructs():
    from modules.report.collector import _dart_client

    # 키 있으면 클라이언트 생성 성공 (list 호출은 backfill에서)
    assert _dart_client() is not None
