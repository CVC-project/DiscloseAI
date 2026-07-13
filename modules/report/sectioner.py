"""sectioner.py — 원문(raw_cache)을 섹션 단위로 분할 → report_section.

목차 기반: 'II. 사업의 내용' 절 + 'III.3 연결재무제표 주석'을 주석 번호(주1..주N) 단위 2차 분할.
표 HTML 보존(text_html) + LLM 투입용 markdown(text_md) 저장. 산업 무관 단일 구현(부록 B-2: 13/14 동일).

⚠️ DART 문서 구조는 기업별 편차가 있어 backfill(실데이터)에서 임계 조정 필요.
실행: python -m modules.report.sectioner
"""

from __future__ import annotations

import os
import re

from .db import get_local_session, init_local_db
from .models import PipelineState, ReportRaw, ReportSection

_HERE = os.path.dirname(__file__)

# 사업의 내용 절(통짜 저장) 패턴
_BIZ_HEAD = (r"II\.\s*사업의\s*내용", "II.사업의내용")
# 연결재무제표 주석 = DART XML의 <TITLE>N. 제목 (연결)</TITLE> 태그로 구분 (주N 아님).
_NOTE_TITLE_RE = re.compile(
    r"<TITLE[^>]*>\s*(\d{1,2})\.\s*(.+?)\s*\(\s*연결\s*\)\s*</TITLE>", re.S
)


def _load_raw(raw_path: str) -> str | None:
    p = os.path.join(_HERE, raw_path) if raw_path else None
    if not p or not os.path.exists(p):
        return None
    return open(p, encoding="utf-8", errors="ignore").read()


def _to_md(html: str) -> str:
    """표 구조를 대략 보존한 markdown 근사 (LLM 투입용). 표는 |셀| 형태로."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    parts = []
    # DART XML: 표 셀은 <TE>·<TU>(+표준 td/th), 문단은 <P> (html.parser가 소문자화)
    for el in soup.find_all(["p", "table"]):
        if el.name == "table":
            for tr in el.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th", "te", "tu"])]
                if any(cells):
                    parts.append("| " + " | ".join(cells) + " |")
            parts.append("")
        else:
            t = el.get_text(strip=True)
            if t:
                parts.append(t)
    return "\n".join(parts)


def _split_notes(full_xml: str) -> list[tuple[str, str, str]]:
    """연결재무제표 주석을 주석 번호 단위로 분할 → [(note_no, title, html), ...].

    DART XML: '연결재무제표 주석' 헤더 이후 <TITLE>N. 제목 (연결)</TITLE>가 각 주석 시작.
    '(연결)' 접미로 별도재무제표 주석과 구분. 주석 번호가 1로 리셋되면 별도 시작이므로 중단.
    """
    h = re.search(r"연결재무제표\s*주석", full_xml)
    if not h:
        return []
    region = full_xml[h.end():]
    hits = list(_NOTE_TITLE_RE.finditer(region))
    if not hits:
        return []
    out: list[tuple[str, str, str]] = []
    for i, m in enumerate(hits):
        no = m.group(1)
        # 번호가 이전보다 작아지면(1로 리셋 등) 연결 주석 끝 → 중단
        if out and int(no) <= int(out[-1][0]):
            break
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        start = m.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else min(len(region), start + 300_000)
        out.append((no, title, region[start:end]))
    return out


def section_all(tickers: list[str] | None = None) -> None:
    init_local_db()
    sess = get_local_session()
    q = sess.query(ReportRaw)
    if tickers:
        q = q.filter(ReportRaw.ticker.in_(set(tickers)))
    for raw in q.all():
        html = _load_raw(raw.raw_path)
        if not html:
            _mark(sess, raw.rcept_no, raw.ticker, "FAIL")
            continue
        # 기존 섹션 삭제 후 재적재 (idempotent)
        sess.query(ReportSection).filter_by(rcept_no=raw.rcept_no).delete()
        n = 0
        # ① II. 사업의 내용 (통짜)
        mb = re.search(_BIZ_HEAD[0], html)
        if mb:
            seg = html[mb.start() : mb.start() + 800_000]
            md = _to_md(seg)
            sess.add(
                ReportSection(
                    rcept_no=raw.rcept_no,
                    section_key=_BIZ_HEAD[1],
                    note_no=None,
                    title=_BIZ_HEAD[1],
                    text_html=seg[:500_000],
                    text_md=md,
                    char_len=len(md),
                )
            )
            n += 1
        # ② 연결재무제표 주석 → 주석 번호 단위
        for note_no, title, note_html in _split_notes(html):
            md = _to_md(note_html)
            sess.add(
                ReportSection(
                    rcept_no=raw.rcept_no,
                    section_key="III.3.연결주석",
                    note_no=note_no,
                    title=title,
                    text_html=note_html[:500_000],
                    text_md=md,
                    char_len=len(md),
                )
            )
            n += 1
        _mark(sess, raw.rcept_no, raw.ticker, "OK" if n > 1 else "FAIL")
        sess.commit()
        print(f"[{raw.ticker}] {raw.fiscal_year} rcept={raw.rcept_no}: {n} 섹션")
    sess.close()


def _mark(sess, rcept_no, ticker, status):
    st = (
        sess.query(PipelineState)
        .filter_by(rcept_no=rcept_no, target="section")
        .one_or_none()
    )
    if st is None:
        st = PipelineState(rcept_no=rcept_no, ticker=ticker, target="section")
        sess.add(st)
    st.stage, st.status = "SECTIONED", status
    st.attempts = (st.attempts or 0) + 1


if __name__ == "__main__":
    section_all()
