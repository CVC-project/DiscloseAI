# DiscloseAI — Product Requirements Document

> ⚠️ **역사 스냅샷 (초기 기획서)**: 아래 폴더 구조·프로토타입(`corporate_universe_v5.html` 등)·스택 서술은 **기획 시점 기준**이며 현행과 다를 수 있음. **지금 실제로 돌아가는 구조는 [docs/ARCHITECTURE.md](ARCHITECTURE.md)를 정본으로 참조.**
>
> 대회: 2026 AI Rookie (과기부 주최) | 접수 마감: 5월 8일(금) 17시
> 팀: 4인 (전원 CPA)

---

## 1. 프로젝트 개요

### 1.1 한 줄 요약
대한민국 상장사의 공시·재무제표를 AI로 해부하여, 1,400만 개인투자자의 금융 문해력을 향상시키는 플랫폼.

### 1.2 프로젝트 메시지
> "뉴스 12개가 못 본 걸, 숫자 하나가 말해주고 있었다"

### 1.3 문제 정의
- 개인투자자 1,400만 명 중 재무제표와 주석을 교차 분석할 수 있는 사람은 극소수
- 공시가 공개되어도 관련 기업에 미치는 영향을 추론할 도구가 없음
- 재무제표 기반 애널리스트 투자의견의 93%가 매수, 0.1%만 매도 — 구조적 이해상충
- 공시는 공개되어 있지만, **읽히지 않고 연결되지 않는다**

### 1.4 솔루션
공시 데이터를 해부하여 개인투자자에게 네 가지 도구를 제공한다:
1. **기업 우주** — 상장사 관계를 인터랙티브 네트워크로 시각화
2. **공시 파문** — 공시 발생 시 영향 네트워크가 빛나며 파급효과 탐색
3. **이익 해부 (EQS)** — 5개 모듈로 기업 실적의 '진짜 질'을 AI가 자동 진단
4. **공시 타임머신** — 과거 공시를 현재처럼 체험하는 금융 문해력 학습 도구

### 1.5 팀 구성
- 4인 팀 (전원 CPA)
- 개발 방식: Agent-to-Agent 자율 운영 (섹션 4.4 참조)

---

## 2. 핵심 기능 상세

### 2.1 기업 우주 (Corporate Universe)

**목적**: KOSPI·KOSDAQ 전체 상장사 2,600개의 관계를 한눈에 파악

**시각화 방식**:
- WebGL(Three.js/PixiJS) 기반 네트워크 그래프
- 노드 = 기업 (시총 비례 크기, 산업별 색상 클러스터)
- 엣지 = 관계 (지분, 공급, 경쟁, 계열)
- 별하늘 배경 + 성운 + 유성 효과 (우주 테마)
- 이모지 마스코트(🐱)가 행성 사이 점프

**인터랙션**:
- Semantic Zoom: 줌아웃 시 산업 클러스터 / 줌인 시 개별 기업+연결선
- 섹터 필터: 전체, 반도체, 디스플레이, 2차전지, 바이오, 자동차, 금융
- 기업 클릭 → 재무 상세 + EQS + 관계 목록 패널 오픈

**데이터 소스** (100% 무료):
- DART OpenAPI: 지분·계열·특수관계자
- 공정위: 대기업집단 계열사 목록
- KRX: 업종분류, 시가총액

**프로토타입**: `corporate_universe_v5.html` (3D 행성 렌더링, 공시 시뮬레이션 포함)

---

### 2.2 공시 파문 (Disclosure Ripple)

**목적**: 공시 발생 시 관련 기업에 미치는 영향을 시각적으로 탐색

**작동 방식**:
1. **공시 감지**: DART API 1분 간격 폴링으로 준실시간 공시 감지 (일일 ~480회, 한도 10,000건 대비 여유)
2. **영향 분석**: 과거 유사 공시의 실제 주가 반응을 학습한 CatBoost 분류 모델 추론
3. **시각적 알림**: 네트워크 위에서 영향 기업이 순차적으로 빛나며 파문 효과

**ML 모델: CatBoost 3-class 분류**

- **입력 피처**:
  - 공시유형: 범주형 (유상증자, CAPEX, M&A, 지분취득, ...)
  - 관계유형: 범주형 (공급사, 경쟁사, 계열사, 고객사, ...)
  - 금액/시총: 수치형 (공시 금액 ÷ 공시기업 시가총액)
  - 시장환경: 범주형 (최근 60일 KOSPI 수익률 기준 상승/하락/횡보)

- **타깃 라벨링**: 공시 후 5일 주가 변동 기준
  - +2% 이상 → 수혜
  - -2% 이상 → 악재
  - 그 사이 → 중립

- **보정 및 신뢰도**:
  - Isotonic Calibration: "78%라고 했을 때 실제 78번 맞는" 확률 보정
  - 최대확률 <60%면 "판단 유보" (솔직하게 모른다고 표시)
  - 근거 문구: SQL로 과거 유사 건수 카운트 ("과거 유사 142건 중 124건 수혜")

- **왜 수치 예측이 아닌 방향성 분류인가**:
  - 수치 예측(CAR +6.2%)은 과적합 위험 + "투자 조언"으로 해석될 법적 리스크
  - 방향성 분류(수혜/악재/중립)는 해석이 명확하고 법적으로 안전
  - "예측"이 아닌 "과거 유사 사례의 통계적 경향"으로 포지셔닝

**출력 예시**:
```
삼성전자 CAPEX 30조 공시 → 원익IPS(공급사)
AI 판단: 수혜 예상 (확률 78%)
근거: 과거 유사 패턴 142건 중 124건 수혜
⚠ 본 분석은 과거 통계이며 투자 권유가 아닙니다
```

