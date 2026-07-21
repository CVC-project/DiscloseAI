"""Relation 모듈 로컬 DB — 개발/테스트용 SQLite."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# storage/db.py -> modules/relation/data/relation.db
_MODULE_DIR = os.path.dirname(os.path.dirname(__file__))
_DB_PATH = os.path.join(_MODULE_DIR, "data", "relation.db")

# ★U1: busy_timeout — 짧은 배치(FTC 등)가 relation.db에 접근할 때 "database is
# locked"로 즉시 실패하는 대신 잠깐 대기 후 재시도. WAL 모드는 시도하지 않음 —
# 실측 확인: collect()류가 배치 전체를 커밋 1회로 묶는 장기 트랜잭션이라(수천
# 기업 루프 후 최종 commit) WAL 전환 자체가 그 기간 내내 배타 락과 충돌해 실패함.
# 근본 해결은 장기 배치의 증분 커밋 전환(추후) — 그 전까지는 universe/PLAN.md
# §2.1 "장기 배치 직렬 실행 원칙"을 지켜 동시 실행을 피하는 것이 안전.
engine = create_engine(f"sqlite:///{_DB_PATH}", connect_args={"timeout": 30})
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from .models import Base

    Base.metadata.create_all(engine)
    print(f"로컬 DB 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
