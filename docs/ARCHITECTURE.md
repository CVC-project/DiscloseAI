# DiscloseAI 시스템 아키텍처

> 이 문서는 팀원이 프로젝트 전체 구조를 이해하기 위한 가이드이자, **데이터·DB 토폴로지의 단일 출처(single source of truth)**입니다.
> PRD(docs/초기PRD.md)가 "비전"이라면, 이 문서는 "지금 실제로 돌아가는 구조"입니다.

---

## ⚠️ 알려진 문제 & 열린 선택지 (팀 필독)

> 구조상 손봐야 할 부채 목록. **지금 당장 바꾸지 않되, 관련 작업 전 반드시 인지할 것.** 결정은 팀 논의 후.

### 1) 재무 데이터 이중수집
- **현상**: `financial_local`(A, 연간+EQS, 8자리)과 `financial_statement`(B, 분기+ROE·부채비율, 6자리)이 **둘 다 DART에서 재무제표를 독립 수집**한다.
- **왜 단순 중복이 아닌가**: financial은 **연간만** 저장([batch.py](../modules/financial/batch.py)가 분기 제거), disclosure의 분기 재무는 **Groq 공시분석 맥락**([collector.py](../modules/disclosure/collector.py) `get_financial_context`)에 독립적으로 쓰인다 → "financial이 주인"이라 단정 못 함.
- **진짜 문제 3가지**: ① 식별자 불일치(같은 `corp_code`가 8자리 financial / 6자리 disclosure) ② DART 재무 중복 수집 ③ 컬럼명 발산(`total_liabilities`/`total_equity` vs `total_debt`/`equity`).
- **열린 선택지**: ⒜ 현행 유지 + **식별자 규칙만 통일**(저비용) / ⒝ **financial을 분기까지 확장 → 단일 소유**(disclosure는 읽기) / ⒞ **shared(Supabase) 이관 시 통합**.
- **(2026-07 확대, R6) report 모듈 신설**: `modules/report/`가 `fnlttSinglAcntAll`(×5개년)로 재무 정형을 추가 수집 → 정형 **3중**(financial·disclosure·report), 원문도 disclosure·relation·report **3중**. galaxy 파이프라인 전용이라 격리(`reports.db`·`raw_cache/` 비커밋), DART 콜 총량은 일일 한도 3%로 무영향(플랜 §6.5). [이슈 #43](https://github.com/CVC-project/DiscloseAI/issues/43) 등재 — 중기 공용 수집 캐시 계층 논의 트리거.

### 2) financial firm 상세 — 데이터 주도 템플릿으로 전환 (✅ 대부분 해소, 2026-06 / option ⒞-lite)
- **변경 전**: `financial/dashboard.py`가 데이터를 인라인한 완성 HTML(`docs/prototype/firm_<ticker>.html` 48개)을 생성하고 integration v1·v2가 `<iframe>` 임베드.
- **변경 후 (integration-only, financial 코드 무수정)**: firm 상세 = **데이터(JSON) + 단일 템플릿** 구조.
  - 데이터: `integration/dossier/data/firm_<ticker>.json` 48개 — 기존 HTML의 `const DATA`를 extract_firm_json.py로 **무손실 추출**(원 단위, 슈퍼셋 그대로). (1회성 스크립트 — 원본 HTML 삭제 후 은퇴·제거, git 이력 보존)
  - 표현: `integration/dossier/firm.html` 단일 템플릿 — [build_firm_template.py](../integration/dossier/build_firm_template.py)가 financial `_HTML_TEMPLATE`에서 파생(CSS·Chart.js·렌더 로직 **바이트 동일**). `?ticker=`로 해당 JSON fetch.
  - iframe: v1 `../dossier/firm.html?ticker=<t>&v=`, v2 `../dossier/firm.html?ticker=<t>`. `injectV2Theme()` 그대로 작동.
- **해소**: ① financial이 표현 생성 → **integration이 표현 소유**(financial은 데이터만) ② 런타임 자산 `docs/prototype/`(문서) → `integration/dossier/`(서빙)로 이동.
- **의도적 보류**: ③ firm 상세도 데이터 주도가 됐으나 **iframe은 유지** — CSS·JS 격리벽(제거 시 firm 테마 CSS와 v2 `styles.css` 충돌, 시각 변형 위험). (④ `injectV2Theme()`는 3탭 디자인 통일로 폐기 → 2026-07-13 코드에서 제거 완료 — firm은 `?theme=galaxy` 스코프 CSS 셀프 테마.)
- **후속(범위 외)**: `docs/prototype/firm_*.html` 48개는 **삭제 완료**(2026-06-10, post-#28 정리). financial 재batch 시 HTML 재생성을 막으려면 `dashboard.py`에 JSON 출력(`write_firm_json`) 추가 필요(A 담당과 협의). `eqs_data.json`은 `modules/financial/data/`로 이동해 보존(`extract_data.py`가 history·percentile용으로 읽음 — 이슈 #3).

### 3) financial 생성물·데이터·캐시 위치 부채 (✅ 해결, 2026-07)
- **과거 현상**: financial 모듈의 출력 경로(`_DASHBOARD_DIR`·`_CACHE_DIR`·EQS 배치)가 `docs/prototype/`에 박혀 빌드 산출물·런타임 데이터·캐시가 문서 폴더로 쏟아졌다.
- **왜 문제였나**: `docs/`는 **문서·디자인 목업 전용**(§2)인데 소유·생명주기가 다른 코드 산출물이 섞여 "문서 폴더 = 덤프장"이 됨.
- **✅ 확정 규칙**:
  - financial **생성물(HTML)·데이터(JSON)·캐시**는 `docs/`가 아니라 **`modules/financial/data/`** 아래. `docs/`에는 **문서·순수 디자인 목업만**.
  - 표현(HTML)은 데이터 생산자가 아니라 **서빙 계층(integration)**이 소유 (이슈 #2 firm 사례).
- **해결 내역**:
  - firm 상세 → `integration/dossier/`(표현)·`integration/dossier/data/`(데이터). (이슈 #2)
  - [dashboard.py](../modules/financial/dashboard.py) `_DASHBOARD_DIR`·[batch.py](../modules/financial/batch.py)·[industry_groups.py](../modules/financial/industry_groups.py) `_CACHE_DIR` 출력 경로를 `modules/financial/data/`로 변경. 생성 HTML(`financial_dashboard.html`·`kospi50_ranking.html`)은 `.gitignore`의 `modules/*/data/*.html`로 커밋 제외(재생성물).
  - `eqs_data.json` → `modules/financial/data/eqs_data.json` 이동. integration 읽기 경로([extract_data.py](../integration/extract_data.py)) + [scripts/refresh_history_percentile.py](../scripts/refresh_history_percentile.py) 동기 갱신 → `python -m integration.extract_data`로 **48개 메타 로드 검증 완료**.
  - `_sector_stats.json`(빈 캐시)·`financial_dashboard.html`(재생성물)은 `docs/prototype/`에서 삭제 — 다음 배치 실행 시 새 위치에 재생성.
- **보존(진짜 목업)**: `corporate_universe_v6_galaxies.html`(v1 dashboard 원형)은 `design/prototypes/`로 이동해 보존(2026-07-12, 디자인 정본 폴더 신설). (`corporate_universe_v5.html`은 #28 정리에서 삭제 — relation `viewer/index.html`이 이미 fork 완료. 모듈 문서의 v5 라인 참조는 fork 시점 이력으로만 유효.)

### 4) price 타임머신 데이터가 코드에 하드코딩
- **현상**: 타임머신 시나리오 12개가 DB가 아니라 `modules/price/quiz_data.py`의 **`QUIZ_LIST` Python 상수**에 하드코딩(손으로 엄선한 과거 사건). integration은 이를 JSON으로 추출해 **inline 렌더**(iframe 아님). 주가·라벨 자체는 `price_local`(DB)에 정상.
- **열린 선택지**: ⒜ 현행 유지(엄선 교육 콘텐츠라 무방) / ⒝ DB 테이블로 이관해 갱신 가능하게.

### 5) 기타
- `shared/models.py` 95% 미사용(테스트 fixture만 참조). 미래 운영 이관 시 정리. relation `storage/CLAUDE.md`의 shared 승격 계획도 그때 일괄.

### 6) 화면 데이터 소스 일원화 (방향 확정 — 리더, 2026-07-12)
- **현상**: 화면이 긁어오는 곳이 4갈래 — ① `integration/data/`(extract 생성) ② `modules/relation/data/graph_top50.json` **직접 fetch**(유일한 모듈 폴더 침투) ③ `integration/dossier/data/`(추출 스크립트별 생성) ④ business 데이터의 SSOT가 프로토타입 HTML(`design/prototypes/kospi50_business_tabs.html`의 `const DATA`).
- **확정 방향**: UIUX 정본=`design/`, 모듈 데이터=`modules/*`(정본), 사업보고서=report DB(`reports.db`→publish). **화면(프론트)이 fetch하는 것은 전부 `integration/` 아래로 통일**(모듈=정본 생산, integration=서빙 사본). **프로토타입 HTML 데이터 의존은 중기 제거.**
- **단계**: ⑴ ✅ **완료(2026-07-12)** relation 그래프를 extract 단계에서 `integration/data/graph_top50.json`으로 무변환 동기화, v1 dashboard·v2 loader fetch 경로 전환 ⑵ ✅ **완료(2026-07-12)** 오케스트레이터 `integration/build_data.py` 신설(`python -m integration.build_data`, opt-in `--business`·`--history`) ⑶ business SSOT를 프로토타입 HTML → JSON/DB 이관, galaxy 47사는 report 파이프라인(Phase 4)이 채움 — **중기(Phase 4 착수 후)**.
- **⚠️ 재생성 함정(A 담당과 협의 필요)**: 현재 `modules/financial/data/eqs_data.json`의 `market_cap`이 **48건 전부 null** — 이 상태에서 extract를 재실행하면 서빙 중인 `eqs_summary.json`의 시총 47건이 null로 덮인다(2026-07-12 실측, 재생성분은 원복함). 커밋된 eqs_summary.json(6/9)이 마지막 정상 시총 보유. **다음 재생성 전에 eqs_data.json 시총 재적재 필요**(financial 배치 또는 refresh_history_percentile의 yfinance 활성 실행).

> 참고: disclosure 모듈은 `disclosure.db`(sqlite)에서만 소비되는 **깨끗한 DB 기반** 구조다(손댈 것 없음).

---

## 0. 구현 현황 (Implementation Status) — 2026-06

| 항목 | 설계 비전(PRD) | **실제 (정본)** |
|---|---|---|
| 데이터 저장 | Supabase 중앙 DB (`shared/models.py`) | **모듈별 로컬 SQLite** (각 `modules/*/data/*.db`) |
| 서빙 계층 | `api/`(FastAPI) + `frontend/`(Next.js) | **루트 `integration/`** (v2=React 유일 UI + 파이프라인). api/frontend 미구현 |
| 통합 방식 | API가 공용 DB 조회 | `integration/extract_data.py`가 로컬 DB → JSON, v2가 fetch |
| MCP | 5개 | 3개 (GitHub·Context7·Sequential) |
| Sandbox / Hooks | 활성 | 미설정 (Permissions만) |
| 면책 로직 | `api/middleware/safety.py` | **미구현** (향후 백엔드 구축 시) |

> `shared/models.py`는 **미래 운영(Supabase) 이관 타깃**이며 현재 미사용(`PriceData`만 활성). 미래 백엔드 `api/`(RAG·learning 포함)는 [docs/AI_DIRECTION_PLAN.md](AI_DIRECTION_PLAN.md) 참조 — 서빙 아키텍처(프론트·미들웨어·백엔드 3계층·연결 계약·호스팅·CD 파이프라인)의 실행 계획 정본은 [api/PLAN.md](../api/PLAN.md)(2026-07-20, 문서화 완료·코드 미착수).

---

## 1. 시스템 전체 그림 (실제)

```
[데이터 소스]        [수집·계산 — 각 담당자]          [저장: 로컬 SQLite]     [서빙: 리더]        [사용자]

DART OpenAPI ──→  modules/financial/  ──→  financial.db (financial_local)  ┐
(재무제표)         (A, 연간+EQS)                                            │
                                                                           │
DART OpenAPI ──→  modules/disclosure/ ──→  disclosure.db                   │   integration/
(공시)            (B, 공시+분기재무)        (disclosure_local,              ├─→ extract_data.py
                                            financial_statement)           │   → data/*.json
yfinance ─────→  modules/price/       ──→  price.db (price_local, vkospi)   │      ↓ fetch
(주가)            (D, 주가+라벨)                                            │   v2 index.html(React)
공정위/DART ──→  modules/relation/    ──→  relation.db                      │      ↓
(기업관계)        (C, 지분·계열)            → data/graph_top50.json ────────┘   브라우저
                                            (extract가 integration/data/로 동기화)
```

**핵심**: 각 팀원은 자기 폴더에서 데이터를 로컬 SQLite에 저장. 리더가 `integration/`에서 그 산출물(DB·JSON)을 **읽어** 교차 통합 대시보드로 보여줌. (Supabase 중앙 DB는 미래 운영 단계.)

---

## 2. 폴더별 역할

### 공용 폴더 (프로젝트 리드만 수정)
| 폴더 | 역할 |
|------|----------|
| `.claude/` | Skills, Agents, 설정 |
| `shared/` | 환경변수 로드(config.py, **활성**) + 미래 운영 DB 스키마(db.py·models.py, **현재 미사용**) |
| `docs/` | **기초 뼈대 문서만** — 아키텍처(본 문서)·PRD·온보딩·머지 절차. 실행 계획(plan/spec)은 실행되는 폴더에(예: `integration/dossier/DOSSIER_TABS_PLAN.md`) |
| `design/` | **디자인 정본** — 프로토타입 원형(`prototypes/`: 해방판·kospi50·corporate_universe·dc-runtime.js)·제작 사양서(프롬프트_v6). 디자인 규칙 SSOT는 루트 `DESIGN.md` |
| (공통) | ⚠️ docs/·design/ 모두 **코드 생성 산출물·데이터·캐시 금지** — 모듈 출력은 `modules/<모듈>/` 아래로 (이슈 #3) |

### 데이터 생산자 (`modules/` 아래, 각 담당자만 수정)
| 폴더 | 담당 | 역할 | 로컬 테이블 |
|------|------|----------|------|
| `modules/financial/` | A | 재무제표 + EQS 등급 | `financial_local` |
| `modules/disclosure/` | B | DART 공시 + 분기 재무 + 쉬운 설명 | `disclosure_local`, `financial_statement` |
| `modules/relation/` | C | 기업 간 관계 (지분·계열) | `company_node`, `relation_raw`, `relation_local` |
| `modules/price/` | D | 주가 + 공시 후 변동 라벨 | `price_local`, `vkospi_local` |
| `modules/report/` | 리더 | 사업보고서 원문·정형계정 5개년 (galaxy 파이프라인, Q1) | `report_raw`, `report_section`, `fs_account`, `pipeline_state` (reports.db, 비커밋) |

각 모듈: `db.py`(SQLite 연결), `models.py`(로컬 테이블 = **정본 스키마**), `data/`(DB·JSON, git 커밋됨). **모듈이 생성하는 산출물(HTML·JSON·캐시)도 `docs/`가 아니라 이 폴더 아래**에 둔다 (이슈 #3).

### 서빙 계층 (리더 소유)
| 폴더 | 역할 |
|------|----------|
| `integration/` | 4개 모듈 산출물 교차 통합. `extract_data.py`+`build_data.py`(데이터 파이프라인) · `v2/`(React, **유일 서빙 UI**) · `data/`(공유 JSON 4종) · `dossier/`(기업 상세 3탭 — 이슈 #2) · `index.html`(진입점→v2) · 규약 `integration/CLAUDE.md`. (v1은 2026-07-13 폐지 — git 이력 보존) |
| `api/` *(코드 미구현)* | 미래 백엔드 (FastAPI·RAG·learning). 실행 계획 정본은 [api/PLAN.md](../api/PLAN.md) — 코드 구현은 후속 세션 |

---

## 3. 데이터 흐름

```
A: DART 재무 → financial_local (financial.db)
B: DART 공시 → disclosure_local + financial_statement (disclosure.db)
C: 공정위·DART 관계 → relation_local (relation.db) → graph_top50.json export
D: yfinance 주가 → price_local (price.db);  linker.py가 공시-주가 라벨을 shared.PriceData에도 적재

→ integration/extract_data.py 가 financial.db·disclosure.db·price quiz_data 를 읽어
  integration/data/{eqs_summary,disclosures,price_scenarios}.json 생성
  + modules/relation/data/graph_top50.json 을 integration/data/ 로 무변환 동기화 (§1-6 ⑴)
  (financial.db에 없는 history·percentile·시총은 modules/financial/data/eqs_data.json 에서 보강 — 이슈 #3)
  (단일 진입점: python -m integration.build_data — §1-6 ⑵)
→ v2 index.html 가 integration/data/*.json 4종을 fetch (모듈 폴더 직접 fetch 없음)
→ 기업 상세(ENTER CORPORATION): v2가 integration/dossier/ 3탭(business·galaxy·firm.html?ticker=<t>)을 iframe 로드
  → firm.html 이 integration/dossier/data/firm_<t>.json 을 fetch 해 렌더 (이슈 #2)
```

---

## 3.5. DB 토폴로지 & 식별자 규칙

| 데이터 | DB 파일 | 테이블 | 식별자 | 비고 |
|---|---|---|---|---|
| 재무(연간+EQS) | `modules/financial/data/financial.db` | `financial_local` | corp_code **8자리** | EQS 5모듈 포함 |
| 공시 | `modules/disclosure/data/disclosure.db` | `disclosure_local` | corp_code **8자리** | AI 분석·high_impact 등 |
| 재무(분기+비율) | `modules/disclosure/data/disclosure.db` | `financial_statement` | corp_code **6자리(ticker)** | Groq 공시분석 맥락용 |
| 주가 | `modules/price/data/price.db` | `price_local`, `vkospi_local` | corp_code | 라벨은 shared.PriceData에도 |
| 관계 | `modules/relation/data/relation.db` | `company_node`, `relation_raw`, `relation_local` | **ticker 6자리** | company_node가 8↔6 매핑 보유 |
| (미래 운영) | Supabase | `shared/models.py` 6개 | — | `PriceData`만 활성, 나머지 미사용 |

> ⚠️ **같은 `corp_code` 컬럼이 테이블마다 8자리/6자리로 다르다.** join 시 반드시 자릿수를 확인할 것. relation의 `company_node`가 corp_code(8)↔ticker(6) 매핑의 기준.

---

## 4. 모듈 간 연결 규칙

### 데이터 생산자끼리는 import 금지 → 로컬 산출물(DB·JSON)로만 공유
```python
# 잘못된 예 (modules 간 금지)
from modules.financial.eqs.score import calculate_eqs   # ✗

# 올바른 예 (자기 모듈 로컬 테이블 사용)
from modules.financial.db import get_session
from modules.financial.models import FinancialLocal      # ✓
```

### integration만 예외 (리더 소유 서빙 계층)
타 모듈 코드 import·DB/JSON **읽기** 허용 (쓰기·수정 금지, 단방향). 상세: [integration/CLAUDE.md](../integration/CLAUDE.md).

### relation → integration 데이터 계약
`modules/relation/data/graph_top50.json` (스키마 `[{n, t, s, sz, mc, group, rl:[...]}]`)이 계약 정본. extract_data.py가 `integration/data/graph_top50.json`으로 **무변환 동기화**하고 v1·v2는 그 사본을 fetch (2026-07-12 — §1-6 ⑴, 과거 직접 fetch). **스키마를 바꾸면 integration이 조용히 깨진다** → 변경 시 [integration/CLAUDE.md](../integration/CLAUDE.md) "데이터 소스 계약"과 본 문서를 함께 갱신하고 재동기화.

---

## 5. 기술 용어 번역표

| 용어 | 쉬운 설명 |
|------|----------|
| **API** | 프로그램끼리 데이터를 주고받는 통로. "주문 창구" 같은 것 |
| **DB (데이터베이스)** | 엑셀 시트를 서버에 올려둔 것. 여러 사람이 동시에 사용 가능 |
| **DB 스키마** | 엑셀 시트의 열 이름(헤더)을 미리 정해둔 설계도 |
| **테이블** | 엑셀의 시트 하나. 예: 재무 테이블, 주가 테이블 |
| **ORM** | Python 코드로 DB를 조작하는 도구. SQL 몰라도 됨 |
| **SQLite** | 파일 하나로 동작하는 가벼운 DB. 개발·테스트용 (우리의 현재 정본) |
| **Supabase** | PostgreSQL 기반 DB 서비스. 미래 운영 단계에 사용 예정 |
| **FastAPI** | Python으로 만드는 API 서버. "주문 창구를 만드는 도구" (미구현) |
| **Next.js** | React 기반 웹 프론트엔드 프레임워크 (현재는 integration의 단일 HTML+React-CDN로 대체) |
| **Three.js** | 3D 그래픽을 웹에서 그리는 라이브러리 |
| **Celery** | 예약된 시간에 자동으로 코드를 실행해주는 스케줄러 |
| **WebSocket** | 서버가 브라우저에 실시간으로 알림을 보내는 방법 |
| **CatBoost** | 범주형 데이터에 강한 AI 분류 모델. 공시 영향 예측에 사용 |
| **pytest** | Python 코드가 올바르게 동작하는지 자동 확인하는 테스트 도구 |
| **Black** | Python 코드를 일정한 형식으로 자동 정리하는 포매터 |
| **CI (Continuous Integration)** | PR 올리면 자동으로 테스트 실행. 통과해야 merge 가능 |
| **PR (Pull Request)** | "내 작업 확인해주세요" 요청. GitHub에서 코드 리뷰 요청 |
| **Branch** | 내 작업 공간. 다른 사람 작업에 영향 X |
| **Merge** | 내 작업을 메인 코드에 합치는 것 |
| **MCP** | Claude Code가 외부 도구(GitHub, DB)와 대화하는 연결선 |
| **Skill** | Claude Code에 미리 짜둔 작업 레시피. `/이름`으로 호출 |
| **Agent** | Claude Code의 전문가 동료. Skill이 호출하여 작업 위임 |
| **Hook** | 자동 안전장치. 위험한 행동을 자동으로 막아줌 (현재 미설정) |
