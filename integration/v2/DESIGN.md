# DiscloseAI v2 — Design Spec & Logic Record

> **목적**: 이 문서는 v2 UI에 적용된 모든 디자인 결정·로직·수치를 기록한다.
> 다음 세션에서도 동일하게 재현·수정할 수 있도록 단일 출처(source of truth)로 유지.
>
> **수정 시**: 코드 변경과 함께 이 문서도 반드시 업데이트할 것.

---

## 1. 전체 디자인 원칙

- **standalone UI 시스템 보존**: 폰트·창·패널 레이아웃·canvas 그리기·전환·애니메이션은 절대 수정 안 함.
  원본 JSX(`src/bundle.jsx`) 자체가 standalone 코드 그대로.
- **어댑터 방향**: 데이터 → UI (UI가 기대하는 shape으로 우리 데이터를 변환).
  UI를 데이터 형태에 맞추지 않는다.
- **새 row·뱃지 추가 시**: standalone의 클래스·간격·타이포 토큰 재사용해 디자인 일관성 유지.

---

## 2. 색상 팔레트

### 섹터 색 — universe 25종 (2026-07-22 확장, UX-005)

**정본은 [adapter.js](src/adapter.js) `SECTOR_DEF`** (구 12종 표는 폐기 — 여기 복제하면 표류 재발).
색 = **패밀리(계열) 그룹핑**: 관련 산업끼리 인접 색상. 배정 절차·규칙은 루트 [DESIGN.md](../../DESIGN.md) §2.5.

| 패밀리 | 색 대역 | 섹터 |
|---|---|---|
| 테크·전자 | teal→cyan→blue | 반도체 · 전기전자부품 · 소재 · 플랫폼 · 통신 |
| 모빌리티·중공업 | violet→purple | 자동차 · 기계·장비 · 중공업·방산 · 철강·금속 |
| 금융 | amber→gold | 금융 · 지주 |
| 에너지·화학 | orange | 에너지 · 건설 · 화학 |
| 소비 | lime→green | 유통 · 식음료 · 레저·교육 |
| 헬스·뷰티 | pink→rose | 제약바이오 · 화장품 · 섬유·의류 |
| 미디어 | magenta | 미디어 |
| 서비스·중립 | 개별 | 운송·물류 · 부동산 · 전문서비스 · 기타 |

- 신규 섹터 = `SECTOR_DEF`(adapter.js)+`SECTOR_PALETTE`(bundle.jsx) **동시 추가** — 미등록 시
  extract_data.py **V-2 assert가 빌드 실패**로 차단(FN-002). 구 바이오/2차전지/디스플레이는 하위호환 잔존(미사용).

### 관계 유형 색 (REL_STYLES in bundle.jsx)

| 유형 | 영문 key | 색 | 선 스타일 | 화살표 |
|---|---|---|---|---|
| 종속기업 | `subsidiary` | `#5eead4` | 실선 `[]` | ✅ outgoing → |
| 관계기업 | `associate` | `#a78bfa` | 실선 `[]` | ✅ outgoing → |
| 유의적 투자 | `significant` | `#fbbf24` | 실선 `[]` | ✅ outgoing → |
| 계열사 | `group` | `#94a3b8` | 점선 `[6,4]` | ❌ |
| 특수관계자 | `related` | `#f472b6` | 점선 `[2,3]` | ❌ |
| 수동 보정 | `manual` | `#64748b` | 점선 `[1,4]` | ❌ |

### UI 기본 색

| 용도 | 값 |
|---|---|
| 배경 | `#020408` |
| 패널 배경 | `rgba(8,14,26,0.9)` |
| 패널 테두리 | `rgba(94,234,212,0.18)` |
| 액센트 (cyan) | `#5eead4` |
| 보조 액센트 | `#a78bfa` |
| 텍스트 주 | `#e2e8f0` |
| 텍스트 보조 | `#94a3b8` |
| 텍스트 희미 | `#64748b` |

---

