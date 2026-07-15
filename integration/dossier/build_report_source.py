# -*- coding: utf-8 -*-
"""build_report_source.py — 현금 은하수 '사업보고서 원문 보기' 팝업용 원문 JSON 생성.

딥다이브 카드에서 그 카드가 유래한 사업보고서 원문(재무제표 5본 + 주석 전수)을
좌측 팝업에 띄우기 위한 per-ticker 원문 데이터를 만든다. LLM 무관 — 결정론 추출.

입력(read-only, integration 예외 경로):
  - modules/report/data/reports.db  report_section (주석 text_md, 이미 분할됨)
  - modules/report/data/raw_cache/<t>/<rcept>.xml  (연결재무제표 2-1~2-5 TITLE 블록)
출력: integration/dossier/data/report_<ticker>.json (팀 공유 파생물 — 커밋 대상)

실행: python integration/dossier/build_report_source.py 005930
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

# modules.report.sectioner._to_md 재사용 (HTML→pipe-table md). integration read-only 예외.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modules.report.sectioner import _to_md  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DB = os.path.join(_ROOT, "modules", "report", "data", "reports.db")
_REPORT_DIR = os.path.join(_ROOT, "modules", "report")
_OUT_DIR = os.path.join(_HERE, "data")

# 연결재무제표 5본: TITLE 접두 → JSON 키·표시명
_STMTS = [
    (r"2-1\.", "bs", "연결 재무상태표"),
    (r"2-2\.", "is", "연결 손익계산서"),
    (r"2-3\.", "cis", "연결 포괄손익계산서"),
    (r"2-4\.", "eq", "연결 자본변동표"),
    (r"2-5\.", "cf", "연결 현금흐름표"),
]
_TITLE_RE = re.compile(r"<TITLE[^>]*>[^<]*</TITLE>")


def _latest(cur, ticker):
    return cur.execute(
        "select rcept_no, raw_path from report_raw where ticker=? order by fiscal_year desc limit 1",
        (ticker,),
    ).fetchone()


def _extract_statements(doc: str) -> dict:
    """raw XML에서 재무제표 5본 블록(TITLE→다음 TITLE)을 잘라 md로."""
    titles = [(m.start(), m.group(0)) for m in _TITLE_RE.finditer(doc)]
    out = {}
    for i, (pos, tag) in enumerate(titles):
        txt = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", tag)).strip()
        for pat, key, name in _STMTS:
            if key in out:
                continue
            if re.match(pat, txt):
                end = titles[i + 1][0] if i + 1 < len(titles) else len(doc)
                out[key] = {"title": name, "md": _to_md(doc[pos:end])}
    return out


def _extract_notes(cur, rcept: str) -> dict:
    rows = cur.execute(
        "select note_no, title, text_md from report_section "
        "where rcept_no=? and note_no is not null",
        (rcept,),
    ).fetchall()

    def nk(n):
        p = re.split(r"[.\-]", str(n))
        return tuple(int(x) if x.strip().isdigit() else 0 for x in p)

    rows.sort(key=lambda r: nk(r[0]))
    return {no: {"title": title or "", "md": md or ""} for no, title, md in rows}


def build(ticker: str) -> str:
    con = sqlite3.connect(_DB)
    cur = con.cursor()
    row = _latest(cur, ticker)
    if not row:
        raise SystemExit(f"[{ticker}] report_raw 없음 — collector 먼저")
    rcept, raw_path = row
    doc = open(os.path.join(_REPORT_DIR, raw_path), encoding="utf-8", errors="ignore").read()
    data = {
        "ticker": ticker,
        "rcept_no": rcept,
        "statements": _extract_statements(doc),
        "notes": _extract_notes(cur, rcept),
    }
    con.close()
    os.makedirs(_OUT_DIR, exist_ok=True)
    out_path = os.path.join(_OUT_DIR, f"report_{ticker}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(out_path) / 1024
    print(f"[{ticker}] report_{ticker}.json — 재무제표 {len(data['statements'])}본·주석 {len(data['notes'])}개·{kb:.0f}KB")
    _write_index()
    return out_path


def _write_index() -> None:
    """report_*.json 스캔 → report_index.json 매니페스트(galaxy.html이 fetch해 원문 지원 티커 판정 — 404 방지)."""
    import glob
    ts = sorted(os.path.basename(p)[7:-5] for p in glob.glob(os.path.join(_OUT_DIR, "report_*.json"))
                if os.path.basename(p) != "report_index.json")
    idx = os.path.join(_OUT_DIR, "report_index.json")
    with open(idx, "w", encoding="utf-8") as f:
        json.dump({"tickers": ts, "note": "사업보고서 원문 지원 티커 — build_report_source.py가 생성"}, f, ensure_ascii=False)
    print(f"  report_index.json — {len(ts)}개: {ts}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "005930")
