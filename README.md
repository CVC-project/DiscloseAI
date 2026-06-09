# DiscloseAI (공시해부학)

대한민국 상장사의 공시·재무제표를 AI로 해부하여, 개인투자자의 금융 문해력을 향상시키는 플랫폼.

## 시작하기

[docs/ONBOARDING.md](docs/ONBOARDING.md) 참조

## 문서

- [PRD](docs/PRD.md) — 제품 요구사항
- [아키텍처](docs/ARCHITECTURE.md) — 시스템 구조 + 기술 용어
- [온보딩](docs/ONBOARDING.md) — 팀원 시작 가이드
- [프로토타입](docs/prototype/corporate_universe_v5.html) — UI 프로토타입

## 구조

데이터 생산자(`modules/`)와 서빙 계층(`integration/`)이 분리되어 있다. 데이터 정본은 모듈별 로컬 SQLite. 전체 토폴로지는 [아키텍처 문서](docs/ARCHITECTURE.md) 참조.

| 폴더 | 담당 | 범위 |
|------|------|------|
| modules/financial/ | A | 재무제표 + EQS |
| modules/disclosure/ | B | 공시 수집 + 분기 재무 |
| modules/relation/ | C | 기업 관계 (지분·계열) |
| modules/price/ | D | 주가 + 라벨링 |
| **integration/** | 리더 | 4개 모듈 교차 통합 대시보드 (v1=fallback, v2=정본) |

## 통합 대시보드 실행

```bash
python -m integration.v1.extract_data    # 모듈 DB → 통합 JSON 생성
python -m http.server 8000               # http://localhost:8000/integration/
```
