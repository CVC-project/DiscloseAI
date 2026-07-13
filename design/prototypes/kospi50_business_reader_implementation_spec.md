# 국내상장기업 사업보고서 reader — 구현 확정 명세서

> **이 문서의 목적**: `docs/prototype/kospi50_business_tabs.html` 완성본을 기준으로, 지금까지 구현한 기능·화면 구성·데이터 구조·CSS/JS 렌더링 규칙을 코드 수준으로 정리한 문서입니다. 이 문서만 보고도 로컬 IDE에서 동일한 프로토타입을 재구현할 수 있어야 합니다.
>
> **대상 HTML**: `docs/prototype/kospi50_business_tabs.html`
>
> **생성 스크립트**: `scripts/build_kospi50_business_reader.py` → `scripts/build_kospi50_business_reader.mjs` → HTML 출력
>
> **기술 스택**: 단일 HTML 파일, 인라인 CSS, 바닐라 JavaScript, 외부 프레임워크 없음. 데이터는 HTML 내부의 `DATA` 상수로 포함합니다.

---

# PART 1 — 최종 확정 방향

## 1-1. 화면의 목적

이 화면은 EQS나 재무제표 분석 탭이 아니라, **상위 국내 상장기업의 사업보고서 II. 사업의 내용**을 초보 투자자가 먼저 이해할 수 있도록 풀어주는 **사업보고서 reader 첫 번째 탭**입니다.

핵심 UX는 다음입니다.

- 기업을 고르면 중앙 행성에 회사명이 표시된다.
- 행성 주변에는 회사의 주요 사업·제품·서비스가 카드 형태로 배치된다.
- 아래에는 DART 사업보고서의 사업개요·사업현황 문장을 기반으로 요약한 내용이 나온다.
- “사업보고서를 볼 때 확인할 점”이 아니라, **우리가 사업보고서를 읽고 요약한 내용**처럼 보여야 한다.
- 어려운 용어는 처음 등장할 때만 밑줄 주석으로 설명한다.
- 재무 흐름·EQS·주석 전문은 별도 탭에서 다룰 예정이므로, 이 탭은 회사의 사업 이해에 집중한다.

## 1-2. 최종 화면 제목과 탭

상단 제목은 한 줄입니다.

```text
국내상장기업 사업보고서 reader
```

상단 보조 설명은 pill 형태로 짧게 표시합니다.

```text
DART 사업보고서 기반으로 각 회사가 무엇을 팔고 만드는지 먼저 보여줍니다
행성 주변 사업·제품 카드는 사업보고서 문구와 업종 키워드로 구성
원문 스니펫은 로컬 수집된 사업보고서에서 추출
```

탭은 3개를 표시하되 현재는 첫 번째 탭만 활성화합니다.

```html
<button class="tab active">사업 우주지도</button>
<button class="tab" disabled>재무제표 갤럭시 맵</button>
<button class="tab" disabled>주석 달린 사업보고서</button>
```

## 1-3. 유지해야 할 최종 톤

금지 톤:

- “추후 사업보고서를 볼 때 확인하세요”
- “이 항목을 체크하세요”
- “무엇을 봐야 합니다”
- “체크포인트입니다”

권장 톤:

- “사업보고서에는 이렇게 공시되어 있습니다”
- “이 회사는 이런 사업 구조입니다”
- “이 제품군이 매출을 만듭니다”
- “이 비용·투자·계약은 실적에 이렇게 반영됩니다”

최종 문구 정규화 함수는 `reportSummaryTone(text)`입니다. 렌더링 전 카드 문구를 다음처럼 변환합니다.

```js
function reportSummaryTone(text) {
  return String(text || '')
    .replace(/같이 봐야 합니다\./g, '함께 실적에 반영됩니다.')
    .replace(/확인해야 합니다\./g, '사업보고서에서 관련 흐름을 설명합니다.')
    .replace(/읽어야 합니다\./g, '함께 실적을 만드는 구조입니다.')
    .replace(/체크포인트/g, '요약 포인트')
    .replace(/단서입니다\./g, '내용입니다.')
    .replace(/신호입니다\./g, '내용입니다.')
    .replace(/입니다\.입니다\./g, '입니다.');
}
```

