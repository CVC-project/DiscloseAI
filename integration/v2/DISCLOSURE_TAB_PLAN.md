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

## 6. 공시 영향 라우팅 (2026-08-07 신설 — 반도체 프로토 구현 완료)

> **한 줄**: 공시를 "목록"이 아니라 **"이 회사의 어느 면을 건드리는가"**로 읽게 한다.
> 구현: [`../dossier/build_disclosure_impact.py`](../dossier/build_disclosure_impact.py) → `../dossier/data/impact_<ticker>.json` → 은하수 lite 헤더 배지·오버레이.
> 프로토 대상: **삼성전기 009150** (실측 64건 전건 라우팅, 미분류 0).

### 6.1 왜 필요한가
공시는 뜨는 순간 화면 어딘가의 전제를 낡게 만든다. 은하수의 숫자는 **결산 스냅샷**(사업보고서 rcept_no)에 고정돼 있는데, 그 뒤로 증자·계열 출자·최대주주 변동이 올라오면 화면은 그대로다.
→ 공시를 **4개 영향 차원**으로 갈라 각 표면에 연결하고, "결산 이후"를 시간 기준선으로 삼는다.

### 6.2 영향 차원 4종 (표면과 1:1)
| 차원 | 라벨 | 연결 표면 | 의미색(DESIGN.md §2) |
|---|---|---|---|
| `cash` | 재무구조 | 현금 은하수 · EQS 재무분석 | cyan(현금) |
| `gov` | 지배구조 | 관계 지도(governance) | gold(자본·주주) |
| `vc` | 밸류체인 | 관계 지도(valuechain) | mint |
| `biz` | 산업·기업 | 사업·기업 탭 | steel |

### 6.3 라우팅 2단
**1차 — `disclosure_type`(collector.`_detect_type` 14종)**
증자·CB·BW·채권발행·자기주식 → `cash` (증자는 +`gov`) / 최대주주변동·임원변동·내부자거래 → `gov` /
M&A·분할·영업양도 → `vc`+`gov` / 계약 → `vc`+`biz` / CAPEX → `vc`+`cash` / 실적·정기보고서 → `cash`+`biz`

**2차 — 제목 키워드 (⚠️ '기타'가 전체의 절반)**
삼성전기 실측에서 '기타' 32/64건. 그 안에 배당·주총결과·사외이사 선임·계열사 출자·대량보유·지배구조보고서 등 **핵심 공시가 묻혀 있다.** 제목 정규식 13종으로 구제:
사업/반기/분기보고서→`cash`+`biz` · 배당→`cash` · 기업가치제고→`cash`+`biz` · 특수관계인/계열회사/기업집단→`vc`+`gov` · 대량보유/의결권/주총/사외이사→`gov` · 합병/분할/영업양수도→`vc`+`gov` · 공급계약/수주→`vc`+`biz` · 지배구조보고서→`gov` · 지급수단별/하도급→`vc` · 지속가능경영→`biz` …
> **결과: 64건 → 미분류 0건.** 라우팅 근거는 `basis`(`type`/`title`) 필드로 남겨 추적 가능.

### 6.4 시간 기준선 — "결산 이후"
`report_raw`의 최신 사업보고서 rcept_no 앞 8자리 = 접수일을 스냅샷 기준일로 삼는다(삼성전기 2026-03-10).
그 이후 공시에 `after_snapshot:true` → 배지: **"결산 이후 공시 13건 — 재무구조 4 · 지배구조 8 · 밸류체인 1 · 산업·기업 5"**.
결산 이후가 0건이면 최근 공시로 폴백(빈 화면 금지, FN-016 준용).

### 6.5 표현 규격
- 항목마다 **"이 공시가 바꾸는 것" 1문장** — `TYPE_MEANING`/2차 룰의 경어체 문구. 예: 증자 = "새 주식을 찍어 돈을 모아요 — 현금은 늘지만 내 지분의 몫은 옅어져요."
  (collector.py `_CPA_TEMPLATES`·`_TYPE_FOCUS`가 원재료. **복사하지 않고 취지만 경어체로 축약** — 코드 소유는 B 모듈)
