# storage/ — 저장 계층 (로컬 SQLite)

> 로컬 SQLite 기반 개발 DB. `shared/models.py`(Supabase PostgreSQL용)와는 **별개**.
> MVP 검증 완료 후 별도 PR로 `shared/models.py` 동기화 예정.

## 파일 2개

| 파일 | 역할 |
|---|---|
| `models.py` | SQLAlchemy 테이블 정의 (`CompanyNode`, `RelationLocal`) |
| `db.py` | 엔진·세션 + `init_local_db()` / `get_local_session()` |

## 테이블 2개

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

### 왜 두 테이블을 분리하는가
- 노드 메타(CompanyNode)는 최초 1회 수집 후 거의 변하지 않음 (top50.csv 기반)
- 엣지(RelationLocal)는 재수집 시마다 `DELETE WHERE bsns_year=X` 후 재삽입
- 조회 시 JOIN으로 기업명·시총·섹터 가져오기

## DB 파일 위치

`modules/relation/data/relation.db` (gitignored)

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
- 스키마 변경 시: `drop_all()` → `create_all()` 후 재수집
- 이유: MVP 단계에서 실제 운영 데이터가 아니며 재수집 비용이 낮음 (DART API 100회 + 공정위 수회)
- Phase 2 완료 후 Supabase 이전 시점부터 Alembic 도입 검토

## shared/ 동기화 계획 (v2)

MVP 검증 완료 후 별도 PR로:
1. `shared/models.py`의 `RelationData` 컬럼을 `RelationLocal`과 동일하게 확장
2. `CompanyNode`에 해당하는 `CorpMaster` 테이블 추가 (현재 `shared/`에 없음)
3. Supabase → Claude Code MCP(PostgreSQL)로 마이그레이션 테스트
4. 로컬 SQLite 데이터를 Supabase로 복사하는 1회성 스크립트 작성

## 주의

- SQLAlchemy 2.0 문법 사용 (`declarative_base` 대신 `DeclarativeBase` 권장되지만 MVP는 호환성 위해 `declarative_base` 유지)
- `RelationLocal`에 고유 제약(UNIQUE)을 걸지 않는 이유: 같은 (source, target)에 relation_type이 다른 엣지 공존 허용
- 필요 시 복합 인덱스 추가: `(source_corp, target_corp, relation_type)` 조회 빈번
