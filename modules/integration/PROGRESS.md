# Integration 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-22 (Phase C — 통합 대시보드 신설)

- **작업**: 4개 모듈(relation·financial·disclosure·price) 데이터를 localhost 단일 대시보드로 통합
- **배경 — Phase 구조**:
  - Phase A (2026-04-21, PR #8): `.gitignore` 수정으로 `modules/*/data/*.db`·`*.json` 추적 허용 + v6 galaxies 디자인 relation viewer 이식
  - Phase B (2026-04-22, PR #9·#10·#11): 담당자 3명 DB 공유. financial·disclosure 완료, price는 `quiz_data.py` 15건(DB 없음)
  - Phase C (이번 세션): `modules/integration/` 폴더 신설
- **파일**:
  - `__init__.py` (패키지 마커)
  - `CLAUDE.md` (리더 소유 규약 + 데이터 소스 계약 + 업데이트 플로우)
  - `PROGRESS.md` (이 파일)
  - `extract_data.py` (DB·Python 상수 → JSON 배치 추출)
  - `dashboard.html` (v6 galaxies + 4개 fetch + 통합 패널)
  - `data/eqs_summary.json`·`disclosures.json`·`price_scenarios.json` (extract 결과)
- **데이터 소스 (extract 대상)**:
  - `modules/financial/data/financial.db` — `financial_local` 테이블
  - `modules/disclosure/data/disclosure.db` — `disclosure_local` + `financial_statement`
  - `modules/price/quiz_data.py` — `QUIZ_LIST` 상수 (15건)
  - `modules/relation/data/graph_top50.json` — dashboard가 직접 fetch (변환 불필요)
- **설계 결정**:
  - **방법 B (정적 JSON fetch) 채택**. shared DB(Supabase) 적재 결정 전까지 유지. 향후 FastAPI 승격 시 dashboard.html의 fetch URL만 교체하면 됨 (방법 C)
  - relation viewer(`modules/relation/viewer/index.html`)는 **유지** — relation 단독 뷰 역할. integration은 그 확장판
  - 경계 예외: integration에서만 타 모듈 import·DB 읽기 허용 (수정·삭제 금지)
- **limitations**:
  - price 커버리지 **15/50 = 30%**. 나머지 35개 기업은 `has_quiz=false` 플래그로 timemachine 모드에서 "데이터 없음(수집 중)" 뱃지 표시
  - shared DB(Supabase) 미적재. 공식 서빙 구조는 Phase D 이후

## 향후 업데이트 시 체크리스트 (팀원 공유용)

팀원이 자기 모듈 데이터 갱신 → git merge → **리더가 integration 재생성** 순서.

1. `git checkout dev && git pull`
2. `git checkout feat/integration-dashboard` (또는 후속 브랜치)
3. `git merge origin/dev`
4. `python -m modules.integration.extract_data` — JSON 3개 재생성
5. `python -m http.server 8000` → 브라우저로 육안 확인
6. 이상 없으면 `git add modules/integration/data/*.json && git commit -m "data(integration): <모듈> 업데이트 반영"`
7. PR 생성 → 본인 승인 후 merge

## 의존성 계약 (스키마 안정성)

`CLAUDE.md`의 "데이터 소스 계약" 표 참조. 각 모듈 담당자가 스키마를 바꿀 경우 integration 쪽에도 영향을 주므로 **PR 본문에 스키마 변경 명시** 필수.