## 3. 관계 그래프 — SectorMap 드릴인 LOD + EgoView

### 3-0. LOD 구조 (2026-07-22~28 개편 — UX-003·UX-010 현행)

```
galaxy(SolarSystem) → 섹터 성운 개요(KOSPI/KOSDAQ 프록시 2노드 + dots)
  → 시장 드릴인(시총 top-10 named + 배경 dots)          ← SectorMap
    → 기업 선택 = EgoView (ego/<ticker>.json 1-hop 재구성)  ← LOD-2, §3-7
```

- **한 화면 = 한 초점**(UX-001·002). 브레드크럼 `GALAXY › 섹터 › 시장 › 기업`.
- 배경 dots도 1급 시민: hover 툴팁·클릭 진입, 활성화 시 노드 승격(UX-009).
- 패널 콘텐츠는 LOD 모드를 따라감 — 드릴인에선 그 시장 기업 목록(UX-008).
- **§3-3 allRelated 폴리곤은 company phase의 기본 렌더에서 은퇴** — ego fetch 실패 시
  폴백으로만 동작(UX-010, FN-005 사다리). §3-1·3-4~3-6 시각 문법은 EgoView가 그대로 계승.

### 3-1. 관계 유형 우선순위

동일 기업에 복수 관계 유형(예: associate + ftc_group)이 있을 때:
```
subsidiary(1) > associate(2) > significant(3) > group(4) > related(5) > manual(6)
```
가장 낮은 번호 = 가장 significant한 관계를 primary type으로 선택.
`hasGroup`, `hasEquity` 플래그는 모두 보존.

### 3-2. 양방향 관계

- **outgoing** (A→B): A가 B를 보유 → 화살표가 B 방향
- **incoming** (A←B): B가 A를 보유, A 입장에서 역방향 → 화살표가 A 방향
- `adapter.js buildRelations()`: forward pass 후 reverse edge 자동 생성 (`isIncoming: true`)
- Reverse edge의 type = forward edge의 type 그대로 보존 (이전엔 `group`으로 flatten하다 수정됨)

### 3-3. 노드 배치 (allRelated polygon) — **폴백 전용 (2026-07-28, UX-010)**

모든 관계기업(in-sector + cross-sector 구분 없이)을 **canvas center 기준 polygon**에 배치:
```js
radius = Math.min(0.88, 0.60 + n * 0.032)  // n = 관계사 수
startAng = -Math.PI / 2                      // 첫 노드는 상단(12시 방향)
ang[i] = startAng + (i / n) * Math.PI * 2
gx = Math.cos(ang) * radius
gy = Math.sin(ang) * radius
```
- active company의 위치에 관계없이 항상 canvas 내 균등 배치
- n이 늘수록 radius 자동 확장으로 arc-spacing 유지

### 3-4. 선 스타일 규칙

**단일 관계 유형**:
```
equity(subsidiary/associate/significant) → 실선(lineWidth:2) + 화살표(size:14)
group/related/manual → 점선(dash pattern) + 화살표 없음
```

**복수 유형(equity + group 동시)**:
```
+4px perpendicular offset으로 평행 이중선:
  - 실선 (equity, offset +2px): 화살표 포함
  - 점선 (group, offset -2px): 화살표 없음
```

### 3-5. 화살표 규칙

| 상황 | 화살표 위치 | 크기 |
|---|---|---|
| Outgoing (A→B) | 관계사 노드 쪽 | 14px |
| Incoming (A←B) | active 노드 바깥 경계면 (`nodeR * 1.4`) | 14px |
| Group/계열사 | 없음 | — |

화살표 형태: isosceles triangle, angle ±0.42 rad

### 3-6. 노드 색 규칙

| 요소 | 색 |
|---|---|
| 관계 노드 glow + core | **관계기업의 섹터 색** (SECTOR_PALETTE 조회) |
| 관계 엣지 선 + 화살표 | **관계 유형 색** (REL_STYLES 조회) |
| 섹터 내 active 기업 노드 | 현재 섹터 색 |
| 관계 노드 라벨 | 섹터 색 (노드와 동일) |
| 관계 유형 라벨 | `#64748b` (희미한 회색) |

