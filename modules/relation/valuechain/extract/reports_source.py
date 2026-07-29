"""shared/data/reports.db 읽기 전용 접근 (valuechain PLAN.md D11 예외).

**`modules.report` 패키지를 import하지 않는다** — 루트 CLAUDE.md "데이터 모듈끼리
import 금지" 원칙은 그대로 유지하고, D11 예외(reports.db는 report 모듈 쓰기 단독·
그 외 read-only)는 **DB 파일 직결(read-only URI)** 로만 행사한다. 스키마(컬럼명)는
modules/report/models.py의 ReportRaw·ReportSection과 값 대조로 동기화 상태 유지 —
report 쪽 스키마 변경 시 이 파일도 함께 갱신.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
REPORTS_DB_PATH = _REPO_ROOT / "shared" / "data" / "reports.db"


def _connect_readonly() -> sqlite3.Connection:
    uri = f"file:{REPORTS_DB_PATH.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_rp_note_sections() -> list[dict]:
    """특수관계자 주석 노트 전량 — 제목 접두 규칙(U-확대 2026-07-29).

    NOTE_TITLES 정확 일치(실측 10종)는 867사만 커버 — 전 상장사 코퍼스(2,590사
    섹셔닝)에서 제목 변형이 ~40종·120여사 추가 실측됨('특수관계자 공시'·
    '특수관계자 등'·'특수관계자와의 거래내역'…). 변형을 일일이 열거하는 대신
    접두 규칙으로 잡는다 — 정밀도는 파서가 표 형태 앵커로 지키므로(억지 매칭
    금지 원칙) 제목망 확대는 재현율만 올린다. 제외 2종은 제목이 '특수관계'로
    시작하지 않는 무관 주석(담보제공자산·지급보증)이라 접두 규칙이 자연 배제.
    section_key는 전량 'III.3.연결주석' 실측 — 별도재무제표 혼입 없음.
    """
    conn = _connect_readonly()
    try:
        cur = conn.execute(
            """
            SELECT rs.rcept_no, rs.title, rs.text_md, rs.text_html, rr.corp_code8, rr.fiscal_year
            FROM report_section rs
            JOIN report_raw rr ON rs.rcept_no = rr.rcept_no
            WHERE rs.title LIKE '특수관계%'
               OR rs.title LIKE '연결실체와 특수관계자%'
               OR rs.title = '중요한 특수관계자 거래'
            """
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_sections_by_title(titles: set[str]) -> list[dict]:
    """report_section ⋈ report_raw — title이 titles에 속하는 행 전량.

    Returns: [{"rcept_no", "title", "text_md", "text_html", "corp_code8", "fiscal_year"}, ...]
    text_html은 sectioner의 markdown 변환 이전 원본 HTML(ROWSPAN 등 보존) — U3
    행=개별회사형처럼 markdown 평탄화로 유실되는 표 구조를 복원해야 할 때 사용.
    """
    if not titles:
        return []
    conn = _connect_readonly()
    try:
        placeholders = ",".join("?" for _ in titles)
        cur = conn.execute(
            f"""
            SELECT rs.rcept_no, rs.title, rs.text_md, rs.text_html, rr.corp_code8, rr.fiscal_year
            FROM report_section rs
            JOIN report_raw rr ON rs.rcept_no = rr.rcept_no
            WHERE rs.title IN ({placeholders})
            """,
            list(titles),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()