---

# PART 2 — 화면 레이아웃 구현 명세

## 2-1. 전체 DOM 구조

최상위 구조는 다음과 같습니다.

```html
<main class="page">
  <header class="hero">
    <div>
      <div class="eyebrow">DiscloseAI Galaxy Annual Report Reader</div>
      <h1>국내상장기업 사업보고서 reader</h1>
      <div class="subtitle">...</div>
    </div>
    <div class="hero-actions">
      <span id="coverageBadge">수집 기업</span>
      <span>2025 연결 기준</span>
      <span>단위: 억원/조원</span>
    </div>
  </header>

  <nav class="tabs">...</nav>

  <section class="workspace">
    <aside class="rail">
      <div class="rail-head">
        <h2>기업 선택</h2>
        <input id="searchInput" type="search">
        <div class="sorts">
          <button data-sort="market_cap">시총순</button>
          <button data-sort="ttm_per">TTM PER순</button>
        </div>
      </div>
      <div id="companyList" class="company-list"></div>
    </aside>

    <section id="readerPanel" class="panel" aria-live="polite"></section>
  </section>
</main>
```

## 2-2. 그리드 구성

```css
.page {
  width: min(1440px, calc(100% - 32px));
  margin: 0 auto;
  padding: 22px 0 30px;
}

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.rail {
  position: sticky;
  top: 14px;
  max-height: calc(100vh - 28px);
  overflow: hidden;
}

.panel {
  overflow: hidden;
}
```

좌측 rail은 고정형 기업 선택 영역입니다. 우측 panel은 선택된 기업의 전체 reader 콘텐츠를 렌더링합니다.

## 2-3. 배경과 컬러 토큰

기본 팔레트는 galaxy 컨셉입니다.

```css
:root {
  color-scheme: dark;
  --bg: #060914;
  --panel: #0c1222;
  --panel2: #11182b;
  --line: rgba(148,163,184,.18);
  --text: #edf6ff;
  --soft: #b8c6d9;
  --muted: #7d8ba3;
  --cyan: #41dcff;
  --teal: #36e5bd;
  --pink: #ff4f7e;
  --gold: #f7d56f;
  --violet: #9d81ff;
}
```

body 배경은 3개의 radial gradient와 별먼지 레이어를 겹칩니다.

```css
body {
  background:
    radial-gradient(circle at 15% 4%, rgba(65,220,255,.18), transparent 28%),
    radial-gradient(circle at 86% 0%, rgba(255,79,126,.18), transparent 30%),
    radial-gradient(circle at 54% 74%, rgba(157,129,255,.14), transparent 38%),
    var(--bg);
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(circle, rgba(255,255,255,.35) 0 1px, transparent 1.6px),
    radial-gradient(circle, rgba(65,220,255,.25) 0 1px, transparent 1.5px);
  background-size: 92px 92px, 137px 137px;
  opacity: .16;
}
```

---

# PART 3 — 데이터 구조

## 3-1. DATA 배열

HTML 내부에 `const DATA = [...]` 형태로 48개 기업 데이터가 들어갑니다.

각 기업 객체의 최소 필드는 다음입니다.

```js
{
  rank: 1,
  name: "삼성전자",
  stock_code: "005930",
  corp_code: "00126380",
  sector: "반도체/전자부품",
  display_category: "종합반도체",
  badge_label: "종합반도체",
  market_cap: 1871470485210000,
  last_price: 285000,
  ttm_per: 41.3979,
  dart_url: "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...",
  report: {
    name: "사업보고서 (2025.12)",
    date: "20260310",
    rcept_no: "20260310002820"
  },
  snippets: {...},
  business_cards: [...]
}
```

## 3-2. snippets 구조

`snippets`는 로컬에 수집된 DART 사업보고서 원문에서 추출한 사업 관련 문단입니다.

