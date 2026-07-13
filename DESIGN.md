---
# DiscloseAI 디자인 토큰 (machine-readable — 구현 SSOT는 integration/dossier/{tokens,theme-galaxy}.css)
standard: cash-milky-way # 기준 = 현금 은하수 (design/prototypes/현금은하수_해방판.html)
palette:
  mint: "#74EEC6" # 손익(수익성) · 주 액센트
  cyan: "#5CC7EA" # 현금(현금흐름)
  gold: "#E9C46B" # 자본(주주 몫)
  coral: "#EC8C6A" # 유출(비용·투자·환원)
  steel: "#7590B0" # 잔액(재무상태표)
  green: "#63d68e" # 보조(증가·긍정 델타)
base:
  bg: "#05060d"
  text: "#eef4fb"
  dim: "#8fa1b6"
  dim2: "#5c6b80"
  panel: "rgba(12,17,30,.78)"
  line: "rgba(140,170,210,.13)"
fonts:
  sans: "Pretendard Variable" # 한글 본문·제목 (로컬: integration/dossier/assets/fonts/pretendard/)
  mono: "IBM Plex Mono"       # 숫자·금액·영문 라벨·로고·디스플레이 (로컬: integration/dossier/assets/fonts/ibm-plex-mono/)
panel_edge:
  radius: "3px"       # 각진(angular) — 메인 셸 컨셉
  bracket: "10x10, 1px solid var(--edge-accent), 샤프 코너, opacity 0.7, top-left+bottom-right"
  placement: "탭당 주요 패널에만 (business=부문별, EQS=상단 2패널). 나머지는 브래킷 없이 radius만"
sector_theme: "ENTER 시 셸이 섹터색을 &accent=<color>로 3탭 iframe에 전달 → --edge-accent·--mint 오버라이드(galaxy는 색=의미 보존, edge-accent만)"
verify: "변경 시 Playwright 전후 스크린샷 or ui-ux-reviewer — DESIGN.md와 다른 렌더는 버그"
---

# DESIGN.md — DiscloseAI 디자인 정본

> **목적**: 화면·탭·모듈이 늘어나도 일관된 디자인·레이아웃이 나오도록 하는 단일 규칙 문서. **모든 UI 작업(사람·Claude·GPU 산출 포함) 전 반드시 읽고 준수**한다 (CLAUDE.md가 이를 강제).
> **기준(리더 확정)**: **현금 은하수(milky way) 표준** — 원형 [design/prototypes/현금은하수_해방판.html](design/prototypes/현금은하수_해방판.html). 3탭·v2 셸을 이 표준으로 수렴.
> **구현 SSOT는 코드**: 값의 정본은 CSS 2계층. 이 문서는 그 지도·규칙이다. 문서와 CSS가 다르면 **같은 커밋에서** 정합시킨다.

## 1. 토큰 2계층

| 층 | 파일 | 내용 | 사용 |
|---|---|---|---|
| 층1 프리미티브 | [integration/dossier/tokens.css](integration/dossier/tokens.css) | 간격 `--sp-1~8`(4~38px)·radius `--r-1~5`(4~10px)·타입 스케일 `--t-*`·자간 `--ls-*`·모션 `--dur-*`·행높이 `--row-*` — **표면 무관 원자값** | 모든 화면이 `<link>` (v2 셸 포함, 2026-07-13~) |
| 층2 시맨틱 테마 | [integration/dossier/theme-galaxy.css](integration/dossier/theme-galaxy.css) | mint 팔레트·기본색·폰트 스택·표준 패널(`.gx-panel`) — **galaxy 표준 룩** | §4 표면 매트릭스 참조 |

CSS 변수는 iframe 경계를 넘지 못한다 → **각 페이지가 직접 link**한다 (부모 상속 금지). 새 표면은 이 두 파일을 재사용하고, 독자 토큰 세트를 만들지 않는다.

## 2. 색 = 의미 (미학적 선택 금지)

색은 재무적 의미에 고정 — 예쁘다고 바꾸지 않는다. 도메인 문법 전문: [CASH_GALAXY_STYLE_GUIDE.md](integration/dossier/CASH_GALAXY_STYLE_GUIDE.md) A2.

| 토큰 | 색 | 의미 |
|---|---|---|
| `--mint` | #74EEC6 | 손익(수익성) — 주 액센트 |
| `--cyan` | #5CC7EA | 현금(현금흐름) |
| `--gold` | #E9C46B | 자본(주주 몫) |
| `--coral` | #EC8C6A | 유출(비용·투자·주주환원) |
| `--steel` | #7590B0 | 잔액(재무상태표) |
| `--green` | #63d68e | 보조(증가·긍정 델타) |

