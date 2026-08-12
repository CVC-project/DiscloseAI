# -*- coding: utf-8 -*-
"""V-100 stale 섹션 꼬리 절단 검출(sectioning_health deep) 회귀.

배경(V-058 실사고): 고려아연 FY2025가 옛 sectioner 잔재로 주29에서 잘린 25노트였는데,
health의 기존 3종 검사(붕괴·괴물블록·결번)는 전부 통과했다 — 꼬리가 통째로 없는 것은
어느 검사도 보지 않았기 때문. 법인세(32)·주당이익(33)·특수관계자(37)·부문(39)이
사라진 채 골든 빌드에 들어갈 뻔했다.

지키는 것: ① 실제 절단 상태를 잡는가 ② 정상 티커에 오탐이 없는가
③ 원문 캐시가 없으면 판정을 생략하는가(없는 근거로 FAIL 금지).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modules.report import sectioner as sc  # noqa: E402


def _raw_path(ticker):
    from modules.report.db import get_local_session
    from modules.report.models import ReportRaw

    sess = get_local_session()
    try:
        raw = (
            sess.query(ReportRaw)
            .filter(ReportRaw.ticker == ticker)
            .order_by(ReportRaw.fiscal_year.desc())
            .first()
        )
        return raw.raw_path if raw else None
    finally:
        sess.close()


TICKER = "010130"  # V-058 당사자(고려아연) — 현재 DB는 재섹션 완료본(39노트)


def _skip_if_no_raw():
    try:
        rp = _raw_path(TICKER)
    except Exception:
        pytest.skip("로컬 reports.db 없음(CI)")
    if not rp or not sc._load_raw(rp):
        pytest.skip("로컬 raw_cache 없음(CI) — 원문 재분할 판정 불가")
    return rp


def test_detects_truncated_tail():
    """DB가 주29에서 잘린 상태(V-058 재현)면 유실 꼬리를 지목해야 한다."""
    rp = _skip_if_no_raw()
    issues = sc._stale_tail_issues(TICKER, rp, list(range(1, 30)), 25)
    assert issues, "꼬리 절단을 통과시킴 — health 사각 재발"
    msg = issues[0]
    assert "stale 꼬리 절단" in msg and "section_all" in msg
    assert "주32" in msg or "법인세" in msg, f"유실 꼬리를 지목하지 못함: {msg}"


def test_no_false_positive_on_current_db():
    """재섹션 완료된 현재 상태에서는 갭이 없어야 한다(오탐 금지)."""
    _skip_if_no_raw()
    assert sc.sectioning_health(TICKER) == []


def test_skips_without_raw_cache():
    """원문 캐시가 없으면 판정 생략 — 없는 근거로 FAIL시키지 않는다."""
    assert sc._stale_tail_issues(TICKER, "raw_cache/__없는파일__.xml", [1, 2, 3], 3) == []
    assert sc._stale_tail_issues(TICKER, "", [1, 2, 3], 3) == []


def test_deep_flag_off_keeps_legacy_behavior():
    """deep=False면 기존 3종 검사만 — 호출부 무회귀."""
    _skip_if_no_raw()
    assert sc.sectioning_health(TICKER, deep=False) == []
