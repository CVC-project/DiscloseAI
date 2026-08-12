"""fs_enrich.py — DART fnlttSinglAcntAll(전 계정) ×5개년 → fs_account.

galaxy가 요구하나 firm_*.json에 없는 계정(법인세·OCI·비현금조정·운전자본·이자/세금납부·환율·
기초/기말현금·배당·자사주·CF 세부)을 정형 API로 5개년 보강. LLM 금지(D7).
⚠️ 계정→소스 매핑표(계정×연도 전수)는 CLAUDE.md에 작성 — S 24키 각 소스가 A/B/추출/파생 중 어디서.

실행: python -m modules.report.fs_enrich --tickers 240810   (DART_API_KEY 필요)
      python -m modules.report.fs_enrich --all               ← 전 종목(수 시간·API 대량)

⚠️ **`--all`을 명시하지 않으면 전량 수집하지 않는다** (V-115, 2026-08-12 사고 교정).
   종전에는 `__main__`이 argparse 없이 `enrich()`를 불러 **인자를 조용히 무시**했다 —
   문서화된 `--tickers 240810`이 전 2,651사 재수집으로 돌아 정답지 55사가 298사로 불어났다.
   fs_account는 fs_parse의 **정답지(G1 분모)** 이므로 대상 확대는 반드시 명시적이어야 한다.
"""

from __future__ import annotations

import argparse
import os
import sys
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


def main() -> None:
    ap = argparse.ArgumentParser(description="DART fnlttSinglAcntAll ×5개년 → fs_account")
    ap.add_argument("--tickers", help="쉼표 구분 종목코드 (예: 240810,005930)")
    ap.add_argument("--all", action="store_true",
                    help="corps.csv 전 종목 (수 시간 · DART API 대량 소모)")
    ap.add_argument("--dry-run", action="store_true", help="대상만 출력하고 수집하지 않음")
    args = ap.parse_args()

    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    elif args.all:
        tickers = None  # 전량
    else:
        # ⚠️ V-115 — 인자 없이 전량이 돌면 정답지가 통째로 재작성된다. 명시 요구.
        ap.error("--tickers 또는 --all 중 하나가 필요합니다 "
                 "(--all 은 전 종목 재수집 — fs_account 정답지 범위가 바뀝니다)")

    if args.dry_run:
        corps = load_corps()
        if tickers:
            corps = [c for c in corps if c["ticker"] in set(tickers)]
        print(f"대상 {len(corps)}사: {[c['ticker'] for c in corps][:20]}"
              f"{' ...' if len(corps) > 20 else ''}")
        missing = sorted(set(tickers or []) - {c["ticker"] for c in corps})
        if missing:
            print(f"⚠ corps.csv에 없는 티커 {len(missing)}: {missing}")
        return

    enrich(tickers)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # cp949 콘솔 크래시 방지
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
