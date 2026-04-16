"""Financial 모듈 로컬 테이블 정의

이 파일에 A가 필요한 테이블을 자유롭게 추가하세요.
shared/models.py의 FinancialData와 동일한 구조를 유지하면
나중에 Supabase로 옮길 때 편합니다.
"""
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FinancialLocal(Base):
    """로컬 재무 데이터 (shared/models.py의 FinancialData와 동일 구조)"""
    __tablename__ = "financial_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)
    corp_name = Column(String)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer)
    revenue = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)
    operating_cashflow = Column(Float)
    investing_cashflow = Column(Float)
    financing_cashflow = Column(Float)
    eqs_m1 = Column(Float)
    eqs_m2 = Column(Float)
    eqs_m3 = Column(Float)
    eqs_m4 = Column(Float)
    eqs_m5 = Column(Float)
    eqs_total = Column(Float)
    eqs_grade = Column(String)
