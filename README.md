# DiscloseAI (공시해부학)

대한민국 상장사의 공시·재무제표를 AI로 해부하여, 개인투자자의 금융 문해력을 향상시키는 플랫폼.

## 빠른 시작

```bash
# 1. 의존성 설치 (Python 3.11)
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 환경변수 설정 (DART_API_KEY 등 본인 키 입력)
copy .env.example .env          # macOS/Linux: cp .env.example .env

# 3. 테스트 실행
python -m pytest tests/ -v
```

설치 단계별 안내(스크린샷 포함)는 [docs/ONBOARDING.md](docs/ONBOARDING.md) 참조.

## 실행

```bash
# 로컬 개발 서버 (공시 스케줄러 + 챗서버)
python run_dev.py

# 통합 대시보드
python -m integration.build_data          # 모듈 DB → 통합 JSON 생성 (개별: -m integration.extract_data)
python -m http.server 8000               # http://localhost:8000/integration/
```

## 문서

- [아키텍처](docs/ARCHITECTURE.md) — 지금 실제로 돌아가는 구조·DB 토폴로지 (SSOT)
- [PRD](docs/초기PRD.md) — 제품 요구사항·비전
- [온보딩](docs/ONBOARDING.md) — 팀원 시작 가이드
- [프로토타입](design/prototypes/corporate_universe_v6_galaxies.html) — UI 프로토타입 원형 (디자인 정본: [DESIGN.md](DESIGN.md))
- [DART Chatbot 백엔드](https://github.com/malangoppa/dart-chatbot) — AI 코파일럿의 OpenDART RAG 챗봇 백엔드 (질의 분류·정형 조회·벡터 검색·Bedrock 답변 생성)

## 구조

데이터 생산자(`modules/`)와 서빙 계층(`integration/`)이 분리되어 있다. 데이터 정본은 모듈별 로컬 SQLite. 전체 토폴로지는 [아키텍처 문서](docs/ARCHITECTURE.md) 참조.

| 폴더 | 담당 | 범위 |
|------|------|------|
| modules/financial/ | A | 재무제표 + EQS |
| modules/disclosure/ | B | 공시 수집 + 분기 재무 |
| modules/relation/ | C | 기업 관계 (지분·계열) |
| modules/price/ | D | 주가 + 라벨링 |
| **integration/** | 리더 | 4개 모듈 교차 통합 대시보드 (v1=fallback, v2=정본) |
