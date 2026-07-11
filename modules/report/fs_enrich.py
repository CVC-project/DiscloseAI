"""fs_enrich.py — DART fnlttSinglAcntAll(전 계정) ×5개년 → fs_account.

galaxy가 요구하나 firm_*.json에 없는 계정(법인세·OCI·비현금조정·운전자본·이자/세금납부·환율·
기초/기말현금·배당·자사주·CF 세부)을 정형 API로 5개년 보강. LLM 금지(D7).
⚠️ 계정→소스 매핑표(계정×연도 전수)는 CLAUDE.md에 작성 — S 24키 각 소스가 A/B/추출/파생 중 어디서.

실행: python -m modules.report.fs_enrich   (DART_API_KEY 필요)
"""

from __future__ import annotations

import os
from datetime import datetime

from .collector import _dart_client, load_corps
from .db import get_local_session, init_local_db
from .models import FsAccount, PipelineState

REPRT_CODE = "11011"  # 사업보고서
FS_YEARS = 5

# 연결(CFS) 우선, 없으면 개별(OFS)
_FS_DIV_PREF = ["CFS", "OFS"]


def enrich(tickers: list[str] | None = None) -> None:
    init_local_db()
    dart = _dart_client()
    if dart is None:
        print("⚠ DART_API_KEY 없음 — fs_enrich 스킵.")
        return
    corps = load_corps()
    if tickers:
        corps = [c for c in corps if c["ticker"] in set(tickers)]
    this_year = datetime.now().year
    years = list(range(this_year - 1, this_year - 1 - FS_YEARS, -1))
    sess = get_local_session()
    for c in corps:
        ticker, corp_code8, corp_name = c["ticker"], c["corp_code"], c["corp_name"]
        n = 0
        for fy in years:
            df = _fetch_accounts(dart, corp_code8, fy)
            if df is None or len(df) == 0:
                continue
            # 기존 (ticker,fy) 삭제 후 재적재 (idempotent)
            sess.query(FsAccount).filter_by(ticker=ticker, fiscal_year=fy).delete()
            for _, row in df.iterrows():
                sess.add(
                    FsAccount(
                        rcept_no=str(row.get("rcept_no", "")),
                        ticker=ticker,
                        fiscal_year=fy,
                        sj_div=str(row.get("sj_div", "")),
                        account_id=str(row.get("account_id", "")),
                        account_nm=str(row.get("account_nm", "")),
                        amount=_num(row.get("thstrm_amount")),
                        currency=str(row.get("currency", "KRW")),
                    )
                )
                n += 1
            _mark(sess, ticker, fy)
        sess.commit()
        print(
            f"[{ticker}] {corp_name}: fs_account {n}행 ({len([y for y in years])}개년 시도)"
        )
    sess.close()


def _fetch_accounts(dart, corp_code8: str, year: int):
    """fnlttSinglAcntAll — 연결 우선 폴백 개별."""
    for div in _FS_DIV_PREF:
        try:
            df = dart.finstate_all(corp_code8, year, reprt_code=REPRT_CODE, fs_div=div)
        except TypeError:
            # 구버전 시그니처: fs_div 미지원
            try:
                df = dart.finstate_all(corp_code8, year, reprt_code=REPRT_CODE)
            except Exception:
                df = None
        except Exception:
            df = None
        if df is not None and len(df) > 0:
            return df
    return None


def _num(v):
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _mark(sess, ticker, fy):
    key = f"{ticker}-FY{fy}"
    st = (
        sess.query(PipelineState).filter_by(rcept_no=key, target="enrich").one_or_none()
    )
    if st is None:
        st = PipelineState(rcept_no=key, ticker=ticker, target="enrich")
        sess.add(st)
    st.stage, st.status = "ENRICHED", "OK"
    st.attempts = (st.attempts or 0) + 1


if __name__ == "__main__":
    enrich()