### 3-7. EgoView — LOD-2 지배구조 셸 (2026-07-28 신설, universe/PLAN.md §5)

기업 선택 시 기본 렌더. `ego/<ticker>.json` 지연 fetch(세션 캐시) → 앵커 중앙 1-hop 재구성 뷰.
universe **전 상장사 2,651본** 커버 (allRelated는 top50 상호 간만 — §3-3 폴백).

**축 문법 (UX-011) — 축의 의미 = 관계의 성질**:

| 축 | 의미 | 대상 | 배치 |
|---|---|---|---|
| 세로 | **위계 있음** (출자 방향) | 지분 엣지 보유 이웃 | 위=나를 출자(in) / 아래=내가 출자(out), `gy=±0.62` 행 |
| 가로 | **위계 없음** | 순수 비지분 이웃 | 좌=계열사(파선) / 우=특수관계자·기타(점선), `gx=±0.86` 열 |

- **지분이 하나라도 있으면 세로** — 계열·특수관계는 이중 평행선으로 같은 엣지에 얹음(§3-4 계승).
  세로 방향은 **primary(최우선) 지분 타입의 dir** — 첫 엣지 dir을 쓰면 순서 종속(하네스 V-3 설계 중 발견·수정).
- 가로 엣지는 **화살촉 없음** — 방향 없는 관계임을 형태로 표현.
- 표시 한도: 세로 사이드당 **Top-N 6** / 가로 사이드당 **4** (`tier→type→지분율` 랭킹),
  잔여는 "○○ 외 n사" 묶음 노드 → 클릭 시 하단 팝오버 리스트(행 클릭 = re-root).
- **re-root**: 이웃 클릭 = 앵커 재구성(크로스섹터 자동 점프). 이력은 상단바 `← 직전기업` 버튼 하나로 축약
  — 브레드크럼 나열은 무한 증식이라 기각(UX-012). 상단바 = 레이어 토글 2개(지배구조 활성 / 밸류체인 U3 대기) 전용.
- **밸류체인 레이어 (U3 활성, 2026-07-28 — UX-013·014·015)**: 상/하 = **흐름(type)에서 파생**(supply=공급처=위 / customer=고객사=아래 — up/down 배열은 미러 기록이라 무시), (상대,type) 병합=최신 as_of. 문법(U-D14): 색=**은백 `#e8f1ff` 단일**(3축 미충돌) + 선=신뢰등급 + **오픈 셰브런**=흐름 위→아래. 노드색=섹터색 유지, **노드 크기=신뢰등급**(T1 크게/T2 작게+빈 테두리). 가로축 없음. 토글=데이터 보유 기업만 활성(현 T1 509사), 범례는 FLOW TYPOLOGY로 통째 교체(혼합 금지).
  - **레일 토폴로지(UX-015)** — 방사형이 아니다. 바깥부터 `기업(세로 스택 1행 1사) → 산업 라벨(N사·금액) → 레일 → 트렁크 → 앵커`. 기업마다 앵커까지 선을 뽑지 않는다. 캡=**산업군 5 · 그룹당 4사**(그룹 순서=최상위 멤버 랭킹), 초과는 "외 n개 산업" 묶음.

```
   [기업] [기업] [기업]        ← 세로 스택 (1행 1사, 노드 우측에 이름·금액)
   반도체 5사·7,469억           ← 산업 라벨 + 집계
   ├──────┴──────┤            ← 레일
          │ 공급처              ← 트렁크 (셰브런 = 흐름 방향)
       ● 앵커
          │ 고객사
   ├──────┬──────┤
```
- ego fetch 실패 → §3-3 allRelated 폴백(UX-010). 캔버스 사이징은 **JSX 인라인 고정**(FN-009 — 스타일시트 캐시에 레이아웃을 의존시키지 않는다).
- 기계 검증: `window.__egoDebug`(분할 상태)·`window.splitEgoSides` 노출 → **V-3 하네스**
  ([../qa/v3_harness.py](../qa/v3_harness.py))가 JSON 도출 기대값과 실화면 대조. U2 게이트 실행 수단.

