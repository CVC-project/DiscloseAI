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
    # 실 DART XML 형태: <TITLE>N. 제목 (연결)</TITLE> — '(연결)' 접미로 별도재무제표 주석과 구분(V-045 이후 계약).
    html = (
        "<TITLE>1. 일반사항 (연결)</TITLE>일반사항 내용"
        "<TITLE>16. 우발부채 (연결)</TITLE>우발부채 내용"
        "<TITLE>34. 후속사건 (연결)</TITLE>후속사건 내용"
    )
    notes = sectioner._split_notes(html)
    keys = [no for no, _, _ in notes]
    assert keys == ["1", "16", "34"]
    # 각 조각이 다음 주석 전까지
    assert "일반사항" in notes[0][2]
    assert "우발부채" in notes[1][2]


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
def test_db_init_and_models(tmp_path, monkeypatch):
    """⚠️ **정본 `shared/data/reports.db`를 건드리면 안 된다** — 임시 경로로 격리한다.

    종전에는 `init_local_db()`를 그대로 불러 정본 경로에 **빈 스키마 파일을 실제로 생성**했다.
    로컬에는 이미 정본이 있어 무해했지만 CI에는 파일이 없으므로, 이 테스트가 먼저 돌면서
    빈 DB를 만들어 놓고 → 알파벳 순으로 뒤에 오는 `test_series_*`의
    `if not os.path.exists(_DB): skip` 가드가 **무력화**돼 빈 DB로 단정 검사를 돌다 실패했다
    (PR #106 CI 실패의 근본 원인). 아래 두 층으로 막는다:
      ① 여기서 정본 경로를 쓰지 않는다(이 함수)
      ② 스킵 가드를 '파일 존재'가 아니라 '데이터 존재'로 판정한다(`_dbguard.has_report_data`)
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from modules.report import db as report_db

    tmp_db = tmp_path / "reports.db"
    eng = create_engine(f"sqlite:///{tmp_db}")
    monkeypatch.setattr(report_db, "_DB_PATH", str(tmp_db))
    monkeypatch.setattr(report_db, "engine", eng)
    monkeypatch.setattr(report_db, "LocalSession", sessionmaker(bind=eng))

    init_local_db()
    assert tmp_db.exists()
    s = get_local_session()
    try:
        # 테이블 존재 + 쿼리 가능
        assert s.query(ReportRaw).count() >= 0
        assert s.query(FsAccount).count() >= 0
    finally:
        s.close()


def test_corps_csv_full_universe():
    """★V0(2026-07-21): 48사(galaxy 파이프라인 시드) → 전 상장사(~2,651) 확장.

    기존 48행의 tier/cluster(T0/T1/scope-out)는 보존, 신규 2,600여 행은 빈 값.
    """
    from modules.report.collector import load_corps

    corps = load_corps()
    assert len(corps) >= 2600
    tickers = [c["ticker"] for c in corps]
    assert len(tickers) == len(set(tickers))  # 중복 없음
    assert all(len(c["ticker"]) == 6 and len(c["corp_code"]) == 8 for c in corps)
    assert any(c["ticker"] == "005930" for c in corps)  # 삼성전자
    samsung = next(c for c in corps if c["ticker"] == "005930")
    assert samsung["tier"] == "0"  # T0 골든 레퍼런스 보존 확인


# ── DART 의존 (실API) — 키 있을 때만 ──
@pytest.mark.skipif(
    not os.getenv("DART_API_KEY"), reason="DART_API_KEY 없음 — 실API 스킵"
)
def test_dart_client_constructs():
    from modules.report.collector import _dart_client

    # 키 있으면 클라이언트 생성 성공 (list 호출은 backfill에서)
    assert _dart_client() is not None
