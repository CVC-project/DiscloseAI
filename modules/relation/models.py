"""Relation 모듈 로컬 테이블 정의"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RelationLocal(Base):
    __tablename__ = "relation_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_corp = Column(String, nullable=False, index=True)
    target_corp = Column(String, nullable=False, index=True)
    relation_type = Column(String)
    detail = Column(String)
