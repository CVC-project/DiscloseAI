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
