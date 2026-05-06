"""Relation 모듈 로컬 DB — 개발/테스트용 SQLite."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# storage/db.py -> modules/relation/data/relation.db
_MODULE_DIR = os.path.dirname(os.path.dirname(__file__))
_DB_PATH = os.path.join(_MODULE_DIR, "data", "relation.db")

engine = create_engine(f"sqlite:///{_DB_PATH}")
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from .models import Base

    Base.metadata.create_all(engine)
    print(f"로컬 DB 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
