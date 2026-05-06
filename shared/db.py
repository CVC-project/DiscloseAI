"""Supabase(PostgreSQL) 연결 설정 — 모든 모듈에서 공유.

엔진은 lazy 생성: 모듈 import 시점에는 만들지 않고, get_session()이
실제로 호출될 때만 create_engine을 실행한다. 이렇게 해야 placeholder
DATABASE_URL이 있는 .env 상태에서도 shared.models import가 성공한다.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from shared.config import DATABASE_URL

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요."
            )
        _engine = create_engine(DATABASE_URL)
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal


def get_session():
    """DB 세션을 생성하여 반환합니다.

    사용 예:
        session = get_session()
        results = session.query(FinancialData).all()
        session.close()
    """
    return _get_session_factory()()
