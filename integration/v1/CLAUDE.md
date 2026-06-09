# integration/v1/ — 통합 대시보드 (vanilla JS, fallback)

> 이 파일은 `integration/v1/` 아래 파일 작업 시 자동 로드됨 (Progressive Disclosure).
> 관련 문서: [PROGRESS.md](PROGRESS.md) — 작업 이력·데이터 스냅샷 일자
> 상위: `integration/`은 **DiscloseAI 루트의 서빙 계층**(데이터 생산자 `modules/`와 분리). v1=fallback, v2=정본 트랙, `../data/`=공유 산출물.

## 폴더 성격

**리더 소유 서빙 계층.** 4개 모듈(relation·financial·disclosure·price)의 산출물을 **localhost 단일 대시보드**로 통합한다. 각 담당자가 자기 모듈만으로는 보여줄 수 없는 **교차 시각화·교차 분석**이 이 폴더의 존재 이유. (v1=vanilla JS 대시보드, fallback / v2=React 정본)

## 모듈 경계 — 예외 규약 (중요)

프로젝트 일반 규칙은 "남의 모듈 import 금지"이지만, **이 폴더는 예외**다:

- ✅ **타 모듈 코드 `import` 허용** — 예: `from modules.price.quiz_data import QUIZ_LIST`
- ✅ **타 모듈 DB·JSON 파일 **읽기** 허용** — `sqlite3.connect("modules/financial/data/financial.db")`
- ❌ **타 모듈 파일 **수정·삭제 금지** — 쓰기 금지. 버그 수정이 필요하면 담당자에게 PR 요청
- ❌ **타 모듈에 대한 반대 방향 의존 금지** — `modules/{financial,disclosure,price,relation}/`에서 `integration`을 import하지 않음 (단방향 유지)

이 예외는 리더 소유 서빙 계층(= 루트 `integration/`)에만 한정된다. (미래 백엔드 `api/`도 동일 — 현재 미구현)

## 데이터 흐름

