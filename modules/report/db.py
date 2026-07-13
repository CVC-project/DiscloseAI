"""report 모듈 로컬 DB — reports.db (SQLite, 정본). disclosure/db.py 패턴 복제(import 금지)."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "reports.db")
engine = create_engine(f"sqlite:///{_DB_PATH}")
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from .models import Base

    Base.metadata.create_all(engine)
    print(f"reports.db 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
