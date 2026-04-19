"""Disclosure 모듈 로컬 테이블 정의"""
from sqlalchemy import Column, String, Integer, Float, Date, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DisclosureLocal(Base):
    __tablename__ = "disclosure_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disclosure_id = Column(String, unique=True, index=True)
    corp_code = Column(String, nullable=False, index=True)
    corp_name = Column(String)
    disclosure_date = Column(Date)
    disclosure_type = Column(String)
    title = Column(String)
    amount = Column(Float)
    summary = Column(Text)
    ai_analyzed = Column(Boolean, default=False, nullable=False, server_default="0")


class FinancialStatement(Base):
    """기업별 분기 재무제표 히스토리 (최근 8분기 보관)"""
    __tablename__ = "financial_statement"
    __table_args__ = (
        UniqueConstraint("corp_code", "year", "quarter", name="uq_corp_period"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)
    corp_name = Column(String)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)        # 1·2·3·4
    revenue = Column(Float)                          # 매출액
    operating_income = Column(Float)                 # 영업이익
    net_income = Column(Float)                       # 당기순이익
    total_assets = Column(Float)                     # 총자산
    total_debt = Column(Float)                       # 총부채
    equity = Column(Float)                           # 자본총계
    operating_cashflow = Column(Float)               # 영업활동현금흐름
    fetched_at = Column(Date)                        # 수집일
