# DiscloseAI 시스템 아키텍처

> 이 문서는 팀원이 프로젝트 전체 구조를 이해하기 위한 가이드이자, **데이터·DB 토폴로지의 단일 출처(single source of truth)**입니다.
> PRD(docs/PRD.md)가 "비전"이라면, 이 문서는 "지금 실제로 돌아가는 구조"입니다.

---

## 0. 구현 현황 (Implementation Status) — 2026-06

| 항목 | 설계 비전(PRD) | **실제 (정본)** |
|---|---|---|
| 데이터 저장 | Supabase 중앙 DB (`shared/models.py`) | **모듈별 로컬 SQLite** (각 `modules/*/data/*.db`) |
| 서빙 계층 | `api/`(FastAPI) + `frontend/`(Next.js) | **루트 `integration/`** (v1=vanilla JS, v2=React). api/frontend 미구현 |
| 통합 방식 | API가 공용 DB 조회 | `integration/v1/extract_data.py`가 로컬 DB → JSON, 대시보드가 fetch |
| MCP | 5개 | 3개 (GitHub·Context7·Sequential) |
| Sandbox / Hooks | 활성 | 미설정 (Permissions만) |
| 면책 로직 | `api/middleware/safety.py` | **미구현** (향후 백엔드 구축 시) |

> `shared/models.py`는 **미래 운영(Supabase) 이관 타깃**이며 현재 미사용(`PriceData`만 활성). 미래 백엔드 `api/`(RAG·learning 포함)는 [docs/AI_DIRECTION_PLAN.md](AI_DIRECTION_PLAN.md) 참조.

---

## 1. 시스템 전체 그림 (실제)

```
[데이터 소스]        [수집·계산 — 각 담당자]          [저장: 로컬 SQLite]     [서빙: 리더]        [사용자]

DART OpenAPI ──→  modules/financial/  ──→  financial.db (financial_local)  ┐
(재무제표)         (A, 연간+EQS)                                            │
                                                                           │
DART OpenAPI ──→  modules/disclosure/ ──→  disclosure.db                   │   integration/
(공시)            (B, 공시+분기재무)        (disclosure_local,              ├─→ v1 extract_data.py
                                            financial_statement)           │   → data/*.json
yfinance ─────→  modules/price/       ──→  price.db (price_local, vkospi)   │      ↓ fetch
(주가)            (D, 주가+라벨)                                            │   v1 dashboard.html
                                                                           │   v2 index.html(React)
공정위/DART ──→  modules/relation/    ──→  relation.db                      │      ↓
(기업관계)        (C, 지분·계열)            → data/graph_top50.json ────────┘   브라우저
```

**핵심**: 각 팀원은 자기 폴더에서 데이터를 로컬 SQLite에 저장. 리더가 `integration/`에서 그 산출물(DB·JSON)을 **읽어** 교차 통합 대시보드로 보여줌. (Supabase 중앙 DB는 미래 운영 단계.)

---

## 2. 폴더별 역할

### 공용 폴더 (프로젝트 리드만 수정)
| 폴더 | 역할 |
|------|----------|
| `.claude/` | Skills, Agents, 설정 |
| `shared/` | 환경변수 로드(config.py, **활성**) + 미래 운영 DB 스키마(db.py·models.py, **현재 미사용**) |
| `docs/` | PRD, 아키텍처(본 문서), 온보딩 |

### 데이터 생산자 (`modules/` 아래, 각 담당자만 수정)
| 폴더 | 담당 | 역할 | 로컬 테이블 |
|------|------|----------|------|
| `modules/financial/` | A | 재무제표 + EQS 등급 | `financial_local` |
| `modules/disclosure/` | B | DART 공시 + 분기 재무 + 쉬운 설명 | `disclosure_local`, `financial_statement` |
| `modules/relation/` | C | 기업 간 관계 (지분·계열) | `company_node`, `relation_raw`, `relation_local` |
| `modules/price/` | D | 주가 + 공시 후 변동 라벨 | `price_local`, `vkospi_local` |

각 모듈: `db.py`(SQLite 연결), `models.py`(로컬 테이블 = **정본 스키마**), `data/`(DB·JSON, git 커밋됨).

