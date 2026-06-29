"""Disclosure 모듈 로컬 테이블 정의"""

import json

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Date,
    Text,
    Boolean,
    UniqueConstraint,
)
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
    stock_code = Column(String)  # 종목코드 (yfinance용) — corp_code와 별도
    high_impact = Column(
        Boolean, default=False, server_default="0"
    )  # 유상증자·CB·BW·감사의견 이상
    dilution_ratio = Column(Float)  # 발행금액 ÷ 시가총액 (희석률)
    display_worthy = Column(
        Boolean, default=False, index=True, server_default="0"
    )  # 대시보드 기본 뷰 노출 여부 (Tier 1 or high_impact)


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
    quarter = Column(Integer, nullable=False)  # 1·2·3·4
    revenue = Column(Float)  # 매출액
    operating_income = Column(Float)  # 영업이익
    net_income = Column(Float)  # 당기순이익
    total_assets = Column(Float)  # 총자산
    total_debt = Column(Float)  # 총부채
    equity = Column(Float)  # 자본총계
    operating_cashflow = Column(Float)  # 영업활동현금흐름
    fetched_at = Column(Date)  # 수집일
    roe = Column(Float)  # ROE = 순이익/자본 × 100
    debt_ratio = Column(Float)  # 부채비율 = 총부채/자본 × 100
    operating_margin = Column(Float)  # 영업이익률 = 영업이익/매출 × 100


def _load_json(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


class CompanySummary(Base):
    """사업보고서 + (후속) 감사보고서를 AI 가공해 만든 회사 참고서 데이터.

    3탭 "참고서" UI 데이터 소스:
      Tab 1 (Galaxy 시각화) ← products, segments
      Tab 2 (재무·감사 풀이) ← financial_highlights, kam, emphasis
      Tab 3 (본문 + 용어 주석) ← glossary_terms

    회사당 1행. JSON 필드는 Text + 직렬화 — SQLite 호환·읽기 패턴 단순.
    헬퍼(get_*)는 JSON 디코드만; 쓰기는 ``set_*`` 또는 직접 ``json.dumps``.

    kam·emphasis는 감사보고서 별도 수집 후 채움 (현재 nullable).
    """

    __tablename__ = "company_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, unique=True, index=True)
    corp_name = Column(String)

    # 출처 사업보고서 식별 — UI에서 "출처: 2024년 사업보고서" 표시용
    rcept_no = Column(String)
    rcept_dt = Column(String)  # YYYYMMDD

    # Tab 1 — 사업 시각화
    products = Column(Text)   # JSON: ["갤럭시", "DDR5", "HBM", ...]
    segments = Column(Text)   # JSON: [{"name","desc","revenue_share"}, ...]

    # Tab 2 — 재무·감사 풀이
    financial_highlights = Column(Text)  # JSON: [{"item","value","yoy","explain"}, ...]
    kam = Column(Text)        # JSON: [{"title","summary","plain"}, ...]
    emphasis = Column(Text)   # JSON: 감사보고서 강조사항, 동일 구조

    # Tab 3 — 본문 hover 툴팁 보강
    glossary_terms = Column(Text)  # JSON: ["EBITDA","HBM","CAPEX", ...]

    # 종합
    investor_notes = Column(Text)  # 주린이용 한단락 요약 (plain text)

    # 메타
    model_used = Column(String)      # 예: "claude-sonnet-4-6"
    source_version = Column(String)  # parsed.json mtime-size hash — 재추출 트리거
    generated_at = Column(Date)

    # ─── JSON 디코더 헬퍼 ───────────────────────────────────────────
    def get_products(self) -> list[str]:
        return _load_json(self.products, [])

    def get_segments(self) -> list[dict]:
        return _load_json(self.segments, [])

    def get_financial_highlights(self) -> list[dict]:
        return _load_json(self.financial_highlights, [])

    def get_kam(self) -> list[dict]:
        return _load_json(self.kam, [])

    def get_emphasis(self) -> list[dict]:
        return _load_json(self.emphasis, [])

    def get_glossary_terms(self) -> list[str]:
        return _load_json(self.glossary_terms, [])
