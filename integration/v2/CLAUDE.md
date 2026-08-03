# integration/v2/ — v2 React UI 신규 구축

> 이 파일은 `integration/v2/` 아래 작업 시 자동 로드됨 (Progressive Disclosure).
> 부모 규약: [../CLAUDE.md](../CLAUDE.md) (모듈 경계 예외 — 리더 소유 폴더, 타 모듈 read-only 접근 허용)
> 진행 기록: [PROGRESS.md](PROGRESS.md) — Phase J 시리즈

## 폴더 성격

`integration/v2/`는 React + Babel(in-browser)로 구축한 **유일 서빙 UI(정본)**.
(v1 vanilla 대시보드는 2026-07-13 폐지 — 파이프라인은 `../extract_data.py`로 승격, 원본은 git 이력 보존.)

## 절대 규칙

- ❌ **`../extract_data.py` 로직 수정 금지** — JSON 스키마 단일 출처 (경로 조정은 예외). 계약: [../CLAUDE.md](../CLAUDE.md)
- ✅ **공유 `data/*.json` 직접 fetch는 OK** — `../data/eqs_summary.json`(= `integration/data/`) 그대로 사용
- ✅ `v2/data/`의 `valuation.js`·`narration.js`는 구 v1 dashboard 함수의 포팅본(정본은 이제 이 폴더 — 원본은 git 이력)
- ❌ **빌드 도구 도입 금지** — Vite/esbuild 등은 추후 검토. 현재는 React-CDN + Babel-in-browser 유지
- ✅ **UI 작업 전 루트 [DESIGN.md](../../DESIGN.md) 준수** — 팔레트·토큰·폰트·엣지 규칙

## UX 원장 규율 (2026-07-22 신설 — 현금 은하수 VARIATIONS 선례 이식)

리더의 UI/UX 피드백·기각·재설계는 **[UX_DECISIONS.md](UX_DECISIONS.md)** 에 `UX-###` 번호로 채록한다:

1. **착수 전 필독(S0)**: v2 UI 작업 시작 전 원장을 읽는다 — **기각된 접근(예: UX-002 한 화면 병렬 성운)을 다시 제안하지 않기 위해**.
2. **작업 후 기록(S7)**: 리더 피드백으로 방향이 바뀌면 그 자리에서 항목 추가(일자·표면·피드백 요지→결정→적용 커밋·상태).
3. **2회 반복 = 승격**: 같은 판단이 2회 이상 재확인되면 [DESIGN.md](DESIGN.md)(v2 스펙)·루트 DESIGN.md 조문 또는 코드 게이트로 승격하고 `→ 조문화`/`→ 코드화` 표기. 원장은 이력, 스펙은 현재 상태 — 역할을 섞지 않는다.

> **기능 결정**(캐시버스트·폴백 사다리·NaN 크래시류)은 UI 원장이 아니라 [../DECISIONS.md](../DECISIONS.md)(`FN-###`) — 같은 규율, 층만 다름.

## CORPORATION DOSSIER 오버레이 — DOSSIER_TABS 탭바 (Phase 2, D1)

ENTER CORPORATION 오버레이는 **`DOSSIER_TABS` 설정 배열이 주도하는 탭바**를 가진다(bundle.jsx). 헤더와 본문 사이에 탭바(언더라인 스타일·mint 토큰), 본문은 활성 탭 iframe(keep-alive `display` 토글), 우측 `OverlayAiChat`(탭별 `context` 갱신)·하단 면책은 유지.

```js
const DOSSIER_TABS = [   // 순서 = 화면 탭 순서. 기본 랜딩 = dossierTab 초기값 'business'
  { id:'business', label:'사업·기업',   src:'business.html', context:'business', activeWhen:'always'  }, // ①
  { id:'galaxy',   label:'현금 은하수', src:'galaxy.html',   context:'galaxy',   activeWhen:'hasData' }, // ②
  { id:'eqs',      label:'EQS 재무분석', src:'firm.html',    context:'finance',  activeWhen:'always'  }, // ③
];
```
→ **탭 추가/재정렬 = 배열만 수정** (bundle.jsx 재수술 불요). `activeWhen:'hasData'`는 **매니페스트 `../dossier/data/galaxy_index.json`** 을 fetch한 `galaxyTickers`(state)로 판정, 없으면 "· 준비중" 비활성. **새 골든 추가 = `python integration/dossier/build_galaxy_index.py` 재실행**(galaxy_*.json 스캔 → 매니페스트 갱신)만으로 UI 자동 반영 — 코드 수정 불요. 현재 **12본**(000660·000720·005380·005930·010130·011200·012450·017670·033780·035420·051910·068270 — 매니페스트 실측 2026-08-03). 기본 탭은 `dossierTab` useState 초기값·`enterCorporation`·딥링크 리셋 3곳(모두 `'business'`).

- **탭① 사업·기업**: `../dossier/business.html?ticker=<t>` (kospi50_business_tabs 이식·데이터 구동, `business_<t>.json` fetch). **injectV2Theme 미적용** — 자체 `:root`(galaxy 토큰 스왑) + `tokens.css` 정적 link. rail·자체 3탭 제거, industryKey 우선순위 수정.
- **탭② 현금 은하수**: `../dossier/galaxy.html?ticker=<t>` (해방판 이식·데이터 구동, `galaxy_<t>.json` fetch). **injectV2Theme 미적용** — 자체 `:root`(Mint 표준) + `tokens.css`.
- **탭③ EQS**: `../dossier/firm.html?ticker=<t>&theme=galaxy` (데이터 주도 단일 템플릿, ARCHITECTURE 이슈 #2). **`injectV2Theme()` 미적용**(디자인 통일로 전환 완료) — firm.html이 `?theme=galaxy`면 `<html data-theme="galaxy">` + 자체 스코프 CSS(galaxy 헤더·mint 팔레트·IBM Plex Mono·Chart.js 색)로 셀프 테마. **v1(무파라미터)은 원본 인디고 룩 불변**(모든 오버라이드가 `[data-theme="galaxy"]` 스코프). `injectV2Theme` 함수는 잔존하나 호출 안 함(과거 #5eead4·Courier가 galaxy 표준과 어긋나 폐기).
- **성능(§8)**: 오버레이 열림 동안 `window.__dossierOpen` 플래그로 배경 캔버스 draw 루프 정지(rAF는 유지해 재개). 딥링크 `?corp=<ticker>`로 오버레이 직접 열기(로컬 테스트).
- 상세: [../dossier/](../dossier/) · [DOSSIER_TABS_PLAN](../dossier/DOSSIER_TABS_PLAN.md) Phase 2.

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

## 승격 완료 (2026-07-13)

v2/index.html이 유일 메인으로 승격 — `integration/index.html`이 직행 라우팅, v1 폴더는 삭제(git 이력 보존). 빌드 파이프라인(Vite·esbuild) 도입은 추후 검토.

## 마스코트 결정 보류

dashboard는 고양이(cat hop), v2는 우주인(astronaut "CADET LV.01"). 톤 일관성 vs 친근성 선택은 J6에서 결정.
