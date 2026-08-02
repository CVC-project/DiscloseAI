"""report 모듈 로컬 DB — reports.db (SQLite, 정본).

shared/data/ 승격(2026-07-21, valuechain D11): 쓰기는 이 모듈(collector·sectioner·
fs_enrich)만, relation 등 타 모듈은 read-only. "정본=모듈 로컬" 원칙의 명시적 예외
(루트 CLAUDE.md·docs/ARCHITECTURE.md §3.5 참조).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_DB_PATH = os.path.join(_REPO_ROOT, "shared", "data", "reports.db")
engine = create_engine(f"sqlite:///{_DB_PATH}")
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from .models import Base

    Base.metadata.create_all(engine)
    print(f"reports.db 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