---

## 4. 섹터 칩 (SECTOR INDEX / LIST)

### 4-1. 레이아웃 (CSS override in index.html)

```css
/* 4-column 단일 행: dot | EN | KO뱃지 | 시총 */
.sector-chip {
  grid-template-columns: 8px 1fr auto auto;
  grid-template-rows: auto;
}
.sector-chip .sector-ko {
  background: color-mix(in oklab, var(--c) 14%, transparent);
  border: 1px solid color-mix(in oklab, var(--c) 40%, transparent);
  border-radius: 2px;
  padding: 1px 5px;
}
```

### 4-2. 원인

원본 CSS의 두 규칙이 `sector-en`과 `sector-ko` 모두 `grid-area: 1/2 !important`로 강제 → 겹침.
index.html에서 4컬럼 단일행으로 override.

---

## 5. 패널 시스템

### 5-1. 패널 폭

| 패널 | 폭 |
|---|---|
| TL (MISSION GUIDE / SECTOR OVERVIEW / COMPANY DOSSIER) | `320px !important` |
| BL (EDGE TYPOLOGY) | `320px` (legend-panel override) |
| TR (AI FINANCIAL) | `300px` (기본) |
| BR (SECTOR INDEX/LIST) | `300px` (기본) |

### 5-2. 헤더 텍스트 줄바꿈 방지

```css
.panel-head { flex-wrap: nowrap; }
.panel-head-l { min-width: 0; overflow: hidden; }
.panel-title, .panel-sub, .panel-count { white-space: nowrap; }
```

### 5-3. 패널 헤더 텍스트

| 패널 | title | sub/count |
|---|---|---|
| 마스코트 | `MISSION GUIDE` | count: `우주비행사 · LV.01` |
| AI 패널 | `AI FINANCIAL` | sub: `Gemini · 한·영 v2.4` |
| 섹터 개요 | `SECTOR OVERVIEW` | sub: `섹터 개요` |
| 기업 도시에 | `COMPANY DOSSIER` | sub: `기업 개요` |

---

## 6. Company Dossier 패널 구조

섹션 순서 (위→아래):
1. **Hero** — 기업명 / 영문명 / KOSPI·ticker·섹터
2. **밸류에이션** — 시가총액(실값) / PER / PBR / ROE(색: 양수=green, 음수=red)
3. **현재가** — "데이터 수집 중" 회색 badge (`yfinance pending`)
4. **FINANCIALS** — 매출 / 영업이익 / 영업이익률(%) / 부채비율(%) / 영업CF / 투자CF + Sparkline + 백분위 뱃지
5. **EQS** — 등급·총점 + M1(현금) / M2(매출) / M3(부채) / M4(본업) / M5(자본) + 면책
6. **RECENT DISCLOSURES** — 최신 3건, high_impact=빨간 날짜
7. **RELATED ENTITIES** — 관계사 목록 (REL_STYLES 색·스타일)
8. **ENTER CORPORATION** — 오버레이 버튼

### 6-1. Sparkline

```js
D.sparklinePath(node.history.revenue, { w: 72, h: 16, pad: 1 })
// SVG path + dot 반환, stroke: #5eead4
```

### 6-2. 백분위 뱃지

```js
D.percentileBadge(node.percentile?.eqs_total, sector.memberCount)
// { topPct, color, label: "업계 상위 N%" }
// color: top30=green, top70=amber, else=red
```

---

## 7. ENTER CORPORATION 오버레이 — CORPORATION DOSSIER 3탭 (2026-07 개편)

