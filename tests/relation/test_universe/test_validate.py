"""universe/validate.py 하드 게이트 로직 검증 (합성 데이터 + 실 DB 통합).

하드 게이트는 오염(우선주/ETN) 탐지가 핵심 — KOSPI200 90% 프록시를 대체한
의도 기준 게이트(2026-07-21 재정의)의 결정론 부분을 고정한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.relation.storage.models import CompanyRegistry
from modules.relation.universe.validate import hard_gate

_RELATION_DB = Path(__file__).resolve().parents[3] / "modules" / "relation" / "data" / "relation.db"


_corp_seq = 0


def _mk(session, ticker, market, tier, name=None, ksic="264", sector="semi", cap=1e12):
    global _corp_seq
    _corp_seq += 1
    session.add(
        CompanyRegistry(
            corp_code=f"{_corp_seq:08d}",  # 항상 고유
            ticker=ticker,
            name_current=name or f"회사{ticker}",
            market=market,
            ksic_code=ksic,
            sector_id=sector,
            universe_tier=tier,
            market_cap_krw=cap,
        )
    )


def _clean_ticker(n: int) -> str:
    """6자리 + 끝자리 0 보장 (보통주 관행). n는 0~9998."""
    return f"{n:05d}0"


def _populate_clean(session):
    """G1~G5를 모두 통과하는 최소 합성 유니버스 (named 400 + registry ≥2500)."""
    for i in range(200):
        _mk(session, _clean_ticker(i), "KOSPI", "named400")
        _mk(session, _clean_ticker(2000 + i), "KOSDAQ", "named400")
    # dot으로 registry 총계 ≥ 2500 채우기
    for i in range(2200):
        _mk(session, _clean_ticker(5000 + i), "KOSPI", "dot")
    session.commit()


def test_hard_gate_pass_clean(in_memory_session):
    _populate_clean(in_memory_session)
    result = hard_gate(session=in_memory_session)
    assert result["pass"] is True, result["checks"]


def test_g3_detects_preferred_by_name(in_memory_session):
    _populate_clean(in_memory_session)
    # 우선주 명칭 노드를 named400에 심음 → G3 실패해야
    _mk(in_memory_session, "005935", "KOSPI", "named400", name="삼성전자우")
    in_memory_session.commit()
    result = hard_gate(session=in_memory_session)
    assert result["pass"] is False
    assert result["checks"]["G3_common_only"]["pass"] is False


def test_g3_detects_non_common_ticker_tail(in_memory_session):
    _populate_clean(in_memory_session)
    # 종목코드 끝자리 비-0(우선주 관행) → G3 실패
    _mk(in_memory_session, "000875", "KOSPI", "named400", name="정상명칭")
    in_memory_session.commit()
    result = hard_gate(session=in_memory_session)
    assert result["checks"]["G3_common_only"]["pass"] is False


def test_g4_detects_unmapped_sector(in_memory_session):
    _populate_clean(in_memory_session)
    # ksic는 있는데 sector_id 없음 → G4 실패
    _mk(in_memory_session, "999990", "KOSDAQ", "dot", ksic="999", sector=None)
    in_memory_session.commit()
    result = hard_gate(session=in_memory_session)
    assert result["checks"]["G4_sector_mapped"]["pass"] is False


@pytest.mark.skipif(not _RELATION_DB.exists(), reason="relation.db 미존재")
def test_real_db_passes_u0_gate():
    """커밋된 relation.db(전 상장사 적재분)가 실제 U0 하드 게이트를 통과하는지 — 회귀 게이트."""
    result = hard_gate()
    assert result["pass"] is True, result["checks"]
