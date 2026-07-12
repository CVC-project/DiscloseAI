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
  sans: "Pretendard (로컬 벤더링: integration/dossier/assets/fonts/pretendard/)"
  mono: "IBM Plex Mono (로컬 벤더링: integration/dossier/assets/fonts/ibm-plex-mono/)"
---

# DESIGN.md — DiscloseAI 디자인 정본

> **목적**: 화면이 늘어나도 디자인이 흔들리지 않게 하는 단일 규칙 문서. UI·화면 작업 전 반드시 읽는다.
> **기준(리더 확정)**: **현금 은하수(milky way) 표준** — 원형은 [design/prototypes/현금은하수_해방판.html](design/prototypes/현금은하수_해방판.html). 탭①(business)·탭②(EQS)는 이 표준에 맞춰 통일한다.
> **구현 SSOT는 코드**: 값의 정본은 CSS 2계층이고, 이 문서는 그 지도와 규칙이다. 문서와 CSS가 다르면 CSS를 고치든 문서를 고치든 **같은 커밋에서** 정합시킨다.

## 1. 토큰 2계층 (D3)

| 층 | 파일 | 내용 | 사용 |
|---|---|---|---|
| 층1 프리미티브 | [integration/dossier/tokens.css](integration/dossier/tokens.css) | 간격(--sp-*)·radius(--r-*)·타입 스케일(--t-*)·자간·모션·행높이 — **표면 무관** | 모든 dossier 페이지가 `<link>` |
| 층2 시맨틱 테마 | [integration/dossier/theme-galaxy.css](integration/dossier/theme-galaxy.css) | mint 팔레트·기본색·폰트 스택 — **galaxy 표준 룩** | 아래 표면 매트릭스 참조 |

CSS 변수는 iframe 경계를 넘지 못한다 → 각 페이지가 **직접 link**한다 (부모 상속 금지).

## 2. 색 = 의미 (미학적 선택 금지)

색은 재무적 의미에 고정된다 — 예쁘다고 바꾸지 않는다. 전문: [CASH_GALAXY_STYLE_GUIDE.md](integration/dossier/CASH_GALAXY_STYLE_GUIDE.md) A2.

| 토큰 | 색 | 의미 |
|---|---|---|
| `--mint` | #74EEC6 | 손익(수익성) — 주 액센트 |
| `--cyan` | #5CC7EA | 현금(현금흐름) |
| `--gold` | #E9C46B | 자본(주주 몫) |
| `--coral` | #EC8C6A | 유출(비용·투자·주주환원) |
| `--steel` | #7590B0 | 잔액(재무상태표) |

**토큰 명명 규칙**: 위 이름만 사용한다. 별칭(`--teal`·`--pink`·`--violet` 등) 금지 — 2026-07-12 business.html에서 표준화 완료.

## 3. 표면별 적용 매트릭스

| 표면 | 룩 | 팔레트 출처 | 비고 |
|---|---|---|---|
| dossier 탭① [business.html](integration/dossier/business.html) | galaxy 표준 | **theme-galaxy.css link** | 페이지 고유 토큰(--panel2·--soft·--muted)만 인라인 |
| dossier 탭② [galaxy.html](integration/dossier/galaxy.html) | galaxy 표준(원조) | 자체 `:root` (해방판 자구 — 값은 theme-galaxy.css와 동일) | **의도적 미링크**: 해방판 자구가 판정 기준이라 인라인 유지 |
| dossier 탭③ [firm.html](integration/dossier/firm.html) | 이중 룩 | `[data-theme="galaxy"]` 스코프 인라인 | **예외**: v1은 원본 인디고 룩 불변, v2 오버레이(`?theme=galaxy`)만 galaxy 룩. link하면 v1 룩이 오염되므로 스코프 방식 유지 |
| v2 셸(기업 우주) [integration/v2/](integration/v2/) | **별도 트랙(의도적)** | styles.css (#5eead4 cyan · Inter/JetBrains Mono/Space Grotesk) | 우주 지도 셸은 galaxy 표준으로 통일하지 **않는다**(기존 룩 보존 — D3). 기록: [integration/v2/DESIGN.md](integration/v2/DESIGN.md) |
| legacy (v1 dashboard · relation viewer · price HTML) | 구세대(#4da6ff / #3b82f6 계열) | 각자 인라인 | 신규 스타일 작업 금지 — 손댈 일이 생기면 galaxy 표준 이관을 먼저 검토 |

## 4. 새 표면(탭·페이지) 추가 체크리스트

1. `tokens.css` link (층1 프리미티브)
2. 룩 결정 — 전면 galaxy 룩이면 `theme-galaxy.css` link, 기존 룩과 공존해야 하면 firm.html처럼 `[data-theme]` 스코프
3. 폰트는 **로컬 벤더링만** (`integration/dossier/assets/fonts/` — CDN 금지, GitHub Pages 오프라인 안전)
4. 색은 §2 의미에 맞는 토큰만 — hex 하드코딩·별칭 토큰 금지
5. 완료 후 **ui-ux-reviewer(또는 Playwright 스크린샷)로 시각 검증** — 특히 v2 오버레이 iframe 안에서 확인

## 5. 관련 문서 지도

| 문서 | 역할 |
|---|---|
| 이 파일 (루트 DESIGN.md) | 프로젝트 전체 디자인 규칙·표면 지도 (SSOT) |
| [integration/dossier/CASH_GALAXY_STYLE_GUIDE.md](integration/dossier/CASH_GALAXY_STYLE_GUIDE.md) | 탭③ 현금 은하수 **도메인 문법** 전문(색=의미·viz 8종·카피 규칙·삼성 골든) |
| [integration/dossier/GALAXY_JSON_SCHEMA.md](integration/dossier/GALAXY_JSON_SCHEMA.md) | galaxy_&lt;ticker&gt;.json 데이터 스키마 (디자인 아님) |
| [integration/dossier/DOSSIER_TABS_PLAN.md](integration/dossier/DOSSIER_TABS_PLAN.md) | 3탭 실행 계획 (디자인 결정 D1~D12 포함) |
| [integration/v2/DESIGN.md](integration/v2/DESIGN.md) | v2 셸 전용 디자인·로직 기록 (셸 별도 트랙의 정본) |
| [design/](design/) | 프로토타입 원형·제작 사양서(프롬프트_v6) — 자구·데이터 판정 기준 |

## 6. 알려진 잔여 격차 (다음 정비 대상)

- business.html에 구세대 액센트의 rgba 하드코딩 잔재(`rgba(65,220,255,…)` = 구 #41dcff 글로우) 소수 존재 — 시각 위험이 낮아 보류, 다음 스타일 작업 시 `--cyan` 기반으로 정리.
- v2 셸 폰트 3종(Inter·JetBrains Mono·Space Grotesk)은 라틴 서브셋 — 한글 본문은 시스템 폴백. 셸은 별도 트랙이므로 허용.
