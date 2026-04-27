"""
KRX 실제 데이터로 퀴즈 changePct & kospiChangePct 검증

측정 기준:
  종목  : pykrx  — 공시 전날(t-1) 종가 → 공시 후 n거래일(t+n) 종가
  KOSPI : yfinance ^KS11 — 동일 기간

실행:
    python -m modules.price.verify_quiz_prices
"""

from __future__ import annotations
import warnings
warnings.filterwarnings("ignore")

from pykrx import stock as krx
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ── 퀴즈 항목 정의 ─────────────────────────────────────────────────────────
# window=-1  => 월간 (month_end 필요)
# note       => 특이사항 메모
QUIZ_ITEMS = [
    {"id":  1, "company": "LG화학",          "ticker": "051910", "date": "20200917", "window":  5},
    {"id":  2, "company": "HD현대중공업",     "ticker": "009540", "date": "20260422", "window":  3},
    {"id":  3, "company": "삼성전자",         "ticker": "005930", "date": "20230407", "window":  5},
    {"id":  4, "company": "현대차",           "ticker": "005380", "date": "20210108", "window":  3},
    {"id":  5, "company": "SK하이닉스",       "ticker": "000660", "date": "20201020", "window":  5},
    {"id":  8, "company": "SK이노베이션",     "ticker": "096770", "date": "20240717", "window":  5},
    {"id": 10, "company": "POSCO홀딩스",      "ticker": "005490", "date": "20211210", "window":  5},
    {"id": 11, "company": "삼성전자(소각)",    "ticker": "005930", "date": "20260331", "window":  3,
     "note": "2026년 데이터, 검증 불가"},
    {"id": 12, "company": "삼성물산",         "ticker": "028260", "date": "20150526", "window":  5},
    {"id": 13, "company": "NAVER",            "ticker": "035420", "date": "20240430", "window":  5},
    {"id": 14, "company": "현대모비스",       "ticker": "012330", "date": "20180521", "window":  3},
    {"id": 15, "company": "카카오",           "ticker": "035720", "date": "20210901", "window": -1,
     "month_end": "20210930"},
]

# quiz_data.py 현재 등록값
CURRENT = {
     1: {"change": -11.2, "kospi":  -6.7},
     2: {"change":  12.6, "kospi":   2.4},
     3: {"change":   4.8, "kospi":   4.6},
     4: {"change":  26.7, "kospi":   3.8},
     5: {"change":  -5.1, "kospi":  -0.7},
     8: {"change":  -6.0, "kospi":  -3.7},
    10: {"change":  -1.0, "kospi":  -0.4},
    11: {"change":   5.6, "kospi":   1.9},   # 삼성전자 자사주소각 (2026-03-31)
    12: {"change":  13.8, "kospi":  -3.1},
    13: {"change":   1.9, "kospi":   0.9},
    14: {"change":  -1.9, "kospi":   0.0},
    15: {"change": -23.4, "kospi":  -4.3},
}


# ── 데이터 취득 헬퍼 ───────────────────────────────────────────────────────

def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")

def _str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")

