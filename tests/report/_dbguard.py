# -*- coding: utf-8 -*-
"""로컬 전용 테스트의 스킵 가드 — '파일 존재'가 아니라 '데이터 존재'로 판정한다.

`shared/data/reports.db`는 gitignore라 CI에는 없고, 그 DB가 필요한 테스트는 skip해야 한다.
종전 가드는 `os.path.exists(_DB)`였는데 **sqlite는 연결만 해도 빈 파일을 만든다** —
`init_local_db()`를 부르는 테스트가 알파벳 순으로 먼저 돌면서 정본 경로에 빈 스키마를
만들어 놓으면, 뒤에 오는 테스트의 가드가 무력화돼 **빈 DB로 단정 검사를 돌다 실패**한다
(PR #106 CI 실패의 근본 원인).

그래서 판정을 한 겹 낮춘다: 파일이 있어도 `fs_account`에 행이 없으면 '없는 것'으로 본다.
"""
import os
import sqlite3

from modules.report import series as _S

DB = _S._DB


def has_report_data(db_path: str = DB) -> bool:
    """reports.db에 실제 수집 데이터가 있는가(빈 스키마·부재는 False)."""
    if not os.path.exists(db_path):
        return False
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        row = con.execute(
            "select name from sqlite_master where type='table' and name='fs_account'"
        ).fetchone()
        if not row:
            return False
        return con.execute("select 1 from fs_account limit 1").fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        con.close()
