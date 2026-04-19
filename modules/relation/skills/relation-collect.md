---
name: relation-collect
description: DART + 공정위 + 사업보고서 주석 원천 데이터를 순차 수집하여 RelationRaw에 저장합니다. relation 모듈 개발·재수집 시 사용.
auto-invocable: false
---

# /relation-collect

Relation 모듈의 원천 데이터 3종을 수집합니다. Phase 2 안정화 이후 `.claude/skills/`로 승격 예정.

## 사전 조건
- `.env`의 `DART_API_KEY`, `FTC_API_KEY` 설정 완료
- `modules/relation/data/top50.csv`의 `corp_code` 컬럼 채워짐 (최초 1회 `map-corp-codes` 필요)

## 실행 절차

```bash
cd DiscloseAI
source .venv/Scripts/activate

# 1. 로컬 DB 초기화 (최초 1회)
python -m modules.relation init

# 2. corp_code 매핑 (top50.csv 변경 시에만)
python -m modules.relation map-corp-codes

# 3. DART 지분 수집 (100회 API 호출, ~20초)
python -m modules.relation collect dart --year 2024

# 4. 공정위 계열 수집 (페이징 7회, ~15초)
python -m modules.relation collect ftc

# 5. 공정위 미포함 기업 주석 파싱 (best-effort, 1~3개만)
python -m modules.relation collect filing
```

## 기대 출력

```
[hyslrSttus] 005930 삼성전자: 26건
[otrCprInvstmntSttus] 005930 삼성전자: 138건
... (top50 순회)
DART 수집 완료: 최대주주 N건 + 타법인출자 M건. errors=0

FTC 수집 시작: yyyymm=202505
공정위 소속회사 전체: 3,301건
top50 매칭: 49/50 | 커버된 집단 22개
FTC 수집 완료: ftc_group_edges=62 missing_group_count=1

filing 파싱 대상 1개: ['한미반도체']
한미반도체: 파싱 12건
filing 수집 완료: targets=1 parsed=1 edges=0
```

## 에러 대응
- `DartError status=800` → DART_API_KEY 점검
- `FtcError resultCode=22` → 일일 한도 초과, 내일 재시도
- `missing_group_count` > 3 → FTC 응답 포맷 변경 가능성, NAME_ALIASES 점검

## 다음 단계
수집 완료 후 → `/relation-graph` 호출 (transform → graph → export)