---

### 2.3 이익 해부 (Earnings Quality Score, EQS)

**목적**: 애널리스트가 이해상충으로 못하는 독립 실적 검증을 AI가 대신 수행

**포지셔닝**: "주가 예측이 아닌 재무 건강 진단" (의사의 건강검진과 동일 성격)

**5개 모듈**:

| 모듈 | 방법론 | 핵심 질문 |
|------|--------|----------|
| M1 발생액 품질 | 수정 Jones 모델 | 이익이 현금으로 뒷받침되는가? |
| M2 분식 확률 | Beneish M-score | 이익을 조작했을 확률은? |
| M3 현금흐름 괴리 | OCF/NI 비율 추세 | 이익은 늘어나는데 현금은 어디? |
| M4 이익 지속성 | AR(1) + 일회성 비중 | 올해 이익이 내년에도 유지? |
| M5 재무 건전성 | Piotroski F-score | 기초 체력이 좋아지고 있나? |

**종합 점수**: 5개 모듈 가중 합산 → 0~100점 → A/B/C/D/F 등급

**한국 시장 적용 — K-Beneish Score**:
- 미국 Beneish 모델의 계수를 K-IFRS 환경에 맞게 재추정
- 한국 상장사 데이터로 로지스틱 회귀 재학습
- 학술 기여 가능 포인트

**재무제표 번역기** (CPA 팀 강점):
- 손익계산서: "100원 팔면 12원이 남습니다" (영업이익률)
- 재무상태표: "빚이 전체 자산의 22%입니다" (부채비율)
- 현금흐름표: "벌어서 투자하고 — 여유 있는 구조"
- ⚡ 주목 포인트 3개 자동 추출 (규칙 기반, CPA 팀이 20~30개 규칙 설계)

**업종별 예외**:
- 금융업: M3 제외, BIS비율 등 별도 기준 적용

**데이터**: 100% DART 무료 데이터, 전체 상장사 2,600개 커버

---

### 2.4 공시 타임머신 (Disclosure Time Machine)

**목적**: 과거 공시를 현재처럼 체험하여 금융 문해력을 자연스럽게 학습

**핵심 원리**: "우리가 해석하지 않는다. 팩트를 시간순으로 놓고 '당신이라면 어디서 알아챘을까요?'라고만 물어본다"

**기본 체험**:
1. 과거 특정 날짜로 이동
2. 당시 공시 + 뉴스 반응 제시
3. 사용자가 매수/관망/매도 선택
4. 실제 결과 공개 + 학습 포인트

**변형 퀴즈**:
- 숫자 하나의 무게: 재무 숫자 변화 → 결과 맞추기
- 감춰진 한 줄: 주석 한 줄의 의미 파악
- AI vs 나: EQS 판단 vs 사용자 판단 비교

**뉴스 데이터**: 빅카인즈(BIGKinds) 또는 네이버 뉴스 API (무료)

---

### 2.5 사용자 참여 엔진 (MLP 요소)

**공시 블라인드 테스트** — 세상에 없는 금융 교육 도구:
- 기업 이름을 가리고 재무 데이터·공시만으로 투자 판단
- 결정 후 기업명 공개 → "이게 그 회사였어?!" 반응
- 편향 제거(debiasing)를 게임으로 만든 것
- 이름 있을 때 vs 블라인드 정확도 비교 → 자기 편향 인식

**투자 기질 리포트** (Spotify Wrapped 방식):
- 월간 활동 기반 자동 생성
- "나의 블라인드 정확도가 이름 있을 때보다 15%p 높다" 같은 인사이트
- SNS 공유 → 바이럴 요소

**해부력 (解剖力)** — 단일 성장 지표:
- 공시를 꿰뚫어 보는 능력 수치화
- 등급: 실습생 → 인턴 → 레지던트 → 전문의 → 교수 → 해부왕
- "얼마나 많이 했나"가 아니라 "얼마나 정확하게 맞췄나" 기반

---

## 3. 데이터 아키텍처

### 3.1 데이터 규모 추정

| DB | 예상 행 수 | 예상 용량 |
|----|-----------|----------|
| 공시 DB | ~50만행 | ~500MB |
| 재무 DB | ~260만행 (EQS 점수 포함) | ~1GB |
| 주가 DB | ~650만행 | ~2GB |
| 뉴스 DB | ~130만행 (헤드라인만) | ~500MB |
| 그래프 DB | 노드 2,600 + 엣지 ~1만 | ~10MB |
| 예측 DB | 실시간 누적 (CatBoost 추론 결과) | 가변 |
| **전체 합계** | | **약 5GB** |

주요 컬럼 참고:
- 재무 DB: `corp_code, 연도, 매출, 영업이익, EQS_M1~M5, EQS_total, EQS_grade`
- 주가 DB: `corp_code, 날짜, 종가, 수익률, 공시후_5일변동, 라벨(수혜/악재/중립)`
- 예측 DB: `disclosure_id, 관련_corp, 판단, 확률, 근거건수, 실제결과(5일후)`

클라우드 무료 티어 가능 규모.

---

## 4. 기술 스택

### 4.1 핵심 스택

