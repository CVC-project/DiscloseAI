"""Disclosure 모듈 로컬 테이블 정의"""
from sqlalchemy import Column, String, Integer, Float, Date, Text
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
