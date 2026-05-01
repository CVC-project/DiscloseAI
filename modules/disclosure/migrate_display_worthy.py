"""
기존 DB의 display_worthy 컬럼 백필 스크립트.
SQLite ALTER TABLE로 컬럼을 추가하고, 4,978건에 대해 기준 적용.

실행:
    python -m modules.disclosure.migrate_display_worthy
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import text
from modules.disclosure.db import get_local_session, engine
from modules.disclosure.models import Base, DisclosureLocal
from modules.disclosure.collector import _is_display_worthy


def main():
    # 컬럼이 없으면 ALTER TABLE로 추가
    with engine.connect() as conn:
        cols = [
            row[1]
            for row in conn.execute(
                text("PRAGMA table_info(disclosure_local)")
            ).fetchall()
        ]
        if "display_worthy" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE disclosure_local ADD COLUMN display_worthy INTEGER DEFAULT 0"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_disclosure_local_display_worthy ON disclosure_local (display_worthy)"
                )
            )
            conn.commit()
            print("[마이그레이션] display_worthy 컬럼 추가 완료")
        else:
            print("[마이그레이션] display_worthy 컬럼 이미 존재 — 값만 업데이트")

    session = get_local_session()
    rows = session.query(DisclosureLocal).all()
    total = len(rows)
    worthy_count = 0

    for rec in rows:
        worthy = _is_display_worthy(
            rec.disclosure_type or "",
            rec.title or "",
            bool(rec.high_impact),
        )
        rec.display_worthy = worthy
        if worthy:
            worthy_count += 1

    session.commit()
    session.close()

    print(
        f"[완료] 전체 {total}건 처리 | display_worthy=True: {worthy_count}건 | False: {total - worthy_count}건"
    )


if __name__ == "__main__":
    main()
