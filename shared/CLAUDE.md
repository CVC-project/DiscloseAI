# shared/ 폴더 규칙

**이 폴더는 프로젝트 리드만 수정합니다.** 변경이 필요하면 프로젝트 리드에게 요청하세요.

## 이 폴더의 역할
- 환경변수 로드 (config.py) — **현재 활성**, 모든 모듈이 공유 (`from shared.config import DART_API_KEY`)
- 미래 운영 DB 연결 (db.py) + 미래 운영 스키마 (models.py)

## ⚠️ 정본은 로컬 SQLite, shared는 "미래 운영 이관 대상"
개발 단계 합의에 따라 **데이터 정본은 모듈별 로컬 SQLite**다 (각 `modules/*/db.py`·`models.py`).
`shared/models.py`는 **현재 운영 미사용** — Supabase(PostgreSQL) 이관 시점에 통합·정렬할 타깃 스키마다.
- 현재 활성 테이블: `PriceData`만 ([modules/price/linker.py](../modules/price/linker.py)가 적재)
- relation `storage/CLAUDE.md`의 shared 승격 계획(CompanyNode·RelationLocal)도 그 이관 시점에 일괄 반영
- 전체 DB 토폴로지·식별자 규칙·미해결 이슈: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

```python
# 현재 모듈에서 실제로 쓰는 것:
from shared.config import DART_API_KEY, FTC_API_KEY   # 환경변수 (활성)
# from shared.models import ...  ← 미래 운영 이관 전까지 사용 안 함 (PriceData 제외)
```
