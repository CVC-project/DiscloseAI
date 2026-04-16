"""Supabase(PostgreSQL) 연결 설정 — 모든 모듈에서 공유"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from shared.config import DATABASE_URL

Base = declarative_base()

engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine) if engine else None


def get_session():
    """DB 세션을 생성하여 반환합니다.

    사용 예:
        session = get_session()
        results = session.query(FinancialData).all()
        session.close()
    """
    if SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    return SessionLocal()
