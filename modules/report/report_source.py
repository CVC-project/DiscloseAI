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
_DB = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "shared", "data", "reports.db")

# 연결재무제표 최대 5본: raw XML <TITLE> **명칭 매칭** → 키. (V-068)
# 번호 접두(2-1…)는 회사마다 다르다 — 단일 포괄손익계산서 회사(SK·NAVER·고려아연·현대건설)는
# 손익계산서가 없어 2-1~2-4로 밀린다. 번호 하드코딩(구 2-1~2-5)은 이들의 is/cis/eq를 한 칸씩
# 오라벨하고 cf를 결손시켰다. 명칭으로 매칭하면 5본/4본 레이아웃을 모두 정합 추출한다.
# 주석도 2-x 접두를 갖는 회사(셀트리온)가 있으나 주석 명칭은 재무제표명과 겹치지 않고, 재무제표가
# 주석보다 문서상 앞서므로 키별 first-wins가 실제 재무제표를 집는다.
_STMT_MATCH = [
    ("bs", lambda s: "재무상태표" in s),
    ("is", lambda s: "손익계산서" in s and "포괄" not in s),
    ("cis", lambda s: "포괄손익" in s),
    ("eq", lambda s: "자본변동" in s),
    ("cf", lambda s: "현금흐름" in s),
]
_STMT_NUMPREFIX = re.compile(r"^\d+-\d+\.?\s*")
_TITLE_RE = re.compile(r"<TITLE[^>]*>[^<]*</TITLE>")
_CELL_TAGS = ["td", "th", "te", "tu"]
# 초장문 표(종속기업/계열사 목록 등 수백 행)는 원문 학습 목적상 상위 N행만 — 파일 비대 방지.
_ROW_CAP = 60
# 비정형 표 가드: DART 종속기업/계열사 목록 등은 마크업이 뭉개져 격자 전개 시 수백 열·거대 셀이
# 됨(삼성 주1: 60행×1486열·23,752자 셀). 재무 표는 열≤~12·셀 짧음 → 아래 임계 초과면 표 생략.
_COL_CAP = 18
_CELL_CAP = 600


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
    rows = [[row[c] for c in keep] for row in rows] if keep else rows
    # 완전 빈 행 제거 (rowspan 전개로 생긴 성긴 행 — 세로 여백 낭비)
    return [r for r in rows if any(c.strip() for c in r)]


def _html_to_blocks(html: str, *, row_cap: int | None = _ROW_CAP) -> list[dict]:
    """HTML을 문서 순서의 blocks로: 표→{t:'table',rows}, 문단→{t:'p',v}. (표는 격자 전개)

    ⚠️ `row_cap=None`이면 행 절단을 하지 않는다 — **재무제표 본표 전용**(V-109).
    _ROW_CAP은 주석의 초장문 표(종속기업 목록 등)를 위한 가드인데, 본표에 적용하면
    대한항공 연결현금흐름표(119행)처럼 투자·재무활동 절반이 통째로 잘려 3-way
    계정셀 링크가 그 행들에 닿지 못한다. 본표는 열 ≤ ~12·셀이 짧아 비대 위험이 없다.
    """
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
            # V-119 — **1열 표는 표가 아니라 레이아웃 컨테이너다.** DART 원문은 산문 주석을
            #   1열×1행 표의 <td> 안에 <p>로 싣는 경우가 있다(원익IPS 주5 실측: <p> 19개 전부
            #   표 안 → 표 안 <p> 스킵 + 셀 초과 비정형 판정 → 본문 통째 소실). 셀 안 문단을 전개한다.
            _tds = el.find_all("td")
            if len(_tds) <= 2 and not el.find("table"):
                _ps = [q.get_text(" ", strip=True) for q in el.find_all("p")]
                _ps = [t for t in _ps if t]
                if len(_ps) >= 3:  # 문단 여럿 = 산문 컨테이너. 값 표(1~2셀 짧은 표)는 종전 경로.
                    blocks.extend({"t": "p", "v": t} for t in _ps)
                    continue
            rows = _table_grid(el)
            if not rows:
                continue
            ncols = max((len(r) for r in rows), default=0)
            maxcell = max((len(c) for r in rows for c in r), default=0)
            # 비정형 표(종속기업 목록 등) — 격자가 뭉개진 경우 표 대신 안내 문단
            if ncols > _COL_CAP or maxcell > _CELL_CAP:
                blocks.append(
                    {
                        "t": "p",
                        "v": "(종속기업 목록 등 대형·비정형 표는 여기선 생략했어요 — 전체는 DART 원문에서 확인)",
                    }
                )
                continue
            n = len(rows)
            if row_cap and n > row_cap:
                rows = rows[:row_cap]
            blocks.append({"t": "table", "rows": rows})
            if row_cap and n > row_cap:
                blocks.append(
                    {
                        "t": "p",
                        "v": f"… (표가 길어 상위 {row_cap}행만 표시했어요 · 원문 총 {n}행)",
                    }
                )
    return blocks


def _extract_statements(doc: str) -> dict:
    """raw XML에서 재무제표 블록(TITLE→다음 TITLE)을 **명칭 매칭**으로 잘라 blocks로.
    title은 XML 실제 제목에서 번호 접두만 제거해 사용(회사별 번호 차이 흡수). 재무제표가
    주석보다 앞서므로 키별 first-wins가 실제 재무제표를 집는다(주석 2-x 오매칭 방지)."""
    titles = [(m.start(), m.group(0)) for m in _TITLE_RE.finditer(doc)]
    out: dict[str, dict] = {}
    for i, (pos, tag) in enumerate(titles):
        txt = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", tag)).strip()
        for key, match in _STMT_MATCH:
            if key in out:
                continue
            if match(txt):
                end = titles[i + 1][0] if i + 1 < len(titles) else len(doc)
                disp = _STMT_NUMPREFIX.sub("", txt)
                # 본표는 행 절단 금지(V-109) — 절단하면 잘린 행의 계정셀 링크가 사라진다.
                out[key] = {
                    "title": disp,
                    "blocks": _html_to_blocks(doc[pos:end], row_cap=None),
                }
                break
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
    return {
        no: {"title": title or "", "blocks": _html_to_blocks(html or "")}
        for no, title, html in rows
    }


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