| 영역 | 기술/도구 | 용도 |
|------|---------|------|
| 데이터 수집 | DART OpenAPI, yfinance, 공정위 공시 | 공시·재무제표·주가·기업관계 |
| NLP | KoBERT / LLM API (Claude) | 공시 이벤트 분류, 자연어 해설 |
| 그래프 | NetworkX → Neo4j (고도화) | 기업 관계 그래프 저장·탐색 |
| ML/통계 | CatBoost, scikit-learn | 공시 영향 분류(수혜/악재/중립), Isotonic 보정 |
| EQS 엔진 | pandas, numpy, scipy | Jones·Beneish·F-score 5모듈 |
| 프론트엔드 | Next.js + Three.js(WebGL) + D3.js | 기업 우주 시각화 + 차트 |
| 백엔드 | FastAPI + Celery + Redis | 실시간 공시 폴링·비동기 처리 |
| DB | PostgreSQL (Supabase) | 정형 데이터 저장 |
| 배포 | Vercel + Railway | 무료 티어 활용 가능 |

### 4.2 학습 파이프라인

1. **데이터 수집**: DART 10년 수시공시 + yfinance 주가
2. **라벨링**: 공시 후 5일 주가 변동으로 수혜(+2%↑) / 악재(-2%↓) / 중립 분류
3. **피처 구성**: 공시유형(범주), 관계유형(범주), 금액/시총(수치), 시장환경(범주)
4. **모델 학습**: CatBoost Classifier + Isotonic Calibration 확률 보정

예상 학습 데이터: 10만 공시 × 5개 연결기업 = ~50만 레코드

### 4.3 데이터 처리 방식
- 정형 데이터(재무제표, 주가, 공시 메타): SQL 기반 조회 + 수식 엔진 처리
- 자연어 해설(재무 요약, 공시 설명): 정형 데이터를 LLM API에 전달하여 텍스트 생성
- 비정형 텍스트 검색(유사 과거 공시): 벡터 임베딩 기반 RAG 파이프라인 (고도화 단계)
- LLM 의존도: 전체의 10~20% (자연어 생성 시에만 호출), 나머지는 DB 쿼리 + 수식 + 규칙 기반

### 4.4 AI 엔지니어링 환경

> ⚠️ **구현 현황 (2026-06)**: 본 절은 설계 비전이다. 실제 구현과 차이가 있다 — 데이터 정본은 모듈별 로컬 SQLite(Supabase 미적재), 서빙은 루트 `integration/`(v1/v2; `api/`·`frontend/`는 미구현), MCP는 3개(GitHub·Context7·Sequential), sandbox·hooks 미설정. `api/middleware/safety.py` 등 면책 로직도 미구현. **문서↔현실 차이와 DB 토폴로지의 단일 출처는 [docs/ARCHITECTURE.md](ARCHITECTURE.md) "구현 현황" 참조.**

#### 4.4.1 Agent-to-Agent 개발 방식

> 참조: OpenAI "Harness engineering: leveraging Codex in an agent-first world" (2026.02)

팀 전원이 CPA(코딩 초보)이므로, 직접 코드를 짜지 않는다. **Claude Code가 코드를 작성하고, Agent가 검증하고, CI가 강제하고, CPA가 도메인 로직만 판단**하는 구조로 운영한다.

```
팀원(CPA)의 역할 = 회계법인의 감사 파트너
  → 코드를 읽을 필요 없음
  → "이 숫자가 맞는지, 이 로직이 K-IFRS에 부합하는지" 판단
  → Claude Code에게 CPA 용어로 요청

Claude Code = 주니어 회계사
  → 파트너가 시킨 일을 실제로 수행 (코드 작성)
  → 테스트 작성 및 실행까지 자율적으로 수행

code-reviewer agent = 시니어 회계사
  → 주니어가 한 작업의 형식·절차가 맞는지 체크
  → PR에 자동 코멘트

CI (GitHub Actions) = 품질관리팀 (QC)
  → 포매팅·테스트 자동 검증
  → 기준 미달이면 merge 자체를 차단

프로젝트 리드 = 최종 merge 판단만
```

**실제 작업 흐름**:
```
1. 팀원이 Claude Code에게 도메인 언어로 요청
   "Beneish M-score를 K-IFRS 기준으로 계산하는 코드 짜줘.
    DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI 8개 변수 사용.
    금융업(업종코드 064~066)은 제외해."

2. Claude Code가 코드 계획을 제시 → 팀원이 승인

3. Claude Code가 자율적으로 코드 작성

4. 팀원이 `/check` skill 호출 → 아래 3가지가 자동 병렬 실행
   a. code-reviewer agent(Sonnet) — 코드 품질 + 도메인 리뷰
   b. test-generator agent(Haiku) — pytest 자동 생성 및 실행
   c. 요약 리포트 생성 (무엇을 했는지, 테스트 결과)

5. 팀원이 확인할 것은 두 가지만
   a. Agent가 지적한 도메인 이슈 (예: "업종코드 067 보험업도 제외해야 하지 않나?")
   b. 결과값의 회계적 합리성 (예: "M-score -2.3이면 조작 가능성 낮음 범위, 맞아")

6. 모두 통과 시 → PROGRESS.md에 자동 기록
   (날짜, 작업 내용, 테스트 통과 여부, 도메인 메모)

7. git commit → git push → PR 생성

8. CI(GitHub Actions)가 black + pytest 재검증
   → code-reviewer agent가 PR에 코멘트

9. 프로젝트 리드가 최종 merge
```

**Skill 사용 시나리오** (팀원이 상황에 따라 선택):
```
/check  — 작업 완료 후 "최종 점검" (리뷰+테스트+기록, 한번에)
           → auto-invocable: false (팀원이 명시적으로 호출)
/review — "아직 완성은 아닌데 방향이 맞는지 봐줘" (리뷰만)
           → auto-invocable: true (Claude Code가 적절한 시점에 자동 호출 가능)
/test   — "이 함수에 테스트만 추가해줘" (테스트만)
           → auto-invocable: true (Claude Code가 적절한 시점에 자동 호출 가능)
```