### 서빙 계층 (리더 소유)
| 폴더 | 역할 |
|------|----------|
| `integration/` | 4개 모듈 산출물 교차 통합. `v1/`(vanilla JS, fallback) · `v2/`(React, 정본) · `data/`(공유 JSON, v1이 생성→v1·v2 fetch) · `index.html`(진입점) |
| `api/` *(미구현)* | 미래 백엔드 (FastAPI·RAG·learning). 현재 폴더 없음 — 구축 시 생성 |

---

## 3. 데이터 흐름

```
A: DART 재무 → financial_local (financial.db)
B: DART 공시 → disclosure_local + financial_statement (disclosure.db)
C: 공정위·DART 관계 → relation_local (relation.db) → graph_top50.json export
D: yfinance 주가 → price_local (price.db);  linker.py가 공시-주가 라벨을 shared.PriceData에도 적재

→ integration/v1/extract_data.py 가 financial.db·disclosure.db·price quiz_data 를 읽어
  integration/data/{eqs_summary,disclosures,price_scenarios}.json 생성
→ v1 dashboard.html / v2 index.html 가 위 JSON + modules/relation/data/graph_top50.json 을 fetch
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

## 4. 🔴 알려진 문제 & 열린 선택지

### 재무 데이터 이중수집 (추후 팀 논의 — 현재 코드 변경 안 함)
- **현상**: `financial_local`(A, 연간+EQS, 8자리)과 `financial_statement`(B, 분기+ROE·부채비율, 6자리)이 **둘 다 DART에서 재무제표를 독립 수집**한다.
- **왜 단순 중복이 아닌가**: financial은 **연간만** 저장([batch.py](../modules/financial/batch.py)가 분기 제거), disclosure의 분기 재무는 **Groq 공시분석 맥락**([collector.py](../modules/disclosure/collector.py) `get_financial_context`)에 독립적으로 쓰인다 → "financial이 주인"이라 단정 못 함.
- **진짜 문제 3가지**:
  1. **식별자 불일치** — 같은 `corp_code` 컬럼이 8자리(financial)/6자리(disclosure).
  2. **DART 재무 중복 수집** — 같은 원천을 두 번 호출.
  3. **컬럼명 발산** — `total_liabilities`/`total_equity`(financial·shared) vs `total_debt`/`equity`(disclosure).
- **열린 선택지** (지금 결정·구현 X):
  - ⒜ 현행 유지 + **식별자 규칙만 통일**(저비용)
  - ⒝ **financial을 분기까지 확장 → 단일 소유**(disclosure는 읽기)
  - ⒞ **shared(Supabase) 이관 시 통합**
- → 팀 논의 후 결정.

### 기타
- `shared/models.py` 95% 미사용(테스트 fixture만 참조). 미래 운영 이관 시 정리. relation `storage/CLAUDE.md`의 shared 승격 계획도 그때 일괄.

---

## 4.5. 모듈 간 연결 규칙

### 데이터 생산자끼리는 import 금지 → 로컬 산출물(DB·JSON)로만 공유
```python
# 잘못된 예 (modules 간 금지)
from modules.financial.eqs.score import calculate_eqs   # ✗

# 올바른 예 (자기 모듈 로컬 테이블 사용)
from modules.financial.db import get_session
from modules.financial.models import FinancialLocal      # ✓
```

### integration만 예외 (리더 소유 서빙 계층)
타 모듈 코드 import·DB/JSON **읽기** 허용 (쓰기·수정 금지, 단방향). 상세: [integration/v1/CLAUDE.md](../integration/v1/CLAUDE.md).

### relation → integration 데이터 계약
`modules/relation/data/graph_top50.json` (스키마 `[{n, t, s, sz, mc, group, rl:[...]}]`)을 integration v1·v2가 **직접 fetch** (`../../modules/relation/...`). **이 스키마를 바꾸면 integration이 조용히 깨진다** → 변경 시 [integration/v1/CLAUDE.md](../integration/v1/CLAUDE.md) "데이터 소스 계약"과 본 문서를 함께 갱신.

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