```js
snippets: {
  overview: "사업의 개요 문단",
  raw_material: "원재료 및 생산설비 문단",
  capacity: "생산능력·생산실적·가동률 문단",
  segment_finance: "사업부문별 재무현황 또는 부문 설명",
  rd: "연구개발활동 문단",
  segment_breakdown: [
    {
      name: "DX부문",
      desc: "TV, 냉장고, 스마트폰 등 완제품 생산·판매",
      revenue_share: 0.563
    }
  ],
  investor_note: "초보 투자자용 쉬운 설명",
  products: ["스마트폰", "TV", "DRAM"],
  raw_moves: [
    { name: "반도체 Wafer", pct: -10, direction: "하락" }
  ],
  utilization: [
    { name: "평균가동률", rate: 100 }
  ],
  rd_chart: {
    years: ["제76기", "제77기", "제78기"],
    costs: [],
    expense: [],
    ratios: []
  }
}
```

## 3-3. business_cards 구조

행성 주변 사업·제품 카드는 `business_cards` 배열로 제어합니다. 회사마다 2~4개를 권장합니다. 3개일 때는 중앙 행성을 가리지 않도록 CSS에서 행성을 위로 올립니다.

```js
business_cards: [
  {
    title: "DX 부문",
    caption: "스마트폰, TV, 모니터, 생활가전, 네트워크시스템",
    kind: "device",
    visual: "Galaxy",
    imageKey: "smartphone",
    image: "https://commons.wikimedia.org/...",
    image_source: "Wikimedia Commons",
    image_fallback: null
  }
]
```

필드 역할:

- `title`: 카드 제목
- `caption`: 짧은 설명. `reportSummaryTone()`을 거쳐 표시
- `kind`: CSS 보조 클래스
- `visual`: 이미지가 실패했을 때 표시할 짧은 라벨
- `image`: 제품·서비스 사진 URL
- `image_source`: 카드 우상단 출처 pill

---

# PART 4 — 핵심 컴포넌트 렌더링

## 4-1. 기업 선택 리스트

기업 리스트는 `listRows()`가 렌더링합니다.

기능:

- 검색어가 있으면 `name` 또는 `stock_code`에 포함되는 기업만 표시
- 기본 정렬은 시총순
- `TTM PER순` 클릭 시 양수 PER 낮은 순으로 정렬
- 각 행에는 순위, 회사명, 종목코드, 업종, 현재 정렬 기준 지표, badge 표시

정렬 로직:

```js
if (sortMode === "ttm_per") {
  const ar = av && av > 0 ? av : Infinity;
  const br = bv && bv > 0 ? bv : Infinity;
  if (ar !== br) return ar - br;
  return marketCapDesc;
}

if (sortMode === "market_cap") {
  return marketCapDesc;
}
```

리스트 HTML:

```js
return `
  <button class="company-btn ${active}" data-code="${stock_code}">
    <span class="rank">#${index + 1}</span>
    <span>
      <span class="cname">${name}</span>
      <span class="cticker">${stock_code} · ${display_category}<br>${metric}</span>
    </span>
    <span class="sector-pill">${badge_label}</span>
  </button>
`;
```

## 4-2. 선택 기업 렌더링

선택된 기업은 `render(row)`가 `#readerPanel`에 그립니다.

```js
function render(row) {
  renderedTermNotes = new Set();
  const category = row.display_category || row.sector || '업종 미분류';
  const reportLabel = row.report?.name || '최근 사업보고서';
  const dart = row.dart_url || fallbackDartUrl;

  readerPanel.innerHTML =
    companyHero(row, category, reportLabel) +
    content(row, dart);
}
```

실제 구성:

```html
<section class="company-hero">
  <div class="orbit-lines"></div>
  <div class="planet-ring"></div>
  <div class="planet">...</div>
  <div class="hero-grid cards-N">...</div>
</section>

<div class="content">
  {reportMapHtml(row)}
  <div class="source-row">
    <a class="source-link" href="{dart}" target="_blank">DART 원문 열기</a>
    <span class="mini-label">generated ...</span>
  </div>
</div>
```

## 4-3. 행성 히어로

중앙 행성은 회사명, 종목코드, 업종, 사업보고서 기준연도를 표시합니다.

