# Integration v2 진행경과

> 부모 진행 기록: [../PROGRESS.md](../PROGRESS.md) (Phase A~I, dashboard.html 트랙)
> v2 트랙: Phase J 시리즈

## 2026-05-05 (Phase J1 — 디코드 + 폴더 골격 + IntroScreen)

- **목적**: v2 prototype standalone HTML(2MB minified bundle, React+Babel)을 modules/integration/v2/에 분리해 점진적 React UI로 신규 구축. **CSS·assets·DOM 클래스명은 보존, React 컴포넌트는 신작**.
- **작업 브랜치**: `feat/integration-v2` (분기 안 함). dashboard.html 무변경.

### Stage 1 — 폴더 + 원본 보관
- `modules/integration/v2/` + `_decode/` + `assets/` + `data/` 디렉터리 생성
- `DiscloseAI v2 - standalone (1).html` 2MB → `_decode/standalone-original.html`로 cp 보관

### Stage 2 — 디코드 (assets·raw_js 추출)
- `_decode/extract_v2_assets.py`: `<script type="__bundler/manifest">` JSON 파싱 → 각 entry base64 + `gzip.decompress` → MIME으로 분류
- 산출물:
  - `assets/` 18 파일 — woff2 16개(Inter·JetBrains Mono·Space Grotesk 3 family × 다중 weight × 7 unicode-range subset), astronaut.png 1, bin 1
  - `_decode/raw_js/` 7개 — Babel 3.1MB + ReactDOM 1MB + React 110KB + tweaks-panel 32KB + app code 후보 셋(16+14+12 = 42KB)
- CSS asset은 manifest에 없음 (인라인 `<style>` 854 bytes만)

### Stage 3 — 진짜 CSS 본체 dump (Playwright styleSheets)
- v2의 진짜 CSS는 React runtime이 inject한 styleSheet에 있음 (98 + 237 = 298 rules, 49KB)
- Playwright로 standalone을 띄워 `document.styleSheets` 전체 cssRules cssText dump → `_decode/raw_styleSheets.css`
- 모든 `blob:http://localhost:.../<UUID>` 폰트 url은 페이지 runtime이 만든 임시 UUID(우리 manifest UUID와 다름)
- 16개 blob URL의 `byteLength`를 페이지에서 fetch로 받아 우리 디코드된 woff2 size와 1:1 매칭 (16/16 unique sizes)

### Stage 4 — patch_styles.py + 정적 경로 치환
- `_decode/patch_styles.py`: raw dump JSON-unescape (`\\n` → `\n`, `\\"` → `"`) + 16개 blob URL → `./assets/<fname>.woff2` 치환
- 산출물: `v2/styles.css` 46,647 bytes (298 rules + 헤더 + 16/16 폰트 매핑)

### Stage 5 — index.html + app.jsx 1차
- `index.html`: React 18 + ReactDOM 18 + Babel 7 CDN, `<link rel="stylesheet" href="./styles.css">`, `<script type="text/babel" data-presets="env,react" src="./app.jsx">`
- `app.jsx` 1차 (164줄):
  - `App` 컴포넌트 — `phase` state ('intro' | 'tab') + `tElapsed` T+초 카운터 + `useNowUtc` hook
  - `IntroScreen` — HudTop(브랜드+SESSION/UPLINK/UTC) + HudRails(SECTORS·PLANETS·EDGES·LIVE PULSES + RA·DEC·Z·T) + HudBottom(OBSERVATORY ONLINE 푸터) + 헤로 카피 + ENTER CTA
  - `FinanceTabPlaceholder` — J2 진입 안내 (placeholder-tab 클래스)

### 검증
- localhost http.server 8765 (이미 띄워둔 backgrounded `b8z0v8k0b`)
- `http://localhost:8765/modules/integration/v2/index.html` 로드:
  - 콘솔 errors **0**, warnings 1개 (Babel "in-browser transformer" 권고, 무시 가능)
  - DOM: `#root > div.app.phase-intro.tone-glass` 정상 마운트
  - styleSheet 1개 link · cssRules 298개 모두 적용
  - `getComputedStyle`: html/body/#root/.app 모두 `background: rgb(0, 0, 0)` ✓
  - `.intro-headline` font-family: `"Space Grotesk", Pretendard, ...` ✓ (디코드된 woff2 정상 로드)
  - `.intro-headline` color: `rgb(255, 255, 255)` ✓
- 시각 차이: standalone에는 인트로 갤럭시 SVG/canvas 텍스처가 있고, v2는 빈 `<canvas className="galaxy-canvas">`. **J2에서 갤럭시 시각화 추가 예정** (J1 의도는 골격만)
- dashboard.html: `git diff modules/integration/dashboard.html` 빈 결과 ✓

