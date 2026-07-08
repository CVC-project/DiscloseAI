# 기업 상세 4탭 개편 + 사업보고서 AI 파이프라인 — 실행 계획

> **상태**: v3 최종본 (2026-07-08. 초안 → 4렌즈 적대적 리뷰 53건 반영 → 리더 결정 Q1~Q3·D11·D12 반영 → 가변성 감사·DART 스파이크·A100 반영 → 스타일 가이드 연동 → **최종 총점검 4렌즈 37건 반영**)
> **소유**: 프로젝트 리더
> **이 문서만 읽고 새 세션에서 실행 가능해야 한다.** 각 Phase에 완료 기준(DoD)·검증 방법 포함.
> 선행 필독: [ARCHITECTURE.md](ARCHITECTURE.md) §1·2·3.5 · [integration/v2/CLAUDE.md](../integration/v2/CLAUDE.md)

---

## ✅ 확정된 결정 (2026-07-08 리더 승인)

| # | 결정 | 확정 내용 |
|---|---|---|
| Q1 | 신규 모듈 `modules/report/` 생성 (D6) | **승인.** 데이터 생산은 모듈 소관이고 disclosure는 B 소유라 리더 소유 신규 모듈이 경계 규칙상 유일한 정합 경로 |
| Q2 | 탭④ 범위 | **확정: 기타 주석은 탭④로 일원화.** 탭③ = 은하수 + 연결 주석 20건만. 프로토타입에 내장된 기타 주석 13건(DISC) 뷰·전환 버튼은 ③에서 제거하고("나머지 주석은 ④ 탭에서" 안내로 대체) 그 내용을 탭④가 승계 (D9) |
| Q3 | 타사 확장 시 은하수 기하(가지 굵기·길이) 정책 (D10) | **승인.** 생성기(코드)가 재무 비율로 결정적 산출. LLM 아님. 1차 불가 기업(적자·음수 현금흐름·금융업)은 탭③ "준비 중" 스코프아웃 |

추가 리더 지시 (2026-07-08):
- **삼성전자 템플릿으로 표현이 안 되는 기업·항목은 리더에게 보고하는 공식 절차 필수** → D11 보고 절차.
- **타기업 확장 시 패널 위치 등 미세 UI 변형은 보고 없이 자동 흡수되어야 함** → D12 가변성 정책 + Phase 1 가변성 스파이크 (템플릿 렌더 코드 전수 감사로 검증).

---

## 0. 목표 (한 문단)

현재 v2 기업우주에서 행성 → ENTER CORPORATION 클릭 시 EQS 단일 화면(firm.html iframe)이 뜬다.
이를 **사업보고서 교육 관점의 4탭**으로 개편한다:

| 탭 | 내용 | 원형(프로토타입) | 데이터 |
|---|---|---|---|
| ① 사업·기업 개요 | 사업보고서 기준 사업/기업 소개 | `docs/prototype/kospi50_business_tabs.html` | **48개** 기업분 이미 내장 |
| ② EQS 분석 | 기존 firm 상세 (M1~M5) | `integration/dossier/firm.html` (배포 중) | firm_*.json 48개 존재 |
| ③ 현금 은하수 + 핵심 주석 | 현금흐름 시각화 + 연결 주석 20건 | `docs/prototype/Cash Galaxy.editable.html` | 삼성전자만 (수작업) |
| ④ 나머지 주석 | ③이 다루지 않은 주석 (Q2) | 신규 페이지 (③의 카드 시각 패턴 차용) | 초판 = ③의 DISC 13건 승계 |

**디자인 표준 = Cash Galaxy.** ①·②·④는 Cash Galaxy 토큰(색·폰트·배경)으로 맞춘다.
**이식 원칙**: 프로토타입이 존재하는 ①③은 재설계·재작성하지 않고 그대로 옮긴다(=이식). 허용 범위는 ⓐ 디자인 토큰 치환 ⓑ 데이터 외부화(하드코딩 → JSON fetch, **템플릿 내 하드코딩 텍스트의 `{{ }}` 바인딩 치환 포함**) ⓒ 개발용 임시 도구 삭제 — 이 셋뿐. ④는 프로토타입이 없는 **신규 제작**이라 이식 원칙 대상이 아니다(단 시각 언어는 ③를 따른다).

이후 **AI 확장**: 삼성전자 기준으로 만든 "기본 틀(템플릿+JSON 스키마)"에, 사업보고서 원문을 DB에 저장해 두고 **자체 GPU LLM(원격 A100 + vLLM)** 이 주석 수치·설명을 추출/생성해 채워 48개 기업으로 확장한다.

---

## 1. 현황 진단 (2026-07-08, 4개 탐색 + 4렌즈 리뷰로 검증된 사실)

### 1.1 integration/v2 (셸)
- 빌드 도구 없음: React 18 UMD + Babel standalone. **`v2/src/bundle.jsx`(약 3,000줄)가 정본** — `index.html` → `adapter.js`가 동적 주입. `galaxy.jsx` 등 다른 src 파일은 참고용 조각.
- 행성 클릭 → `CompanyOverviewPanel` → ENTER CORPORATION → `setCorpOverlayTicker()` → **무명 인라인 오버레이 JSX**(bundle.jsx L2956 부근 — `CorpDossierOverlay`라는 이름의 컴포넌트는 없다)가 열림. 오버레이 구성은 3요소:
  - `<iframe src="../dossier/firm.html?ticker=<t>">` + `injectV2Theme(iframe)` (L2719-2832 부근)
  - **`OverlayAiChat` — 우측 고정 300px AI 채팅 사이드바** (L2988-2993, `context="finance"`) → **iframe 가용 폭 = 오버레이 폭 − 300px**
  - 하단 면책 푸터 "⚠ 과거 통계 기반 참고 정보" (L2995-3002)
