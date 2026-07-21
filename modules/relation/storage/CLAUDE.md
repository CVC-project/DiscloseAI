# storage/ — 저장 계층 (로컬 SQLite)

> 로컬 SQLite 기반 개발 DB. `shared/models.py`(Supabase PostgreSQL용)와는 **별개**.
> MVP 검증 완료 후 별도 PR로 `shared/models.py` 동기화 예정.
> **2026-07-21 V0**: universe(전 상장사 확장)·valuechain(밸류체인 레이어) 테이블 8종 추가.
> 상세 컬럼 정의는 `models.py`가 정본(주석 포함) — 이 문서는 개요만.

## 파일 2개

| 파일 | 역할 |
|---|---|
| `models.py` | SQLAlchemy 테이블 정의 (10개 — 아래) |
| `db.py` | 엔진·세션 + `init_local_db()` / `get_local_session()` |

## 테이블 10개 (★V0로 8종 추가)

기존 2개(CompanyNode·RelationLocal 확장) + universe/valuechain 신규 8종:

| 테이블 | 역할 | 정본 문서 |
|---|---|---|
| `CompanyRegistry` | 전 상장사(~2,600) 마스터 — CompanyNode 대체 예정(과도기 병존) | [../universe/PLAN.md](../universe/PLAN.md) U-D5 |
| `CompanyAlias` | 엔티티 링킹용 별칭 사전 (구사명·약칭 등) | [../valuechain/PLAN.md](../valuechain/PLAN.md) §2.2 |
| `ValueChainEdge` | 밸류체인 엣지 정본 (T1/T2/T3) | 〃 |
| `SectorIOEdge` | T3 업종 백본 (한국은행 산업연관표) | 〃 |
| `VcChunk` | 밸류체인 추출 단위 (문장 윈도우 청크) | 〃 §3.1 |
| `VcPipelineState` | 배치 체크포인트 | 〃 §2.2 |
| `LinkFailQueue` | 엔티티 링킹 실패 큐 → 수동 보정(M2) | 〃 |

## 원래 테이블 2개

### `CompanyNode` (기업 노드 메타데이터)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| corp_code | String(8), PK | DART 내부 8자리 (예: `00126380`) |
| corp_name | String, indexed | 기업명 (예: "삼성전자") |
| ticker | String(6), unique, indexed | 종목코드 6자리 (예: `005930`) |
| market_cap | Float | 시가총액 (억원) |
| sector | String | viewer/CLAUDE.md의 sectors 키 |
| group_name | String, indexed | 공정위 기업집단명 (null 가능) |
| is_target | Boolean | top50 포함 여부 (기본 True) |

### `RelationLocal` (관계 엣지)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | Integer, PK, autoincrement | — |
| source_corp | String(6), indexed | source ticker |
| target_corp | String(6), indexed | target ticker |
| relation_type | String, not null | 6종: ftc_group / subsidiary / associate / investment / dart_filing / manual |
| ratio | Float | 지분율 %. ftc_group·manual은 null |
| detail | String | "삼성물산 5.01% (최대주주)" 등 |
| source_type | String | hyslrSttus / otrCprInvstmntSttus / ftc / dart_filing / manual |
| bsns_year | Integer | 사업연도 (DART 기준) |
| group_name | String | 공정위 집단명 (ftc_group 엣지에만) |
| status ★V0 | String | active \| superseded (정정공시 대체) |
| superseded_by ★V0 | Integer | 대체한 엣지 id (nullable) |
| rcept_no ★V0 | String | 근거 공시 접수번호 |

### 왜 두 테이블을 분리하는가
- 노드 메타(CompanyNode)는 최초 1회 수집 후 거의 변하지 않음 (top50.csv 기반)
- 엣지(RelationLocal)는 재수집 시마다 `DELETE WHERE bsns_year=X` 후 재삽입
- 조회 시 JOIN으로 기업명·시총·섹터 가져오기

## DB 파일 위치

`modules/relation/data/relation.db` — **git 커밋 대상**(reports.db와 달리 소용량이라 커밋됨. gitignore 아님)

생성 규칙: `storage/db.py:_DB_PATH`는 `storage/` 위치 기준 상위 → `../data/relation.db`로 계산됨.

## 공용 API (db.py 재사용)

```python
from modules.relation.storage.db import init_local_db, get_local_session
from modules.relation.storage.models import CompanyNode, RelationLocal

init_local_db()                    # 최초 1회
session = get_local_session()
session.query(RelationLocal).filter_by(source_corp="005930").all()
```

## 마이그레이션 전략 (MVP)

- Alembic 같은 정식 마이그레이션 **사용 안 함**
- 신규 테이블: `create_all()`이 없는 테이블만 생성(기존 테이블 무영향) — 표준 SQLAlchemy 동작
- 기존 테이블에 컬럼 추가: **`ALTER TABLE ADD COLUMN`**(nullable/기본값) — ★V0(2026-07-21)에서
  RelationLocal에 `status`/`superseded_by`/`rcept_no` 3컬럼을 이 방식으로 추가, 기존 93행 보존
- `drop_all()`은 **실제 커밋 데이터가 있는 테이블에는 쓰지 않는다** — DART API 재호출로 복구 가능해도
  git 커밋된 로컬 정본을 이유 없이 재수집시키지 않음. 완전 재설계급 변경에서만 검토
- UNIQUE 제약은 SQLite ALTER로 직접 추가 불가 → `CREATE UNIQUE INDEX`로 동등 효과(★V0 uq_relation_local_edge)
- Phase 2 완료 후 Supabase 이전 시점부터 Alembic 도입 검토

## shared/ 동기화 계획 (v2)

MVP 검증 완료 후 별도 PR로:
1. `shared/models.py`의 `RelationData` 컬럼을 `RelationLocal`과 동일하게 확장
2. `CompanyNode`에 해당하는 `CorpMaster` 테이블 추가 (현재 `shared/`에 없음)
3. Supabase → Claude Code MCP(PostgreSQL)로 마이그레이션 테스트
4. 로컬 SQLite 데이터를 Supabase로 복사하는 1회성 스크립트 작성

## 주의

- SQLAlchemy 2.0 문법 사용 (`declarative_base` 대신 `DeclarativeBase` 권장되지만 MVP는 호환성 위해 `declarative_base` 유지)
- `RelationLocal`의 UNIQUE(source_corp, target_corp, relation_type, bsns_year) ★V0: relation_type이
  키에 포함되므로 같은 (source, target)에 다른 relation_type이 공존하는 원칙은 그대로 유지된다 —
  막는 것은 "완전히 같은 엣지의 중복 삽입"뿐 (멱등 upsert 키, valuechain D12/U-D13)
- 필요 시 복합 인덱스 추가: `(source_corp, target_corp, relation_type)` 조회 빈번