기본색: 배경 `--bg #05060d` · 본문 `--text #eef4fb` · 보조 `--dim #8fa1b6` · 희미 `--dim2 #5c6b80` · 패널 `--panel rgba(12,17,30,.78)` · 경계 `--line rgba(140,170,210,.13)`.

**토큰 명명 규칙**: 위 이름만. 별칭(`--teal`·`--pink`·`--violet` 등) 금지 — 2026-07 표준화 완료.

## 3. 폰트 시스템 (2026-07-13 전면 통일)

**두 벌만 쓴다** — 한글은 Pretendard, 그 외 모두 IBM Plex Mono. 로컬 벤더링만(CDN 금지).

| 용도 | 패밀리 | weight | 비고 |
|---|---|---|---|
| 한글 본문·제목 | **Pretendard Variable** (`--sans`/`--font-body`) | 300–800 가변 | 한글 글리프 보유(2MB variable) |
| 숫자·금액 | **IBM Plex Mono** (`--mono`/`--font-mono`) | 400/500/600/700 | 표·수치·라벨 |
| 영문 라벨(ZONE·SECTOR 등) | IBM Plex Mono | 400–700 | letter-spacing `--ls-label .22em` |
| 로고·디스플레이·히어로 | IBM Plex Mono (`--font-display`) | 700 | 셸 데이터 톤과 일관 |

- **@font-face 경로**: `integration/dossier/assets/fonts/{pretendard/PretendardVariable.woff2, ibm-plex-mono/IBMPlexMono-*.latin.woff2}`. v2 셸은 `../dossier/assets/fonts/…` 상대경로로 재사용(복사 없음, 같은 오리진).
- **Chart.js**: `Chart.defaults.font.family`를 반드시 지정(미지정 시 Helvetica로 렌더돼 표면 폰트 어긋남). galaxy 테마=IBM Plex Mono / 기본=Pretendard.
- **금지**: Inter·JetBrains Mono·Space Grotesk 등 라틴 서브셋(한글 글리프 0 → 한글이 시스템 폰트로 깨짐) · CDN 폰트 · 인라인 `font-family` 리터럴(변수 사용).

## 4. 패널 엣지 표준 (메인 셸 컨셉 — 얇고 각진)

**표준 엣지**: 패널 radius **3px**(각진) + **ㄱ자 코너 브래킷**(10×10px · **1px** solid `var(--edge-accent)` · **샤프 코너**(라운드 없음) · opacity 0.7 · top-left + bottom-right). 재사용 클래스 `.gx-panel`(theme-galaxy.css).

**브래킷 배치 = 탭당 주요 패널에만** (전 패널에 넣으면 산만 — 리더 결정):
| 표면 | 브래킷 있는 패널 | 나머지 |
|---|---|---|
| business(탭①) | `.segment-breakdown`(부문별 매출비중) 1곳 | radius 3px만, 브래킷 없음 |
| EQS firm(탭③) | 상단 2패널 `.panel.gx-edge`(EQS 종합점수·5개 모듈 프로파일) | radius 3px만, 브래킷 없음 |
| galaxy(탭②) | ZONE 카드(해방판 인라인, 존별 의미색) | — |
| v2 셸 | HUD·패널 전반 `.panel` | — |

**산업군별 동적 accent**: `--edge-accent`(기본 mint)가 브래킷 색. 셸이 ENTER 시 섹터색을 `&accent=<color>`로 3탭 iframe에 전달 → business·firm은 `--mint`·`--edge-accent` 오버라이드(탭 전체 섹터색 테마), galaxy는 `--edge-accent`만(색=의미 보존). §2의 섹터/관계 의미색 팔레트는 셸 SECTOR_PALETTE.

- radius는 각진 3px 기본 — 표면별 독자 값(10·12·14·16px) 금지. 장식 도형(product-visual)은 규칙 밖.

## 5. 레이아웃·간격·모션

- **간격**: `--sp-1~8`(4·8·12·16·20·26·30·38px)만. 임의 px 금지.
- **패널 조합**: 배경 `--panel` + 경계 `1px solid --line` + radius `--r-5` + 브래킷(주요 패널). 패딩은 `--sp-4~5`.
- **타입 스케일**: `--t-mono-micro`(10) ~ `--t-amt`(42px) 계단값 사용.
- **모션**: `--dur-fast`(180ms, 페이드) · `--dur-mid`(250ms, 게이트) · `--dur-slow`(450ms, 재동기화). 커스텀 duration 지양.
- **행높이**: 재무제표 패널 `--row-h`(64px)·`--row-s`(56px).

## 6. 표면별 적용 매트릭스