```html
<div class="planet">
  <div>
    <strong>삼성전자</strong>
    <span>005930<br>종합반도체<br>(2025.12)</span>
  </div>
</div>
```

애니메이션:

```css
.planet {
  animation: planetFloat 5.8s ease-in-out infinite;
}

.planet-ring {
  animation: planetRingFloat 5.8s ease-in-out infinite;
}

@keyframes planetFloat {
  0%, 100% { transform: translate(-50%, -50%) translateY(0) rotate(-.4deg); }
  50% { transform: translate(-50%, -50%) translateY(-12px) rotate(.7deg); }
}
```

3개 카드 회사는 중앙 하단 카드가 행성을 가리는 문제가 있어 행성을 위로 올립니다.

```css
.company-hero:has(.hero-grid.cards-3) .orbit-lines,
.company-hero:has(.hero-grid.cards-3) .planet,
.company-hero:has(.hero-grid.cards-3) .planet-ring {
  top: 34%;
}
```

## 4-4. 행성 주변 사업 카드

`businessCardsHtml(row)`가 렌더링합니다.

```js
function businessCardsHtml(row) {
  return row.business_cards.map((card) => {
    const image = card.image ? `<img class="segment-image" ...>` : '';
    const source = card.image_source ? `<span class="photo-source">...</span>` : '';
    const caption = reportSummaryTone(card.caption || '사업보고서에 표시된 주요 제품 또는 서비스입니다.');

    return `
      <article class="orbit-card">
        <div class="product-visual ${card.kind} ${card.image ? 'has-image' : ''}">
          ${image}
          <span class="art a"></span>
          <span class="art b"></span>
          <span class="art c"></span>
          <span class="visual-word">${card.visual}</span>
          ${source}
        </div>
        <h3>${rich(card.title)}</h3>
        <p>${rich(caption)}</p>
      </article>
    `;
  }).join("");
}
```

이미지 실패 시:

```html
onerror="
  this.parentElement.classList.remove('has-image');
  this.parentElement.querySelector('.photo-source')?.remove();
  this.remove();
"
```

즉, 사진이 깨져도 로컬 CSS 비주얼로 fallback됩니다.

---

# PART 5 — 사업보고서 요약 영역

## 5-1. `reportMapHtml(row)`

첫 번째 탭의 핵심 본문입니다.

```js
function reportMapHtml(row) {
  return `
    <section class="section report-map">
      <div class="section-head">
        <div>
          <h2>DART II. 사업의 내용 요약</h2>
          <div class="mini-label">${category}</div>
        </div>
        <p>우리가 사업보고서의 사업개요와 사업현황을 읽고, 초보 투자자가 바로 이해할 수 있게 요약했습니다.</p>
      </div>

      <div class="report-grid" style="grid-template-columns:1fr">
        <article class="report-panel">
          <h3>요약 한눈에</h3>
          ${compactList(whatSellsText(row), 3)}
          ${sourceSentence(row.snippets?.overview)}
        </article>
      </div>

      ${segmentBreakdownHtml(row)}
      ${customReportIdeasHtml(row)}
      ${utilizationDetailHtml(row)}
    </section>
  `;
}
```

## 5-2. 요약 한눈에

`whatSellsText(row)`는 다음 3문장을 만듭니다.

1. 회사 사업 축
2. 사업보고서 기준 핵심 품목
3. 아래 카드의 목적

예시:

```text
삼성전자의 사업 축은 DX 부문 · DS 부문 · SDC · Harman입니다.
사업보고서 기준 핵심 품목은 스마트폰, TV, DRAM, NAND Flash 등입니다.
아래 카드는 원문을 그대로 옮기지 않고, 회사 이해에 필요한 내용만 쉬운 말로 압축했습니다.
```

## 5-3. 부문별 매출비중과 사업 설명

`segmentBreakdownHtml(row)`는 `snippets.segment_breakdown`이 있을 때만 표시합니다.

카드 구조:

```html
<article class="segment-card">
  <strong>DX부문</strong>
  <div class="segment-share">56.3%</div>
  <p class="segment-desc">TV, 냉장고, 스마트폰 등 완제품 생산·판매</p>
  <div class="segment-bar"><span style="--w:100%"></span></div>
</article>
```

