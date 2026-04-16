"""Price 모듈 로컬 DB — 개발/테스트용 SQLite"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "price.db")
engine = create_engine(f"sqlite:///{_DB_PATH}")
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from modules.price.models import Base
    Base.metadata.create_all(engine)
    print(f"로컬 DB 생성 완료: {_DB_PATH}")


def get_local_session():
    return LocalSession()