| 표면 | 폰트 | 팔레트 | 패널 엣지 | link | 비고 |
|---|---|---|---|---|---|
| 탭① [business.html](integration/dossier/business.html) | Pretendard+IPM ✅ | galaxy mint | 표준(10+브래킷) ✅ | tokens + theme-galaxy | 페이지 고유 토큰만 인라인 |
| 탭② [galaxy.html](integration/dossier/galaxy.html) | Pretendard+IPM ✅ | galaxy mint(원조) | 표준(인라인 브래킷) | tokens (theme는 의도적 미링크) | 해방판 자구가 판정 기준 |
| 탭③ [firm.html](integration/dossier/firm.html) | Pretendard+IPM ✅ | `[data-theme=galaxy]` 스코프 | 표준(10+브래킷) ✅ | 인라인 스코프 | v1 무테마 룩은 스코프 밖 불변 |
| v2 셸 [integration/v2/](integration/v2/) | Pretendard+IPM ✅ | galaxy mint ✅ | 표준(10+브래킷) ✅ | tokens + styles.css | **전면 통일**(2026-07-13). 섹터·관계 의미색만 셸 고유(amber·violet 등 — 의미 보존) |
| ~~v1 dashboard~~ | — | — | — | — | 2026-07-13 폐지 |
| ~~relation viewer~~ | — | — | — | — | 2026-07-13 은퇴 |
| price standalone (quiz·timemachine) | Apple SD Gothic | 구세대 blue #3b82f6 | 미적용 | — | D 담당 standalone — 신규 스타일 작업 시 galaxy 이관 검토 |

## 7. 새 표면(탭·페이지) 추가 체크리스트

1. `tokens.css` link (층1 프리미티브)
2. 룩 결정 — 전면 galaxy면 `theme-galaxy.css` link, 기존 룩과 공존해야 하면 firm.html처럼 `[data-theme]` 스코프
3. 폰트: `../dossier/assets/fonts/`의 Pretendard+IBM Plex Mono만 (§3 금지 목록 준수)
4. 색: §2 의미 토큰만 (hex 하드코딩·별칭 금지)
5. 패널: `.gx-panel` 또는 §4 스펙(radius `--r-5` + 브래킷). 간격은 `--sp-*`
6. Chart.js 쓰면 `Chart.defaults.font.family` 지정
7. **검증**: Playwright 전후 스크린샷 or ui-ux-reviewer — v2 오버레이 iframe 안에서도 확인. **DESIGN.md와 다른 렌더는 버그.**

## 8. 금지 목록 (하나라도 어기면 리뷰 반려)

- ❌ hex/rgba 하드코딩 (색은 토큰, 위치는 `--sp-*`/`--r-*`)
- ❌ 별칭 토큰(`--teal`/`--pink`/`--violet` 등)
- ❌ 인라인 `font-family` 리터럴 (변수 사용) · Inter/JetBrains/Space Grotesk · CDN 폰트/CSS
- ❌ 표면별 독자 radius(12·14·16px) — `--r-*` 스케일만
- ❌ 목업을 서빙 폴더(integration/)에 두기 — 원형은 `design/prototypes/`

## 9. 관련 문서 지도

| 문서 | 역할 |
|---|---|
| 이 파일 (루트 DESIGN.md) | 프로젝트 전체 디자인 규칙·표면 지도 (SSOT) |
| [CASH_GALAXY_STYLE_GUIDE.md](integration/dossier/CASH_GALAXY_STYLE_GUIDE.md) | 탭③ 현금 은하수 **도메인 문법**(색=의미·viz 8종·카피·삼성 골든) |
| [GALAXY_JSON_SCHEMA.md](integration/dossier/GALAXY_JSON_SCHEMA.md) | galaxy JSON 데이터 스키마 (디자인 아님) |
| [DOSSIER_TABS_PLAN.md](integration/dossier/DOSSIER_TABS_PLAN.md) | 3탭 실행 계획 (디자인 결정 D1~D12) |
| [integration/v2/DESIGN.md](integration/v2/DESIGN.md) | v2 셸 로직·인터랙션 기록 (렌더 알고리즘·데이터 어댑터) |
| [design/](design/) | 프로토타입 원형·제작 사양서 — 자구·데이터 판정 기준 |

## 10. 잔여 격차 (다음 정비 대상)

- **v2 인라인 hex → 토큰**: styles.css/bundle.jsx의 인라인 색이 galaxy mint로 시프트 완료(값은 통일)됐으나, 아직 `var(--)` 토큰 참조가 아닌 리터럴이 다수 — 시각 무변화 토큰 승격은 후속 정비.
- **price standalone**: quiz·timemachine의 구세대 팔레트·폰트(Apple SD Gothic·blue) — D 담당 영역, 신규 작업 시 galaxy 이관 검토.
- **완료(2026-07-13)**: 3탭·v2 셸 폰트(Pretendard+IBM Plex Mono)·패널 엣지(radius 10+브래킷)·팔레트(mint) 전면 통일. business 구 팔레트(#41dcff·pink·violet) 전역 시프트 완료.