막대 길이는 해당 회사 내 최대 매출비중 대비 상대값입니다.

```js
const width = Math.max(6, Math.min(100, (share / maxShare) * 100));
```

주의:

- 내부거래 제거 방식 때문에 단순 합계가 100%와 다를 수 있습니다.
- 이 막대는 정확한 pie chart가 아니라, 회사 안에서 어느 사업이 큰지 비교하는 신호판입니다.

## 5-4. 우리가 읽고 요약한 사업보고서 핵심

`customReportIdeasHtml(row)`는 각 회사별 맞춤형 이해 카드입니다.

화면 제목:

```text
우리가 읽고 요약한 사업보고서 핵심
```

카드 구조:

```html
<article class="custom-report-card">
  <strong>사업 구조</strong>
  <span class="value">DX · DS · SDC · Harman</span>
  <p><b>사업보고서 근거</b><br>...</p>
  <p><b>쉽게 풀면</b><br>...</p>
  <span class="source-chip">DART II. 사업의 내용 기반</span>
</article>
```

중요한 UX 원칙:

- 제품 목록을 다시 반복하지 않는다.
- “투자자가 확인해야 할 것”이 아니라 “사업보고서에 적힌 핵심 내용을 요약”한다.
- 회사별로 3개 카드 내외가 적당하다.
- 카드 제목과 본문이 반드시 일치해야 한다.

## 5-5. 생산능력과 2025년 가동률

제조업·장치산업에서만 `utilizationDetailHtml(row)`를 표시합니다.

```html
<div class="utilization-detail">
  <div class="detail-head">
    <h3>생산능력과 2025년 가동률</h3>
    <p>DART 사업보고서의 생산능력·생산실적·가동률 표를 막대 카드로 바꿨습니다.</p>
  </div>
  <div class="util-grid">...</div>
</div>
```

금융·지주·플랫폼·통신·해운·소비재 등 공장 가동률이 핵심이 아닌 업종은 이 블록을 숨기거나 업종별 다른 카드로 대체합니다.

---

# PART 6 — 용어 주석 시스템

## 6-1. 목적

초보 투자자가 모르는 단어를 바로 이해할 수 있도록, 어려운 용어는 밑줄과 `?` 표시를 붙이고 hover/focus 시 설명 tooltip을 띄웁니다.

예:

- DRAM
- NAND Flash
- 모바일AP
- Foundry
- OLED
- 디지털 콕핏
- HBM
- ROE
- 충당금
- 손해율

## 6-2. 한 페이지 내 중복 주석 방지

같은 회사 화면 안에서 같은 용어가 여러 번 등장하면 **처음 등장한 곳에만 주석**을 붙입니다.

```js
let renderedTermNotes = new Set();

function rich(value) {
  let output = esc(value);

  for (const [term, tip] of TERM_ENTRIES) {
    if (renderedTermNotes.has(term)) continue;
    if (!output.includes(term)) continue;

    renderedTermNotes.add(term);
    output = output.replace(term,
      `<span class="term-note" tabindex="0" data-tip="${esc(tip)}">${term}</span>`
    );
  }

  return output;
}

function render(row) {
  renderedTermNotes = new Set();
  ...
}
```

## 6-3. 오탐 방지

`리스`는 `리스크` 안에 들어가면 안 됩니다. 따라서 특정 단어 뒤에 오면 주석 처리하지 않는 skip 규칙을 둡니다.

```js
TERM_SKIP_AFTER = {
  '리스': ['크']
};
```

## 6-4. tooltip 동작

```js
function setupTermTooltip() {
  const tooltip = document.createElement('div');
  tooltip.className = 'term-tooltip';
  document.body.appendChild(tooltip);

  document.addEventListener('mouseover', (event) => {
    const target = event.target.closest?.('.term-note');
    if (target) show(target);
  });

  document.addEventListener('mouseout', (event) => {
    if (event.target.closest?.('.term-note')) hide();
  });
}
```

tooltip은 화면 밖으로 나가지 않도록 좌표를 clamp합니다.

---

