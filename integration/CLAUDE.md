# integration/ — 서빙 계층 규약 (리더 소유)

> 이 파일은 `integration/` 아래 파일 작업 시 자동 로드됨 (Progressive Disclosure).
> 하위 상세: [v2/CLAUDE.md](v2/CLAUDE.md)(정본 UI) · [dossier/DOSSIER_TABS_PLAN.md](dossier/DOSSIER_TABS_PLAN.md)(3탭 실행 계획)
> 디자인 규칙: 루트 [DESIGN.md](../DESIGN.md) 준수.
>
> **결정 원장 규율 (2026-07-22 신설)** — 반복 실수 방지 2종, 착수 전 필독(S0)·작업 후 기록(S7)·2회 반복 시 코드/조문 승격:
> - **기능**: [DECISIONS.md](DECISIONS.md) (`FN-###` — 파이프라인·와이어링·배포·환경. 예: cp949 print 크래시, 캐시버스트 규율, V-2 게이트)
> - **UI/UX**: [v2/UX_DECISIONS.md](v2/UX_DECISIONS.md) (`UX-###` — 리더 피드백·기각·재설계. 예: 병렬 성운 기각→드릴인 확정)

## 폴더 성격

**리더 소유 서빙 계층.** 4개 데이터 모듈(financial·disclosure·relation·price)의 산출물을 교차 통합·시각화한다. UI 정본은 `v2/`(React CDN), 기업 상세는 `dossier/` 3탭, 데이터 파이프라인은 이 폴더 루트(`extract_data.py`·`build_data.py`).

> v1(vanilla 대시보드)은 2026-07-13 폐지 — UI는 v2 단일화, 파이프라인은 `integration/extract_data.py`로 승격. 복원은 git 이력.

## 모듈 경계 — 예외 규약 (중요)

프로젝트 일반 규칙은 "남의 모듈 import 금지"이지만, **이 폴더는 예외**다:

- ✅ **타 모듈 코드 `import` 허용** — 예: `from modules.price.quiz_data import QUIZ_LIST`
- ✅ **타 모듈 DB·JSON 파일 읽기 허용** — `sqlite3.connect("modules/financial/data/financial.db")`
- ❌ **타 모듈 파일 수정·삭제 금지** — 쓰기 금지. 버그 수정이 필요하면 담당자에게 PR 요청
- ❌ **반대 방향 의존 금지** — `modules/*`에서 `integration`을 import하지 않음 (단방향)

이 예외는 리더 소유 서빙 계층(= 루트 `integration/`)에만 한정된다. (미래 백엔드 `api/`도 동일 — 현재 미구현)

## 데이터 흐름

```
[Source 계층 — 각 담당자 소유]            [추출 계층 — 이 폴더]        [렌더 계층]
modules/relation/data/graph_top50.json ─┐ (무변환 동기화)
modules/financial/data/financial.db    ─┤
modules/disclosure/data/disclosure.db  ─┼──→ extract_data.py ──→ data/*.json ──→ v2/index.html
modules/price/quiz_data.py             ─┘   (python -m integration.build_data)    + dossier 3탭
```

- **데이터 갱신 = 명령 하나**: `python -m integration.build_data` (opt-in: `--business` `--history`). 추출 스크립트를 새로 만들면 build_data.py에 단계로 등록한다.
- 기업 상세(ENTER CORPORATION)는 `dossier/` 3탭 iframe — per-ticker JSON(`dossier/data/`)을 fetch.

## 데이터 소스 계약 (extract_data.py가 각 모듈에서 뽑는 것)

각 모듈이 스키마를 바꿀 경우 **이 표를 반드시 업데이트하고 extract_data.py를 검증**할 것.

### financial 모듈 (Source: `modules/financial/data/financial.db`)
- 테이블: `financial_local`
- 추출 컬럼: `corp_code, corp_name, year, quarter, revenue, operating_income, net_income, total_assets, total_liabilities, total_equity, operating_cashflow, investing_cashflow, financing_cashflow, eqs_m1, eqs_m2, eqs_m3, eqs_m4, eqs_m5, eqs_total, eqs_grade`
- 보강: `modules/financial/data/eqs_data.json`에서 market_cap·dart_url·industry_code·latest_year·history·percentile
- 매칭 키: `corp_code` (8자리) / 기대 레코드: top50 × 최신 연도 1건씩

### disclosure 모듈 (Source: `modules/disclosure/data/disclosure.db`)
- 테이블 1: `disclosure_local` — `corp_code, corp_name, disclosure_date, disclosure_type, title, amount, summary, high_impact, dilution_ratio` (기업당 최근 5건)
- 테이블 2: `financial_statement` — `corp_code, year, quarter, revenue, operating_income, net_income, roe, debt_ratio, operating_margin` (기업당 최근 8분기, ⚠️ corp_code가 6자리 ticker)

### price 모듈 (Source: `modules/price/quiz_data.py`)
- 상수: `QUIZ_LIST: list[dict]` — `id, company, ticker, date, category, title, context, answer, change_pct, kospi_change_pct, window, explanation`
- 매칭 키: `ticker` (6자리) / 기대 레코드: 15건

### relation 모듈 (Source: `modules/relation/data/graph_top50.json`)
- **변환 없음** — extract_data.py가 `data/graph_top50.json`으로 무변환 동기화(byte 복사), 화면은 그 사본을 fetch
- 스키마: `[{n, t, s, sz, mc, group, rl:[...]}]` — **이 스키마를 바꾸면 화면이 조용히 깨진다** (docs/ARCHITECTURE.md §4와 함께 갱신)

## 실행 방법

```bash
# 데이터 재생성 (공유 JSON 4종) — 프로젝트 루트에서
python -m integration.build_data          # 또는 개별: python -m integration.extract_data

# 로컬 확인 (HTTP 서빙 필수 — file://은 fetch CORS 차단)
python -m http.server 8000
#  진입점: http://localhost:8000/integration/   (→ v2)
#  3탭 딥링크: http://localhost:8000/integration/v2/index.html?corp=005930
```

## 팀 데이터 업데이트 플로우

1. **담당자**: 자기 모듈 수집 → `modules/<모듈>/data/*.db·*.json` 커밋 → dev로 PR
2. **리더**: PR 머지 후 `python -m integration.build_data` → `integration/data/*.json` 재생성 확인 → 커밋
3. **스키마 변경 시**: extract_data.py 동작 확인 → 위 계약 표 갱신 → extract 쿼리 수정 → PR에 근거 포함

## 주의

- extract_data.py는 소스가 비어도 빈 배열·객체를 내보낸다 (fetch 404 방지)
- `integration/data/*.json`은 git 커밋 대상 (팀 공유 파생물)
- top50 기준(`modules/relation/data/top50.csv`) 밖 기업은 추출 대상 외
- ⚠️ eqs_data.json의 market_cap이 비면 eqs_summary 시총이 소실됨 — 재생성 전 `git diff`로 점검 (ARCHITECTURE §1-6)
