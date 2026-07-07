# DiscloseAI — Codex 프로젝트 규칙

## 첫 세션 시 필수 읽기
이 프로젝트를 처음 접하면 아래 순서로 읽어 전체 구조를 파악하세요:
1. docs/ARCHITECTURE.md — 지금 실제로 돌아가는 구조·데이터 흐름·DB 토폴로지 (SSOT)
2. shared/models.py — DB 스키마 (테이블 정의)
3. docs/초기PRD.md — 제품 비전·요구사항 전문 (전체 맥락이 필요할 때)

## 프로젝트 개요
한국 상장사 공시·재무제표를 AI로 분석하여 개인투자자의 금융 문해력을 향상시키는 플랫폼.
PRD 상세: docs/초기PRD.md

## 기술 스택
현재 (구현됨):
- Python 3.11 — 데이터 수집·계산 (DART OpenAPI, yfinance, 공정위, 한국은행 ECOS)
- 모듈별 로컬 SQLite — 데이터 정본
- 정적 HTML + Canvas/Three.js(WebGL)·D3.js — viewer·통합 대시보드
- ML: CatBoost, scikit-learn — price 라벨링·EQS

계획 (미구현 — 향후 api/ 구축·운영 이관 시):
- Backend: FastAPI, Celery, Redis (docs/AI_DIRECTION_PLAN.md)
- Frontend: Next.js (SPA 전환 시)
- DB: PostgreSQL (Supabase) — 현재 shared/models.py는 미사용 타깃 스키마

## 코딩 컨벤션
- Python: Black 포매터 사용, type hint 권장
- 함수명: snake_case, 클래스: PascalCase
- DB 모델: shared/models.py에 정의 (SQLAlchemy ORM)
- 테스트: tests/ 폴더, pytest 사용

## 폴더 규칙
공용 폴더 (프로젝트 리드만 수정):
- .codex/ (+ .agents/skills/): Skills, Agents, Settings
- shared/: 환경변수(config.py, 활성) + 미래 운영 DB 스키마(models.py, 현재 미사용)
- docs/: PRD, 아키텍처, 온보딩 가이드

개별 작업 폴더 (각 담당자만 수정):
- modules/financial/ (A), modules/disclosure/ (B), modules/relation/ (C), modules/price/ (D)
- 각 모듈에 **로컬 SQLite(정본)** 포함 — db.py, models.py, data/

서빙 계층 (리더 소유):
- integration/: 4개 모듈 산출물 교차 통합 대시보드 (v1/=fallback, v2/=정본, data/=공유 JSON)
- 미래 백엔드 api/ (FastAPI·RAG·learning)는 현재 미구현 — 구축 시 생성 (docs/AI_DIRECTION_PLAN.md 참조)

데이터 정본은 모듈별 로컬 SQLite. 전체 DB 토폴로지: docs/ARCHITECTURE.md
모듈 간 연결: 데이터 모듈끼리는 import 금지. integration만 예외(타 모듈 read-only)

## 작업 경계 원칙 (일반 규칙)
- **각 모듈 작업은 그 모듈 안에서 끝낸다.** 코드뿐 아니라 **산출물·데이터·캐시도 자기 모듈 폴더 안**에 둔다 — 다른 모듈이나 공용 폴더로 새어나가지 않게. (`docs/`는 문서·디자인 목업 전용 — 코드가 생성하는 산출물·데이터·캐시를 두지 않는다.)
- **통합·표현은 integration이 한다.** integration이 각 모듈의 산출물(DB·JSON 등)을 **읽어서(read-only)** 교차 구현한다. 즉 **모듈은 데이터를 만들고, 화면·표현은 integration이 소유**한다 (데이터 생산자가 표현까지 만들지 않는다).
- 데이터 모듈끼리 서로 import 금지(단방향). integration만 타 모듈 read-only 접근 허용.

### ⚠️ 위반 시 경고
위 경계·폴더 규칙에 어긋나는 작업(예: 한 모듈이 다른 모듈이나 `docs/`에 산출물을 쓰기, 모듈 간 직접 import, 데이터 생산자가 표현까지 생성)을 **요청받거나 발견하면, 그대로 진행하지 말고 먼저 사용자에게 경고**하고 올바른 위치·방식을 제안할 것.

## 보안 규칙
- .env 파일 절대 커밋 금지
- API 키를 코드에 하드코딩 금지 → 환경변수 사용
- git push --force 금지
- main 브랜치 직접 push 금지

## Skill 사용
- /check: 리뷰 + 테스트 + PROGRESS.md 기록 (수동 호출)
- /review: 코드 리뷰만 (자동 호출 가능)
- /test: 테스트 생성/실행만 (자동 호출 가능)

## Agent
- code-reviewer: Sonnet, 읽기 전용 리뷰
- test-generator: Haiku, pytest 자동 생성
- ui-ux-reviewer: Sonnet, UI/UX 시각화 검증 (읽기 전용)

## 브랜치 전략
- main: 배포용 (직접 push 금지)
- dev: 개발 통합 (매주 금요일 합침)
- feat/financial, feat/disclosure, feat/relation, feat/price: 각자 작업

## 커밋 메시지
- feat: 새 기능 | fix: 버그 수정 | docs: 문서 | test: 테스트
- 예: "feat: Beneish M-score 계산 구현"

## 면책
- 모든 AI 분석 결과에 면책 문구 삽입 (면책 로직은 **현재 미구현** — 향후 백엔드 api/ 구축 시 배치 예정)
- "투자 조언" 표현 사용 금지 → "과거 통계 기반 참고 정보"로 대체
