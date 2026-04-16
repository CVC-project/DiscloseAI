"""Financial 모듈 로컬 DB — 개발/테스트용 SQLite

사용법:
    from modules.financial.db import get_local_session, init_local_db

    init_local_db()  # 최초 1회: 테이블 생성
    session = get_local_session()
    session.add(FinancialLocal(corp_code="005930", ...))
    session.commit()
    session.close()

Supabase(공용 DB)에 올릴 때:
    Claude Code에게 "로컬 DB 데이터를 Supabase로 옮겨줘" 라고 요청
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "financial.db")
_DB_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(_DB_URL)
LocalSession = sessionmaker(bind=engine)


def init_local_db():
    """로컬 SQLite DB 생성 + 테이블 초기화"""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    from modules.financial.models import Base
    Base.metadata.create_all(engine)
    print(f"로컬 DB 생성 완료: {_DB_PATH}")


def get_local_session():
    """로컬 DB 세션 반환"""
    return LocalSession()