```
[Source 계층 — 각 담당자 소유]            [추출 계층]               [렌더 계층]
modules/relation/data/graph_top50.json ─┐
modules/financial/data/financial.db    ─┤
modules/disclosure/data/disclosure.db  ─┼──→ extract_data.py ──→ data/*.json ──→ dashboard.html
modules/price/quiz_data.py             ─┘                                       (fetch + 시각화)
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `v1/__init__.py` | 패키지 마커 (`python -m integration.v1.*` 실행용) |
| `v1/extract_data.py` | 4개 소스 → 3개 통합 JSON 생성하는 배치 스크립트 (출력: `../data/`) |
| `v1/dashboard.html` | v6 galaxies 기반 통합 시각화 (fetch + 패널) |
| `../data/eqs_summary.json` | financial_local 테이블 → 50기업 EQS 5모듈·등급·재무 요약 (v1·v2 공유) |
| `../data/disclosures.json` | disclosure_local + financial_statement → 50기업 최근 공시·분기 재무 |
| `../data/price_scenarios.json` | price.quiz_data.QUIZ_LIST → 15개 과거 공시 시나리오 (timemachine 모드용) |

> **참고**: relation 데이터는 별도 파일 없음. dashboard.html이 `../../modules/relation/data/graph_top50.json`을 직접 fetch한다 (integration이 루트로 승격돼 relation은 `modules/`에 남으므로 `../../modules/relation/`. relation은 이미 JSON 산출물이라 변환 불필요).

## 데이터 소스 계약 (각 모듈의 어떤 필드를 뽑는가)

extract_data.py가 의존하는 **테이블·컬럼·Python 상수**. 각 모듈이 스키마를 바꿀 경우 이 표를 반드시 업데이트하고 extract_data.py를 검증할 것.

### financial 모듈 (Source: `modules/financial/data/financial.db`)
- 테이블: `financial_local`
- 추출 컬럼: `corp_code, corp_name, year, quarter, revenue, operating_income, net_income, total_assets, total_liabilities, total_equity, operating_cashflow, investing_cashflow, financing_cashflow, eqs_m1, eqs_m2, eqs_m3, eqs_m4, eqs_m5, eqs_total, eqs_grade`
- 매칭 키: `corp_code` (8자리)
- 기대 레코드: top50 × 최신 연도 1건씩 (최대 50건)

### disclosure 모듈 (Source: `modules/disclosure/data/disclosure.db`)
- 테이블 1: `disclosure_local`
- 추출 컬럼: `corp_code, corp_name, disclosure_date, disclosure_type, title, amount, summary, high_impact, dilution_ratio`
- 쿼리 범위: 기업당 최근 5건 (disclosure_date DESC)
- 테이블 2: `financial_statement`
- 추출 컬럼: `corp_code, year, quarter, revenue, operating_income, net_income, roe, debt_ratio, operating_margin`
- 쿼리 범위: 기업당 최근 8분기

### price 모듈 (Source: `modules/price/quiz_data.py`)
- 상수: `QUIZ_LIST: list[dict]`
- 필드: `id, company, ticker, date, category, title, context, answer, change_pct, kospi_change_pct, window, explanation`
- 매칭 키: `ticker` (6자리)
- 기대 레코드: 15건 (top50 중 ~30% 커버)

### relation 모듈 (Source: `modules/relation/data/graph_top50.json`)
- **이 폴더에서 변환 안 함.** dashboard.html이 직접 fetch.
- 스키마: `[{n, t, s, sz, mc, group, rl:[...]}]` (node list with relation list)

## 실행 방법

### 전체 재생성
```bash
# 프로젝트 루트에서
python -m integration.v1.extract_data
```
→ `integration/data/*.json` 3개 덮어쓰기.

### 로컬 시각 확인
```bash
python -m http.server 8000
# 브라우저(v1): http://localhost:8000/integration/v1/dashboard.html
# 브라우저(v2): http://localhost:8000/integration/v2/index.html
```

## 🔄 팀원·리더 데이터 업데이트 플로우

### 상황 1: 팀원이 자기 모듈에서 새 데이터 수집 후 공유
**담당자가 할 일**:
```bash
git checkout dev && git pull
git checkout -b data/<모듈>-<YYYYMMDD>-update   # 예: data/financial-20260501-update
git add modules/<모듈>/data/*.db modules/<모듈>/data/*.json
git commit -m "data(<모듈>): <수집 범위·건수 요약>"
git push -u origin data/<모듈>-<YYYYMMDD>-update
# GitHub에서 PR 생성 (base: dev)
```

**리더가 할 일** (PR merge 후):
```bash
git checkout dev && git pull                  # 담당자 업데이트 dev에 반영됨
git checkout feat/integration-dashboard        # integration 작업 브랜치
git merge origin/dev                           # dev 반영
python -m integration.v1.extract_data    # JSON 재생성
# 로컬 확인 → 커밋 → PR
```

### 상황 2: 담당자가 스키마를 바꾼 경우 (컬럼 추가·삭제·이름 변경)
1. **extract_data.py가 작동하는지** 먼저 확인 (테이블 구조 mismatch → 예외)
2. 위 "데이터 소스 계약" 표를 갱신
3. extract_data.py의 해당 쿼리 수정
4. PR에 스키마 변경 근거 + 이 CLAUDE.md 업데이트 포함

### 상황 3: 리더가 수동으로 추출만 재실행하고 싶을 때 (dev 업데이트 없이)
```bash
python -m integration.v1.extract_data
```
→ 로컬 DB만 읽고 JSON 생성. git은 안 건드림. 브라우저 새로고침으로 즉시 반영.

## dashboard.html 구조 요약

### 데이터 로드 (init 초입)
```js
const [relData, eqsData, discData, priceData] = await Promise.all([
  fetch('../../modules/relation/data/graph_top50.json').then(r => r.json()),
  fetch('../data/eqs_summary.json').then(r => r.ok ? r.json() : []).catch(() => []),
  fetch('../data/disclosures.json').then(r => r.ok ? r.json() : {}).catch(() => ({})),
  fetch('../data/price_scenarios.json').then(r => r.ok ? r.json() : []).catch(() => [])
]);
```

### 노드 join
- `corp_code`(8자리) 기준으로 relation 노드에 financial·disclosure 데이터 주입
- `ticker`(6자리) 기준으로 price 시나리오 주입
- 데이터 없는 기업은 `has_financial=false`, `has_disclosure=false`, `has_quiz=false` 플래그

### 3개 모드별 패널
- **analyze**: financial EQS 5모듈 상세 (`n.financial.m1` 등)
- **disclosure**: disclosure 공시 리스트 + high_impact 플래그 + 재무제표 요약
- **timemachine**: `has_quiz=true`면 quiz 시나리오 / false면 "타임머신 데이터 없음(수집 중)" 뱃지

## 향후 승격 경로 (FastAPI로)

이 JSON fetch 구조는 프로덕션 진입 시 **FastAPI backend로 쉽게 교체 가능**:
- 현재: `fetch('./data/eqs_summary.json')`
- 미래: `fetch('/api/financial/eqs')`

dashboard.html의 fetch URL만 바꾸고, FastAPI가 `shared.models`(Supabase 적재 완료 후)를 조회해 같은 스키마의 JSON을 반환하면 끝. **대시보드 로직은 무변경**.

## 주의

- extract_data.py 실행 시 각 DB·상수에 데이터가 없어도 빈 배열·객체는 내보낸다 (파일 부재 시 fetch 404 방지)
- JSON 파일은 git에 커밋됨 (`.gitignore`에서 `modules/*/data/*.json` 제외 규칙 없음 — 2026-04-21 변경)
- top50 기준 (`modules/relation/data/top50.csv`)을 벗어나는 기업은 추출 대상 외
- 대시보드는 단일 HTML + vanilla JS. **Three.js·React 등 의존성 추가 금지** (Progressive 정책)
