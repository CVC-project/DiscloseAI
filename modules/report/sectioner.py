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
#  · 번호는 하위번호 허용: "N", "N-M"(셀트리온), "N.M"(LG엔솔) — 구분자 [.-] 둘 다.
#  · 제목은 tempered dot로 </TITLE>를 못 넘게 — '(연결)' 없는 사업내용 제목("6. 주요계약…")에서
#    시작해 다음 '(연결)'까지 통째로 삼켜 428KB 괴물 블록을 만들던 사고(NAVER) 방지.
_NOTE_TITLE_RE = re.compile(
    r"<TITLE[^>]*>\s*(\d{1,2}(?:[.\-]\d{1,2})?)\.?\s*"
    r"((?:(?!</TITLE>).)+?)\s*\(\s*연결\s*\)\s*</TITLE>",
    re.S,
)
# 연결 주석 영역의 끝 = 별도/개별 재무제표 섹션 시작(제목이 딱 '(N.) (별도/개별)?재무제표'로 끝나는 것).
# '재무제표의 작성기준'(SKT 주2) 같은 정상 주석을 경계로 오인하지 않도록 제목 끝을 </TITLE>로 못박음.
# 마지막 연결주석이 이 경계를 넘어 별도재무제표를 통째로 삼키던 사고(NAVER 주37) 방지 — 여기서 캡.
_SEP_BOUNDARY_RE = re.compile(
    r"<TITLE[^>]*>\s*(?:\d+(?:[.\-]\d+)?\.?\s*)?(?:별도|개별)?재무제표\s*"
    r"(?:\(\s*별도\s*\))?\s*</TITLE>"
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


def _note_key(no: str) -> tuple[int, int]:
    """'2-1'·'11.1'·'3' → (주번호, 하위번호) 정렬키. 하위번호 없으면 0."""
    parts = re.split(r"[.\-]", no, maxsplit=1)
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0)


def _split_notes(full_xml: str) -> list[tuple[str, str, str]]:
    """연결재무제표 주석을 주석 번호 단위로 분할 → [(note_no, title, html), ...].

    각 연결 주석은 <TITLE>N. 제목 (연결)</TITLE>로 시작('(연결)' 접미로 별도 주석과 구분).
    '연결재무제표 주석' 헤더는 목차·요약에도 반복 등장(NAVER는 11회)해 신뢰 불가 →
    주석 번호 1(연결)이 처음 나오는 지점을 연결 주석 시작으로 잡는다. 사업의 내용 절 제목엔
    '(연결)' 접미가 없어 오검출되지 않는다. 별도재무제표 섹션 경계 또는 번호 역행에서 중단.
    """
    hits = list(_NOTE_TITLE_RE.finditer(full_xml))
    if not hits:
        return []
    start = next((i for i, m in enumerate(hits) if _note_key(m.group(1))[0] == 1), 0)
    hits = hits[start:]
    # 연결 주석 영역 뒤에 오는 별도재무제표 섹션 시작 = 마지막 주석의 상한(과다 포획 방지)
    sb = _SEP_BOUNDARY_RE.search(full_xml, hits[0].start())
    sep = sb.start() if sb else len(full_xml)
    out: list[tuple[str, str, str]] = []
    for i, m in enumerate(hits):
        no = m.group(1)
        s = m.start()
        if s >= sep:  # 별도재무제표 섹션 진입 → 연결 주석 끝
            break
        # 번호가 이전보다 작아지면(1로 리셋 등) 연결 주석 끝 → 중단 (N.M/N-M 하위번호 정렬)
        if out and _note_key(no) <= _note_key(out[-1][0]):
            break
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        e = hits[i + 1].start() if i + 1 < len(hits) else min(len(full_xml), s + 300_000)
        out.append((no, title, full_xml[s:min(e, sep)]))
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