#### 4.4.2 Harness Engineering: 에이전트를 감싸는 개발 환경 설계

Harness Engineering이란 AI 코딩 에이전트(Claude Code)가 신뢰할 수 있는 코드를 자율적으로 생산하도록 **환경을 설계하고, 의도를 명시하고, 피드백 루프를 구축하는** 방법론이다. 모델 자체를 개선하는 것이 아니라, 모델을 감싸는 구조(외피)를 설계하여 일관된 품질을 보장한다.

DiscloseAI의 Harness는 다음 7개 요소로 구성된다:

```
DiscloseAI Harness (에이전트를 감싸는 구조)
│
├── ① CLAUDE.md 계층        — 지도를 주되 백과사전은 주지 않기
│   루트 60줄(보편 규칙) + 하위 7개 폴더(도메인 지식, on-demand 로드)
│
├── ② .claude/settings.json   — Sandbox + Permissions + Hooks
│   Sandbox: OS 레벨 폴더 격리
│   Permissions: 명령어 허용/차단 목록
│   Hooks: 이벤트 트리거 (추후 추가, 폴더만 생성)
│
├── ③ .claude/skills          — Progressive Disclosure
│   공용 3개: /check(수동), /review(auto), /test(auto)
│   팀원이 필요시 도메인별 skill을 PR로 추가
│
├── ④ .claude/agents          — 독립 전문가 위임
│   code-reviewer(Sonnet), test-generator(Haiku)
│
├── ⑤ .mcp.json + MCP        — 외부 도구 연결
│   GitHub, Context7, Sequential Thinking, PostgreSQL, Playwright
│
├── ⑥ .github/workflows/     — 확정적 검증 (CI)
│   black --check + pytest → 실패 시 PR merge 차단
│
└── ⑦ docs/                  — 에이전트가 읽을 수 있는 문서화
    onboarding.md, agent-catalog.md
```

**핵심 원칙**:
- "지도를 주되 백과사전은 주지 않는다" — 루트 CLAUDE.md는 60줄 이내, 상세 내용은 하위 폴더로 분산
- "확정적 행동은 Hook과 CI로, 권장 행동은 CLAUDE.md로" — 반드시 지켜야 하는 규칙(보안, 포매팅)은 Hook/CI가 100% 강제
- "에이전트가 볼 수 없으면 존재하지 않는 것" — 팀의 암묵지를 docs/와 CLAUDE.md에 명문화

**참고**: `api/middleware/`의 safety.py, orchestrator.py 등은 Harness가 아닌 일반 백엔드 미들웨어 코드(면책 문구, API 오케스트레이션, 에러 복구)이다.

#### 4.4.3 MCP (Model Context Protocol) 구성

프로젝트 레벨 `.mcp.json`으로 팀 전체가 동일한 MCP 환경을 공유한다.

| MCP | scope | 용도 |
|-----|-------|------|
| GitHub | project | 4인 브랜치 전략, PR 생성/리뷰, Issue 관리 |
| Context7 | project | FastAPI, Three.js, CatBoost 등 최신 라이브러리 문서 실시간 참조 |
| Sequential Thinking | project | EQS 모듈 설계, CatBoost 피처 엔지니어링 등 복잡한 판단 시 구조화된 사고 |
| PostgreSQL | user | Supabase DB 자연어 쿼리, 스키마 탐색 |
| Playwright | user | DART 페이지 테스트, 프론트엔드 E2E |

설치 명령:
```bash
# project scope — .mcp.json에 저장, git 추적, 팀 공유
claude mcp add github --scope project --transport http https://mcp.github.com
claude mcp add context7 --scope project -- npx -y @upstash/context7-mcp
claude mcp add sequential-thinking --scope project -- npx -y @modelcontextprotocol/server-sequential-thinking

# user scope — 각자 환경에만 적용
claude mcp add supabase-db --scope user -- npx -y @modelcontextprotocol/server-postgres
claude mcp add playwright --scope user -- npx -y @anthropic-ai/mcp-playwright
```

#### 4.4.4 4-Layer 확장 구조

Claude Code의 확장 시스템은 4개 레이어로 구성된다. 확정도에 따라 적절한 레이어에 규칙을 배치한다.

| Layer | 도구 | 확정도 | DiscloseAI 적용 |
|-------|------|--------|----------------|
| 1 | CLAUDE.md | ~70% | 코딩 스타일, 네이밍, 폴더 규칙 |
| 2 | Skills | on-demand | /check, /review, /test + 팀원이 추가할 도메인 skill |
| 3 | Permissions | 100% | .env 편집 차단, force push 차단 (Hooks는 추후 추가) |
| 4 | Sub-agents | 독립 컨텍스트 | code-reviewer(Sonnet), test-generator(Haiku) |

**CLAUDE.md 계층 구조** (하위 폴더 CLAUDE.md는 해당 폴더 작업 시에만 on-demand 로드):
```
CLAUDE.md (루트, 60줄 이내)       ← 항상 로드: 기술 스택, 코딩 컨벤션, 폴더 규칙
├── shared/CLAUDE.md              ← shared/ 작업 시: "프로젝트 리드만 수정" 규칙
├── financial/CLAUDE.md           ← financial/ 작업 시: EQS 수식, K-IFRS 규칙
├── disclosure/CLAUDE.md          ← disclosure/ 작업 시: DART API 패턴, rate limit
├── relation/CLAUDE.md            ← relation/ 작업 시: NetworkX 규칙
├── price/CLAUDE.md               ← price/ 작업 시: yfinance 패턴, .KS/.KQ suffix
├── api/CLAUDE.md                 ← api/ 작업 시: 라우팅 컨벤션, 에러 처리 패턴
└── frontend/CLAUDE.md            ← frontend/ 작업 시: Three.js, D3.js 컨벤션
```