- `position: fixed; inset: 0; z-index: 999`
- 배경: `rgba(2,4,12,0.88) + backdropFilter: blur(18px)`
- 헤더: cyan dot + `CORPORATION DOSSIER` + ticker, `✕ CLOSE` 버튼
- 본문: **`DOSSIER_TABS` 설정 배열 주도 탭바**(bundle.jsx) — ① 사업·기업 `../dossier/business.html?ticker=<t>` ② 현금 은하수 `../dossier/galaxy.html?ticker=<t>`(galaxy_index.json 매니페스트 판정 — 현재 6본) ③ EQS `../dossier/firm.html?ticker=<t>&theme=galaxy`. iframe keep-alive `display` 토글. 우측 `OverlayAiChat`(탭별 context) 고정.
- 푸터 면책: `⚠ 과거 통계 기반 참고 정보 — 투자 조언 아님`
- 상세: [CLAUDE.md](CLAUDE.md) "CORPORATION DOSSIER 오버레이" · [integration/dossier/DOSSIER_TABS_PLAN.md](../dossier/DOSSIER_TABS_PLAN.md)

### 7-1. iframe CSS 주입 (injectV2Theme) — **폐기(2026-07, 3탭 디자인 통일)**

구 방식(`../../docs/prototype/firm_<ticker>.html` 임베드 + `onLoad` CSS 주입)은 dossier 3탭 전환으로 폐기.
firm.html이 `?theme=galaxy` 파라미터로 `<html data-theme="galaxy">` 스코프 CSS 셀프 테마(mint 팔레트·IBM Plex Mono). `injectV2Theme` 함수는 bundle.jsx에 잔존하나 호출되지 않음. 아래 표는 이력 보존용.

| 요소 | (구) 변경 내용 |
|---|---|
| `body` 배경 | `#020408` (보라 nebula 제거) |
| `.panel` | dark glass + cyan 테두리 + border-radius: 2px |
| `.score-big` | cyan→보라 gradient text |
| 별/행성 장식 `canvas, .planet` | `display: none` |
| `font-family` | monospace for scores |

---

## 8. 우주인 마스코트

PNG 파일(`assets/astronaut.png`)이 dark-themed (평균 R값 41/255).
CSS filter로 밝게:
```css
.mascot-img { filter: invert(0.88) brightness(1.15) saturate(0.6); }
```

---

## 9. SectorMap 인터랙션 규칙

| 동작 | 결과 |
|---|---|
| 빈 캔버스 클릭 | 기업 선택 해제 → sector 화면 복귀 |
| 기업 노드 클릭 | company phase 진입, 해당 기업 active |
| 관계 노드 클릭 | 해당 기업 섹터로 이동 + 그 기업 선택 상태 |
| 기업 hover | cursor: pointer |
| 기업 선택 시 | 비관계 in-sector 노드 완전 숨김(opacity 0) |

### 9-1. Hover 구현 주의사항

`hoverCode` state를 `useEffect` deps에 넣으면 hover마다 전체 animation loop 재시작 → 노드 위치 리셋 → 클릭 불가.

**해결**: `hoverRef` (useRef)로 draw loop 내 판정, `setHoverCode`(state)는 DOM label 전용.
`useEffect` deps에서 `hoverCode` 제외.

---

## 10. GitHub Pages 배포 설정

```html
<!-- index.html viewport -->
<meta name="viewport" content="width=device-width, initial-scale=1.0,
  minimum-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no" />
```

```css
/* index.html <style> */
html {
  box-sizing: border-box;
  font-size: 16px;
  text-size-adjust: 100%;
  -webkit-text-size-adjust: 100%;
}
html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
```

### 진입점 (2026-07-13 v1 폐지 후)

`integration/index.html`이 v2로 직행 redirect:
```js
<script>window.location.replace('./v2/index.html');</script>
```
(과거: index → v1/dashboard.html → 비localhost면 v2 — v1 폐지로 단순화)

---

## 11. 데이터 어댑터 (adapter.js) 핵심 로직

### 11-1. 섹터 집계

