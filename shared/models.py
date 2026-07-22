"""
미래 운영(Supabase PostgreSQL) DB 스키마 — **현재 운영 미사용**.

⚠️ 정본은 모듈별 로컬 SQLite입니다 (개발 단계 합의).
   각 모듈은 자기 폴더의 로컬 테이블을 쓴다:
     financial → modules/financial   (financial_local)
     disclosure → modules/disclosure (disclosure_local, financial_statement)
     price → modules/price            (price_local, vkospi_local)
     relation → modules/relation      (company_node, relation_raw, relation_local)
   전체 DB 토폴로지·식별자 규칙은 docs/ARCHITECTURE.md 참조.

이 파일의 테이블은 **미래 운영 이관(Supabase) 시점에 통합·정렬할 타깃 스키마**다.
relation storage/CLAUDE.md의 승격 계획(CompanyNode·RelationLocal 동기화)도 그때 일괄 반영.
현재 활성: PriceData만 (modules/price/linker.py가 실제로 적재). 나머지는 STATUS 주석 참조.

엑셀 비유: 각 class = 시트, 각 Column = 열(헤더), 각 행 = 데이터 1건.
"""

from sqlalchemy import Column, String, Integer, Float, Date, Text, DateTime
from shared.db import Base


# ============================================================
# 1. 재무 DB — A 담당 (financial/)
# ============================================================
class FinancialData(Base):
    """재무제표 + EQS 점수"""

    # STATUS: 미사용 (미래 운영 타깃). 정본=modules/financial/ financial_local
    __tablename__ = "financial_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)  # 기업코드 (예: "005930")
    corp_name = Column(String)  # 기업명 (예: "삼성전자")
    year = Column(Integer, nullable=False)  # 연도
    quarter = Column(Integer)  # 분기 (1~4, 연간이면 null)

    # 손익계산서
    revenue = Column(Float)  # 매출액 (조 단위)
    operating_income = Column(Float)  # 영업이익
    net_income = Column(Float)  # 당기순이익

    # 재무상태표
    total_assets = Column(Float)  # 자산총계
    total_liabilities = Column(Float)  # 부채총계
    total_equity = Column(Float)  # 자본총계

    # 현금흐름표
    operating_cashflow = Column(Float)  # 영업활동 현금흐름
    investing_cashflow = Column(Float)  # 투자활동 현금흐름
    financing_cashflow = Column(Float)  # 재무활동 현금흐름

    # EQS 5모듈 점수
    eqs_m1 = Column(Float)  # 발생액 품질 (0~100)
    eqs_m2 = Column(Float)  # 분식 확률
    eqs_m3 = Column(Float)  # 현금흐름 괴리
    eqs_m4 = Column(Float)  # 이익 지속성
    eqs_m5 = Column(Float)  # 재무 건전성
    eqs_total = Column(Float)  # 종합 점수 (0~100)
    eqs_grade = Column(String)  # 등급 (A/B/C/D/F)


# ============================================================
# 2. 공시 DB — B 담당 (disclosure/)
# ============================================================
class DisclosureData(Base):
    """DART 공시 데이터"""

    # STATUS: 미사용 (미래 운영 타깃). 정본=modules/disclosure/ disclosure_local
    __tablename__ = "disclosure_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disclosure_id = Column(String, unique=True, index=True)  # DART 접수번호
    corp_code = Column(String, nullable=False, index=True)
    corp_name = Column(String)
    disclosure_date = Column(Date)  # 공시일
    disclosure_type = Column(String)  # 유형 (유상증자, CAPEX, M&A 등)
    title = Column(String)  # 공시 제목
    amount = Column(Float)  # 관련 금액 (원)
    summary = Column(Text)  # AI 생성 쉬운 설명


# ============================================================
# 3. 관계 DB — C 담당 (relation/)
# ============================================================
class RelationData(Base):
    """기업 간 관계 (그래프 엣지)"""

    # STATUS: 미사용 (미래 운영 타깃). 정본=modules/relation/ relation_local (ticker 6자리)
    # 승격 시 storage/CLAUDE.md의 CompanyNode·RelationLocal 동기화 계획 반영
    __tablename__ = "relation_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_corp = Column(String, nullable=False, index=True)  # 출발 기업코드
    target_corp = Column(String, nullable=False, index=True)  # 도착 기업코드
    relation_type = Column(String)  # 관계 유형 (지분/공급/경쟁/계열)
    detail = Column(String)  # 상세 (지분율 등)


# ============================================================
# 4. 주가 DB — D 담당 (price/)
# ============================================================
class PriceData(Base):
    """주가 + 공시 후 변동 라벨"""

    # STATUS: 활성 — modules/price/linker.py가 실제로 적재하는 유일한 shared 테이블
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    close_price = Column(Float)  # 종가
    daily_return = Column(Float)  # 일간 수익률 (%)
    post_disclosure_5d = Column(Float)  # 공시 후 5일 변동률 (%)
    label = Column(String)  # 라벨 (수혜/악재/중립)
    disclosure_id = Column(String)  # 연결된 공시 ID (nullable)


# ============================================================
# 5. 예측 DB — 프로젝트 리드 (CatBoost 추론 결과)
# ============================================================
class PredictionData(Base):
    """CatBoost 모델 추론 결과"""

    # STATUS: 미사용 (정의만 — CatBoost 파이프라인 미구현)
    __tablename__ = "prediction_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    disclosure_id = Column(String, index=True)  # 원본 공시 ID
    related_corp = Column(String)  # 영향받는 기업코드
    prediction = Column(String)  # 판단 (수혜/악재/중립)
    probability = Column(Float)  # 확률 (0~1)
    evidence_count = Column(Integer)  # 근거 건수
    actual_result = Column(String)  # 실제 결과 (5일 후, 사후 기록)
    created_at = Column(DateTime)


# ============================================================
# 6. 뉴스 DB — 프로젝트 리드
# ============================================================
class NewsData(Base):
    """뉴스 헤드라인 (타임머신용)"""

    # STATUS: 미사용 (정의만 — 뉴스 수집 파이프라인 미구현)
    __tablename__ = "news_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, index=True)
    date = Column(Date)
    source = Column(String)  # 언론사
    headline = Column(String)  # 헤드라인
    url = Column(String)
