# -*- coding: utf-8 -*-
"""report_source.py — 사업보고서 '원문 보기' 팝업용 원문 데이터 추출 (report 모듈 로직 정본).

현금 은하수 딥다이브에서 그 카드가 유래한 사업보고서 원문(연결재무제표 5본 + 주석 전수)을
좌측 팝업에 띄우기 위한 per-ticker 데이터를 만든다. **LLM 무관 — 결정론 추출.**

핵심: DART 표는 colspan/rowspan(병합 셀)이 많아 셀을 좌→우로 단순 평탄화하면 열이 어긋난다.
`_table_grid()`가 병합을 격자로 전개(rectangular)해 정렬을 보존한다. 출력은 문단/표 **blocks**
리스트라 렌더러(galaxy.html buildSrcPanel)가 표를 개별·정렬로 그린다.

- 입력(report 모듈 자체 데이터): reports.db report_section(주석 text_html) + raw_cache XML(재무제표).
- 출력 dict: {ticker, rcept_no, statements:{bs/is/cis/eq/cf:{title,blocks}}, notes:{no:{title,blocks}}}.
- 확장: 새 기업 = collector·sectioner로 reports.db에 있으면 `build_report_data(ticker)` 즉시 가능.
  서빙 파일 생성·매니페스트는 integration/dossier/build_report_source.py(서빙 계층)가 호출.

문서: modules/report/REPORT_SOURCE.md
"""
from __future__ import annotations

import os
import re
import sqlite3

_HERE = os.path.dirname(os.path.abspath(__file__))
_DB = os.path.join(_HERE, "data", "reports.db")

# 연결재무제표 5본: raw XML <TITLE> 접두 → 키·표시명
_STMTS = [
    (r"2-1\.", "bs", "연결 재무상태표"),
    (r"2-2\.", "is", "연결 손익계산서"),
    (r"2-3\.", "cis", "연결 포괄손익계산서"),
    (r"2-4\.", "eq", "연결 자본변동표"),
    (r"2-5\.", "cf", "연결 현금흐름표"),
]
_TITLE_RE = re.compile(r"<TITLE[^>]*>[^<]*</TITLE>")
_CELL_TAGS = ["td", "th", "te", "tu"]
# 초장문 표(종속기업/계열사 목록 등 수백 행)는 원문 학습 목적상 상위 N행만 — 파일 비대 방지.
_ROW_CAP = 60


def _table_grid(table) -> list[list[str]]:
    """<table>를 colspan/rowspan 전개한 직사각 격자(list[list[str]])로. 병합 잔여칸은 ''.

    표준 알고리즘: (r,c) 셀맵에 배치하되, 이미 채워진 칸(윗줄 rowspan)은 건너뛴다.
    병합 셀은 좌상단에만 텍스트, 나머지 확장칸은 ''(빈칸)로 채워 열 정렬을 보존한다.
    """
    cellmap: dict[tuple[int, int], str] = {}
    maxc = 0
    for r, tr in enumerate(table.find_all("tr")):
        c = 0
        for cell in tr.find_all(_CELL_TAGS):
            while (r, c) in cellmap:
                c += 1
            text = cell.get_text(" ", strip=True)
            try:
                cs = max(1, int(cell.get("colspan") or 1))
                rs = max(1, int(cell.get("rowspan") or 1))
            except (ValueError, TypeError):
                cs = rs = 1
            for dr in range(rs):
                for dc in range(cs):
                    cellmap[(r + dr, c + dc)] = text if (dr == 0 and dc == 0) else ""
            c += cs
            maxc = max(maxc, c)
    nrows = max((k[0] for k in cellmap), default=-1) + 1
    rows = [[cellmap.get((r, c), "") for c in range(maxc)] for r in range(nrows)]
    # 완전 빈 열 제거(병합 전개 부산물) — 열 정렬 유지하며 폭 축소
    keep = [c for c in range(maxc) if any(rows[r][c] for r in range(nrows))]
    return [[row[c] for c in keep] for row in rows] if keep else rows


def _html_to_blocks(html: str) -> list[dict]:
    """HTML을 문서 순서의 blocks로: 표→{t:'table',rows}, 문단→{t:'p',v}. (표는 격자 전개)"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    blocks: list[dict] = []
    for el in soup.find_all(["p", "table"]):
        # 표 안의 <p>는 표에서 처리되므로 스킵
        if el.name == "p":
            if el.find_parent("table"):
                continue
            t = el.get_text(" ", strip=True)
            if t:
                blocks.append({"t": "p", "v": t})
        else:  # table
            rows = _table_grid(el)
            n = len(rows)
            if n > _ROW_CAP:
                rows = rows[:_ROW_CAP]
            if any(any(c for c in r) for r in rows):
                blocks.append({"t": "table", "rows": rows})
                if n > _ROW_CAP:
                    blocks.append({"t": "p", "v": f"… (표가 길어 상위 {_ROW_CAP}행만 표시했어요 · 원문 총 {n}행)"})
    return blocks


def _extract_statements(doc: str) -> dict:
    """raw XML에서 재무제표 5본 블록(TITLE→다음 TITLE)을 잘라 blocks로."""
    titles = [(m.start(), m.group(0)) for m in _TITLE_RE.finditer(doc)]
    out: dict[str, dict] = {}
    for i, (pos, tag) in enumerate(titles):
        txt = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", tag)).strip()
        for pat, key, name in _STMTS:
            if key in out:
                continue
            if re.match(pat, txt):
                end = titles[i + 1][0] if i + 1 < len(titles) else len(doc)
                out[key] = {"title": name, "blocks": _html_to_blocks(doc[pos:end])}
    return out


def _extract_notes(cur, rcept: str) -> dict:
    """report_section.text_html(주석 원문 HTML) → blocks."""
    rows = cur.execute(
        "select note_no, title, text_html from report_section "
        "where rcept_no=? and note_no is not null",
        (rcept,),
    ).fetchall()

    def nk(n):
        p = re.split(r"[.\-]", str(n))
        return tuple(int(x) if x.strip().isdigit() else 0 for x in p)

    rows.sort(key=lambda r: nk(r[0]))
    return {no: {"title": title or "", "blocks": _html_to_blocks(html or "")} for no, title, html in rows}


def build_report_data(ticker: str, db_path: str = _DB) -> dict:
    """ticker의 최신 사업보고서 원문(재무제표+주석)을 blocks 구조 dict로. reports.db 필요."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        "select rcept_no, raw_path from report_raw where ticker=? order by fiscal_year desc limit 1",
        (ticker,),
    ).fetchone()
    if not row:
        con.close()
        raise ValueError(f"[{ticker}] report_raw 없음 — collector/sectioner 먼저")
    rcept, raw_path = row
    doc = open(os.path.join(_HERE, raw_path), encoding="utf-8", errors="ignore").read()
    data = {
        "ticker": ticker,
        "rcept_no": rcept,
        "statements": _extract_statements(doc),
        "notes": _extract_notes(cur, rcept),
    }
    con.close()
    return data