`loader.js aggregateSectors()`:
- `n.s` (sector 한글명) 기준 groupBy
- `market_cap` (원) 합산 → 조 단위 변환
- `cap` = `Math.max(1, Math.round(totalJo))`

### 11-2. 기업 레이아웃 (phyllotaxis)

```js
// 가장 큰 cap이 center (i=0), 나머지는 golden angle 배치
ang = i * 2.39996               // golden angle
r   = 0.45 + ((i-1) / (n-1)) * 0.43  // min 0.45, max 0.88
gx = cos(ang) * r
gy = sin(ang) * r
cap = Math.min(600, market_cap / 1e12)  // cap 600T 상한
```

### 11-3. 관계 역방향 (reverse edges)

```js
// forward pass 완료 후:
for (srcCode, rels of forward) {
  for r of rels:
    if (!out[r.code].some(x => x.code === srcCode)):
      out[r.code].push({ code: srcCode, type: r.type, isIncoming: true })
}
```

### 11-4. 관계 유형 매핑

| graph_top50 `rl` type | RELATIONS type |
|---|---|
| `subsidiary` | `subsidiary` |
| `associate` | `associate` |
| `investment` | `significant` |
| `ftc_group` | `group` |

---

## 12. 변경 이력 (주요)

| 날짜 | 항목 | 내용 |
|---|---|---|
| 2026-05-06 | K1 | standalone JSX 4개 → src/bundle.jsx concat, adapter.js 주입 |
| 2026-05-06 | PR-F | 실데이터 wiring, 12섹터 / 50기업 |
| 2026-05-06 | PR-G | Company Dossier EQS·재무·sparkline·백분위 |
| 2026-05-06 | PR-H | DAILY HIGHLIGHTS (high_impact 공시) |
| 2026-05-06 | PR-I | ENTER CORPORATION 인페이지 오버레이 |
| 2026-05-06 | fix | sector chip EN+KO 겹침 → 4컬럼 단일행 |
| 2026-05-06 | fix | hover 시 animation loop 재시작 → hoverRef 분리 |
| 2026-05-06 | feat | 관계 그래프: polygon, 화살표, 이중선, 섹터 색 노드 |
| 2026-05-06 | feat | iframe v2 다크 테마 CSS 주입 |
| 2026-05-06 | fix | GitHub Pages 레이아웃 정규화 |
| 2026-07-22 | feat | universe 이전: 25섹터(패밀리 색)·named 400·드릴인 LOD(UX-001~004)·dots 1급 시민(UX-009) |
| 2026-07-28 | feat | EgoView LOD-2 신설 (§3-7) — ego 1-hop·re-root·묶음 노드·allRelated는 폴백(UX-010) |
| 2026-07-28 | feat | 축 재정의: 세로=지분 위계 / 가로=비지분(좌 계열·우 특관), 화살촉 없음 (UX-011) |
| 2026-07-28 | fix | 상단바 토글 2개 전용 — re-root 이력은 뒤로 버튼으로 축약 (UX-012) |
| 2026-07-28 | fix | CSS 캐시버스트 도입·캔버스 인라인 사이징 (FN-009) · dart_filing 카테고리 복구 (FN-010) |
| 2026-07-28 | test | V-3 렌더 하네스 (qa/v3_harness.py) — 시나리오 3종 자동선정·오라클 대조·뮤테이션 캘리브레이션 |
| 2026-07-28 | feat | U3: 밸류체인 토글 활성 — 은백 흐름색·셰브런·신뢰등급 선·FLOW 범례 교체·V-3 VC 검증 55/55 (UX-013·014) |
| 2026-07-28 | feat | 밸류체인 레일 토폴로지 — 산업군 묶음(캡 5×4)·세로 스택·노드 크기=신뢰등급, V-3 61/61 (UX-015) |

> 이 표는 스펙 관점 요약. 결정·기각의 전말은 [UX_DECISIONS.md](UX_DECISIONS.md)(UX-###)·[../DECISIONS.md](../DECISIONS.md)(FN-###)가 정본.
