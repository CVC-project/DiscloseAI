"""Disclosure 모듈 로컬 DB — 개발/테스트용 SQLite"""

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "disclosure.db")
engine = create_engine(f"sqlite:///{_DB_PATH}")
LocalSession = sessionmaker(bind=engine)


def _add_missing_columns():
    """ORM 모델에 정의된 컬럼 중 실제 SQLite 테이블에 없는 것만 ALTER로 추가.

    SQLAlchemy ``create_all``은 새 테이블만 만들고 기존 테이블에 컬럼 추가는 안 함.
    팀이 점진적으로 컬럼을 늘리는 PoC 단계라 가벼운 자동 마이그레이션이 유용.
    DROP·rename은 다루지 않는다 — 그런 변경은 별도 Alembic 도입 후 처리.
    """
    from .models import Base

    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    for tbl_name, table in Base.metadata.tables.items():
        if tbl_name not in existing_tables:
            continue  # create_all 가 만들 것
        existing_cols = {c["name"] for c in insp.get_columns(tbl_name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            col_type = col.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(
                    text(f'ALTER TABLE "{tbl_name}" ADD COLUMN "{col.name}" {col_type}')
                )
            print(f"[migrate] {tbl_name} + {col.name} {col_type}")


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from .models import Base

    Base.metadata.create_all(engine)
    _add_missing_columns()
    print(f"로컬 DB 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
