"""Relation 모듈 로컬 테이블 정의.

shared/models.py의 RelationData와 별개로 개발·테스트 단계에서 사용하는 로컬 스키마.
MVP 검증 완료 후 shared/ 로 승격 PR 예정.
"""

from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CompanyNode(Base):
    """코스피 상위 50개 기업 노드 메타데이터."""

    __tablename__ = "company_node"

    corp_code = Column(String(8), primary_key=True)  # DART 8자리 내부 코드
    corp_name = Column(String, nullable=False, index=True)
    ticker = Column(String(6), unique=True, index=True)  # 종목코드 6자리
    market_cap = Column(Float)  # 시가총액 (억원)
    sector = Column(String)  # 섹터 (viewer/CLAUDE.md의 sectors 키)
    group_name = Column(String, index=True)  # 공정위 기업집단명 (null 가능)
    is_target = Column(Boolean, default=True)  # top50 포함 여부


class RelationLocal(Base):
    """기업 간 관계 엣지.

    relation_type 6종:
      - ftc_group: 공정위 공식 계열
      - subsidiary: K-IFRS 지배 (>50%)
      - associate: K-IFRS 관계 (20~50%)
      - investment: 유의적 투자 (5~20%)
      - dart_filing: 사업보고서 주석 (공정위 미포함 기업 한정)
      - manual: 수동 보정
    """

    __tablename__ = "relation_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_corp = Column(String(6), nullable=False, index=True)  # ticker
    target_corp = Column(String(6), nullable=False, index=True)  # ticker
    relation_type = Column(String, nullable=False)
    ratio = Column(Float)  # 지분율 %. 계열·수동은 null
    detail = Column(String)  # "삼성물산 5.01% (계열사)" 등
    source_type = Column(
        String
    )  # hyslrSttus / otrCprInvstmntSttus / ftc / dart_filing / manual
    bsns_year = Column(Integer)  # 사업연도 (DART 기준)
    group_name = Column(String)  # 공정위 집단명 (ftc_group 엣지에만)