- 오버레이 배경은 `backdrop-filter: blur(18px)`이고 그 밑에서 v2 셸 캔버스 rAF 루프(4곳: L399·700·1120·2002 부근)가 계속 돈다 → 성능 §8.
- v2/CLAUDE.md 제약: v1 수정 금지 · extract_data.py 로직 수정 금지 · 빌드 도구 도입 금지 · "injectV2Theme 무변경" — **마지막 항목은 이번 개편으로 규칙 개정** (Phase 2에서 v2/CLAUDE.md·DESIGN.md, Phase 7에서 ARCHITECTURE.md 이슈 #2의 injectV2Theme 서술까지 동시 갱신).

### 1.2 프로토타입 ①: kospi50_business_tabs.html (382KB, 1,275줄)
- 외부 의존성 0 (vanilla JS + 인라인 CSS). 좌측 기업 rail + 우측 상세 뷰 + 상단 자체 탭바(2개는 disabled).
- **`const DATA = [...]`(L612 부근)에 48개 기업 하드코딩** — rank 1~48. (파일명의 "kospi50"과 달리 실제 48개. **이 48개 집합 = `integration/dossier/data/firm_*.json` 48개와 티커 완전 일치** — 이것이 이 프로젝트의 기업 목록 SSOT다.)
- 각 항목: stock_code/corp_code(8자리)/latest_year 재무(**억원 단위**)/5년 history/snippets(DART 원문 발췌)/business_cards/report(rcept_no — 단 **079550 LIG넥스원은 rcept_no 결측**).
- 차트는 전부 CSS 바(sparkline·track·util-fill) — 라이브러리 불필요.
- 색: bg `#060914`, cyan `#41dcff`, teal `#36e5bd`, gold `#f7d56f`, violet `#9d81ff` → Cash Galaxy와 다르므로 토큰 치환 필요 (D5 매핑표).

### 1.3 프로토타입 ③: Cash Galaxy (원본 22MB / **editable 308KB**, 2,871줄)
- **정본 위계 (2026-07-08 리더 확정)**: ① 최종 정본 = **원본 `Cash Galaxy.html`**(Claude Design 산출물 — v4 md 프롬프트 이후의 수정까지 반영, 22MB 번들·폰트 임베드) ② **이식 작업 사본 = `Cash Galaxy.editable.html`**(원본의 자동 언번들 — 렌더·데이터 100% 동일 + NUDGE 편집 도구만 추가. 2026-07-08 핵심 수치·카피 샘플 대조로 동일성 확인) ③ 스타일 가이드 md = 문법·의도의 정본(자구·데이터 정본 아님). **자구·데이터 의문 시 원본 html이 판정 기준.** 이식 작업은 editable에서 한다(원본은 번들 포맷이라 직접 수정 불가).
- 스택: React + 자체 dc-runtime(`{{ }}` 보간, `<sc-for>`/`<sc-if>`), SVG + CSS 애니메이션. Canvas/Three.js/D3 없음. **상시 rAF 렌더 루프는 없으나 일회성 rAF는 있음**(smoothTo 스크롤 애니·scroll 스로틀·휠 스텝 네비, L587-609 부근) → Phase 1 검증에 휠·앵커 스크롤 포함.
- 데이터 (모두 `<script type="text/x-dc">` 내 JS 하드코딩, **9개 배열이 전부**):
  `KNOTS` 노드 **18개**(cash0·cash1 저수지 포함) · `brSpec` 분기 **11개**(cogs·sga·tax·op_ext·noncash·wc·int·icf·fcf·fx·cap — op_ext·noncash·fx는 `inflow:1`, noncash는 `dash:1`) · `IS`(strong 플래그) · `CFSEC`(**중첩 구조**: {id,title,total,raw,sign,note,role,small,items[]}) · `EQ`(hot 플래그) · `BSMINI`(전기/당기 자산·부채·자본·현금 2행) · `DEST`(가지 목적지 라벨 5건) · `ANNOS` 연결 주석 **20개**(viz 7종: waterfall/bars/delta/sectors/symmetric/steps/puddles, 색 참조 `barColor`/`d1col`/`gauges`) · `DISC` **미연결 주석 13개**(주1·2·3·4/29·5·14·15·16·18·26·28·31·34 한줄 요약 — **전용 disc 뷰 + goFlow/goDisc 네비 전환 내장**, L568-592 부근).
- 데이터 배열 밖 하드코딩도 존재(외부화 대상): **템플릿 마크업 8곳**(헤더 L75 · 게이지 2곳 L95/103 · 히어로 L120 · 도입 문단 L131-132 · 부문합 L360 · puddles 합계 L384 · 푸터 L390 — D4-2 목록이 정본) + 렌더 코드 `runSteps`의 CF 정산 수치 L708.
- **카운트 매핑**: KNOTS 18개 = 본류 매듭 15(번호 1~15) + 위성 2(6b·10b) + 자본 갈래(OCI) 노드 1. 스타일 가이드 B2의 "매듭"은 본류+위성 17항목을 가리킨다 — 골든의 copy 슬롯은 **KNOTS 18개 전부**(OCI 노드 카피는 editable 실물에서 승계).
- 디자인 토큰(=프로젝트 표준): `C = { mint:#74EEC6, cyan:#5CC7EA, gold:#E9C46B, coral:#EC8C6A, steel:#7590B0, hi:#eef4fb, mid:#8fa1b6, lo:#5a6a7d }`, bg `#05060d`, 폰트 **Pretendard + IBM Plex Mono**.
- **1360px 고정폭 + 자가 스케일 내장**: `zoom = Math.min(1, vw/1360)`을 rootStyle에 적용, resize 리스너로 갱신 (L712·L727). iframe 안에서는 innerWidth=iframe 폭이므로 그대로 동작 → **외부 scale 래퍼 추가 금지** (nav·범례·게이지가 전부 `position:fixed`라 transform 조상이 생기면 뷰포트 고정이 깨짐).
- 파일 말미 **`__NUDGE_PANEL` 위치조절 개발 도구(L2748-2871)가 무조건 자동 표시됨** — 이식 시 블록 통째 삭제 필수 (파일 자체 주석에도 "최종본에선 삭제" 명시).

### 1.4 데이터·AI 인프라
- **기업 목록 SSOT = dossier 48사** (`integration/dossier/data/firm_*.json` 파일명 집합 = business DATA 48개). 주의: `modules/disclosure/collector.py:37`의 `TARGET_CORPS`(49개)는 **다른 집합**(dossier에만 13개사·TARGET에만 14개사) — 이 파이프라인에 **사용 금지**. financial의 `batch.py:82 KOSPI_TOP_50`(이름 48개)이 dossier 집합과 일치. relation `top50.csv`(50행)는 제3의 집합.
- **사업보고서 원문은 어디에도 저장 안 됨.** disclosure `collector.py`가 `dart.document(rcept_no)`로 매번 메모리 로드 → 평문 정규식 슬라이싱(`_extract_annual_sections`, 4,500자/섹션·13,000자 총량 캡, **주석 등장 시 의도적 중단**(`_FINSTATE_STOP`)) → Groq 분석 결과만 저장. 이 파서는 우리가 필요한 "표 보존 + 주석 번호별 분할"과 목적이 반대 — **재사용 가치는 목차 키워드 목록 정도, 주석 파서는 신규 작성**.
- LLM 스택: Groq(llama-3.3-70b) + Gemini 2.5 Flash 폴백. **로컬 LLM(ollama/vLLM) 코드·설정 전무.**
- **정형 재무 숫자의 실제 보유 범위 (중요)**:
  - `financial_local`(financial.db): revenue·operating_income·net_income·자산/부채/자본·OCF/ICF/FCF **9계정, year=2025 단일 연도만**. cogs조차 없음.
  - `firm_<t>.json`: 5개년, 위 9계정 + cogs·유동자산/부채·장기차입 등 **14필드/년, 단위 원(遠)**.
  - **galaxy가 요구하나 양쪽 다 없는 계정**: 법인세·영업외/금융손익·OCI·비현금조정·운전자본변동·이자/법인세 실납부·환율효과·기초/기말현금·배당지급·자기주식취득(EQ표)·CF 세부 items·BSMINI 현금 → **DART 정형 API `fnlttSinglAcntAll`(전 계정)로 보강 수집 필요** (Phase 5. LLM 아님 — D7 유지 가능해지는 전제조건).
- DART 원문 바이너리 수집 전례: `modules/relation/ingest/filing.py:109` `dart_get_binary("document.xml", {rcept_no})`.
- `requirements.txt`에 pydantic(직접)·openai·playwright 없음 → Phase 6에서 추가.

---

## 2. 목표 아키텍처

```
[v2 셸 — bundle.jsx]
  행성 클릭 → CompanyOverviewPanel → ENTER CORPORATION
    → 오버레이(기존 무명 JSX 개조): 탭바 4개(Cash Galaxy 토큰) + OverlayAiChat(유지) + 면책 푸터(유지)
        탭① <iframe src="../dossier/business.html?ticker=t">   (lazy: 최초 활성화 시 mount)
        탭② <iframe src="../dossier/firm.html?ticker=t">        (기존, injectGalaxyTheme로 테마 교체)
        탭③ <iframe src="../dossier/galaxy.html?ticker=t">
        탭④ <iframe src="../dossier/notes.html?ticker=t">
      · mount된 iframe은 유지(keep-alive), 탭 전환은 표시 토글 — 방식은 Phase 2 스파이크로 결정(§8)
      · 각 페이지는 dossier/data/<종류>_<ticker>.json 만 fetch (단건)

[데이터 생산 — 신규 modules/report/ (Q1)]
  DART document API + fnlttSinglAcntAll → reports.db (원문·섹션·정형계정·파이프라인 상태)
    → LLM 추출·생성 하네스 (vLLM@A100 원격, OpenAI 호환 — §6)
    → 검증 3층 통과분 → modules/report/data/publish/{galaxy,notes}_<t>.json  (모듈 폴더 안에서 종료)

[서빙 — integration (pull, 단방향 유지)]
  integration/dossier/pull_report_json.py 가 modules/report/data/publish/ 를 read-only 복사
    → integration/dossier/data/  (탭 페이지들의 유일한 fetch 경로)
```

### 2.1 데이터 소싱 4원칙 (이 계획의 핵심 설계)

| 데이터 종류 | 출처 | LLM 사용 | 검증 |
|---|---|---|---|
| **본표 숫자 A** — 기존 확보분 (매출·영업이익·순이익·자산/부채/자본·3대 현금흐름·cogs 등 firm_*.json 14필드) | firm_*.json (5개년) | **금지** | 기존 값 그대로 |
| **본표 숫자 B** — 미확보분 (법인세·OCI·비현금조정·운전자본·이자/세금납부·환율효과·기초/기말현금·배당·자기주식·CF 세부) | **DART `fnlttSinglAcntAll` 정형 API** (Phase 5 보강 수집) | **금지** | API 응답 그대로 + 본표 내적 정합(CF 합산) |
| **주석 세부 표** (유형자산 증감, 판관비 구성, 부문별 실적 등 — 원문에만 있는 것) | 사업보고서 원문 → **LLM 구조화 추출** | 추출만 (계산·변형 금지) | 3층 검증 (§6.3) |
| **설명 산문** (노드 copy, 주석 head/body, DISC 한줄 해설) | **LLM 생성** | 생성 | 가이드라인(§7) + 인용 강제 + 샘플링 리뷰 |

> 계정→소스 매핑표(계정 단위 전수)는 Phase 5에서 `modules/report/CLAUDE.md`에 작성 — galaxy 노드 18개·IS/CFSEC/EQ/BSMINI 각 행이 A/B/LLM 중 어디서 오는지 1:1로 명시. §6.3 L2-③ 교차검증의 앵커도 이 표가 정의.

---

## 3. 기술 스택 결정

| 영역 | 선택 | 근거 |
|---|---|---|
| 프론트 | 현행 유지: 정적 HTML + React CDN(셸만) + dc-runtime(탭③) + vanilla(탭①②④) | v2 "빌드 도구 도입 금지" 규칙 + 이식 원칙. GitHub Pages 정적 호스팅 호환. 탭④는 신규 제작이지만 vanilla로 ③의 카드 시각 언어만 차용(§Phase 4 — dc-runtime 재사용은 결합도 때문에 비채택) |
| 탭 격리 | iframe (same-origin, `integration/` 하위) | 프로토타입별 CSS/JS 생태계 충돌 방지. ARCHITECTURE 이슈 #2에서 이미 채택된 패턴 |
| 데이터 포맷 | 탭별 per-ticker JSON (`integration/dossier/data/`) | firm_*.json 전례. 단건 fetch |
| 수집 | Python 3.11 + OpenDartReader(`dart.document`·`list`·`fnlttSinglAcntAll`) + BeautifulSoup/lxml | disclosure·relation의 기존 패턴 참조(코드 복제, import 금지) |
| 원문 저장 | SQLite `modules/report/data/reports.db` + 원문 파일 `modules/report/data/raw_cache/` | 모듈 표준 구조. **폴더명 `raw_cache/`는 기존 .gitignore 패턴(`modules/*/data/raw_cache/`)이 자동 커밋 제외** |
| LLM 서빙 | **vLLM on A100(원격, 주력)** — OpenAI 호환 API + `guided_json`(스키마 강제 디코딩). 하네스는 로컬 노트북(Windows)에서 실행하고 **LLM 호출만 A100 엔드포인트로** (llm.py는 OpenAI 호환 클라이언트 — base_url 교체만으로 백엔드 스왑). 노트북 단독 폴백: 로컬 GPU가 Intel Arc 140V(CUDA 없음)라 Ollama 본가 미지원 — llama.cpp Vulkan/IPEX-LLM으로 8B급 스모크만 | A100 1장이면 32B급 배치가 시간 단위로 끝남(§6.5·부록 C). 개발·스모크는 로컬, 배치는 A100 |
| 모델 | **기본 Qwen3-32B(AWQ/FP8)**, 대안 EXAONE-3.5-32B — A100 80GB에 여유 탑재(70B급 Q4도 가능하나 32B가 처리량 균형점). 비교군으로 14B·8B도 벤치마크에 포함. **Qwen3 계열은 thinking 기본값 — 반드시 비활성** (vLLM: `chat_template_kwargs.enable_thinking=false` — 버전별 상이, 착수 시 확인 / llama.cpp·Ollama: `think:false` / 공통 폴백: 프롬프트 `/no_think`) | 한국어+표 추출 강점. **최종 선정은 held-out 골든(§6.4) 점수로 결정** |
| 구조화 출력 | vLLM `guided_json`(주력) / llama.cpp server grammar(로컬 폴백) — OpenAI 호환 공통 + **pydantic 재검증** (`requirements.txt`에 pydantic·openai 추가+버전 고정, Phase 6) | 서버측 스키마 강제 + 클라이언트 이중 검증 |
| 파이프라인 검증 | pytest (tests/report/) + 골든 회귀 | 프로젝트 표준 |
| 렌더 검증(L3) | **playwright(파이썬) + chromium** (`pip install playwright && python -m playwright install chromium`, Phase 6) — 파이프라인 자동 게이트. 시각 검수는 별도로 ui-ux-reviewer 에이전트 | 48사 자동화에 수동 검수만으로는 불충분 |

---

## 4. 설계 결정 (D1~D12)

### D1. 탭바는 v2 오버레이(React)에, 탭 내용은 dossier HTML 4개에
- firm.html 안에 탭을 넣지 않는다 — firm.html 자체가 탭②일 뿐이다.
- 오버레이(무명 인라인 JSX)를 개조해 탭바 + iframe 4개(lazy mount, keep-alive)를 둔다.
- **토큰 구획**: 탭바와 iframe 내부 콘텐츠 = Cash Galaxy 토큰. 오버레이 외곽 크롬(헤더 "CORPORATION DOSSIER"·OverlayAiChat·면책 푸터) = 기존 v2 토큰 유지 (셸 무변경 최소침습).
- **OverlayAiChat은 4탭 공통 우측 사이드바로 유지**, 탭 전환 시 `context` prop만 갱신(business/finance/galaxy/notes). **면책은 기존 오버레이 푸터 1곳으로 일원화**(§7.1-7과 합치) — 탭 페이지 내부에 중복 배너를 넣지 않는다.

### D2. 파일 배치
```
integration/dossier/
├── firm.html                    # 탭② (기존 — 수정 최소)
├── business.html                # 탭① (신규 — kospi50_business_tabs 이식)
├── galaxy.html                  # 탭③ (신규 — Cash Galaxy.editable 이식)
├── notes.html                   # 탭④ (신규 제작 — ③의 시각 언어 차용)
├── theme-galaxy.css             # 공유 토큰 (C 팔레트 CSS 변수 + 폰트 선언)
├── extract_business_json.py     # 1회성: 프로토타입 DATA → business_*.json 48개
├── pull_report_json.py          # modules/report/data/publish/ → data/ 복사 (pull, 리더 소유)
├── assets/fonts/                # Pretendard·IBM Plex Mono woff2 (§Phase 0)
└── data/
    ├── firm_<t>.json            # 기존 48개
    ├── business_<t>.json        # 신규 48개
    ├── galaxy_<t>.json          # 초기 005930 1개 → 파이프라인 pull로 확장
    └── notes_<t>.json           # 초기 005930 1개 → 파이프라인 pull로 확장

modules/report/                  # 신규 모듈 (Q1, 리더 소유)
├── CLAUDE.md                    # 모듈 규칙 + 계정→소스 매핑표 + reports.db 비커밋 예외 사유
├── db.py · models.py · collector.py · sectioner.py
├── fs_enrich.py                 # fnlttSinglAcntAll 보강 수집 (§2.1 본표 B)
├── llm.py · schemas.py · extract.py · validate.py · publish.py · benchmark_extract.py
└── data/
    ├── reports.db               # ← .gitignore 신규 추가 (커밋 제외, 예외 사유 명시)
    ├── raw_cache/               # 원문 zip/html ← 기존 패턴이 자동 제외
    ├── corps.csv                # 48사 시드 (ticker,corp_code8,name) — 모듈 자체 보관
    ├── review/                  # 리뷰 큐 md + shots/*.png ← .gitignore 추가 (로컬 전용)
    └── publish/                 # 검증 통과 JSON (커밋 대상 — integration이 pull)
```

### D3. 디자인 표준 적용 방식
- `theme-galaxy.css` 하나에 C 팔레트를 CSS 변수로: `--cg-mint:#74EEC6; --cg-cyan:#5CC7EA; --cg-gold:#E9C46B; --cg-coral:#EC8C6A; --cg-steel:#7590B0; --cg-text-hi:#eef4fb; --cg-text-mid:#8fa1b6; --cg-text-lo:#5a6a7d; --cg-bg:#05060d;` + Pretendard/IBM Plex Mono `@font-face`.
- 탭①④: 페이지가 직접 link. 탭②(firm.html): **`injectGalaxyTheme()` 신설**(injectV2Theme 복제 후 팔레트만 C 기준) — firm.html 원본 CSS는 불변(v1 fallback이 같은 템플릿 사용). injectV2Theme 함수는 **삭제하지 않고 병존**(v1 경로·회귀 대비), corp 오버레이 호출부만 교체.
- 탭③: Cash Galaxy 자체가 표준이므로 그대로 (내부 hex를 CSS 변수로 바꾸지 않는다 — 이식 원칙).

### D4. Cash Galaxy 이식 = editable 작업 사본 기반 + 데이터 외부화 (범위 명세 — 정본 위계는 §1.3)
- `Cash Galaxy.editable.html` → `dossier/galaxy.html` 복사 후:
  1. **8개 데이터 배열**(KNOTS·brSpec·IS·CFSEC·EQ·BSMINI·DEST·ANNOS) → `galaxy_<t>.json` fetch로 치환. **DISC 배열은 `notes_<t>.json`으로 이전** (D9 — ③의 disc 뷰 제거와 세트).
  2. **템플릿 하드코딩 8곳**(헤더 L75·게이지 2곳 L95/103·히어로 L120·도입 문단 L131-132·부문합 L360·puddles 합계 L384·푸터 L390) → `{{ }}` 바인딩 치환 (JSON 필드: corp.name·fiscal_label·cash_gauge·hero_line·intro_lines·sector_sum_line·puddles_sum_line·footer_line). **이 8곳 목록이 정본** — 아래 파라미터화 3번과 같은 작업.
  3. **runSteps의 CF 정산 수치(L708)** → JSON `cf_recon` 배열로 이동.
  4. **`__NUDGE_PANEL` 블록(L2748-2871, `__NUDGE_PANEL_END` 마커까지) 삭제** + 파일 상단 편집 안내 주석 정리.
  5. 폰트 CDN link 2개 → 로컬 `assets/fonts/` 참조.
  6. `?ticker=` 파싱(기본 005930), fetch 실패 시 "데이터 준비 중" 패널(가짜 숫자 노출 금지).
- dc-runtime·React 인라인·스타일 객체·geometry 계산(trunk 등)·C 팔레트 상수는 **코드에 그대로** (JSON은 `color_key` 문자열만 — barColor/d1col/gauges 색 참조 포함 전부).
- **폭 대응: 아무것도 추가하지 않는다** — 내장 zoom(`Math.min(1, vw/1360)`)이 iframe 폭 기준으로 동작. Phase 1에서 좁은 폭(오버레이−300px)의 zoom 동작과 CSS `zoom` 속성의 Chrome/Edge 렌더만 검증.
- **확장 대비 파라미터화 (부록 A 감사에서 확정된 템플릿 수정 5곳 — 데이터 외부화와 같은 시점에 수행)**:
  1. `buildGeo`의 `'cap'` 분기 하드참조(L463-465)에 `if(capTip)` 가드 — cap 분기 없는 기업에서 페이지 백지 방지 (유일한 즉사 crash).
  2. steps viz·runSteps 칩의 상수 45.2/52.4/9.6/2.7(L698-708) 파라미터화. **관계 확정**: 트렁크 runSteps 칩 = 최상위 `cf_recon`, 주27 카드 steps viz = `ANNOS[주27].steps` — 필드 2개·값 동일(검증기가 상호 대조).
  3. markup 고정 삼성 텍스트 placeholder화 = **위 이식 2단계의 8곳 목록과 동일 작업** + triad 칩(L195-204, dead markup) 삭제.
  4. `'noncash'` 유입 파티클 가드(L634-637): 해당 분기 없을 때 offsetPath 무효로 (0,0)에 빛점 고착되는 버그 방지 — `dash:1` 플래그 기반으로 일반화.
  5. DEST tip 가드(L642): `if(!tip) return null` 1줄 (br이 brSpec에 없으면 crash).
  - (선택) bars/symmetric의 0-나눗셈 NaN 가드 — 생성기가 0 항목을 제거하므로 방어용.

### D5. business_tabs 이식 = 단일 기업 뷰로 변형 + 토큰 스왑
- 좌측 rail(검색·정렬)과 상단 자체 탭바 제거 — 기업 선택은 v2 우주, 탭은 오버레이 소관. `?ticker=`가 유일한 입구.
- `const DATA` → `extract_business_json.py`로 `business_<t>.json` **48개** 생성 (extract_firm_json.py 전례).
- 색 치환 매핑표 (초안 — Phase 3 시각 검증으로 확정):

| business_tabs | → Cash Galaxy | 용도 |
|---|---|---|
| `#060914` (bg) | `#05060d` | 배경 |
| `#41dcff` | `#5CC7EA` (cyan) | 주 강조 |
| `#36e5bd` | `#74EEC6` (mint) | 보조 강조 |
| `#f7d56f` | `#E9C46B` (gold) | 경고·자본 |
| `#9d81ff` | `#7590B0` (steel) | 중립 (시각 확인 후 확정) |
| `#edf6ff / #b8c6d9 / #7d8ba3` | `#eef4fb / #8fa1b6 / #5a6a7d` | 텍스트 3단 |
| `Inter, Pretendard, ...` | `Pretendard` + 숫자 `IBM Plex Mono` | 폰트 |

### D6. ⚠️ 사업보고서 파이프라인 위치 = 신규 `modules/report/` (Q1)
- **경계 규칙 검토**: "모듈은 데이터 생산, integration은 표현" → 원문 저장·LLM 추출은 데이터 생산이라 integration 불가. disclosure(B 소유) 확장은 "개별 폴더는 담당자만 수정" 규칙상 리더가 못 함 → 리더 소유 신규 모듈이 유일한 정합 경로.
- **부채 명시**: DART 수집 경로가 늘어난다 — 재무 이중수집(부채 #1)에 `fnlttSinglAcntAll` 추가, 원문 수집도 3중(disclosure 메모리 로드/relation document.xml/report 신규). **ARCHITECTURE.md "알려진 문제"에 항목 추가 + B·C 담당자 공유.** 향후 disclosure가 report의 원문 캐시를 읽는 통합(⒝형)을 열어둔다.
- **루트 CLAUDE.md 모듈 표 등재 시 반드시 `python scripts/sync_codex.py` 재실행 → AGENTS.md 갱신분 함께 커밋** (CI가 `--check`로 강제, `.github/workflows/ci.yml:27`). integration/v2/CLAUDE.md·modules/report/CLAUDE.md는 미러 대상 아님(재실행 불요).

### D7. LLM은 "숫자를 만들지 않는다"
- 본표 A·B(§2.1)는 코드가 채운다 — LLM 호출 전에 "부분 완성 JSON"을 만들고 LLM은 빈 슬롯(주석 표·산문)만 채운다. LLM이 본표 숫자를 건드릴 경로 자체가 없음.
- LLM 추출 수치는 **원문 표기 그대로의 `raw_mn`(백만원 정수)만** — 표시 문자열("205.9")은 코드가 결정적 규칙(백만원→조, 소수 1자리)으로 생성. 산문 속 숫자는 입력 JSON에 있는 값만 인용 가능(검증기 대조).

### D8. 하네스가 품질을 소유한다
- 골든 테스트(§6.4)가 프롬프트·모델 선택을 판정. 모든 산출물은 3층 검증(§6.3) 통과분만 publish. 불통과는 `modules/report/data/review/`에 리뷰 큐 md+스크린샷 자동 생성.

### D9. 탭③/④ 역할 분담 (Q2)
- 탭③ = 은하수 + **연결 주석(ANNOS) 20건**. 이식 시 **③의 내장 disc 뷰·goDisc 네비 버튼을 제거**(이식 원칙의 명시적 예외 — 역할이 탭④로 승격됐기 때문. 제거 대신 "주석 더보기 → ④ 탭" 안내 문구로 대체).
- 탭④ = **DISC 13건 승계 + 이후 파이프라인이 보강하는 기타 주석**. covered 판정 = `ANNOS.anchor ∪ DISC.tag` 기준으로 ③∩④=∅ 검증.
- **타기업의 ANNOS/DISC 배정은 §7.3 라우팅 규칙**("억지 매핑 금지")이 판정 — 삼성의 20:13 구성을 그대로 강제하지 않는다 (기업마다 n:m이 달라지는 것이 정상).
- DISC의 삼성 숫자("21.6조"·"6,605원" 등)도 notes_<t>.json으로 외부화 — galaxy.html의 "삼성 숫자 잔존 0건" DoD의 전제.

### D10. 타사 확장 시 은하수 레이아웃 정책 (Q3 — 부록 A 데이터 감사로 규칙 확정)
- 노드 t/size·분기 len/w는 삼성 흐름 크기의 시각 인코딩(cogs w:58 vs int w:7)이다. 47개 타사분은 **생성기가 재무 값 비율로 결정적 산출** — **√스케일**(스타일 가이드 A3·실물 굵기 부합 — 선형이면 기하 왜곡: sga 실물 40 vs 선형 25): `w = clamp(round(58 × √(항목/매출 ÷ 삼성 cogs/매출)), 6, 58)` + t·len은 삼성 골든의 상대 배치 유지(같은 side 분기 간 t 간격 ≥0.03, side 교대). **Phase 6에서 삼성 골든 w 역산으로 계수 검증(허용 ±2) — 골든 회귀는 raw_mn만 보므로 기하는 이 검증이 잡는다.** LLM·수작업 금지. trunk 기하(코드 고정)는 그대로 둔다.
- **판정·산출 소유**: 스코프아웃 부호 판정과 레이아웃 산출 함수는 `publish.py` 소유, **§6.1 루프가 초입에서 호출**(fs_enrich 후 부호 데이터 보유 — 스코프아웃 기업에 LLM 호출 낭비 방지).
- **부호 처리 3단계 (감사 결과 — 초안의 "재무활동 순유입 스코프아웃"을 그대로 적용하면 48사 중 24사가 탈락하므로 완화)**:
  - **inflow 전환으로 흡수 (스코프아웃 아님)**: fcf>0(차입 조달, 24사)·icf>0(자산 회수, 6사)·bridge(OCF−NI)<0 — brSpec의 기존 `inflow`/`dash` 플래그로 방향·색 전환 + DEST 문구 조건 분기("주주에게 돌려줌"→"차입으로 조달"). cogs 결측(NAVER·카카오·SKT 등 비금융 3사)은 cogs·gp·sga 분기·노드 생략(렌더 코어는 배열 주도라 수용, D4-1 cap 가드가 전제).
  - **스코프아웃 (탭③ "준비 중", ①②④ 정상)**: 금융업 **8사**(KB금융·신한지주·하나금융지주·우리금융지주·삼성생명·삼성화재·메리츠금융지주·미래에셋증권) + SK스퀘어(투자지주, Phase 7 판단) + **최신연도(2025) 단년 기준** OI<0(삼성SDI) · OCF<0 비금융(현대차·현대건설·고려아연·LIG넥스원·포스코퓨처엠) · **NI<0**(SK이노베이션·LG화학 — 영업흑자여도 순손실이면 허브 노드 붕괴). **판정은 반드시 최신연도 단년** (5개년 아무 해 기준으로 읽으면 제공 가능 기업이 7사로 급감).
  - **예상 분포 (2025 부호 기준)**: A 값만 다름 ~14사 / B inflow·생략 규칙으로 흡수 ~16-18사 / C 스코프아웃 ~16-18사 → **탭③ 제공 목표 30~32사**.
- 값 정규화: 모든 w·len·size는 abs 값(방향은 inflow/side/색으로), 0·미미(<0.05조) 항목은 배열에서 제거, reservoir res·노드 size는 sqrt 스케일로 항상 산출.

### D11. 리더 보고 절차 — "템플릿으로 안 되는 것"의 공식 에스컬레이션 (리더 지시)
파이프라인 산출물의 상태를 3단계로 분리한다. **템플릿 부적합은 리뷰 큐와 별개의 공식 보고 대상**이다.

| 상태 | 의미 | 처리 |
|---|---|---|
| `AUTO_PASS` | 3층 검증 통과 | 자동 publish |
| `NEEDS_REVIEW` | 내용 검증 실패 (인용 불일치·산술 불일치 등 — 데이터 품질 문제) | `data/review/<corp>_<target>.md` + 스크린샷. 리더가 개별 승인/수정 |
| `TEMPLATE_MISMATCH` | **구조적 부적합** — 삼성 템플릿이 이 기업을 표현할 수 없음 (필수 노드 결측, 음수/역방향 흐름, 특이 부문 구조, D12 자동 규칙 범위 초과) | 해당 기업·탭 publish 중단 + **배치 보고서에 필수 기재. 리더 결정 없이 진행 금지** |

- **배치 보고서**: 매 배치 실행 종료 시 `modules/report/data/review/_BATCH_REPORT.md` 자동 생성 — ① 요약표(48사 × 타깃별 상태) ② TEMPLATE_MISMATCH 목록(기업·사유·원본 수치·제안 대안: 스코프아웃/템플릿 확장/규칙 추가) ③ NEEDS_REVIEW 건수·링크. 실행 콘솔에도 동일 요약 출력.
- 리더는 TEMPLATE_MISMATCH 항목별로 ⓐ 스코프아웃 확정 ⓑ D12 규칙 추가(자동화 확장) ⓒ 템플릿 수정 승인 중 하나를 결정 → 결정 내용을 이 문서 §9에 누적 기록.

### D12. 확장 가변성 정책 — 미세 UI 변형은 보고 없이 자동 흡수 (리더 지시)
> 판정 근거: 프로토타입 렌더 코드 전수 감사 (부록 A). **감사 결론: 렌더 코어(분기 경로·노드 배치·패널·viz 카드·스크롤 씬)는 전부 배열 map 루프라 개수·구성 가변에 구조적으로 견딘다.** 원칙: 기업별 미세 차이는 ① 템플릿의 배열 주도 렌더(+D4 수정 5곳) + ② 생성기의 결정적 규칙 두 겹으로 흡수하고, 두 겹으로 안 되는 것만 TEMPLATE_MISMATCH(D11)로 승격. 개별 기업 수작업 미세조정 금지(48사 확장이 무너짐).
- **생성기 계약 (galaxy — 부록 A 확정)**: ⓐ 표준 id 어휘 유지(rev·cogs·gp·sga·op·ni·noncash·wc·ocf·icf·fcf·fx·cash0·cash1 등 — hlFor 하이라이트·runIdx 칩이 이 어휘에 결합) ⓑ KNOTS 첫/끝 원소 = 기초/기말 reservoir 관례 ⓒ 모든 노드 br ⊆ brSpec id, br 없으면 t 필수 ⓓ DEST의 br ⊆ brSpec id ⓔ 같은 side 분기 t 간격 ≥0.03 ⓕ 미니라벨 ≤12자·val ≤7자 축약(초과 시 생성기가 단축형 생성) ⓖ 0·음수 항목은 제거 또는 abs+inflow 인코딩(D10) ⓗ 행 수 상한: IS≤10·EQ≤8·CF 섹션당 items≤5·부문 2~6개.
- **구조 불변식 (스타일 가이드 승계 — 모든 기업 공통, 생성기가 보장)**: ⓘ OCI는 순이익 매듭에서 나오지 않는다 — 은하수 밖에서 자본 갈래로 직접 합류하는 시안 점선 ⓙ 매출은 기초현금 저수지에서 나오지 않는다 — 독립 발원, 저수지에는 순증 델타만 합류 ⓚ 곁다리(영업외손익·이자세금 실납부)는 본류 매듭과 같은 크기 금지 — 위성 노드(sat) ⓛ CF 3활동은 동등 위계(들여쓰기 금지), 자본변동표에 기말 BS 혼입 금지 ⓜ 모든 유출 분기에 도착지 라벨(dest) — 화면 밖으로 그냥 흘리지 않는다 ⓝ 색은 §7.2 의미 문법으로만 배정 ⓞ 대분류 = 하위 합 정합(어긋나면 빠진 항목 채우거나 "그 외" 행), 저수지 방정식은 개별 매듭 합산이 아니라 **순증 델타 칩 1개**로 제시(반올림 오차 은닉).
- **생성기 계약 (business — 부록 A 확정)**: business_cards 2~4개(5개 이상 금지 — 겹침) · kind는 21종 중 지정 · 금융사는 display_category에 '금융업' 포함 · dart_url 또는 rcept_no 중 하나는 필수. 결측 필드는 키 생략(폴백이 48사 실데이터로 실증됨 — raw_moves 47사 결측도 정상 렌더).
- **사전 sanity 검증 (생성기 전단)**: rev≥cogs 정합·YoY 10배 점프 감지·단위 교차 검증 — 부록 A에서 실데이터 오류 실증(한화에어로 2025 rev 0.22조 vs cogs 21.25조, R10). 오류는 은하수 기하에 그대로 그려지므로 검증 없이 생성 금지.
- Phase 1에 **가변성 스파이크** 포함: 골든 JSON의 합성 변형 3종(분기 2개 제거판 / 부문 2개 축소판 / 라벨 2배 연장판)을 galaxy.html에 렌더해 깨짐 없음을 확인 — "막힘없이 확장"의 사전 증명.

---

## 5. Phase 계획 (총 8단계)

> 공통: 브랜치 `feat/dossier-tabs-p<N>`(dev에서 분기) → Phase 단위 PR → dev. Phase 종료 시 이 문서 체크박스 + `integration/v2/PROGRESS.md` 갱신.
> 로컬 구동: 저장소 루트에서 `python -m http.server 8000` → `http://localhost:8000/integration/v2/index.html`.

### Phase 0 — 준비 (0.5~1일)
- [ ] **선행 조건 2건 (순서 고정)**: ① ✅ 이 계획서 + CASH_GALAXY_STYLE_GUIDE.md 2개를 `chore/post28-cleanup` 브랜치에 같은 커밋으로 커밋 (2026-07-08 완료) ② 그 브랜치를 dev로 머지 — 계획서가 인용하는 `scripts/sync_codex.py`·CI `--check`·본 문서 2개가 이 브랜치에 있어, 머지 전에 dev에서 분기하면 D6·Phase 5가 파일 없음으로 실패한다. 이후 dev 최신화, `feat/dossier-tabs-p1` 분기.
- [ ] **타 담당자 공유 이슈 2건 생성**(gh issue): ① R10 — `firm_012450.json` 2025 revenue 단위/파싱 오류 재수집 요청(담당 A, 근거 수치 첨부) ② R6 — DART 수집 다중화 부채 공유(B·C). 이슈 링크를 §9 해당 행에 기입.
- [ ] 폰트: **Pretendard 1.3.9 고정**(editable CDN과 동일 버전)의 `web/static` 서브셋에서 **사용 웨이트(400/500/600/700)만** 복사 → `dossier/assets/fonts/pretendard/` (다파일 허용 — pyftsubset 단일화는 하지 않는다). IBM Plex Mono는 css2 응답에서 **웨이트당 latin woff2 1개(총 3개)** — 숫자·라틴 라벨 전용이라 충분. 검증: 임시 `test_fonts.html`(두 폰트 지정 문단)을 로컬 서버로 열어 DevTools Network에서 woff2 200 확인 후 삭제.
- [ ] `theme-galaxy.css` 작성 (D3 변수 + @font-face).
- [ ] **스키마 확정 (§5.1은 골격 초안 — 실물이 정본)**: `Cash Galaxy.editable.html`의 9개 배열(KNOTS·brSpec·IS·CFSEC·EQ·BSMINI·DEST·ANNOS + DISC는 notes 스키마로) + **템플릿 8곳(D4-2 목록)** + cf_recon을 **전수 역산**해 스키마를 확정하고 §5.1을 갱신. ⚠️ §5.1 예시를 그대로 베껴 검증 코드를 먼저 짜지 말 것 — 역산이 먼저다.
- [ ] **골든 데이터**: 위 스키마로 `dossier/data/galaxy_005930.json` + `notes_005930.json`(DISC 13건 승계) 수작업 작성. 모든 수치에 `raw_mn` 병기(표시 문자열은 보존용으로만). **[CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md) Part B(B1 검증 수치·B2 매듭 카피·B3 매핑표·B4 DISC 목록)와 대조**. **우선순위 규칙**: 수치가 어긋나면 스타일 가이드 B1 우선(PDF 재대조 완료본) / **카피 자구·connect·ret 필드는 프로토타입 html 실물 우선**(정본=원본 `Cash Galaxy.html`, 작업 사본=editable — 데이터 동일 확인됨. B2는 문체 기준, B3는 개념 지도 — 이 둘로 실물 필드를 "교정"하지 말 것). 시각 동등성 비교의 텍스트 기준 = 골든 JSON.
- [ ] 필수 키 체크 스크립트 `tests/report/check_golden_keys.py` 작성 (pydantic 아님 — 단순 키·enum·산술 스모크. pydantic 정식 모델은 Phase 6에서 이 스크립트를 승격).
- [ ] 골든 자체 정합성 검토 — 원본의 교육용 단순화 항목에 플래그를 달아 검증 규칙(§6.3)과 모순되지 않게 정리. **확인된 예외 4건(전수)**: 주22(`overlap` — bars 부분합>총계), 주25(`residual` +1.1조 — 11.5−8.4≠4.3), 주20(순증형 워터폴 — 기초/기말 앵커 면제 플래그), 주10(`residual` −0.5조).
- DoD: `python tests/report/check_golden_keys.py` 통과 + 두 골든 JSON이 §5.1 확정판과 일치.

#### §5.1 galaxy_<ticker>.json 스키마 (골격 — Phase 0에서 실물 전수 역산으로 확정)
```jsonc
{
  "schema_version": 1,
  "corp": { "ticker": "005930", "name": "삼성전자", "fiscal_label": "연결재무제표 제57기",
            "fiscal_year": 2025, "rcept_no": "20260310002820", "unit": "백만원" },
  "strings": { "hero_line": "…", "intro_lines": ["…", "…"], "sector_sum_line": "…",
               "puddles_sum_line": "…", "footer_line": "…" },   // D4-2의 8곳 대응
  "cash_gauge": { "begin": 53.7, "end": 57.9, "begin_raw_mn": 0, "end_raw_mn": 0 },
  "cf_recon": [ ["45.2","…"], ["+52.4","…"] ],          // 舊 runSteps
  "nodes": [   // 위치 지정 3종: t(트렁크 위치) | br(가지 끝 앵커) | reservoir+res(저수지)
    { "id": "rev", "t": 0.107, "kind": "income", "label": "매출", "val": "333.6조",
      "raw": "333,605,938", "raw_mn": 333605938, "note": "주30", "copy": "…", "size": 26 },
    { "id": "cash0", "reservoir": true, "res": 53.7, "...": "side/sat/below/delta 필드 실물대로" }
  ],
  "branches": [ { "id": "cogs", "t": 0.164, "side": -1, "len": 150, "w": 58,
                  "color_key": "coral", "inflow": 0, "dash": 0 } ],   // 11개
  "tables": {
    "is": [ { "id": "is.rev", "k": "매출액", "v": "333.6", "raw": "333,605,938", "raw_mn": 0,
              "sign": "", "note": "주30", "strong": 0 } ],   // strong은 실물 0|1|2 2단계, items엔 muted 플래그도 존재
    "cf": [ { "id": "cf.op", "title": "영업활동", "total": "…", "raw": "…", "raw_mn": 0,
              "sign": "", "note": "…", "role": "…", "small": "…",
              "items": [ { "k": "…", "v": "…", "raw_mn": 0, "hot": false } ] } ],  // 중첩(CFSEC)
    "eq": [ { "k": "배당", "v": "…", "raw_mn": 0, "hot": true } ]
  },
  "bs_mini": [ { "kor": "전기말", "assets": 0, "liab": 0, "equity": 0, "cash": 0 } ],  // 2행, raw_mn — 필드명은 실물(kor) 기준
  "dest": [ { "id": "…", "label": "…" } ],               // 5건
  "annotations": [   // ANNOS 20건. 색 참조는 전부 color_key 문자열
    { "anchor": "n10", "tag": "주10 유형자산", "core": 1, "connect": "⑨·⑫", "ret": "noncash",
      "viz": "waterfall", "head": "…", "body": "…",
      "wf": [ { "v": "205.9", "raw_mn": 205945209, "label": "기초", "cls": "base" } ],   // raw_mn은 원문 값 그대로 — 표시값 역산 금지(D7)
      "flags": [], "source_quotes": ["…"] } ],           // LLM 산출물엔 필수, 골든엔 선택
  "meta": { "generated_by": "manual|pipeline@<model>@<prompt_ver>", "validated": true, "review_flags": [] }
}
```
`notes_<t>.json`: `{ "disc": [ { "tag": "주16", "title": "…", "desc": "…", "category": "재무|영업|기타", "viz": null|…, "data": …, "raw_mn": …, "source_quotes": [...] } ], "meta": {...} }` — 초판은 DISC 13건 수준(목록+해설), 세부 표·viz는 Phase 6 이후 보강. `category`는 탭④ 상단 필터용 — 삼성 13건 배정은 Phase 0 골든에서 리더가 확정, 타사분은 §7.3 라우팅 시 LLM이 아니라 코드 규칙(주석 번호·제목 키워드)으로 배정. `ret`/`connect`류 필드는 ④에서 비표시(또는 ③ 딥링크 변환).
**단위 매핑표**: business JSON=억원 · firm JSON=원 · galaxy/notes `raw_mn`=백만원 · 표시 문자열=조(소수 1자리, 코드 생성). 변환은 전부 코드.

### Phase 1 — 탭③ 이식: galaxy.html (1.5일)
- [ ] D4의 6단계 그대로 수행 (8배열 외부화 + DISC→notes 분리 + 템플릿 8곳 바인딩 + cf_recon + NUDGE 삭제 + 폰트 로컬 + ?ticker=).
- [ ] **D4 확장 파라미터화 5곳 수행** (cap 가드 · steps/cf_recon 파라미터화 · 8곳 placeholder · noncash 파티클 가드 · DEST tip 가드) — 데이터 외부화와 같은 커밋에서.
- [ ] disc 뷰·goDisc 네비 제거 → "④ 탭 안내" 문구 (D9).
- [ ] dc-runtime의 async 데이터 수용 최소 변경 (데이터 로드 후 하이드레이션 시작 — 로직 재작성 금지). **첫 반나절 스파이크로 실현성 확인** — 불가 시 폴백 R3(§9).
- [ ] **가변성 스파이크 (D12)**: 골든 JSON 합성 변형 3종(**cap·noncash 분기 제거판** — D4 가드 3건 검증 겸 / 부문 2개 축소판 / 라벨 2배 연장판)을 렌더해 깨짐 없음 확인. 부록 A의 blocker/major 지점이 실제로 방어되는지 이때 실증.
- 검증: ① `galaxy.html?ticker=005930` 단독 열기 → **원본 `Cash Galaxy.html`과 시각 동등성**(ui-ux-reviewer 스크린샷 비교 — 단 **NUDGE 패널 부재·disc 뷰 부재는 의도된 차이**로 명시) ② **주석 카드 20개 전부** 렌더 + 노드 18·분기 11 ③ 휠 스텝 네비·주석 앵커 스크롤·ret 버튼 동작 ④ 콘솔 에러 0(단 dc-runtime 자리표시자 경고 9건은 정상) ⑤ 좁은 폭(1140px)에서 내장 zoom 동작.
- DoD: 시각 동등 + `galaxy.html`에서 grep으로 삼성 숫자·`__nudgePanel` 잔존 **0건**.

### Phase 2 — v2 오버레이 4탭 셸 (1일)
- [ ] 오버레이(무명 JSX, bundle.jsx L2956 부근) 개조: Cash Galaxy 토큰 탭바(①사업·기업 ②EQS ③현금 은하수 ④주석 더보기) + iframe 4개 lazy mount + keep-alive. **OverlayAiChat 유지**(context prop 탭별 갱신), **면책 푸터 유지**(D1).
- [ ] **표시 토글 스파이크**: `display:none` vs `visibility:hidden + position:absolute; left:-9999px`(뷰포트 유지) 비교 — 재표시 시 galaxy의 vw 기반 zoom·스크롤 위치가 정상 복원되는 쪽 채택 (display:none은 내부 치수 0으로 재계산 위험).
- [ ] **오버레이 열림 동안 셸 rAF 일시정지** (또는 오버레이 배경 불투명화로 backdrop-filter 제거) — §8.
- [ ] `injectGalaxyTheme()` 신설, corp 오버레이 호출부만 교체 (D3).
- [ ] 탭 활성화: **Phase 2 시점 = 전 기업 ② 활성, 삼성만 ③ 추가 활성, ①④는 "준비 중" 패널.** (Phase 3 머지 후 ① 48사 활성, Phase 4 후 ④ 삼성 활성.)
- [ ] `integration/v2/CLAUDE.md`("injectV2Theme 무변경" 규칙 → 4탭·injectGalaxyTheme 체제로 개정) + `DESIGN.md`(Dossier 섹션 순서) 갱신.
- 검증: 탭 전환 왕복 20회 — 재로드 없음(Network 탭), 전환 체감 <200ms, 콘솔 에러 0, 재표시 후 ③ 스크롤·zoom 정상. v2 우주 셸 픽셀 변화 없음.
- DoD: 삼성 기준 ②③ 완동 + ①④ 자리, 오버레이 열림 중 셸 rAF 정지 확인.

### Phase 3 — 탭① 이식: business.html (1~1.5일)
- [ ] `extract_business_json.py`: 프로토타입 `const DATA` → `business_<t>.json` **48개** 무손실 추출.
- [ ] `kospi50_business_tabs.html` → `dossier/business.html`: rail·자체 탭바 제거, `?ticker=` 단일 기업 렌더, DATA → fetch 치환, 토큰 스왑(D5 매핑표 — 레이아웃·마크업 구조 불변).
  - **부트스트랩 절제 필수 (부록 A)**: rail DOM만 지우면 `$('#searchInput')` 등 리스너(L1260-1271)가 null TypeError로 즉사해 패널 백지 — `listRows`(L1227-1235)·`selectByCode`(L1255-1259)·이벤트 바인딩을 함께 삭제하고 `render(선택 기업)` 호출만 남긴다. workspace grid 320px 컬럼(L72)을 1fr 단일로. render 파이프라인 자체는 rail 무의존이라 이 기계적 절제로 충분.
  - **업종 lens 우선순위 수정 (부록 A — 현행 48사에서도 오분류 실증)**: `industryKey`(L734-758)의 매칭 순서에서 통신·건설·소비재 패턴을 전력(power)·소재보다 선순위로 재배열 — coarse한 sector 문자열('통신/유틸리티/…')의 '유틸리티'가 power에 선매치되어 SK텔레콤·현대건설·KT&G가 오분류되는 버그. 수정 후 48사 lens 배정표를 스모크에 포함.
- [ ] 탭① 오버레이 연결 + 48사 활성화.
- 검증: 48개 ticker 순회 스모크 스크립트(fetch 200 + 필수 키) + 3사(삼성·SK하이닉스·현대차) ui-ux-reviewer 시각 검수(Cash Galaxy 톤 이질감).
- DoD: 48개 기업 전부 탭①이 실데이터로 뜬다.

### Phase 4 — 탭④ 신규 제작: notes.html (1~1.5일)
- [ ] `notes.html` **신규 제작**(vanilla): ③의 주석 카드 시각 언어(CSS 토큰·카드 구도)를 차용하되 **렌더러는 vanilla 재작성**(dc-runtime 결합 때문 — 이식이 아니라 신규 페이지이므로 원칙 위반 아님). 목록형 레이아웃 + 상단 필터(전체/재무/영업/기타).
- [ ] `notes_005930.json` 초판 = Phase 0 골든(DISC 13건 승계). 세부 표·viz 보강은 Phase 6 산출물로.
- [ ] 탭④ 연결(삼성 활성).
- 검증: ③과 나란히 디자인 동질성 검수 + ③∩④=∅ 스크립트(ANNOS.anchor ∪ DISC.tag 기준, D9).
- DoD: 삼성전자 4탭 전부 실데이터 완동. **여기까지가 "이식" 마일스톤 — dev 머지 후 배포 URL 확인.**

### Phase 5 — modules/report/ 수집 파이프라인 (2일 — Q1 승인 완료, 착수 가능)
- [ ] 모듈 뼈대 생성(D2 트리) + `data/corps.csv` 시드 48행(ticker,corp_code8,name — 생성 시점에 dossier 목록에서 1회 복제해 자체 보관, 이후 모듈 내부 SSOT).
- [ ] `models.py` (reports.db):
  - `report_raw(rcept_no PK, ticker, corp_code8, corp_name, fiscal_year, fetched_at, raw_path)`
  - `report_section(id, rcept_no FK, section_key, note_no, title, text_html, text_md, char_len)` — **text_md = LLM 투입용 변환본 그대로 저장** (source_quote 검증 기준 텍스트, §6.3)
  - `fs_account(rcept_no, sj_div, account_id, account_nm, amount, currency)` — fnlttSinglAcntAll 결과 (§2.1 본표 B)
  - `pipeline_state(rcept_no, target, stage, status, attempts, error, updated_at)` — stage: `FETCHED→SECTIONED→ENRICHED→EXTRACTED→VALIDATED→REVIEWED→PUBLISHED`, status: `AUTO_PASS|NEEDS_REVIEW|TEMPLATE_MISMATCH(+사유)` (D11)
- [ ] `collector.py`: corps.csv 순회 → `dart.list(corp_code, 사업보고서)`로 최신 rcept_no 조회(**rcept_no를 외부 JSON에서 가져오지 않는다** — 역방향 의존 회피 + 079550 결측 대응) → `dart.document`/document.xml 수집 → `raw_cache/` 저장. idempotent(재실행 skip).
  - **정정공시 stub 폴백 (부록 B-2에서 실증)**: 최신 rcept의 `sub_docs`에 "사업의 내용"이 없으면(정정신고 stub — 한화에어로 20260319000633이 subs 2건) 직전 사업보고서 rcept로 폴백하되, **정정 대상 항목이 재무·주석이면 정정본과 원본을 병합**(정정 우선). 판정 로직: `sub_docs ≥ 30건 && has(사업의 내용)`.
- [ ] `fs_enrich.py`: fnlttSinglAcntAll 48사 수집 → fs_account. **계정→소스 매핑표를 modules/report/CLAUDE.md에 작성** (§2.1).
- [ ] `sectioner.py`: **sub_docs 목차 기반** (부록 B 스파이크로 확정 — 정규식 슬라이싱 불필요). `dart.sub_docs(rcept_no)`가 정형 목차 57~58건을 반환하며 삼성·하이닉스 구조 동일: "II. 사업의 내용" 하위 7절(→business 스니펫), "III.3 연결재무제표 주석"(→galaxy·notes의 주석 원문, **별도 서브문서로 존재**), "IV. 이사의 경영진단"(→MD&A). 필요한 서브문서만 다운로드 → 주석 서브문서 내부를 주석 번호(N. 제목) 단위로 2차 분할 → 표는 HTML 보존 + 마크다운 변환본 text_md 동시 저장.
- [ ] `.gitignore` 갱신: `modules/report/data/reports.db`·`modules/report/data/review/`·**루트 `docs_cache/`(OpenDartReader 기본 캐시 — cwd에 자동 생성됨)** 추가(+ 2026-04-21 "모듈 DB 커밋" 정책의 의도적 예외임을 주석 1줄 — 원문 대용량·DART 키로 재현 가능). raw_cache/는 기존 패턴이 커버. collector는 가능하면 OpenDartReader 캐시 경로를 `modules/report/data/raw_cache/` 하위로 지정.
- [ ] CI 정합 결정 2건: ① `modules/report/`를 ci.yml Black 대상에 추가할지 결정 ② report 테스트 중 DART 키 의존분은 `pytest.mark.skipif`(env 부재 시 skip) — CI는 fixture 단위 테스트만 실행.
- [ ] 루트 CLAUDE.md·ARCHITECTURE.md 모듈 표 등재 + **`python scripts/sync_codex.py` 재실행, AGENTS.md 함께 커밋** (D6).
- [ ] pytest: 섹셔닝 단위 테스트(삼성 fixture) + **이종 업종 3사(금융·바이오·플랫폼 각 1) 조기 섹셔닝 테스트** (R5).
- 검증: 48사 backfill → pipeline_state 전부 ENRICHED, 기업당 주석 분할 수 상식 범위(20~40).
- DoD: reports.db에 48사 원문+섹션+정형계정. DART 키만 있으면 `python -m modules.report.collector`로 재현.

### Phase 6 — LLM 추출 하네스 (2.5~3.5일)
- [ ] **LLM 백엔드 준비**: A100 서버에 vLLM 기동(Qwen3-32B AWQ + `--guided-decoding-backend`, OpenAI 호환 포트) → 노트북에서 base_url로 접속 확인. A100 접근 불가 기간 대비 폴백: llama.cpp Vulkan(Arc 140V)으로 8B 스모크. **첫 작업: 단건 추출 지연 실측(thinking 비활성 확인 포함) → §6.5 처리량 갱신.**
- [ ] `requirements.txt`에 pydantic·openai·playwright 추가(버전 고정) + `python -m playwright install chromium`.
- [ ] `schemas.py`: Phase 0 확정 스키마의 pydantic 모델(GalaxyDoc·NotesDoc) — `tests/report/check_golden_keys.py`를 승격. 골든 2종 재검증.
- [ ] `llm.py`(JSON Schema 강제·temperature 0·seed 고정·timeout·재시도) / `extract.py`(§6.1 루프 — template_fit 판정·`_BATCH_REPORT.md` 생성 포함, D11·D12) / `validate.py`(§6.3) / `publish.py`(D10 레이아웃 산출 + D12 자동 흡수 규칙 + `data/publish/` 기록) / `benchmark_extract.py`(§6.4).
- [ ] **검증기 캘리브레이션: validate.py를 골든에 먼저 실행 — 골든이 통과할 때까지 규칙(잔차 허용·오차)을 조정** (§6.3의 전제).
- [ ] **제2 골든(held-out)**: 다른 업종 1개사(권고: POSCO홀딩스 또는 NAVER) 주석 3~5건 수작업 → few-shot에 넣지 않는 벤치마크 전용 세트 (§6.4).
- [ ] `integration/dossier/pull_report_json.py` 작성 (publish/ → dossier/data/ 복사, 리더 소유).
- [ ] 골든 회귀 pytest: 삼성 재생성 diff(`raw_mn` 100% 일치 + 산문 금칙어·인용검증 0건) + **D10 스케일 계수 검증(삼성 골든 w 역산 ±2)** + held-out 점수 리포트. **LLM(A100)·DART 의존 테스트는 `pytest.mark.skipif`(env 부재 시 skip)** — CI에서는 fixture 기반만 돈다.
- 검증: 골든 회귀 통과 + held-out 벤치마크 기록 + 무작위 1사 수동 검수.
- DoD: `python -m modules.report.extract --ticker 005930 --target galaxy` 1커맨드로 검증 통과 JSON 재현.

### Phase 7 — 48사 확장 + 성능·QA 마감 (2일)
- [ ] 배치 실행: **galaxy = 배치 시도 39사(금융·SK스퀘어 제외) 중 D10 부호 판정 통과분 약 30~32사**, **notes = 47사**(삼성 제외 전체 — 금융 포함). resumable이므로 다일 배치 허용.
- [ ] **`_BATCH_REPORT.md` 리더 검토 (D11)**: TEMPLATE_MISMATCH 항목별 결정(스코프아웃/규칙 추가/템플릿 수정) → 결정을 §9에 기록. 이후 리뷰 큐(`data/review/`) 소화 → 승인분 publish → `pull_report_json.py` 실행.
- [ ] 탭 활성화 로직: dossier/data에 JSON 존재하는 ticker·탭만 활성 (금융 8사+SK스퀘어 판단, 적자·음수흐름 기업은 ③ "준비 중").
- [ ] 성능 마감(§8 전항목 계측) + 48사 스모크(fetch 200·스키마·콘솔 에러 0).
- [ ] 문서 마감: ARCHITECTURE.md(모듈 표·데이터 흐름·부채 항목·이슈 #2 injectV2Theme 서술), 이 문서 상태 갱신, PROGRESS.md. 루트 CLAUDE.md를 또 고쳤다면 sync_codex.py 재실행.
- DoD: 배포 URL에서 **48사 탭①② + 비금융·흑자군 탭③ + 전 기업 탭④** 완동. dev 머지.

---

## 6. LLM 하네스 상세 (루프 엔지니어링)

### 6.1 추출 루프 (기업 × 타깃 단위)
```
for corp in corps.csv(48):                       # --ticker 단건 실행 가능
  for target in [galaxy, notes]:
    if scope_out(corp, target): continue         # D10 부호 판정 — publish.py 소유 함수를 초입에서 호출 (galaxy만)
    state = pipeline_state(corp, target)
    if state.stage >= VALIDATED: continue        # resumable
    partial = build_partial_json(corp, target)   # 본표 A(firm_*.json)+B(fs_account) 코드 주입 + D10 레이아웃 산출
    for note_batch in sections(corp, target):    # 주석 1건 = 1호출 (표 추출+head+body 통합)
      for attempt in 1..3:
        out = llm.extract(prompt(note_batch, few_shot=유형별_예시_1건), json_schema)   # 골든 전문 아님
        ok, errors = validate_note(out)          # §6.3 L1·L2
        if ok: break
        prompt += 이전 오류 요약                   # 오류 피드백 재시도
      merge_or_flag(partial, out, ok)
    copy_fill(partial)                           # 노드 copy·DISC 해설 등 산문 생성 호출(배치)
    fit = template_fit(partial)                  # D12 자동 규칙으로 흡수 가능한지 판정
    if not fit: mark TEMPLATE_MISMATCH(사유) ; continue   # D11 — publish 중단, 배치 보고서 기재
    ok = validate_doc(partial)                   # 문서 단위 L2 + L3 렌더
    if ok: mark VALIDATED, status=AUTO_PASS → publish.py 즉시 실행(리더 검토 불요, D11)
    else:  mark NEEDS_REVIEW + data/review/<corp>_<target>.md + shots/  (승인 후에만 publish)
write data/review/_BATCH_REPORT.md               # D11 — 상태 요약표 + MISMATCH 목록 + 콘솔 출력
```
- **결정성**: temperature=0(생성 0.3), seed 고정, `prompt_ver` 태그 → meta에 기록.
- **컨텍스트**: 전문 투입 금지. sectioner의 주석 단위 text_md(표 포함)를 1~3개씩. RAG/임베딩 불필요(사업보고서는 목차 정형 — 슬라이싱으로 충분).

### 6.2 프롬프트 구조 (추출용)
```
[시스템] 너는 한국 재무제표 주석에서 수치를 구조화하는 도구다. 규칙:
 1) 수치는 원문 표기 그대로의 백만원 정수(raw_mn)로만 출력한다. 계산·반올림·단위 변환 금지.
    (조 단위 표시 문자열은 네가 만들지 않는다 — 코드가 생성한다.)
 2) 원문에 없는 값은 null. 추측 금지.
 3) 모든 수치 항목에 source_quote(제공된 원문 텍스트에서 그대로 복사한 15~40자)를 붙인다.
 4) 출력은 JSON Schema를 따른다. 그 외 텍스트 금지.
[유저] <스키마> + <주석 유형별 예시 1건 (few-shot — 골든 전문 아님)> + <대상 주석 text_md>
```
생성용(산문)은 별도 호출: **§7.1 산문 원칙 + §7.2 카드 템플릿 전문**(스타일 가이드 발췌) + 해당 노드/주석의 확정 숫자 JSON(코드가 재계산한 배율·비율 포함) → copy/head/body만 생성. **viz 종류·색은 LLM이 정하지 않는다** — §7.2 선택표·색 문법으로 코드가 결정.

### 6.3 검증 3층
| 층 | 내용 | 실패 시 |
|---|---|---|
| L1 구조 | pydantic (타입·필수키·color_key/viz enum·raw_mn 정수) | 오류 피드백 재시도 |
| L2 사실 | ① **source_quote ⊂ 해당 주석의 text_md**(LLM이 실제로 본 텍스트 기준 — HTML 원문 아님. 비교 전 정규화: 연속 공백·전각/반각·U+2212 '−'↔'-'·천단위 쉼표) ② 표 내적 정합 — **raw_mn 기준**, 규칙은 골든 캘리브레이션으로 확정: waterfall은 `residual` 행 허용 + 오차 ±0.5%, bars는 `overlap` 플래그 없을 때만 부분합≤총계, sectors는 **외부매출 합 또는 내부거래제거 행 포함 합**으로 본표 매출 대조 ③ 본표 교차 — **§2.1 매핑표에 있는 계정만** firm_*.json/fs_account와 raw_mn 대조(±0.1%) ④ 산문 속 숫자가 입력 JSON 값에 존재 | 재시도 → 2회 실패 시 리뷰 큐 |
| L3 렌더 | playwright headless로 galaxy/notes.html 렌더 → 콘솔 에러 0 + 스크린샷 저장(`data/review/shots/`) | 리뷰 큐 |

### 6.4 골든 테스트 = 모델·프롬프트 선정 장치 (오염 방지)
- **삼성 골든**: 회귀 스모크 — 파이프라인 재생성 vs 수작업본 diff(raw_mn 100%·금칙어 0). 단 삼성 유형 예시가 few-shot에 쓰이므로 **모델 선정 지표로는 쓰지 않는다.**
- **held-out 제2 골든**(타 업종 1사 주석 3~5건, few-shot 미포함): `benchmark_extract.py --model … --prompt-ver …`가 raw_mn 일치율·인용 통과율·재시도 횟수를 표로 출력 → **이 점수가 모델·프롬프트를 판정.** 변경은 점수 유지·개선 시에만 허용.

### 6.5 처리량 추정 (Phase 6 첫 실측 후 갱신)
- 텍스트 슬롯/사: 노드 copy 18 + ANNOS head/body 20 + DISC 13 + notes 보강 ≈ **60~70건** → 배치 정책(주석 1건=1호출, copy 6개=1호출)으로 **호출 ~30/사**.
- 대상: galaxy 배치 시도 39사(금융 8사·SK스퀘어 제외) 중 **부호 판정 통과 약 30~32사(D10)** + notes 47사 → **~2,000±500회**, 호출당 평균 in 1.5k/out 0.5k 토큰 가정 → 총 ~4M 토큰.
- **A100 + vLLM 32B AWQ (동시 요청 8~16)**: 배치 처리량 수백~1천+ tok/s → **48사 전체 1~3시간** (프리필 포함 여유). 검증·재시도 포함해도 반나절. 노트북 폴백(8B, Arc 140V)은 다일 배치 — 스모크 외 비권장.
- 2,600사 확장 산술은 부록 C.

---

## 7. LLM 생성 가이드라인 — 산문·차트·라우팅 (프롬프트에 전문 포함)

> **정본: [CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md)** — 리더의 제작 사양서 v4를 48사 확장용으로 정제한 문서 (Part A = 전 기업 일반 문법, Part B = 삼성 기준값·few-shot 소스. 원문 v4는 리더 보관). 아래 §7.1~7.3은 그중 LLM·생성기 규칙의 요약 — 충돌 시 스타일 가이드가 우선. Phase 6 프롬프트에는 §7.1(산문)·§7.2(카드) 전문을 포함한다.

### 7.1 산문 원칙
1. **눈높이**: 금융 초보(중학생 수준). 문장당 1개념. 노드 copy 2~3문장, 주석 body 4~5문장(few-shot 문체와 충돌 시 few-shot 우선). **한 매듭 = 한 호흡** + **자급자족 원칙**(뒤쪽 카드를 전제하지 않고 그 자리에서 이해되게 — 전문용어 첫 등장 시 반 문장 풀이).
2. **서술형 완결 문장**: 모든 설명은 "~이에요/~입니다"로 끝나는 문장. **단어 나열·명사 끊기 금지** (❌ "제품을 만든 값." → ⭕ "제품을 만드는 데 든 값이에요").
3. **비유·비교 먼저, 항목당 1개**: "1초에 약 1,000만 원 꼴", "매출의 61%가 빠져나가요" 류 스케일 비유 — **배율·비율은 코드가 재계산해 입력에 넣어준 값만 사용** (삼성 문구·숫자 재사용 금지).
4. **용어는 그 자리에서 풀이** (스타일 가이드의 표준 풀이 사전 승계): 감가상각="손익 계산 시엔 비용으로 뺐지만 실제 현금은 안 나간 돈", 운전자본="아직 안 들어온 외상값과 묶인 재고", 지분법="지분을 나눠 가진 회사에서 온 몫", 비지배지분="자회사의 다른 주주 몫", OCI="손익을 거치지 않고 자본으로 간 평가손익", 연결="<회사명>+자회사를 합친 기준".
5. **금칙어**: "투자 조언·매수·매도·추천·확실·보장" 금지 → "과거 통계 기반 참고 정보" 프레임. **"장부이익" 금지 → "손익상 이익"**. 미래 전망 서술 금지(원문 전망은 "회사는 …라고 밝혔다"로 귀속).
6. **숫자 규칙**: 입력 JSON의 확정 숫자만 인용. 새 계산 금지. **귀속·추정**: 해석 혼입 시 문두 `[추정]`.
7. **면책**: 생성문에 넣지 않는다 — 오버레이 푸터 1곳이 담당(D1).
8. **어투 few-shot**: Cash Galaxy 기존 copy·카드 5건으로 문체 고정. **질문형 헤더** 관례 유지("공장과 장비, 1년 동안 얼마나 늘고 닳았을까요?").

### 7.2 주석 카드·차트 가이드라인 (기업 특성 반영 + 일관성의 핵심)
- **카드 3조건 (전부 만족해야 채택)**: ① 초보자도 이해되는 설명 ② 표·숫자를 직관적으로 풀어낸 시각화 ③ **은하수 큰 그림과의 유기적 연결** — 그 주석이 어느 매듭·어느 숫자를 설명하는지 분명할 것 (connect·ret 필드로 표현).
- **카드 공통 템플릿 (모든 카드 동일 골격)**: ① 질문형 헤더 ② 서술 한 문단 ③ 미니 그래픽 **1개** ④ 은하수 복귀 배지. 시각 지시가 애매한 카드는 **기본형 = 가로 막대 1개 + 텍스트** (비대칭 방지).
- **viz 선택표 (콘텐츠 유형 → viz — LLM이 아니라 이 표가 결정)**:

| 주석 내용 유형 | viz | 규칙 |
|---|---|---|
| 기초→증감→기말 (유형자산·이익잉여금·세금 감면 등) | `waterfall` | 기초·기말 앵커 필수, 잔차는 "그 외 ±0.x조" 행 |
| 구성·비중 (판관비·비용 성격별·차입 만기) | `bars` | 큰 항목부터 정렬, 최대 항목만 밝게 강조 |
| 부문별 실적 | `sectors` | **크기=매출 / 밝기=이익**, 내부거래 제거 행 필수 |
| 이익→현금 정산 과정 | `steps` | 화면 진입 시 자동 재생 후 토글 |
| 양방향 상쇄 (금융수익 vs 비용) | `symmetric` | 좌우 대칭 막대 + 순액 강조 |
| 두 시점 잔액 비교 (관계기업·무형·FVOCI) | `delta` | 기초→기말 + 변동 사유 갈래 |
| 현금 안 된 채 묶인 것 (외상·재고) | `puddles` | 흐린 웅덩이 — "아직 현금 아님" 톤 |

- **색 = 의미 문법 (고정 — 미학적 선택 금지)**: `mint`=손익 · `cyan`=현금 · `gold`=자본(주주 몫) · `coral`=유출 · `steel`=잔액/BS 상태 · **시안 점선(dash)=비현금**. 생성기·LLM은 color_key를 이 의미로만 배정.
- **표 재현 금지**: 표를 그대로 옮기지 말고 "무엇이 얼마나 늘고 줄었나 + 왜"만. 과한 은유 금지, 직관 먼저.

### 7.3 탭③/④ 라우팅 규칙 — "억지 매핑 금지" (타기업 주석 배정 기준)
각 기업의 주석을 ANNOS(탭③)와 DISC(탭④)로 나누는 판정 — **가능한 한 많이 매핑하되, 억지로 끌어오지 않는다**:
- **ANNOS 채택 기준**: 주석이 은하수의 특정 매듭·특정 숫자와 **수치로 맞물릴 때만** (예: 판관비 주석의 합계 = ⑤ 매듭 값). 채택 시 connect(매듭 번호)·ret(복귀 앵커) 필수.
- **DISC 강등 기준** (스타일 가이드 A0-3·B4 승계): 잔액 불변 항목·측정 기법·순수 서술(회계정책·위험관리·특수관계자·보고기간후사건·우발부채 등) — 한 줄 요약만.
- **무주석 통과 매듭 허용**: 기초/기말현금·매출총이익·환율 같은 통과/저수지 매듭에 주석을 억지로 붙이지 않는다.
- 라우팅 결과(기업별 ANNOS n개/DISC m개)는 extract 단계 산출물 meta에 기록 — D11 배치 보고서에 집계.

---

## 8. 성능 최적화 체크리스트

- [ ] 탭 lazy mount + keep-alive (Phase 2) — 첫 진입은 활성 탭 1개만.
- [ ] 비활성 탭 표시 토글 방식은 **Phase 2 스파이크로 결정** — display:none(페인트 0, 단 내부 치수 0 재계산 위험) vs visibility:hidden+offscreen(뷰포트 유지). 재표시 시 ③ zoom·스크롤 복원이 판정 기준.
- [ ] **오버레이 열림 동안 v2 셸 rAF 일시정지** (또는 오버레이 배경 불투명화로 backdrop-filter:blur(18px) 제거) — 움직이는 배경 실시간 블러가 최대 GPU 비용원.
- [ ] 폰트 로컬 서브셋(Pretendard static 서브셋 + IBM Plex Mono 3종) + `font-display: swap`. 22MB 원본 임베드 금지(editable 기반).
- [ ] JSON 단건 fetch — 48개 선로딩 금지.
- [ ] galaxy.html 애니메이션은 컴포지터 전용 유지 — 이식 중 JS 애니메이션 추가 금지.
- [ ] business.html 382KB → 데이터 분리 후 페이지 ~40KB 목표. 이미지 `loading="lazy"`+onerror 폴백 유지.
- [ ] 측정 기준: 탭 전환 <200ms(재방문), 탭 최초 로드 <1.5s(로컬), ③ 스크롤 중 55fps 이상(DevTools), 콘솔 에러 0 — Phase 7에서 ui-ux-reviewer 계측 기록.
- [ ] 미달 시 2차 수단(순서대로): feGaussianBlur stdDeviation 축소(26→14) → 배경 파티클 축소 → 필터 정적 프리렌더. **1차 이식에서는 손대지 않는다.**

---

## 9. 리스크 & 미결

| # | 리스크/미결 | 대응 |
|---|---|---|
| R1 | ~~Q1 신규 모듈 — 조직 결정~~ **승인 완료 (2026-07-08)** | Phase 5 착수 가능. D6 절차(문서 등재+sync_codex) 준수 |
| R2 | ~~Q2 탭④ 해석~~ **확정 완료 (2026-07-08)** | 기타 주석은 탭④로 일원화 (D9) |
| R3 | dc-runtime의 async 데이터 수용 | Phase 1 첫 반나절 스파이크. 불가 시 폴백: 빌드 스크립트가 ticker별로 `<script type="application/json" id="galaxy-data">` 인라인 주입된 HTML 48개 생성(최후수단) |
| R4 | ~~GPU VRAM 미확인~~ **확인 완료**: 로컬 노트북 = Intel Arc 140V(공유 16GB, CUDA 없음 — 배치 부적합) / **가용 주력 = A100 1장 80GB(원격, 리더 확정 2026-07-08)** | §3·부록 C 반영. **Phase 6 착수 조건 — 리더 지정 목록**: ① 접근 방식(SSH·포트)·가용 시간대 ② 서버 사전 셋업 범위(vLLM·CUDA 설치 주체·권한) ③ 모델 가중치 리포(HF — AWQ 양자화본 복수 존재) + HF 토큰 ④ 엔드포인트 인증 방식 + env 변수명(`REPORT_LLM_BASE_URL`/`REPORT_LLM_API_KEY`, shared/config.py 등재) |
| R5 | 주석 HTML 구조가 기업마다 상이 | **리스크 하향 (부록 B)**: 사업보고서 sub_docs 목차가 정형(삼성·하이닉스 동일 구조 실증). 이종 업종 3사(금융·바이오·플랫폼) 조기 섹셔닝 테스트는 유지 |
| R6 | DART 수집 다중화 부채 심화(원문 3중 + fnlttSinglAcntAll) | ARCHITECTURE.md 부채 등재 + B·C 공유 (D6) |
| R7 | 금융업 8사(+SK스퀘어) 및 적자·음수흐름 기업은 은하수 기하 부적합 | D10 자동 스코프아웃 — ③만 "준비 중", ①②④ 정상. Phase 7 DoD도 이 기준 |
| R8 | 대용량 산출물 커밋 사고 | raw는 `raw_cache/` 명명(기존 ignore 재활용), reports.db·review/는 .gitignore 신규 추가(Phase 5 체크박스), publish/ JSON(기업당 수십 KB)만 커밋 |
| R9 | 파일명 "kospi50" vs 실제 48사 혼동 | 이 문서·코드 주석에서 항상 "48사(dossier 집합)"로 표기. 신규 기업 추가는 별도 과제 |
| R10 | **기존 데이터 오류 발견 (부록 A)**: `firm_012450.json`(한화에어로스페이스) 2025 revenue 0.223조 vs cogs 21.25조 — 전년 대비 100배 급락한 단위/파싱 버그 | **financial 모듈(A 담당) 소관 — 리더가 직접 수정 금지.** A에게 재수집 요청 + 해결 전까지 한화에어로는 galaxy 생성 대상에서 제외(sanity 검증이 자동 차단, D12). 탭①②④는 영향 없음 |
| R11 | 프로토타입 DATA 내 이상치: 삼성 rd_chart revenue 배열에 비율값 혼입 `[1301282, 56.3, 1879673]` | Phase 3 `extract_business_json.py`에서 rd_chart 유효성 게이트(기존 템플릿 게이트와 동일 기준)로 필터 — 무효값은 키 생략 |

---

## 10. 새 세션 부트스트랩 (이 계획을 실행할 때)

1. 이 문서 전체 + `docs/ARCHITECTURE.md` §1·2·3.5 + `integration/v2/CLAUDE.md`를 읽는다.
2. Q1~Q3은 모두 **승인 완료**(문서 머리 표). 남은 리더 지정 항목은 R4(A100 접속 정보)뿐.
3. `git status` 확인 → dev 기준 해당 Phase 브랜치 생성. **타 모듈 소유 미추적 파일(modules/financial·price 등)은 add 금지** — 커밋은 항상 경로 명시 add(`integration/dossier/`·`modules/report/`·`docs/`·`tests/report/`·`integration/v2/` 한정).
4. 진행 상태는 이 문서 체크박스가 정본. Phase 종료 시 체크 + DoD 증거(스크린샷·테스트 출력)를 PR 본문에 첨부.
5. 검증 없이 다음 Phase 진행 금지 (특히 Phase 1 시각 동등성, Phase 6 골든·캘리브레이션).
6. 막히면: R3 폴백, 이식 원칙(§0 — 허용 범위 ⓐⓑⓒ) 재확인. "다시 그리고 싶다"는 유혹 = 계획 위반.

### 진행 상태
- [ ] Phase 0 준비 (스키마 확정 + 골든 2종)
- [ ] Phase 1 탭③ galaxy.html
- [ ] Phase 2 4탭 셸
- [ ] Phase 3 탭① business.html
- [ ] Phase 4 탭④ notes.html  ← **이식 마일스톤 (dev 머지·배포)**
- [ ] Phase 5 modules/report/ 수집 (Q1 확정 — 승인됨)
- [ ] Phase 6 LLM 하네스 + 골든
- [ ] Phase 7 48사 확장·마감

---

## 부록 A. 확장 가변성 감사 결과 (2026-07-08, 3에이전트 렌더 코드·실데이터 전수 조사)

> 리더 질문 "삼성 템플릿이 타기업으로 미세 UI 조정까지 막힘없이 확장되는가"에 대한 근거. D4·D10·D12·Phase 3의 규칙들이 여기서 나왔다.

### A-1. galaxy (Cash Galaxy.editable.html) — 판정: 골격은 이미 데이터 주도, 템플릿 수정 5곳 필요
렌더 코어(분기 경로·노드 배치·IS/EQ/CFSEC 패널·viz 카드 — 7종 중 6종은 카드 map 루프, steps는 렌더 코드 특수 처리(D4 파라미터화 2번 대상)·DISC 그리드·스크롤 씬)는 전부 배열 주도 — 분기 7개·주석 15개·부문 2~6개 등 개수 가변에 구조적으로 견딤. **"템플릿 1회 수정(5곳, D4에 반영) + 생성기 계약 8규칙(D12)"이면 47사 확장 가능.**

| 심각도 | 지점 | 증상 | 해법 |
|---|---|---|---|
| blocker | `buildGeo` 'cap' 하드참조 (L463-465) | cap 분기 없는 기업 → TypeError → **페이지 백지** (유일한 즉사) | `if(capTip)` 가드 (D4-1) |
| blocker | steps viz·runSteps 상수 45.2/52.4/9.6/2.7 (L698-708) | JSON 바꿔도 삼성 숫자 표시 | ANNOS `steps` 필드로 파라미터화 (D4-2) |
| blocker | markup 삼성 텍스트 8곳 (nav·h1·도입·게이지2·sectors합·puddles합·푸터) | 타사에서 삼성 문구 노출 | placeholder 바인딩 (D4-3) |
| major | 'noncash' 유입 파티클 (L634-637) | 분기 없으면 (0,0) 빛점 고착 | dash 플래그 기반 가드 (D4-4) |
| major | DEST tip 미가드 (L642) | br≠brSpec이면 crash | 가드 1줄 + 생성기 계약 ⓓ (D4-5) |
| major | 텍스트 길이 (미니라벨 nowrap 무클리핑) | 긴 라벨 겹침 | 생성기 축약 규칙 ⓕ |
| minor | 분기 충돌·음수 기하·NaN·BSMINI 2장 전제·hlFor 어휘 | 시각 실종/왜곡 (crash 아님) | 생성기 계약 ⓐⓑⓒⓔⓖⓗ |
| none | 트렁크 기하·스크롤 씬·connect/ret·ANNOS viz 루프 | 안 깨짐 | — |

### A-2. business (kospi50_business_tabs.html) — 판정: 구조적 장애 없음 (48사 실데이터로 폴백 실증)
- 결측 대응 실증: raw_moves 47사 결측·가동률 44사 결측·카드 2/3/4개 혼재(4/29/15사)·LIG넥스원 overview/R&D 전결측 — 전부 빈 칸 없이 폴백 렌더. 삼성 전용 분기 코드 0건.
- 수정 2곳: ① **단일 뷰 변형 시 부트스트랩 절제**(rail 리스너 L1260-1271 — 안 지우면 TypeError 백지, Phase 3에 반영) ② **industryKey 우선순위 버그**(SK텔레콤·현대건설·KT&G가 power lens로 오분류 — 현행 배포본에도 존재하는 버그, Phase 3에서 수정).
- 생성기 계약 3개: 카드 2~4개 · kind 21종 지정 · 금융사 display_category '금융업' (D12).

### A-3. 데이터 (firm_*.json 48사 실측) — 판정: 3그룹, 탭③ 제공 목표 30~32사
- **A그룹 ~14사** (값만 다름 — 삼성·SK하이닉스·기아·현대모비스·삼바 등): 스케일 함수만으로 수용.
- **B그룹 ~16-18사** (역방향·일부 결측): fcf>0 24사(절반!)·icf>0 6사·bridge<0 → **inflow 전환으로 흡수**(스코프아웃하면 반토막 — D10 수정의 근거). cogs 결측 NAVER·카카오·SKT → 분기 생략.
- **C그룹 ~16-18사** (구조 상이 — 스코프아웃): 금융 8사+SK스퀘어(5개년 아닌 3개년 보유와도 일치), OI<0 삼성SDI, OCF<0 비금융 5사(현대차 포함 — 할부금융 혼재로 상시 음수), NI<0 SK이노·LG화학, 데이터 오류 한화에어로(R10).
- **최상위 전제 재확인**: firm_*.json 14필드로는 11개 분기 중 4개만 산출 가능 — tax·op_ext·noncash·wc·int·fx·현금잔액은 48사 전부 원천 부재. **Phase 5의 fnlttSinglAcntAll 수집 없이는 A그룹 14사도 생성 불가** (§2.1 본표 B가 최우선 선행).

## 부록 B. DART 실수집 스파이크 (2026-07-08)

### B-1. 삼성전자·SK하이닉스 (기준 2사)

`dart.list → sub_docs → 서브문서 다운로드 → document.xml` 전 구간 실측 성공 (스크립트: 세션 스크래치패드 `dart_spike.py`, 저장소 외부).

| 확인 항목 | 결과 |
|---|---|
| 최신 사업보고서 조회 | `dart.list(ticker, kind='A')` → 삼성 rcept 20260310002820 · 하이닉스 20260317000635 |
| 문서 구조 | **sub_docs 57~58건, 두 회사 목차 사실상 동일** — "II. 사업의 내용" 7절, "III. 재무에 관한 사항" 하위에 **"3. 연결재무제표 주석" 별도 서브문서 존재** |
| 주석 위치 | 본문 서브문서로 확보 가능 (감사보고서 첨부 경유 불필요) |
| 표 보존 | "III. 재무" 서브문서 1.6~1.8MB에 `<table>` 1,632~1,813개 — HTML 표 온전 |
| 주석 번호 분할 | "1. 일반사항 / 2. 중요한 회계처리방침 …" 패턴 확인 — 서브문서 내 2차 분할 가능 |
| 원문 용량 | document.xml zip 0.69~0.78MB/사 → **48사 ≈ 40MB** (raw_cache 커밋 제외 유지) |

→ Phase 5 섹셔너는 정규식 슬라이싱이 아니라 **목차 기반 수집**으로 설계 (본문에 반영 완료). R5 리스크 하향.

### B-2. 산업별 확장성 판별 (2026-07-08, 48사 바운더리 내 14개 산업 대표 실측)

리더 지시 "반도체 외 산업군 각 1사 파싱으로 구조 확장성 판별" 실행 결과 — **13/14 산업 구조 동일 확인, 파싱 구조는 전 산업 확장 가능**.

| 기업 | 산업 | subs | 연결주석 서브문서 | 표 수 | 주석 번호 |
|---|---|---|---|---|---|
| 현대차 | 자동차 | 63 | 997KB | 1,118 | ~39번 |
| LG에너지솔루션 | 배터리 | 57 | 1,009KB | 974 | ~38번 |
| 삼성바이오로직스 | 바이오 | 59 | 709KB | 863 | ~34번 |
| NAVER | 플랫폼 | 58 | 1,120KB | 1,138 | ~37번 |
| **KB금융** | 은행지주 | 70 | **3,435KB** | 2,390 | ~45번 |
| **삼성생명** | 보험 | 58 | **2,467KB** | 1,767 | ~37번 |
| POSCO홀딩스 | 철강지주 | 60 | 1,363KB | 965 | ~43번 |
| HD한국조선해양 | 조선 | 57 | 1,010KB | 1,144 | ~50번 |
| SK텔레콤 | 통신 | 57 | 943KB | 931 | ~41번 |
| 한국전력 | 전력유틸 | 64 | **3,361KB** | 1,153 | ~47번 |
| 현대건설 | 건설 | 57 | 1,354KB | 1,034 | ~37번 |
| HMM | 해운 | 57 | 662KB | 852 | ~43번 |
| KT&G | 소비재 | 57 | 897KB | 1,077 | ~34번 |
| 한화에어로스페이스 | 방산 | **2** | — | — | 정정 stub |

핵심 판정:
1. **골격 전 산업 동일**: "I. 회사의 개요 → II. 사업의 내용 → III. 재무에 관한 사항(하위 3. 연결재무제표 주석 별도 서브문서) → IV. MD&A" 구조가 금융·보험 포함 전 산업 공통 → **섹셔너(목차 기반)는 산업 무관 단일 구현으로 충분**.
2. **금융·보험의 차이는 "II. 사업의 내용" 하위 구성**: 제조업 7절(주요 제품·원재료 및 생산설비·매출 및 수주 등) vs 금융 5절(영업의 현황·파생상품거래 현황·영업설비·재무건전성 등) → 탭①(business) 스니펫 추출 시 금융용 섹션 매핑 분기 1개 필요 (Phase 5 sectioner에 반영). 주석 번호 체계는 동일 형식("N. 제목 (연결)")이라 2차 분할 로직 공통.
3. **문서량 편차 3~5배**: 금융(2.4~3.4MB, 표 1,700~2,400개)·한전(3.4MB)은 제조업(0.7~1.4MB)의 3배 — LLM 투입은 주석 단위 슬라이싱(§6.1)이라 영향 없고, 원문 저장 용량 추정만 상향(48사 ≈ 60~80MB).
4. **정정공시 stub 엣지케이스 발견**: 한화에어로의 최신 rcept(20260319000633)는 서브문서 2건짜리 정정신고 껍데기 — 산업 문제가 아니라 **수집기 폴백 규칙 필요** (Phase 5 collector에 반영: `sub_docs ≥ 30 && has(사업의 내용)` 판정 + 직전 보고서 폴백). KB금융·삼성생명도 정정신고였으나 전체 목차 포함형이라 정상 처리됨 — 정정에도 두 유형이 있다는 것까지 확인.

## 부록 C. GPU 전략 — "생성·검증 모두 GPU?"에 대한 검토 (2026-07-08 리더 질문)

### C-1. 원칙: 확률적 작업만 GPU, 결정적 작업은 CPU
리더의 원안("확장 시 계산량 폭증 → 생성과 검증 모두 GPU")은 **절반이 맞다**. 계산량 분해:

| 작업 | 성격 | 2,600사 규모 계산량 | 올바른 자원 |
|---|---|---|---|
| 원문 수집·파싱(HTML→섹션) | 결정적 | ~2,600 × 1~3MB, BeautifulSoup — CPU 병렬 수십 분 | **CPU** |
| LLM 추출·산문 생성 | 확률적 | ~10만 호출, 1~1.5억 토큰 — **전체 계산량의 99%+** | **GPU** ✔ |
| 검증 L1~L2 (스키마·인용 포함·산술 정합·DB 대조) | 결정적 | 문자열·산술 연산 — 2,600사 전체 CPU **수 초** | **CPU** ✔ |
| 검증 L3 (헤드리스 렌더) | 결정적 | ~2,600 렌더 × 1~2초 — CPU 병렬 ~1시간 | CPU |
| 레이아웃 생성(D10 스케일 함수) | 결정적 | 나눗셈 수천 번 | CPU |

**"검증을 GPU(=LLM)에 맡기면 안 되는 이유**: 우리 검증은 일부러 결정적으로 설계했다(§6.3 — 인용 문자열 포함, 기초+증감=기말, DB 교차 대조). 이걸 LLM-judge로 바꾸면 검증 자체가 확률적이 되어 **검증자가 환각하는 순간 게이트가 무의미**해진다. 속도도 역전: 결정적 검증은 GPU가 필요 없을 만큼 싸다. LLM-judge는 산문 문체·눈높이 품질의 **샘플링 보조 검수**(전수 아님)로만 쓰고, 그 용도라면 GPU 사용이 맞다.
→ 결론: **생성 = GPU ✔ / 검증 = CPU(결정적) + GPU는 보조 판정만.** 이 분리가 D7·D8("LLM은 숫자를 만들지 않는다, 하네스가 품질을 소유한다")의 하드웨어 버전이다.

### C-2. 가용 장비와 역할 분담 (실측 2026-07-08)
| 장비 | 스펙 | 역할 |
|---|---|---|
| 로컬 노트북 | Intel Arc 140V (Lunar Lake 내장, 공유 16GB, **CUDA 없음**) | 개발·하네스 실행·8B급 스모크(llama.cpp Vulkan). 배치 부적합 |
| **A100 1장 (80GB, 원격)** | 데이터센터급 | **배치 주력**: vLLM + Qwen3-32B AWQ, OpenAI 호환 API + guided_json. 하네스(노트북)가 원격 호출 |

llm.py를 OpenAI 호환 클라이언트로 짜면 A100(vLLM)↔노트북(llama.cpp/Ollama)↔클라우드 API가 base_url 교체만으로 스왑된다 — 백엔드 종속 없음.

### C-3. 단계별 GPU 활용처
- **지금 (48사, Phase 6~7)**: A100 vLLM 32B로 추출·생성 배치 — 총 ~4M 토큰, **1~3시간**. 골든 벤치마크(8B/14B/32B 비교)도 A100에서 병렬로.
- **본선 (전 상장사 ~2,600사)**: ~10만 호출·1~1.5억 토큰 → A100 vLLM 연속 배칭(동시 16~32 요청) 처리량 기준 **1~3일 배치**. 검증·파싱은 CPU로 수십 분. **A100 1장으로 전 상장사 커버 가능** — 연 1회(사업보고서 시즌) 배치성 작업이라 상시 점유 불필요. 실패·고난도 건은 API(Claude/Gemini) 에스컬레이션 라우팅(AI_DIRECTION_PLAN §3.1과 동일 원칙).
- **미래 (AI_DIRECTION_PLAN 연계)**: 임베딩 생성(RAG·학습 레이어 — 공시·주석 벡터화), 학습 기능의 LLM-judge 채점(고빈도·저난도 → 로컬 GPU 라우팅), QLoRA 도메인 파인튜닝(회계 언어 특화 — A100 80GB면 32B QLoRA 여유. 단 held-out 골든이 베이스 모델 부족을 증명할 때만).
- price 모듈 CatBoost GPU 학습은 데이터 규모상 이득 미미 — CPU 유지.
