# integration/v2/ — v2 React UI 신규 구축

> 이 파일은 `modules/integration/v2/` 아래 작업 시 자동 로드됨 (Progressive Disclosure).
> 부모 규약: [../CLAUDE.md](../CLAUDE.md) (모듈 경계 예외 — 리더 소유 폴더, 타 모듈 read-only 접근 허용)
> 진행 기록: [PROGRESS.md](PROGRESS.md) — Phase J 시리즈

## 폴더 성격

`modules/integration/v2/`는 v2 디자인 prototype을 React + Babel(in-browser)로 신규 구축하는 폴더.
**dashboard.html은 5/8 데모 fallback으로 동결**, v2/는 별도 트랙으로 진행.

## 절대 규칙

- ❌ **`modules/integration/dashboard.html` 수정 금지** — 5/8 fallback. v2 작업이 어떤 단계에서 실패해도 dashboard는 살아있어야 함
- ❌ **`extract_data.py` 수정 금지** — JSON 스키마 단일 출처
- ✅ **`v2/data/*.json` 직접 fetch는 OK** — `../data/eqs_summary.json` 등 부모 폴더 JSON 그대로 사용
- ✅ **dashboard.html의 함수 포팅 OK** — `_calcValuation`/`_eqsNarration`/`_sparkline`/`_percentileBadge`를 ES module로 분리해 `v2/data/`에 두는 것만 허용
- ❌ **빌드 도구 도입 금지 (J1~J5 동안)** — Vite/esbuild 등은 5/8 마감 후 검토. 현재는 React-CDN + Babel-in-browser 유지

## 스택

- React 18 (UMD CDN)
- ReactDOM 18 (UMD CDN)
- Babel Standalone 7 (in-browser JSX transform)
- 빌드 도구 0건. `<script type="text/babel" src="./app.jsx">`로 직접 마운트
- 데이터: `Promise.allSettled` fetch + ticker 인덱싱 + mock fallback (J3 이후)

## 폴더 구조

```
v2/
├── CLAUDE.md                 # 이 파일
├── README.md                 # 구동·디코드 재현 절차
├── PROGRESS.md               # Phase J 시리즈 기록 (이번 PR에서 추가)
├── index.html                # CDN + root div + app.jsx 로드
├── app.jsx                   # type="text/babel". App + 16 컴포넌트
├── styles.css                # 디코드된 v2 CSS (46.6KB, 298 rules)
├── data/                     # J3 이후 채워질 wiring 모듈
│   ├── loader.js             # fetch + ticker 인덱싱 (예정)
│   ├── valuation.js          # _calcValuation 포팅 (예정)
│   ├── narration.js          # _eqsNarration 포팅 (예정)
│   └── mock.js               # fetch fallback용 mock 상수 (예정)
├── assets/                   # 디코드된 18개 자산 (woff2 16, png 1, bin 1)
└── _decode/                  # 1회용 디코드 도구 (read-only)
    ├── extract_v2_assets.py  # assets·raw_js 추출
    ├── patch_styles.py       # raw styleSheets dump → 정적 styles.css
    ├── raw_js/               # 7개 JS bundle (Babel·React·ReactDOM·tweaks-panel·app-code)
    ├── raw_styleSheets.css   # Playwright dump 원본
    ├── _uuid_map.json        # uuid → fname 매핑 캐시
    └── standalone-original.html  # 디자인 ref 원본
```

## 디코드 재현 절차

```bash
# 1. assets·raw_js 추출 (CSS는 인라인만 추출됨 — 854 bytes)
cd modules/integration/v2/_decode
python extract_v2_assets.py

# 2. styleSheets 본체는 Playwright로 dump (한 번만 수행, 결과는 raw_styleSheets.css에 보관)
#    아래는 1회용 — 새 standalone HTML이 들어올 때만 재실행:
#    a) python -m http.server 8000 (프로젝트 루트에서)
#    b) 브라우저로 http://localhost:8000/modules/integration/v2/_decode/standalone-original.html 열기
#    c) DevTools 콘솔에서 styleSheets 전체 cssText dump → raw_styleSheets.css에 저장

# 3. blob URL → 정적 ./assets/<fname> 치환
python patch_styles.py
# → ../styles.css 에 46KB 결과 (16/16 폰트 URL 매핑됨)
```

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