**Skills 설계** (프로젝트 `.claude/skills/`에 모두 git 추적):

| Skill | 호출 방법 | auto-invocable | 용도 |
|-------|----------|----------------|------|
| `/check` | 수동 호출 | false | 리뷰+테스트+PROGRESS.md 기록 통합 |
| `/review` | 자동 또는 수동 | true | 코드 리뷰만 (방향 확인용) |
| `/test` | 자동 또는 수동 | true | 테스트만 생성/실행 |

- 네이밍 규칙: Skill = 동사형 (`/review`, `/test`, `/check`), Agent = 역할명 (`code-reviewer`, `test-generator`)
- 도메인별 skill(eqs-calculator, dart-collector 등)은 팀원이 필요시 직접 만들어 PR로 추가 (docs/ONBOARDING.md에 생성 가이드 제공)
- Progressive Disclosure 원칙: 세션 시작 시 skill의 frontmatter(name+description)만 로드(~20토큰/개), 실제 호출된 skill만 전체 내용 로드

**Hooks 설계** (`.claude/hooks/`):
- 현재: **폴더 구조만 생성**, 실제 hook 스크립트는 추후 추가
- 이유: Windows 환경에서 `.sh` 파일 미동작, `jq` 의존성, exit code 차이(exit 2가 차단) 등 호환성 이슈로 안정화 후 도입
- 보호 기능은 **Permissions deny rules**로 우선 처리 (아래 참조)

**Sub-agents 설계** (`.claude/agents/`):

| Agent | 모델 | 용도 | 비용 |
|-------|------|------|------|
| code-reviewer | Sonnet | 읽기 전용 PR 리뷰 (Write 차단) | 표준 |
| test-generator | **Haiku** | pytest 테스트 자동 생성 | **5배 절감** |

- 도메인별 agent(dart-collector, eqs-analyst, threejs-builder)는 팀원이 필요시 추가
- `/check` skill이 code-reviewer + test-generator를 **병렬 호출**

**Sandbox + Permissions** (`.claude/settings.json`):