# PART 7 — 반응형 규칙

## 7-1. 데스크톱

- `.workspace`: `320px + 1fr`
- `.company-hero`: 최소 높이 430px
- `.hero-grid`: 좌우 2열, 카드 폭 260px
- 중앙 행성: 178px 원형

## 7-2. 태블릿

화면 폭이 줄면 주요 grid는 2열로 줄입니다.

```css
@media (max-width: 1100px) {
  .workspace { grid-template-columns: 1fr; }
  .rail { position: relative; top: auto; max-height: none; }
  .company-list { max-height: 340px; }
}
```

## 7-3. 모바일

```css
@media (max-width: 760px) {
  .page { width: min(100% - 20px, 1440px); }
  h1 { white-space: normal; font-size: 32px; }
  .company-hero { min-height: auto; }
  .planet, .planet-ring, .orbit-lines { position: relative; }
  .hero-grid { grid-template-columns: 1fr; height: auto; }
  .orbit-card { width: 100%; }
}
```

## 7-4. 접근성: reduced motion

사용자가 모션 감소 설정을 켜면 행성 진자운동과 hover transform을 끕니다.

```css
@media (prefers-reduced-motion: reduce) {
  .planet,
  .planet-ring,
  .orbit-lines,
  .orbit-card {
    animation: none;
    transition: none;
  }

  .orbit-card:hover {
    transform: none;
  }
}
```

---

# PART 8 — 생성 파이프라인

## 8-1. 입력 데이터

주요 입력은 다음입니다.

- KOSPI 50/상위 시총 기업 리스트
- DART 사업보고서 원문 수집 결과
- 사업보고서에서 추출한 `snippets`
- 시총, 주가, TTM PER snapshot
- 사업 카드 이미지 manifest

관련 산출물:

```text
docs/prototype/kospi50_market_snapshot.json
integration/data/business_images_manifest.json
integration/data/business_images/
```

## 8-2. 빌드 스크립트

최종 HTML은 다음 명령으로 생성합니다.

```powershell
node scripts/build_kospi50_business_reader.mjs
```

정상 출력 예:

```text
wrote ...\docs\prototype\kospi50_business_tabs.html
companies 48
snippets 47
```

## 8-3. 검증 명령

문법 검증:

```powershell
python -m py_compile scripts/build_kospi50_business_reader.py
node --check scripts/build_kospi50_business_reader.mjs
```

HTML 생성:

```powershell
node scripts/build_kospi50_business_reader.mjs
```

문구 톤 검증:

```js
const patterns = [
  '봐야 합니다',
  '확인해야 합니다',
  '읽어야 합니다',
  '체크포인트',
  '단서입니다',
  '신호입니다',
  '입니다.입니다'
];
```

48개 기업을 렌더링한 뒤 위 문구가 0건이어야 합니다.

---

# PART 9 — UX 검수 기준

## 9-1. 사업 카드 검수

각 회사의 `business_cards`는 다음 기준을 만족해야 합니다.

- 실제 사업부문 또는 제품·서비스여야 한다.
- 자본정책, 운용자산, 리스크 같은 추상 항목은 행성 주변 사업 카드로 쓰지 않는다.
- 4개로 억지 분류하지 않는다. 사업이 2~3개면 2~3개만 배치한다.
- 사진은 가능한 실제 제품·서비스 사진을 사용한다.
- 같은 회사 안에서 동일 사진을 반복 사용하지 않는다.
- 이미지가 깨질 경우 CSS fallback이 자연스럽게 보여야 한다.

## 9-2. 사업보고서 요약 카드 검수

`custom-report-card`는 다음 기준을 만족해야 합니다.

- 제목과 본문이 서로 맞아야 한다.
- 사업보고서 원문 근거가 있어야 한다.
- “보세요/확인하세요”가 아니라 “요약하면 이렇다” 톤이어야 한다.
- 제품 목록 반복보다 회사 이해에 도움이 되는 구조, 매출 축, 계약 구조, 생산 구조, 고객 구조를 우선한다.
- 업종별로 맞춤형이어야 한다.

예:

- 금융지주: 순이자마진, 충당금, 자본비율, 비은행 자회사
- 보험: 손해율, 지급여력, 운용자산
- 조선: 수주잔고, 선종, 원가·납기 리스크
- 반도체: 제품 믹스, 가동률, 고부가 제품, CAPEX
- 플랫폼: 이용자, 광고·커머스 수익화, AI/콘텐츠 투자
- 통신: ARPU, 가입자, CAPEX, IDC/AI 성장축

## 9-3. 용어 주석 검수

- 같은 용어는 한 회사 화면에서 처음 한 번만 주석 처리
- `리스크` 안의 `리스` 같은 오탐 제거
- tooltip이 카드 밖으로 넘치거나 잘리지 않아야 함
- 모바일에서는 focus 접근도 가능해야 함

## 9-4. 레이아웃 검수

- 회사명이 긴 경우 중앙 행성 내부에서 줄바꿈 가능해야 함
- 3개 사업 카드 회사는 행성이 카드에 가려지지 않아야 함
- 카드 문장 끝이 잘리면 안 됨
- `...`로 문장이 끊기는 요약은 금지
- 좌측 기업 리스트의 회사명, 업종 pill이 잘리지 않아야 함

---

# PART 10 — 현재 남겨둔 확장 지점

## 10-1. 두 번째 탭: 재무제표 갤럭시 맵

현재 비활성화 상태입니다.

추후 연결 예정:

- 기존 삼성전자 재무 흐름 시각화
- 매출 → 원가 → 매출총이익 → 판관비 → 영업이익 → 당기순이익 흐름
- 현금흐름표와 재무상태표 연결

## 10-2. 세 번째 탭: 주석 달린 사업보고서

현재 비활성화 상태입니다.

추후 연결 예정:

- DART 사업보고서 원문 전문 또는 핵심 문단
- 어려운 용어 주석
- 사업보고서 목차 기반 이동
- 배당, 핵심감사사항, 사업위험, 연구개발 등 상세 섹션

## 10-3. 재무요약 블록

`segmentFinancialDetailHtml(row)` 등 재무 관련 함수는 남아 있지만, 현재 첫 번째 사업 탭에서는 호출하지 않습니다.

이유:

- 첫 번째 탭은 회사 사업 이해에 집중
- 사업부문별 요약 재무현황은 추후 재무요약/재무제표 탭에서 사용하는 편이 더 자연스러움

---

# PART 11 — 재구현 순서

로컬 IDE에서 처음부터 다시 만들 때는 다음 순서로 구현합니다.

1. 단일 HTML 뼈대 작성
2. CSS 토큰과 galaxy 배경 적용
3. header, tabs, workspace, rail, readerPanel DOM 작성
4. `DATA` 샘플 1개 기업 삽입
5. `listRows()` 구현
6. `render(row)` 구현
7. `businessCardsHtml(row)` 구현
8. `reportMapHtml(row)` 구현
9. `segmentBreakdownHtml(row)` 구현
10. `customReportIdeasHtml(row)` 구현
11. `rich()`와 `setupTermTooltip()` 구현
12. 48개 기업 데이터 연결
13. 시총순/TTM PER순 정렬 검증
14. 모바일 반응형 검증
15. 48개 기업 문구 톤 검증

---

# PART 12 — 최종 성공 기준

완성 기준:

- `docs/prototype/kospi50_business_tabs.html`을 브라우저에서 바로 열 수 있다.
- 좌측에서 48개 기업을 선택할 수 있다.
- 검색과 시총순/TTM PER순 정렬이 작동한다.
- 선택한 회사의 행성, 사업 카드, 사업보고서 요약이 즉시 바뀐다.
- DART 원문 열기 버튼이 최근 사업보고서로 연결된다.
- 어려운 용어는 처음 등장할 때만 주석이 붙는다.
- 카드 문구가 “추후 확인”이 아니라 “요약 제공” 톤이다.
- 사진이 깨져도 UI가 무너지지 않는다.
- 카드 텍스트가 박스 밖으로 잘리지 않는다.
- 행성 애니메이션이 과하지 않고, reduced motion에서 꺼진다.
