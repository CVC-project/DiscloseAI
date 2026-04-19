"""Relation 모듈 로컬 테이블 정의.

shared/models.py의 RelationData와 별개로 개발·테스트 단계에서 사용하는 로컬 스키마.
MVP 검증 완료 후 shared/ 로 승격 PR 예정.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
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


class RelationRaw(Base):
    """ingest 단계의 원본 수집 데이터 (기업명 정규화·ticker 매칭 전).

    transform/filters.apply()가 이 테이블을 읽어 ticker 매칭 + 개인·재단 필터를 거쳐
    RelationLocal로 마이그레이션. ingest는 이 테이블에 "원본 그대로" 저장하는 것이 원칙.

    source_type 값:
      - hyslrSttus: DART 최대주주 현황 (target_name = 자기 기업명, source_name = 주주명)
      - otrCprInvstmntSttus: DART 타법인 출자 (source_name = 자기 기업명, target_name = 피투자법인명)
      - ftc: 공정위 소속회사 정보
      - dart_filing: 사업보고서 주석 특수관계자 섹션
    """

    __tablename__ = "relation_raw"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(
        String, nullable=False, index=True
    )  # 정규화 전 원본 기업명·주주명
    target_name = Column(String, nullable=False, index=True)
    relate = Column(String)  # DART hyslrSttus의 관계 필드 (본인/친인척/계열회사 등)
    ratio = Column(Float)  # 지분율 %
    stock_knd = Column(String)  # 주식 종류 (보통주/우선주)
    source_type = Column(String, nullable=False)
    bsns_year = Column(Integer)  # 사업연도 (DART 기준)
    raw_response = Column(Text)  # 원본 API 응답 항목 (JSON 문자열, 감사 추적용)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


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