`settings.json`은 3가지 구성 요소로 Claude Code의 행동 규칙을 정의한다:
- **Sandbox** = "울타리" — OS 레벨에서 프로젝트 폴더 바깥 접근 차단. 한 번 켜두면 신경 쓸 일 없음.
- **Permissions** = "허용/금지 목록" — 특정 명령어를 자동 허용하거나 완전 차단.
- **Hooks** = "자동 트리거" — 이벤트 발생 시 스크립트 100% 실행. Permissions(단순 허용/차단)과 달리 조건부 로직 가능. (추후 안정화 후 도입)

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m pytest *)", "Bash(black *)", "Bash(git status)",
      "Bash(git diff*)", "Bash(git log*)", "Bash(git add *)", "Bash(git commit *)"
    ],
    "deny": [
      "Bash(git push --force*)", "Bash(git push -f*)", "Bash(git push * main)",
      "Bash(git reset --hard*)",
      "Edit(.env)", "Edit(.env.*)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  }
}
```

**CI 파이프라인** (`.github/workflows/ci.yml`):

PR 생성 시 GitHub 서버가 자동으로 포매팅·테스트를 검증한다. 실패 시 merge 자체가 차단된다.

```yaml
name: CI
on: [pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: black --check .
      - run: python -m pytest tests/ -v
```

#### 4.4.5 백엔드 미들웨어 (`api/middleware/`)

유저 서빙 시 FastAPI 앱에서 실행되는 일반 백엔드 코드다. Harness Engineering과는 별개 영역.

| 모듈 | 파일 | 역할 |
|------|------|------|
| Safety | safety.py | 면책 문구 자동 삽입, 신뢰도 < 60% → "판단 유보", 금지 표현 치환 |
| Orchestration | orchestrator.py | DART/Market/News/Graph/LLM 호출 순서·의존성 관리. LLM 의존도 10~20% |
| Recovery | recovery.py | 그레이스풀 디그레이드 (LLM 실패→데이터만, DART 실패→캐시, 전체 실패→기본 정보) |
| Monitoring | monitoring.py | CatBoost 예측 정확도 추적, API 성능 로깅 |
| Caching | Redis | yfinance 5분 캐시, DART 일간 캐시, EQS 분기별 캐시 |

#### 4.4.6 데이터 흐름 아키텍처

Sub-agent와 Skills는 **개발 단계에서 코드를 작성하는 도구**이지, 유저 서빙 시 실행되는 것이 아니다. 전체 데이터 흐름은 4단계로 구성된다.

```
① 개발 단계 (Claude Code + Sub-agents + Skills)
   → 수집·계산·서빙 코드(.py)를 작성하는 과정
   → CPA는 코드를 읽지 않고, 결과물(숫자, 차트)의 회계적 합리성만 검증

② 배치 파이프라인 (Celery 스케줄러, 매일 자동 실행)
   → ①에서 만든 코드가 서버에서 자동 실행
   → DART 재무제표 수집 → EQS 5모듈 계산 → PostgreSQL 저장
   → Claude Code 개입 없음, 순수 Python 코드만 실행

③ 실시간 파이프라인 (DART 폴링, 1~5분 간격)
   → 새 공시 감지 → CatBoost 추론 → 결과 DB 저장 + WebSocket 알림

④ 유저 서빙 (FastAPI, 0.05초 응답)
   → 유저가 기업 클릭 → DB에서 이미 계산된 결과 SELECT → JSON 응답
   → AI 실시간 계산 없음, DB 조회만
```

---

## 5. 팀 역할 분담 및 협업 구조

### 5.1 기능별 수직 분할

| 담당 | 브랜치 | 폴더 | 범위 |
|------|--------|------|------|
| A | feat/financial | financial/ | 재무제표 수집 + EQS 등급 + 재무 요약 |
| B | feat/disclosure | disclosure/ | DART 공시 수집(과거+실시간) + 쉬운 설명 |
| C | feat/relation | relation/ | 기업 간 관계 분석(지분·공급·경쟁) |
| D | feat/price | price/ | 주가 수집 + 공시 후 주가변동 라벨링 + 공시-주가 연결 |
| 프로젝트 리드 | dev (통합) | api/ + frontend/ | FastAPI + Next.js + 전체 통합 + 최종 merge |

### 5.2 브랜치 전략

```
main ────── 배포용 (직접 push 금지)
  └── dev ── 개발 통합 (매주 금요일 합침)
       ├── feat/financial
       ├── feat/disclosure
       ├── feat/relation
       └── feat/price
```

**규칙**:
- 남의 폴더 건드리지 않기 (conflict 최소화)
- 모듈 간 연결은 DB 테이블을 통해 (import 아닌 데이터 공유)
- 매주 금요일 feat → dev PR + merge
- dev 안정 확인 후 → main 반영 (프로젝트 리드만)

### 5.3 폴더 구조

```
disclose-ai/
├── CLAUDE.md                     ← 루트 (60줄 이내, 보편 규칙만, 항상 로드)
├── CLAUDE.local.md               ← 개인 설정 (.gitignore)
├── .mcp.json                     ← project scope MCP (팀 공유, git 추적)
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
│
├── .github/                      ← CI (확정적 검증)
│   └── workflows/
│       └── ci.yml                ← PR 시 black --check + pytest 자동 실행
│
├── .claude/                      ← Claude Code 확장 시스템 (git 추적, 프로젝트 리드만 편집)
│   ├── settings.json             ← Sandbox + Permissions (Hooks는 추후 추가)
│   ├── skills/
│   │   ├── check/SKILL.md        ← /check: 리뷰+테스트+기록 통합 (수동 호출)
│   │   ├── review/SKILL.md       ← /review: 코드 리뷰만 (auto-invocable)
│   │   └── test/SKILL.md         ← /test: 테스트만 (auto-invocable)
│   ├── agents/
│   │   ├── code-reviewer.md      ← Sonnet, 읽기 전용 PR 리뷰
│   │   └── test-generator.md     ← Haiku, pytest 자동 생성
│   └── hooks/                    ← 폴더만 생성 (추후 Windows 호환 스크립트 추가)
│       └── README.md
│
├── shared/                       ← 전원 공유 (DB, ORM, 설정) — 프로젝트 리드만 수정
│   ├── CLAUDE.md                 ← "이 폴더는 프로젝트 리드만 수정" 규칙
│   ├── db.py
│   ├── models.py                 ← 테이블 정의 = DB 스키마 문서
│   └── config.py
│
├── financial/                    ← A 담당
│   ├── CLAUDE.md                 ← EQS 수식, K-IFRS 규칙, 금융업 예외
│   ├── CLAUDE.local.md           ← A 개인 설정 (.gitignore)
│   ├── PROGRESS.md               ← 진행경과 자동 기록 (/check 실행 시 업데이트)
│   ├── collector.py
│   ├── eqs/
│   │   ├── m1_accruals.py
│   │   ├── m2_beneish.py
│   │   ├── m3_cashflow.py
│   │   ├── m4_persistence.py
│   │   ├── m5_piotroski.py
│   │   └── calculator.py
│   ├── summary.py
│   └── grade.py
│
├── disclosure/                   ← B 담당
│   ├── CLAUDE.md                 ← DART API 패턴, rate limit, 폴링 규칙
│   ├── CLAUDE.local.md           ← B 개인 설정 (.gitignore)
│   ├── PROGRESS.md               ← 진행경과 자동 기록
│   ├── collector.py
│   ├── realtime.py
│   ├── parser.py
│   └── explainer.py
│
├── relation/                     ← C 담당
│   ├── CLAUDE.md                 ← NetworkX 규칙, 그래프 스키마
│   ├── CLAUDE.local.md           ← C 개인 설정 (.gitignore)
│   ├── PROGRESS.md               ← 진행경과 자동 기록
│   ├── collector.py
│   ├── graph.py
│   └── query.py
│
├── price/                        ← D 담당
│   ├── CLAUDE.md                 ← yfinance 패턴, .KS/.KQ suffix 규칙
│   ├── CLAUDE.local.md           ← D 개인 설정 (.gitignore)
│   ├── PROGRESS.md               ← 진행경과 자동 기록
│   ├── collector.py
│   ├── labeler.py
│   └── linker.py
│
├── api/                          ← 프로젝트 리드 (통합)
│   ├── CLAUDE.md                 ← API 라우팅 컨벤션, 에러 처리 패턴
│   ├── main.py
│   ├── routes/
│   └── middleware/
│       ├── safety.py             ← 면책 문구, 신뢰도 필터, 금지어
│       ├── orchestrator.py       ← DART/Market/News/Graph/LLM 오케스트레이션
│       ├── recovery.py           ← 그레이스풀 디그레이드
│       └── monitoring.py         ← 모델 정확도 + API 성능 추적
│
├── frontend/                     ← 프로젝트 리드 (AI 생성)
│   ├── CLAUDE.md                 ← Three.js, D3.js 프론트엔드 컨벤션
│   └── (Next.js 프로젝트)
│
├── docs/                         ← 프로젝트 문서
│   ├── PRD.md                    ← 본 문서
│   ├── ARCHITECTURE.md           ← 시스템 아키텍처 + 기술 용어 번역표
│   ├── ONBOARDING.md             ← 팀원용 시작 가이드 (Git, Skill, DB 등)
│   └── prototype/
│       └── corporate_universe_v5.html  ← UI 프로토타입
│
├── tests/                        ← 테스트
│   ├── conftest.py               ← 공유 fixtures
│   └── (각 모듈별 test_*.py)
│
└── notebooks/                    ← 각자 실험 공간
```

**CLAUDE.md 로딩 규칙**:
- 루트 CLAUDE.md: 매 세션 시작 시 항상 로드 (60줄 이내, 보편 규칙만)
- 하위 폴더 CLAUDE.md: 해당 폴더 파일 작업 시에만 on-demand 로드 (컨텍스트 절약)
- CLAUDE.local.md: .gitignore 대상, 개인 취향만 (git에 올라가지 않음)
- 하위가 상위와 충돌 시 하위 우선

### 5.4 소통 규칙
- 매일: 카톡/슬랙에 3줄 공유 (한 것, 할 것, 막힌 것)
- 매주 금: 30분 화상회의 (각자 시연 + dev merge)
- Notion: 기능별 진행률 추적
- GitHub: PR 기반 코드 리뷰 (`/pr-review` skill 또는 `code-reviewer` agent 활용)
- docs/onboarding.md: 팀원 온보딩 가이드 (Claude Code 설치, MCP 연결, 첫 세션 시작법)

### 5.5 팀원 행동 가이드

```
해야 할 것:
  ✅ Claude Code에게 CPA 용어로 요청 (코딩 용어 몰라도 됨)
  ✅ 결과물(숫자, 차트)이 회계적으로 맞는지 판단
  ✅ Agent 리뷰 코멘트에서 도메인 이슈만 확인
  ✅ 자기 폴더의 CLAUDE.md에 도메인 지식 추가
  ✅ 자기 skill을 .claude/skills/에 추가하여 PR

하지 말 것:
  ❌ 남의 폴더 파일 수정
  ❌ shared/ 폴더 건드리기 (프로젝트 리드에게 요청)
  ❌ .env 파일 커밋 (Hook이 차단하지만 시도도 말 것)
  ❌ 남의 SKILL.md 파일 수정
```

---

## 6. AI Rookie 심사항목 대응

### 도전성 (창의성 + 혁신성)
- **창의성 ★★★★★**: 한국에 상장사 전체를 네트워크로 시각화하며 공시 파급효과를 학습 기반으로 분석하는 서비스 없음
- **혁신성 ★★★★★**: WebGL 시각화 + Event Study + EQS의 결합은 기존 기술/서비스의 한계를 넘는 시도

### 팀역량 (추진성 + 성장성)
- **추진성 ★★★★**: 데이터 100% 무료 공개, 기술 스택 검증됨, CPA 팀의 재무/회계 도메인 전문성
- **성장성 ★★★★★**: 1,400만 투자자 타깃, 금융 플랫폼 API, 구독형 SaaS 등 사업화 경로 명확

### 실용성 (실효성 + 가치성)
- **실효성 ★★★★★**: 공시 정보의 비대칭 해소라는 실제 현장 문제, 개인투자자가 즉시 사용 가능한 도구
- **가치성 ★★★★★**: 금융 문해력 향상이라는 사회적 가치, 정보 민주화를 통한 자본시장 건전성 기여

---

## 7. 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| "투자 조언"으로 해석될 법적 리스크 | `api/middleware/safety.py`에서 면책 문구 자동 삽입 + 금지 표현 치환을 코드 레벨로 강제 |
| DART API 일일 한도 (10,000건) | 과거 데이터는 배치 수집, 실시간은 5분 간격. `api/middleware/orchestrator.py`에서 rate limit 관리 |
| 금융업 EQS 적용 어려움 | M3 제외, BIS비율 등 별도 기준 적용. `financial/CLAUDE.md`에 예외 규칙 명시 |
| ML 모델 과적합 | 시계열 교차검증(Time-series CV) + 최소 표본 수 기준. `api/middleware/monitoring.py`에서 정확도 추적 |
| 팀원 전원 개발 초보 | Agent-to-Agent 자율 운영: 코드 품질은 Agent가, 도메인 로직은 CPA가 분업 |
| .env·API키 유출 | Hook(`block-dangerous.sh`) + Sandbox에서 100% 차단 |
| 코드 충돌 | 남의 폴더 수정 시 Hook 경고 + 모듈 간 DB 테이블 기반 데이터 공유 (import 금지) |
| Claude Code 컨텍스트 낭비 | 하위 폴더 CLAUDE.md on-demand 로드 + Skills progressive disclosure + 도메인별 auto-invocable: false |
| 코드 품질 저하 | CI(GitHub Actions)가 포매팅·테스트 100% 강제 + code-reviewer agent 1차 리뷰 |

---

## 8. 산출물 목록

### 이미 완성된 것
- HTML 프로토타입 v1~v5 (기업 우주, 공시 시뮬레이션, 3D 행성)
- PPT 피치덱 12슬라이드 (스크린샷 삽입, CatBoost 분류 모델 설명 포함)
- EQS 5개 모듈 상세 설계 + K-Beneish Score 방법론
- 데이터 아키텍처 설계 (5GB, PostgreSQL)
- 팀 협업 구조 (브랜치 전략, 폴더 구조, 소통 규칙)
- Harness Engineering 설계: CLAUDE.md 계층(루트+7개 하위), MCP 5개, Skills 6개, Hooks 2개, Sub-agents 5개, CI 파이프라인, Sandbox+Permissions

### 제작 필요
- 도전제안서 5페이지 (양식: 일반사항/아이디어상세/구현계획/기대효과)
- 3분 YouTube 영상
- DART OpenAPI 인증키 발급 + 데이터 수집 파이프라인
- CLAUDE.md 실제 파일 작성 (루트 + 하위 7개)
- `.claude/` 폴더 구성 (settings.json, hooks, skills, agents)
- `.github/workflows/ci.yml` CI 파이프라인 구성
- `shared/models.py` DB 스키마 확정
- docs/onboarding.md 팀원 가이드 작성

---

## 부록: 핵심 용어 정리

### 금융·ML 용어
- **CatBoost**: 범주형 피처에 강한 그래디언트 부스팅 분류 모델
- **Isotonic Calibration**: 모델 출력 확률을 실제 빈도에 맞게 보정하는 기법
- **EQS (Earnings Quality Score)**: 이익의 질을 0~100점으로 수치화하는 종합 지표
- **Beneish M-score**: 재무제표 조작 가능성을 탐지하는 통계 모델
- **Piotroski F-score**: 재무 건전성을 9개 지표로 평가하는 모델
- **K-Beneish**: Beneish 모델을 한국 K-IFRS 환경에 맞게 재추정한 버전

### AI 엔지니어링 용어
- **Agent-to-Agent 자율 운영**: CPA가 Claude Code에게 도메인 언어로 요청 → Claude Code가 코드 작성·테스트·PR 생성 → Agent가 1차 리뷰 → CI가 강제 검증 → 프로젝트 리드가 최종 merge. 코딩 초보 팀이 AI 에이전트의 자율성을 활용하여 프로덕션 코드를 생산하는 방식
- **Harness Engineering**: AI 코딩 에이전트가 신뢰할 수 있는 코드를 자율적으로 생산하도록 환경을 설계하고, 의도를 명시하고, 피드백 루프를 구축하는 방법론. CLAUDE.md 계층, Hooks, Skills, Sub-agents, MCP, CI, docs 등 에이전트를 감싸는 구조 전체를 의미한다. `api/middleware/`의 safety.py 같은 일반 백엔드 코드와는 별개 개념 (참조: OpenAI "Harness engineering: leveraging Codex in an agent-first world", 2026.02)
- **MCP (Model Context Protocol)**: AI 코딩 에이전트를 외부 도구(GitHub, DB 등)에 연결하는 오픈 프로토콜
- **CLAUDE.md**: Claude Code가 매 세션 시작 시 읽는 프로젝트 컨텍스트 파일. 루트는 항상 로드, 하위 폴더는 해당 폴더 작업 시에만 on-demand 로드
- **Skills (SKILL.md)**: Claude Code의 재사용 가능한 워크플로우 정의. `/스킬이름`으로 호출하는 사용자 명령어. 네이밍은 동사형(`/check`, `/review`, `/test`). frontmatter(name+description)만 초기 로드, 호출 시에만 전체 내용 로드 (Progressive Disclosure)
- **Sub-agents**: 독립 컨텍스트 윈도우에서 실행되는 전문 에이전트 워커. 네이밍은 역할명(`code-reviewer`, `test-generator`). Skill이 Agent를 호출하는 구조. 메인 세션의 컨텍스트를 오염시키지 않음
- **Skill과 Agent의 차이**: Skill = 사용자가 `/`로 호출하는 명령어 (인터페이스). Agent = 뒤에서 실제 작업을 수행하는 전문가 (워커). 예: `/check` skill이 `code-reviewer` agent + `test-generator` agent를 병렬 호출
- **Hooks**: Claude Code의 특정 이벤트(파일 저장, Bash 실행 등)에 자동 실행되는 스크립트. 100% 확정적으로 실행. 단, Windows에서는 `.sh` 대신 PowerShell/`.bat` 사용 필요. stdin JSON으로 데이터 수신, exit 2가 차단(exit 1은 경고만)
- **Sandbox**: OS 레벨에서 Claude Code의 파일 시스템·네트워크 접근을 격리하는 보안 메커니즘
- **Permissions**: settings.json의 allow/deny 목록으로 특정 명령어를 자동 허용하거나 완전 차단하는 규칙
- **CI (Continuous Integration)**: PR 생성 시 GitHub 서버가 자동으로 포매팅·테스트를 실행하여 검증. 실패 시 merge 차단. `.github/workflows/ci.yml`에 정의
- **Progressive Disclosure**: 모든 정보를 한꺼번에 로드하지 않고, 필요한 시점에 필요한 만큼만 로드하는 원칙
- **auto-invocable: false**: Skill이 프로젝트에 존재하지만, Claude가 자동으로 호출하지 않고 `/스킬이름`으로 수동 호출해야만 실행되는 설정
- **Graceful Degradation**: 일부 도구/API가 실패해도 서비스 전체가 중단되지 않고 제한된 기능으로 응답하는 설계 패턴