def _ystr(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def fetch_stock(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        df = krx.get_market_ohlcv_by_date(start, end, ticker)
        return df if not df.empty else None
    except Exception:
        return None


def fetch_kospi(start_dt: datetime, end_dt: datetime) -> pd.Series | None:
    try:
        df = yf.download(
            "^KS11",
            start=_ystr(start_dt - timedelta(days=3)),
            end=_ystr(end_dt + timedelta(days=3)),
            progress=False, auto_adjust=True
        )
        if df.empty:
            return None
        df.columns = df.columns.get_level_values(0)
        return df["Close"].astype(float)
    except Exception:
        return None


def prev_trading_day(ann_date_str: str) -> str:
    """공시일 직전 거래일 (삼성전자 캘린더 이용)."""
    dt = _dt(ann_date_str)
    start = _str(dt - timedelta(days=10))
    end   = _str(dt - timedelta(days=1))
    df = fetch_stock("005930", start, end)
    if df is None or df.empty:
        return end
    return df.index[-1].strftime("%Y%m%d")


def pct(p0: float, pn: float) -> float:
    return round((pn / p0 - 1) * 100, 1)


# ── 계산 함수 ──────────────────────────────────────────────────────────────

def calc_window(ticker: str, ann_date: str, n: int):
    """t-1 종가 -> t+n 종가 변동률 (종목 + KOSPI)."""
    prev = prev_trading_day(ann_date)
    end  = _str(_dt(ann_date) + timedelta(days=n * 3 + 15))

    df_s = fetch_stock(ticker, prev, end)
    if df_s is None or len(df_s) < n + 2:
        return None, None

    # df_s.iloc[0] = t-1, iloc[1] = t, iloc[1+n] = t+n
    if 1 + n >= len(df_s):
        return None, None
    chg = pct(df_s.iloc[0]["종가"], df_s.iloc[1 + n]["종가"])

    # KOSPI: 동일 날짜 기준
    date_0 = df_s.index[0]           # t-1
    date_n = df_s.index[1 + n]       # t+n
    ks = fetch_kospi(date_0, date_n)
    kospi_chg = None
    if ks is not None:
        ks_filt = ks[(ks.index >= pd.Timestamp(date_0)) &
                     (ks.index <= pd.Timestamp(date_n))]
        if len(ks_filt) >= 2:
            kospi_chg = pct(float(ks_filt.iloc[0]), float(ks_filt.iloc[-1]))

    return chg, kospi_chg


def calc_month(ticker: str, start: str, end: str):
    """첫 거래일 종가 -> 마지막 거래일 종가 (월간)."""
    df_s = fetch_stock(ticker, start, end)
    if df_s is None or len(df_s) < 2:
        return None, None
    chg = pct(df_s.iloc[0]["종가"], df_s.iloc[-1]["종가"])

    ks = fetch_kospi(_dt(start), _dt(end))
    kospi_chg = None
    if ks is not None:
        ks_filt = ks[(ks.index >= pd.Timestamp(start)) &
                     (ks.index <= pd.Timestamp(end))]
        if len(ks_filt) >= 2:
            kospi_chg = pct(float(ks_filt.iloc[0]), float(ks_filt.iloc[-1]))

    return chg, kospi_chg


# ── 메인 ──────────────────────────────────────────────────────────────────

def main() -> None:
    SEP = "-" * 100
    print(SEP)
    print(f"{'ID':>3}  {'Company':<14}  "
          f"{'cur_chg':>8} {'krx_chg':>8} {'chg':>5}  "
          f"{'cur_ksp':>8} {'krx_ksp':>8} {'ksp':>5}  Note")
    print(SEP)

    updates_needed = []

    for item in QUIZ_ITEMS:
        cid     = item["id"]
        name    = item["company"]
        ticker  = item["ticker"]
        date    = item["date"]
        window  = item["window"]
        note    = item.get("note", "")
        cur     = CURRENT[cid]

        print(f"  fetching [{cid:2d}] {name}...", end="\r", flush=True)

        if window == -1:
            krx_chg, krx_ksp = calc_month(ticker, date, item["month_end"])
        else:
            krx_chg, krx_ksp = calc_window(ticker, date, window)

        def flag(actual, expected):
            if actual is None:
                return " N/A "
            return " [OK]" if abs(actual - expected) < 1.5 else " [NG]"

        def fmt(v):
            return f"{v:+.1f}%" if v is not None else "  N/A  "

        chg_ok = flag(krx_chg, cur["change"])
        ksp_ok = flag(krx_ksp, cur["kospi"])

        print(f"{cid:>3}  {name:<14}  "
              f"{cur['change']:>+7.1f}% {fmt(krx_chg):>8} {chg_ok}  "
              f"{cur['kospi']:>+7.1f}% {fmt(krx_ksp):>8} {ksp_ok}  {note}")

        if "[NG]" in chg_ok or "[NG]" in ksp_ok:
            updates_needed.append({
                "id": cid, "company": name,
                "cur_change": cur["change"], "krx_change": krx_chg,
                "cur_kospi":  cur["kospi"],  "krx_kospi":  krx_ksp,
                "chg_ng": "[NG]" in chg_ok,
                "ksp_ng": "[NG]" in ksp_ok,
                "note": note,
            })

    print(SEP)

    if updates_needed:
        print("\n[수정 필요 항목 요약]")
        for r in updates_needed:
            parts = []
            if r["chg_ng"] and r["krx_change"] is not None:
                parts.append(f"change {r['cur_change']:+.1f}% -> {r['krx_change']:+.1f}%")
            if r["ksp_ng"] and r["krx_kospi"] is not None:
                parts.append(f"kospi {r['cur_kospi']:+.1f}% -> {r['krx_kospi']:+.1f}%")
            flag_note = f"  ({r['note']})" if r["note"] else ""
            print(f"  [{r['id']:2d}] {r['company']:<14} {' | '.join(parts) if parts else '데이터 없음(N/A)'}{flag_note}")
    else:
        print("\n[OK] 모든 값이 KRX/yfinance 실데이터와 일치합니다 (허용 오차 +-1.5%p)")


if __name__ == "__main__":
    main()
