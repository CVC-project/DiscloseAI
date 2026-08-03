# 공시(DISCLOSURES) 탭 — 실행 계획

> **상태**: 2026-08-03 착수(브랜치 `feat/disclosure-tab`). Phase 0(현황 인벤토리 + 타임머신 폐지) 완료, Phase 1~ 미착수.
> **소유**: 프로젝트 리더 (integration 서빙 계층)
> **이 문서만 읽고 새 세션에서 실행 가능해야 한다.**
> 선행 필독: [UX_DECISIONS.md](UX_DECISIONS.md) · [../DECISIONS.md](../DECISIONS.md) · [CLAUDE.md](CLAUDE.md) · 루트 [DESIGN.md](../../DESIGN.md)

---

## 0. 목표 (한 문단)

v2 셸 상단 탭은 이제 **2탭**(FINANCIALS · DISCLOSURES)이다. FINANCIALS는 은하 → 섹터 → 기업 →
CORPORATION DOSSIER(3탭)까지 완성돼 있으나, **DISCLOSURES는 FINANCIALS와 같은 3D 무대를 공유하면서
좌상단 패널만 공시용으로 갈아끼운 얕은 상태**다. 이 탭을 "공시를 읽고 이해하는 독립 표면"으로
본격 개발한다.

---

## 1. 현황 인벤토리 (2026-08-03 실측, bundle.jsx 기준)

### 1.1 화면 구조 — 지금 있는 것
| 요소 | 위치 | 상태 |
|---|---|---|
| 탭 전환 | `TopTabs` (`tabs` 배열) | **2탭으로 축소 완료** — `finance` / `disclose` |
| 무대 | `activeTab === 'finance' \|\| 'disclose'` 공통 `.finance-tab` 블록 | FINANCIALS와 **동일한 SolarSystem·SectorMap·EgoView 공유** |
| 좌상단 패널 (galaxy) | `MascotPanel` (공시용 대사 3종) | 안내 문구만 다름 |
| 좌상단 패널 (sector) | `SectorDisclosurePanel` | 섹터 공시 피드 목록 |
| 좌상단 패널 (company) | `CompanyDisclosurePanel` | 자사 공시 + "관계 기업 공시" 접이식 |
| 공시 상세 | `discDetailItem` 오버레이 | 공시 1건 상세 |
| 풀스크린 | DISCLOSURE DOSSIER 오버레이 (`discFullOverlayTicker`, `enterDisclosures`) | 기업 단위 공시 전체 |
| 공통 크롬 | `OverlayHeader` — 로고=홈 · 전역 검색 (UX-036) | 3종 오버레이 공통 |
| AI | `OverlayAiChat` / `AssistantPanel` (탭별 프롬프트 분기) | 공시 프롬프트 존재 |

### 1.2 데이터 현황 — `integration/data/disclosures.json` (disclosure 모듈 산출물, read-only)
- `meta.generated_at` 2026-07-31 · `disclosures` **180행 / 36사** · `statements` 252행 / 36사
- 공시 레코드 필드: `disclosure_id`(rcept_no) · `corp_code` · `corp_name` · `disclosure_date` ·
  `disclosure_type` · `title` · `amount` · `summary`(LLM 4섹션 텍스트) · `high_impact` ·
  `dilution_ratio` · `stock_code` · `ticker`
