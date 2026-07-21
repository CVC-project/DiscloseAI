"""universe/validate.py — U0 유니버스 게이트 (의도 기준, 2026-07-21 재정의).

원래 U0 게이트의 "KOSPI 상위 200이 KOSPI200 지수와 교집합 ≥90%"는 **잘못 지정된 프록시**였다.
우리 선정은 순수 시총 상위 200이고, KOSPI200 지수는 시총 + 유동성 + 섹터균형 + 증권유형
(리츠·인프라펀드) 제외를 함께 쓴다. 두 방법론은 설계상 다르므로 순수 시총 선정으로는
교집합이 구조적으로 ~84%에서 천장을 친다(실측: 168/200). 이때 불일치 64건은 전부 실제
기업·펀드이고 오염(우선주·ETN·SPAC)은 0건이었다.

따라서 게이트를 **의도**로 재정의한다 — "유니버스가 건강한가": 오염 0 + 전부 보통주 +
레지스트리/시총/섹터 정합. 이 부분은 전부 로컬·결정론이라 하드 게이트다. KOSPI200
교집합은 **정보용 크로스체크**로만 남긴다(외부 원천·리밸런싱 stale 가능).

하드 게이트 (로컬, 결정론):
  G1 registry ≥ 2,500
  G2 named400 == 400 (KOSPI 200 + KOSDAQ 200)
  G3 named400 전부 보통주 (종목코드 끝자리 0, 우선주 명칭 없음) — 오염 0
  G4 섹터 미매핑 0 (ksic_code 있는 전 행에 sector_id)
  G5 시총 확보율: named400 전부 market_cap_krw 존재 (순위 근거)

정보용 크로스체크 (네트워크, best-effort, 게이트 아님):
  KOSPI200 지수(Wikipedia) 대비 교집합 % + 불일치 종목의 오염 여부.
"""

from __future__ import annotations

import io
import logging

from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import CompanyRegistry

logger = logging.getLogger(__name__)

MIN_REGISTRY = 2500
NAMED_TOTAL = 400


def hard_gate(session=None) -> dict:
    """로컬 결정론 게이트 G1~G5. 반환 dict의 'pass'가 최종 판정.

    session: 주입 시 그 세션으로 조회(테스트용 — 닫지 않음). None이면 로컬 relation.db.
    """
    owns_session = session is None
    if owns_session:
        session = get_local_session()
    try:
        total = session.query(CompanyRegistry).count()
        named = (
            session.query(CompanyRegistry)
            .filter(CompanyRegistry.universe_tier == "named400")
            .all()
        )
        unmapped = (
            session.query(CompanyRegistry)
            .filter(
                CompanyRegistry.ksic_code.isnot(None),
                CompanyRegistry.sector_id.is_(None),
            )
            .count()
        )
    finally:
        if owns_session:
            session.close()

    # G3: 보통주 판정 — 종목코드 끝자리 0 + 명칭에 우선주 표기 없음
    pref = [
        (r.ticker, r.name_current)
        for r in named
        if (r.ticker and r.ticker[-1] != "0")
        or r.name_current.endswith("우")
        or "우B" in r.name_current
    ]
    # G5: 시총 근거
    no_cap = [r.ticker for r in named if r.market_cap_krw is None]

    kospi = [r for r in named if r.market == "KOSPI"]
    kosdaq = [r for r in named if r.market == "KOSDAQ"]

    checks = {
        "G1_registry_min": (total >= MIN_REGISTRY, f"{total} ≥ {MIN_REGISTRY}"),
        "G2_named400": (len(named) == NAMED_TOTAL, f"named={len(named)} (KOSPI {len(kospi)}, KOSDAQ {len(kosdaq)})"),
        "G3_common_only": (len(pref) == 0, f"우선주/특수 {len(pref)}건 (예: {pref[:3]})"),
        "G4_sector_mapped": (unmapped == 0, f"미매핑 {unmapped}건"),
        "G5_cap_backed": (len(no_cap) == 0, f"시총 결측 {len(no_cap)}건"),
    }
    passed = all(ok for ok, _ in checks.values())
    return {"pass": passed, "checks": {k: {"pass": ok, "detail": d} for k, (ok, d) in checks.items()}}


def kospi200_crosscheck() -> dict | None:
    """정보용: 실제 KOSPI200(Wikipedia) 대비 교집합. 게이트 아님.

    네트워크·외부 원천 실패 시 None(크로스체크 생략, 하드 게이트엔 영향 없음).
    Wikipedia는 반기 리밸런싱 주기상 stale 가능 — 절대 판정 근거로 쓰지 않는다.
    """
    try:
        import pandas as pd
        import requests
    except ImportError:
        return None
    try:
        r = requests.get(
            "https://en.wikipedia.org/wiki/KOSPI_200",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        tables = pd.read_html(io.StringIO(r.text))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"KOSPI200 크로스체크 원천 실패(무시): {e}")
        return None

    index_df = next((t for t in tables if t.shape[0] in (200, 201) and "Symbol" in t.columns), None)
    if index_df is None:
        return None
    index_tickers = {str(s).zfill(6) for s in index_df["Symbol"]}

    session = get_local_session()
    try:
        ours = (
            session.query(CompanyRegistry.ticker, CompanyRegistry.name_current)
            .filter(CompanyRegistry.market == "KOSPI", CompanyRegistry.universe_tier == "named400")
            .all()
        )
    finally:
        session.close()
    our_tickers = {t for t, _ in ours}
    both = our_tickers & index_tickers
    overlap = 100 * len(both) / len(index_tickers) if index_tickers else 0.0
    return {
        "overlap_pct": round(overlap, 1),
        "intersection": len(both),
        "index_size": len(index_tickers),
        "our_size": len(our_tickers),
        "only_ours": len(our_tickers - index_tickers),
        "only_index": len(index_tickers - our_tickers),
        "note": "정보용 참조 — 순수 시총 vs 유동성/섹터균형 지수의 방법론 차이로 ~84%가 정상. 게이트 아님.",
    }


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    gate = hard_gate()
    cross = kospi200_crosscheck()
    print(json.dumps({"hard_gate": gate, "kospi200_crosscheck": cross}, ensure_ascii=False, indent=2))
    print("\nU0 하드 게이트:", "PASS ✅" if gate["pass"] else "FAIL ❌")