### 미해결 / J2 인계
- 갤럭시 SVG/canvas 시각화 (인트로·메인 양쪽)
- TopTabs(FINANCIALS·DISCLOSURES·TIME MACHINE) + breadcrumb
- DISCLOSURES/TIME MACHINE 탭의 placeholder-tab "UNDER CONSTRUCTION" 화면 동일 재현
- Mascot panel 우주인 + 모드별 말풍선

### 명시적 비범위 (J2 이후)
- 데이터 wiring (loader.js·valuation.js·narration.js)
- Company Dossier·Sector Overview real data
- ENTER CORPORATION → firm_<ticker>.html iframe

## 2026-05-06 (Phase J2 — TopTabs + Galaxy/Solar canvas + UC placeholder)
- App에 phase('intro'|'tab') + activeTab + activeSectorId state 추가
- GalaxyCanvas: Canvas2D 별 + radial 갤럭시 디스크 + dust 회전 (인트로·phase-tab 공통 배경)
- SolarCanvas: 12개 섹터 행성 두 링 분배 + 회전 + 클릭 hit-test
- TopTabs: 3 탭(FINANCIALS·DISCLOSURES·TIME MACHINE) + breadcrumb + KOSPI live mock
- PlaceholderTab: DISCLOSURES/TIME MACHINE은 "UNDER CONSTRUCTION" + BACK 버튼
- 검증: 콘솔 errors 0 / canvas 2개 / 3 탭 전환 정상 / dashboard.html 무변경
- commit `3fe6caa`

## 2026-05-06 (Phase J3 — data layer + 4 패널)

데이터 wiring:
- `data/valuation.js` — calcValuation(PER/PBR/ROE) + percentileBadge + trillionFmt/Label + sparklinePath (dashboard L4844-4920 포팅)
- `data/narration.js` — eqsBucket + eqsNarration 5모듈×3단계 + EQS_MODS 라벨·색상 + gradeColor
- `data/mock.js` — SECTOR_META 12종(한글→영문/색상) + EDGE_LEGEND + MOCK_NODES + KOSPI_MOCK
- `data/loader.js` — Promise.all 4 fetch + ticker 인덱싱 + enrichNode + aggregateSectors + dailyHighlights/highlightsForSector
- `index.html` — data scripts 4개 일반 script 로드 (Babel 전, window.DiscloseAI에 export). ?v=j5 cache-bust 파라미터.

Galaxy 단계 패널:
- MascotPanel (panel-tl): 우주인 PNG + 모드별 말풍선 + 별 트윙클 + Cadet LV.01
- AssistantPanel (panel-tr): mock AI Co-pilot 메시지 (stage별) + disabled input + 면책 문구
- LegendPanel (panel-bl): EDGE TYPOLOGY (K-IFRS solid 3 + dashed 비-지분 3)
- SectorPanel (panel-br): 12 섹터 chip (top50.csv distinct 자동) + 활성 표시

SolarCanvas: real-data sectors prop 기반 (memberCount 비례 행성 크기)
- commit `348022e`

## 2026-05-06 (Phase J4 + J5 — Sector Overview + Company Dossier + ENTER CORPORATION)

### Stage 1 — SolarStage 일반화 (J4 기반)
- SolarCanvas → SolarStage로 rename. stage prop ('galaxy'|'sector'|'company')으로 다양한 planets 처리.
- galaxy: 12 sectors / sector: 해당 섹터의 회사 노드 / company: 회사 + rl 관계기업 5건
- 회사 stage에선 행성 아래 라벨(회사명) 출력. 중심 별은 sector 색.

### Stage 2 — SectorOverviewPanel (J4 본체)
- panel-tl 위치 (galaxy 단계 MascotPanel 대체)
- Sector hero: orb + 영문/한글 + 시총·기업수·YTD(mock)·P/E(mock)
- DAILY HIGHLIGHTS · 해당 섹터 high_impact 우선, 없으면 최근 공시 fallback (현재 데이터에 high_impact 단 1건뿐이라 fallback 필수)
- SECTOR PULSE — 12개 mock 막대 + "예시 데이터" 워터마크
- ← GALAXY back-link

