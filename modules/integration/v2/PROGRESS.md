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
