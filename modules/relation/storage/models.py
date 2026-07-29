"""Relation 모듈 로컬 테이블 정의.

shared/models.py의 RelationData와 별개로 개발·테스트 단계에서 사용하는 로컬 스키마.
MVP 검증 완료 후 shared/ 로 승격 PR 예정.

2026-07-21 V0: universe(전 상장사 확장)·valuechain(밸류체인 레이어) 스키마 동시 반영.
CompanyRegistry가 CompanyNode를 대체하는 전 상장사 마스터 — graph/build.py 전환 완료까지
CompanyNode는 병존(universe/PLAN.md U-D5).
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CompanyNode(Base):
    """코스피 상위 50개 기업 노드 메타데이터.

    ★V0: CompanyRegistry(전 상장사 마스터)로 전환 예정 — graph/build.py가
    Registry를 읽도록 바뀌기 전까지 과도기적으로 병존(universe/PLAN.md U-D5).
    """

    __tablename__ = "company_node"

    corp_code = Column(String(8), primary_key=True)  # DART 8자리 내부 코드
    corp_name = Column(String, nullable=False, index=True)
    ticker = Column(String(6), unique=True, index=True)  # 종목코드 6자리
    market_cap = Column(Float)  # 시가총액 (억원)
    sector = Column(String)  # 섹터 (viewer/CLAUDE.md의 sectors 키)
    group_name = Column(String, index=True)  # 공정위 기업집단명 (null 가능)
    is_target = Column(Boolean, default=True)  # top50 포함 여부


class CompanyRegistry(Base):
    """전 상장사(~2,600) 마스터 — CompanyNode의 전수 확장 (universe/PLAN.md U-D5).

    valuechain V0와 universe U0가 공유하는 단일 마스터. universe 컬럼 5종
    (market_cap_krw·cap_asof·sector_id·universe_tier·universe_rank)을 처음부터 포함해
    마이그레이션을 1회로 완결한다(valuechain D11·§2.1 스키마 합의 전제).
    """

    __tablename__ = "company_registry"

    corp_code = Column(String(8), primary_key=True)  # DART 8자리
    ticker = Column(String(6), index=True)  # 6자리 (상폐 시에도 보존)
    name_current = Column(String, nullable=False, index=True)
    market = Column(String)  # KOSPI | KOSDAQ
    ksic_code = Column(String)  # 통계청 KSIC 중분류 코드
    io_sector = Column(String)  # 한국은행 산업연관표 부문 (T3용, valuechain D1)
    listing_status = Column(String, default="listed")  # listed | delisted | merged
    delisted_at = Column(String)  # 상장폐지일 (listing_status=delisted일 때)
    merged_into = Column(String(8))  # 승계 corp_code (listing_status=merged일 때)

    # universe 컬럼 5종 (universe/PLAN.md U-D5)
    market_cap_krw = Column(Float)  # 시가총액 (원)
    cap_asof = Column(String)  # 시총 스냅샷 기준일 (pykrx 실패 시 폴백 스냅샷 신선도 표기)
    sector_id = Column(String, index=True)  # ksic_sector_map.csv 매핑 결과
    universe_tier = Column(String)  # named400 | dot
    universe_rank = Column(Integer)  # 시총 순위 (시장 내)

    synced_at = Column(DateTime, default=lambda: datetime.now(UTC))  # M1 루프 갱신 시각


class CompanyAlias(Base):
    """엔티티 링킹용 별칭 사전 — 밸류체인·주석 추출의 상대 기업명 매칭 정확도 관건.

    valuechain PLAN.md §2.2. 구사명·약칭·영문명·그룹관용명을 corp_code에 연결해
    5개년 보고서의 과거 표기(사명 변경 이력 포함)를 매칭한다.
    """

    __tablename__ = "company_alias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String(8), nullable=False, index=True)
    alias = Column(String, nullable=False, index=True)
    alias_kind = Column(String)  # former_name | abbreviation | english | group_common
    valid_from = Column(String)  # 사명 변경 이력 — 유효 시작일
    valid_to = Column(String)  # 유효 종료일 (null=현재까지)
    source = Column(String)  # dart_history(자동) | manual(수동 보정 큐)


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

    ★V0(U-D13): 멱등 upsert 키 UNIQUE(source_corp, target_corp, source_type, bsns_year) +
    정정공시 supersede용 status/superseded_by/rcept_no 추가.

    ★U1 실측 수정(2026-07-21): 최초 설계는 relation_type을 키에 포함했으나, kifrs.apply()가
    relation_type을 사후 재분류("ownership"→"subsidiary"/"associate"/"investment")하므로
    relation_type은 **파생 필드**이지 안정적 식별자가 아니다 — 그 값을 유니크 키에 넣으면
    kifrs 재분류 UPDATE 자체가 제약 위반으로 즉시 깨진다(재현 확인됨). source_type
    (hyslrSttus/otrCprInvstmntSttus/ftc/dart_filing/manual)은 kifrs가 건드리지 않는
    안정적 "이 raw 사실이 어디서 왔는가" 식별자라 이걸로 교체. 레이어 공존 원칙(storage/
    CLAUDE.md)은 그대로 유지 — 같은 (source, target) 쌍에 다른 source_type(예: ftc vs
    hyslrSttus)이면 여전히 별도 행으로 공존한다. 막는 것은 "완전히 같은 raw 사실의 중복
    삽입"뿐.
    """

    __tablename__ = "relation_local"
    __table_args__ = (
        UniqueConstraint(
            "source_corp", "target_corp", "source_type", "bsns_year",
            name="uq_relation_local_edge",
        ),
    )

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

    # ★V0(U-D13) 정정공시 supersede
    status = Column(String, default="active")  # active | superseded
    superseded_by = Column(Integer)  # 대체한 엣지 id (nullable)
    rcept_no = Column(String)  # 근거 공시 접수번호