### Stage 3 — CompanyOverviewPanel (J5 본체)
- panel-tl 위치 (sector→company 진입 시 SectorOverviewPanel 대체)
- Hero: orb + 회사명 + KOSPI · ticker · 섹터
- 시총 / PER / PBR / ROE — `_calcValuation` 포팅 + percentile.roe 우선·statements[0].roe·calcValuation 순 fallback + toFixed(1) 정규화
- **현재가 자리 "실시간 데이터 수집 중" 회색 뱃지** (가짜 숫자 노출 금지 — 사용자 정책)
- RECENT DISCLOSURES · `discByTicker[t].slice(0,3)` (날짜만, 시:분 자리 없음)
- RELATED ENTITIES · n.rl 4건 (관계 유형별 색상 dot — 종속/관계/유의/계열/특수)
- ENTER CORPORATION CTA → 새 창에서 `../../../docs/prototype/firm_<ticker>.html` 열기 (47개 회사만 존재)
- ← SECTOR back-link

### Stage 4 — App + breadcrumb 확장
- activeCompanyCode state 추가
- breadcrumb 3단 (GALAXY › 섹터 › 회사) — 클릭 시 해당 단계로 복귀
- handlePickSector·handlePickCompany·handleBackToGalaxy·handleBackToSector·handleEnterCorp 핸들러 분리
- dev/QA hook (`window.__v2_dev`) — 회전 SolarStage hit-test가 어려워 외부 자동화에서 직접 호출용

### Polish
- `valuation.trillionLabel` — 1000+조도 `1,461T`처럼 toLocaleString으로 표시 (이전 `1K T` 어색)
- ROE — `+Number(v).toFixed(1)`로 정규화 (statements[0].roe 원본은 raw float)
- index.html — data scripts에 ?v=j5 cache-bust 파라미터 (dev 환경 새 버전 강제 로드)

### 검증 (Playwright E2E, dev hook 활용)
- Intro → ENTER → Galaxy phase ✓
- SECTOR INDEX 12 칩 노출 (반도체 2,614T 합산) ✓
- 첫 칩 클릭 → SectorOverviewPanel 노출 + breadcrumb [GALAXY, 반도체] ✓
- DAILY HIGHLIGHTS 3건 (high_impact 매칭 0건이면 최근 공시 fallback)
- SECTOR PULSE 12 막대 + "예시 데이터" 워터마크 ✓
- BR panel 라벨 "SECTOR LIST" (galaxy 단계는 "SECTOR INDEX") ✓
- `__v2_dev.pickCompany('005930')` → CompanyOverviewPanel 노출
  - 시총 1,461T / PER 32.3 / PBR 3.35 / ROE 10.4% ✓
  - 현재가 "실시간 데이터 수집 중" 뱃지 ✓
  - 최근 공시 3건 ✓ / 관계기업 4건 ✓
  - breadcrumb [GALAXY, 반도체, 삼성전자] ✓
- ENTER CORPORATION 클릭 → window.open URL = `../../../docs/prototype/firm_005930.html` ✓
- 콘솔 errors 0 / dashboard.html `git diff --stat` 빈 결과

### 명시적 비범위 (후속 phase)
- **현재가 yfinance 연동** — 1차는 뱃지로만
- **AI Co-pilot Gemini 실 연결** — 1차는 mock 메시지 그대로, disabled input
- **DISCLOSURES / TIME MACHINE 탭 본체 구현** — 1차는 UC placeholder 유지
- **회사 → 관계기업 행성 클릭 시 그 기업으로 이동** — J6 이후
- **firm_<ticker>.html iframe 풀스크린 overlay** — 1차는 새 창. iframe overlay는 dashboard 풀스크린 패턴 차용해 후속에 추가
- **`window.__v2_dev` 디버깅 hook 제거** — 마감 직전 production 빌드에서 정리

---

## 2026-07-11 — CORPORATION DOSSIER 3탭 전환 (DOSSIER_TABS Phase 0~S2 요약)

- ENTER CORPORATION: 새 창(`window.open`) → **iframe 오버레이 + `DOSSIER_TABS` 탭바** 전환 완료 — ① 사업·기업(business.html) ② 현금 은하수(galaxy.html, 005930만) ③ EQS(firm.html?theme=galaxy)
- `injectV2Theme()` 폐기 — firm.html `[data-theme="galaxy"]` 스코프 셀프 테마 + dossier 공용 `tokens.css`
- 커밋: 46b3e5e(Phase 0 골든·토큰) · 1ff6dab(Phase 1 galaxy 데이터 구동) · 1b534da(Phase 2 탭바) · 890241e(S2 business 이식) · 04a59d5(3탭 디자인 통일) · 472d6cd(로고·AI 사이드바 토글)
- 상세 계획·설계 결정: [docs/DOSSIER_TABS_PLAN.md](../../docs/DOSSIER_TABS_PLAN.md) (본 파일은 요약만 기록)
