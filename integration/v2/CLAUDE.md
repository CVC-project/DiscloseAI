# integration/v2/ — v2 React UI 신규 구축

> 이 파일은 `integration/v2/` 아래 작업 시 자동 로드됨 (Progressive Disclosure).
> 부모 규약: [../CLAUDE.md](../CLAUDE.md) (모듈 경계 예외 — 리더 소유 폴더, 타 모듈 read-only 접근 허용)
> 진행 기록: [PROGRESS.md](PROGRESS.md) — Phase J 시리즈

## 폴더 성격

`integration/v2/`는 v2 디자인 prototype을 React + Babel(in-browser)로 신규 구축하는 폴더.
**v1(`../v1/dashboard.html`)은 fallback으로 유지**, v2/는 정본 트랙으로 진행.

## 절대 규칙

- ❌ **`../v1/dashboard.html` 기능 수정 금지** — fallback 안정성 우선. v2 작업이 어떤 단계에서 실패해도 v1 dashboard는 살아있어야 함
- ✅ **상대경로 수정만 허용** — 폴더 승격(`integration/` 루트화)·v1/v2 분리에 따른 경로 조정은 필수 (예: redirect·relation fetch·data fetch). 기능·렌더 로직은 불변
- ❌ **`../v1/extract_data.py` 로직 수정 금지** — JSON 스키마 단일 출처 (경로 조정은 예외)
- ✅ **공유 `data/*.json` 직접 fetch는 OK** — `../data/eqs_summary.json`(= `integration/data/`) 그대로 사용
- ✅ **v1 dashboard의 함수 포팅 OK** — `_calcValuation`/`_eqsNarration`/`_sparkline`/`_percentileBadge`를 ES module로 분리해 `v2/data/`에 두는 것만 허용
- ❌ **빌드 도구 도입 금지 (J1~J5 동안)** — Vite/esbuild 등은 5/8 마감 후 검토. 현재는 React-CDN + Babel-in-browser 유지

## firm 상세 iframe (CORPORATION DOSSIER)

ENTER CORPORATION 오버레이의 iframe은 **`../dossier/firm.html?ticker=<t>`** 를 로드한다(bundle.jsx). 과거 `../../docs/prototype/firm_<t>.html`(데이터 인라인 완성본)에서 **데이터 주도 단일 템플릿**으로 전환됨 (ARCHITECTURE 이슈 #2, integration-only). firm.html이 `./data/firm_<t>.json`을 fetch해 렌더.

- **`injectV2Theme()` 무변경** — firm.html은 기존 템플릿과 CSS 클래스(`.score-big`·`.grade-A`·`canvas[id]` 등)가 동일하므로 테마 주입이 그대로 작동. iframe same-origin(둘 다 `integration/` 하위)이라 `contentDocument` 접근 보장.
- 상세: [../dossier/](../dossier/) 와 [../v1/CLAUDE.md](../v1/CLAUDE.md) "firm 상세 도시에" 참조.

## 스택

- React 18 (UMD CDN)
- ReactDOM 18 (UMD CDN)
- Babel Standalone 7 (in-browser JSX transform)
- 빌드 도구 0건. `<script type="text/babel" src="./app.jsx">`로 직접 마운트
- 데이터: `Promise.allSettled` fetch + ticker 인덱싱 + mock fallback (J3 이후)

## 폴더 구조

```
integration/v2/
├── CLAUDE.md                 # 이 파일
├── README.md                 # 구동 안내
├── PROGRESS.md               # Phase J 시리즈 기록
├── index.html                # CDN + root div + loader/adapter/bundle 로드
├── src/                      # React 소스
│   ├── bundle.jsx            # standalone 포팅 통합 컴포넌트 (정본)
│   ├── adapter.js            # loader 결과 → standalone 글로벌 변환
│   └── galaxy.jsx · solar-system.jsx · companies.jsx · app.jsx
├── data/                     # wiring 모듈
│   ├── loader.js             # 4개 JSON fetch + ticker 인덱싱
│   ├── valuation.js          # _calcValuation 포팅
│   ├── narration.js          # _eqsNarration 포팅
│   └── mock.js               # fetch fallback용 mock 상수
├── assets/                   # 자산 (woff2 16, png 1, bin 1)
├── styles.css                # v2 CSS (46.6KB, 298 rules)
└── config.local.js(.example) # Gemini 키 (gitignored)
```

> **디코드 도구(`_decode/`)·구버전(`_archive/`)은 1회용이라 제거됨** (필요 시 git 이력에서 복원). 원본 standalone HTML과 추출 스크립트는 커밋 히스토리에 보존되어 있다.

## 컴포넌트 라이프사이클 (J1 현재 상태)

- ✅ **IntroScreen** — HudTop·HudRails·HudBottom·헤로 카피·ENTER CTA
- ⏳ **TopTabs** — J2
- ⏳ **MascotPanel / SectorPanel / SectorOverviewPanel / CompanyOverviewPanel / LegendPanel / AssistantPanel** — J3~J5
- ⏳ **Galaxy/Solar canvas 시각화** — J3 (현재는 빈 `<canvas className="galaxy-canvas">`)

## 데이터 정책 (1차)

| 항목 | 1차 | 후속 |
|---|---|---|
| 현재가 | "데이터 수집 중" 회색 뱃지 (가짜 숫자 노출 금지) | yfinance 1일 캐시 |
| 공시 시간 (14:32) | 날짜만 표시. 시:분 자리는 `--:--` | DART rcept_dt 분 단위 |
| AI Co-pilot | mock 메시지 + disabled 입력 | Gemini 키 모달 (dashboard 패턴) |
| SECTOR PULSE 차트 | mock + "예시 데이터" 워터마크 | price_scenarios 활용 계산 |
| DAILY HIGHLIGHTS | `disclosures.json` `high_impact=true` 최신 3건 (즉시 wiring) | — |
| 16 → 12 섹터 | top50.csv `sector` distinct count 자동 축소 | — |

## 향후 승격 경로

J5 안정화 후, dashboard.html을 `dashboard_legacy.html`로 archive하고 `v2/index.html`을 새 메인으로 승격. 빌드 파이프라인(Vite·esbuild) 도입은 그 이후.

## 마스코트 결정 보류

dashboard는 고양이(cat hop), v2는 우주인(astronaut "CADET LV.01"). 톤 일관성 vs 친근성 선택은 J6에서 결정.
