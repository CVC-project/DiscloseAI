"""reports.db 스키마 (DOSSIER_TABS_PLAN Phase 3). 5개년 원문·섹션·정형계정·파이프라인 상태.

⚠️ shared/models.py(미래 운영 PostgreSQL)와 별개 — 이건 모듈 로컬 SQLite 정본.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ReportRaw(Base):
    """사업보고서 원문 1건 = 1행 (5개년치 다행). raw_path는 raw_cache/ 상대경로."""

    __tablename__ = "report_raw"

    rcept_no = Column(String, primary_key=True)  # 접수번호 (DART 고유)
    ticker = Column(String, nullable=False, index=True)  # 6자리 종목코드
    corp_code8 = Column(String, nullable=False, index=True)  # 8자리 DART corp_code
    corp_name = Column(String)
    fiscal_year = Column(Integer, nullable=False, index=True)  # 사업연도 (FY)
    report_nm = Column(String)  # 보고서명 (사업보고서 / 정정 등)
    fetched_at = Column(DateTime, server_default=func.now())
    raw_path = Column(String)  # raw_cache/<ticker>/<rcept_no>.xml 등


class ReportSection(Base):
    """원문을 섹션(주석 번호 단위 등)으로 분할. 표 HTML 보존 + markdown."""

    __tablename__ = "report_section"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rcept_no = Column(
        String, ForeignKey("report_raw.rcept_no"), nullable=False, index=True
    )
    section_key = Column(String, index=True)  # 예: 'II.사업의내용', 'III.3.연결주석'
    note_no = Column(String)  # 주석 번호 (주16 등), 없으면 null
    title = Column(String)
    text_html = Column(Text)  # 표 보존용 원본 HTML
    text_md = Column(Text)  # LLM 투입용 markdown
    char_len = Column(Integer)


class FsAccount(Base):
    """fnlttSinglAcntAll(전 계정) ×5개년 정형 재무 숫자. sj_div = BS/IS/CF/CE/CIS."""

    __tablename__ = "fs_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rcept_no = Column(String, index=True)
    ticker = Column(String, nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    sj_div = Column(String, index=True)  # 재무제표 구분 (BS/IS/CF/CE/CIS)
    account_id = Column(String, index=True)  # 표준계정ID (ifrs-full_Revenue 등)
    account_nm = Column(String)
    amount = Column(Float)  # 원 단위
    currency = Column(String, default="KRW")


class PipelineState(Base):
    """rcept×target(collect/section/enrich/series/generate)별 진행 상태."""

    __tablename__ = "pipeline_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rcept_no = Column(String, index=True)
    ticker = Column(String, index=True)
    target = Column(String)  # collect | section | enrich | series | generate
    stage = Column(String)  # COLLECTED | SECTIONED | ENRICHED | ...
    status = Column(String, default="PENDING")  # PENDING | OK | FAIL
    attempts = Column(Integer, default=0)
    error = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