- `disclosure_type` 8종: 정기보고서 · 실적 · 계약 · 자기주식 · 내부자거래 · 최대주주변동 · BW · 기타
- 날짜 범위 **2026-03-18 ~ 2026-05-04** (약 7주 스냅샷)
- ⚠️ **커버리지 갭**: universe는 2,651사인데 공시 보유는 **36사**. 나머지는 "공시 데이터 없음" 문구로 떨어진다.
- ⚠️ **summary 품질**: 위 8종 중 '기타' 다수가 템플릿 문구("공시 유형상 직접적인 현금 영향을 즉시
  파악하기 어렵습니다" 등) — 화면 확장 전에 원문 대비 실효성 판단 필요.

### 1.3 경계 (CLAUDE.md 준수)
- **공시 데이터 생산은 disclosure 모듈(B 담당) 소관.** integration은 `integration/data/*.json`을
  **read-only**로 읽어 표현만 한다. 수집 범위·요약 품질 개선이 필요하면 B에 요청 — integration이
  직접 수집하지 않는다.
- 화면·표현은 전부 integration 소유. 이 탭 작업 산출물은 `integration/v2/` 안에서 끝낸다.

---

## 2. Phase 0 — 정리 (2026-08-03, 완료)

- [x] **타임머신 탭 폐지** (UX-037) — `TimeMachineTab`·`ScenarioCard`·`ScoreBoardPanel`·
      `TmCategoryFilterPanel`·`ScenarioIndexPanel` 제거(bundle.jsx −207행), TM 전용 CSS 제거
      (styles.css −195행), 탭 배열에서 `timemach` 제거
- [x] **price_scenarios 와이어링 은퇴** (FN-018) — loader.js의 fetch·`scenariosByTicker`·
      `tmAll`/`has_quiz`, adapter.js의 `scenarios` 노출 제거. **데이터 파일
      `integration/data/price_scenarios.json`은 price 모듈 산출물이라 보존**(삭제 금지)
- [x] 캐시버스트 `?v=m1h → ?v=m1i` (FN-004·FN-009 — JS 3종 + CSS 2종 전부)
- [x] 스모크 검증 — 로컬 서버 렌더, 콘솔에 JSX/런타임 에러 0 (남은 에러는 KOSPI 시세 fetch CORS,
      기존과 동일)

---

## 3. 리더 확인 필요 (Phase 1 착수 전)

착수 전 아래를 확정해야 방향이 갈리지 않는다.

| # | 질문 | 선택지 |
|---|---|---|
| Q1 | **탭의 정체성** — 공시 탭은 FINANCIALS와 같은 3D 은하 무대를 계속 공유하나, 아니면 **공시 전용 레이아웃**(피드/타임라인 중심)으로 갈라서나? | ⓐ 무대 공유 + 패널만 교체(현행 유지) ⓑ 공시 전용 표면 신설 |
| Q2 | **진입 단위** — 공시를 "기업별"로 보나, "시장 전체 최신순 피드"로 보나? | ⓐ 기업 중심(현행) ⓑ 전 시장 피드 우선 + 기업 드릴인 |
| Q3 | **커버리지 36사 문제** — 데이터 없는 2,600여 사를 어떻게 다루나? | ⓐ 있는 기업만 노출 ⓑ 전체 노출 + 빈 상태 명시 ⓒ 수집 확대를 B에 선요청 |
| Q4 | **AI 요약의 위치** — 현행 `summary` 텍스트를 그대로 쓰나, galaxy처럼 **구조화 JSON**으로 승격하나? | ⓐ 현행 텍스트 ⓑ 스키마화(Cash/Risk/Hidden/Verdict 4필드 분리) |

---

## 4. Phase 뼈대 (Q1~Q4 확정 후 상세화)

- **Phase 1 — 표면 정의**: Q1·Q2 결정 반영. 화면 골격·상태 머신(무대/피드/상세/DOSSIER)·
  뒤로가기(ESC) 계약 확정.
- **Phase 2 — 데이터 계약**: loader/adapter의 공시 인덱싱 확장(유형·날짜·영향도 축), 빈 상태 규칙(Q3).
- **Phase 3 — 화면 구현**: 패널·필터·상세 뷰. 루트 DESIGN.md 팔레트(색=의미) 준수.
- **Phase 4 — AI 층**: 요약·질의 프롬프트 정비(Q4), 면책 문구 규율.
- **Phase 5 — 검증**: `/viewer-check`(ui-ux-reviewer) + 캐시버스트 체크리스트 + 회귀(FINANCIALS 무손상).

---

## 5. 작업 규율 (매 세션 체크리스트)

1. 착수 전 [UX_DECISIONS.md](UX_DECISIONS.md)·[../DECISIONS.md](../DECISIONS.md) 필독 — 기각안 재제안 금지
2. 수정 후 **캐시버스트 5개소**(styles.css·tokens.css·mock/valuation/narration/loader/adapter) 버전 상향 (FN-004·FN-009)
3. 리더 피드백은 성격에 따라 UX-### / FN-### 로 즉시 채록
4. 브라우저 스모크(콘솔 에러 0) 후 완료 보고