- 차원 칩 + 날짜 + 제목 + DART 원문 링크(`rcpNo=disclosure_id`).
- 문체는 STYLE_GUIDE A7 준수(경어체·격식체 금지), 투자 조언 표현 금지.

### 6.6 경계 (§1.3 재확인)
- **수집은 건드리지 않는다.** disclosure.db를 `mode=ro`로 읽어 **분류·라우팅만** 한다. 수집 범위 확대(현재 49사 하드코딩)는 **B 담당이 별도 진행 중**(`feat/live-disclosures`) — 이 계획은 그 결과를 그대로 받아 쓴다.
- extract_data.py 경로(`disclosures.json`, per_corp=5 캡 + top50 교집합 → 36사)와 **별개 경로**다. impact JSON은 캡 없이 전건을 읽는다.

### 6.7 Q1~Q4에 대한 제안안 (§3 리더 확정 대기 항목)
| # | 제안 | 근거 |
|---|---|---|
| Q1 | **ⓐ 무대 공유** 유지 + 기업 단위는 dossier 배지로 해결 | 상단 DISCLOSURES 탭(전 시장)과 dossier 배지(기업 단위)는 층이 달라 상호보완. 전용 표면 신설은 중복 |
| Q2 | **ⓑ 전 시장 피드 우선 + 기업 드릴인** | 기업 단위는 이미 dossier 배지가 담당하므로, 상단 탭은 "오늘 시장에 무슨 일이"를 맡는 게 역할 분담에 맞음 |
| Q3 | **ⓑ 전체 노출 + 빈 상태 명시** (ⓒ는 B가 이미 진행 중) | impact JSON 404면 배지를 숨기는 방식이 이미 구현돼 있어, 데이터 없는 기업은 조용히 비활성 |
| Q4 | **ⓑ 스키마화** — 단 4필드가 아니라 **차원 라우팅 + 1문장**부터 | 삼성전기 실측상 `summary` 다수가 템플릿 문구(§1.2 경고). 라우팅+1문장은 LLM 없이도 성립하고, 4필드 승격은 요약 품질 개선 이후 |

### 6.8 다음 단계
> **표면 변경 (리더 결정 08-11, UX-041)**: 은하수 lite 화면의 배지·오버레이는 **제거** — 학습 화면과 공시 피드는 결이 다르다. 빌더(`build_disclosure_impact.py`)와 `impact_<t>.json` 산출물·라우팅 테이블은 그대로 유효하며, 노출 표면은 아래에서 재결정한다.
1. B의 수집 확대 결과 반영 — 대상 기업이 늘면 빌더를 그대로 재실행(코드 변경 불요)
2. 라우팅 결과의 1차 노출 표면 = **상단 DISCLOSURES 탭**(차원 필터·결산 이후 구분선) — Q1·Q2 확정과 함께 설계
3. EgoView(지배구조·밸류체인) 표면에 `gov`/`vc` 공시 연결 — `relation_local.rcept_no`·`value_chain_edge.rcept_no`가 `disclosure_id`와 **직접 조인 가능**(기존 훅)

---

## 5. 작업 규율 (매 세션 체크리스트)

1. 착수 전 [UX_DECISIONS.md](UX_DECISIONS.md)·[../DECISIONS.md](../DECISIONS.md) 필독 — 기각안 재제안 금지
2. 수정 후 **캐시버스트 5개소**(styles.css·tokens.css·mock/valuation/narration/loader/adapter) 버전 상향 (FN-004·FN-009)
3. 리더 피드백은 성격에 따라 UX-### / FN-### 로 즉시 채록
4. 브라우저 스모크(콘솔 에러 0) 후 완료 보고