class ValueChainEdge(Base):
    """밸류체인 엣지 정본 (valuechain PLAN.md §2.2).

    지배구조(RelationLocal)와 별개 레이어 — 방향은 물자 흐름(공급자→수요자).
    UNIQUE(src_corp, dst_corp, edge_type, as_of, rcept_no)가 멱등 upsert 키(D12).
    """

    __tablename__ = "value_chain_edge"
    __table_args__ = (
        UniqueConstraint(
            "src_corp", "dst_corp", "edge_type", "as_of", "rcept_no",
            name="uq_value_chain_edge",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    src_corp = Column(String(8), nullable=False, index=True)  # corp_code
    dst_corp = Column(String(8), nullable=False, index=True)  # corp_code
    edge_type = Column(String, nullable=False)  # supply | customer | raw_material | competition
    tier = Column(String, nullable=False)  # T1 | T2 | T3
    source_kind = Column(String)  # rp_note | supply_contract | equity_inv | biz_prose | io_table
    rcept_no = Column(String)  # 근거 공시 접수번호
    provenance = Column(Text)  # 섹션key + 청크id + 원문 문장 (T2 필수)
    amount = Column(Float)  # 거래금액 (있으면 — 엣지 가중치)
    as_of = Column(Integer)  # 사업연도 (연도 스냅샷 — 삭제 대신 보존)
    valid_until = Column(String)  # 계약 종료일 "YYYY-MM-DD" (supply_contract 전용, nullable)
    #   ★2026-07-29 리더 결정(신선도 정책): 공급계약은 종료일 기준 유효 판정, 없으면 2년 컷.
    #   저장은 전 연도 보존(D7) — 필터는 export 단계(valuechain/freshness.py)에서만.
    extractor_ver = Column(String)  # T2: 어댑터·프롬프트·임계값 버전
    confidence = Column(Float)  # T2: 보정된 모델 신뢰도 (§3.6 운영점)
    status = Column(String, default="active")  # active | superseded
    superseded_by = Column(Integer)  # 대체한 엣지 id (nullable)


class SectorIOEdge(Base):
    """T3 업종 백본 (한국은행 산업연관표) — valuechain Phase V4."""

    __tablename__ = "sector_io_edge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    src_sector = Column(String, nullable=False, index=True)
    dst_sector = Column(String, nullable=False, index=True)
    flow_amount = Column(Float)
    io_year = Column(Integer)


class VcChunk(Base):
    """밸류체인 추출 단위 = 문장 윈도우 청크 (valuechain PLAN.md §3.1).

    chunk_id는 rcept_no+section_key+seq로 결정적 생성 — 재실행해도 동일 id(멱등, D12).
    """

    __tablename__ = "vc_chunk"

    chunk_id = Column(String, primary_key=True)  # rcept_no+section_key+seq 결정적 생성
    rcept_no = Column(String, nullable=False, index=True)
    corp_code = Column(String(8), nullable=False, index=True)
    section_key = Column(String)
    text = Column(Text)
    char_span = Column(String)  # "start-end" 원문 오프셋 (provenance 역추적)
    has_candidate = Column(Boolean, default=False)  # 후보 게이트 통과 여부 (§3.1 ①단계)


class VcPipelineState(Base):
    """밸류체인 배치 체크포인트 — 처리 단위는 청크 (valuechain PLAN.md §2.2)."""

    __tablename__ = "vc_pipeline_state"

    chunk_id = Column(String, primary_key=True)
    stage = Column(String, nullable=False)  # extract | verify | link | load
    status = Column(String, default="pending")  # pending|done|failed|requeued|skipped
    attempt = Column(Integer, default=0)
    extractor_ver = Column(String)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class LinkFailQueue(Base):
    """엔티티 링킹 실패 큐 → 수동 별칭 등록 워크플로 (valuechain PLAN.md §2.2, M2 루프)."""

    __tablename__ = "link_fail_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    surface_form = Column(String, nullable=False, index=True)  # 매칭 실패한 원문 표기
    freq = Column(Integer, default=1)  # 등장 빈도 (M2 우선순위)
    sample_chunk_id = Column(String)  # 대표 예시 청크
    resolved_corp = Column(String(8))  # 수동 보정 후 매칭된 corp_code (nullable)
