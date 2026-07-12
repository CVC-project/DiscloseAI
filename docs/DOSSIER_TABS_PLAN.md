# 기업 상세 3탭 개편 + 사업보고서 AI 파이프라인 — 실행 계획 (디자인 세대 v6, 해방판 기준)

> **상태**: 2026-07-10. 프로토타입 디자인 세대 **v6**(해방판) 기준으로 전면 재작성 — 짝문서 [CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md)도 v6. 이력: 초안(4탭·editable) → 4렌즈 리뷰 53건 → Q1~Q3·D11·D12 → 가변성 감사·DART 스파이크·A100 → 총점검 37건 → **v6 재설계(3탭·해방판·5개년·일관성 하네스, 이 판)** → v6 정합 리뷰 16건 반영.
> **소유**: 프로젝트 리더
> **이 문서만 읽고 새 세션에서 실행 가능해야 한다.** 각 Phase에 완료 기준(DoD)·검증 방법 포함.
> 선행 필독: [CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md) · [ARCHITECTURE.md](ARCHITECTURE.md) §1·2·3.5 · [integration/v2/CLAUDE.md](../integration/v2/CLAUDE.md)

---

## ✅ 확정된 결정

| # | 결정 | 확정 내용 |
|---|---|---|
| Q1 | 신규 모듈 `modules/report/` 생성 (D6) | **승인** (2026-07-08). 데이터 생산은 모듈 소관, disclosure는 B 소유라 리더 소유 신규 모듈이 유일한 정합 경로 |
| Q3 | 타사 확장 시 은하수 정책 (D10) | **승인** (2026-07-08). 생성기(코드)가 결정적 산출, LLM 아님. **v6 전환으로 굵기가 기본 2단 고정**(`ribbon.uniform:true` — √스케일 함수는 코드에 잔존하나 미사용) → D10 대폭 단순화 |
| Q4 | 탭④ 삭제 → **3탭** | **확정** (2026-07-10). v6 해방판이 주석 전체(핵심 딥다이브 + APPENDIX 14)를 탭③에 내장 → 탭④·notes.html 폐기. 3탭 = ①사업·기업 개요 ②EQS ③현금 은하수 |

추가 리더 지시:
- (2026-07-08) 삼성 템플릿으로 표현 안 되는 기업·항목은 **리더 보고 공식 절차** → D11. 미세 UI 변형은 **보고 없이 자동 흡수** → D12.
- (2026-07-10) v6 전환에 따른 **기술 요소(GPU·API) 영향 파악** → 부록 C·§6.5. **타사 생성 일관성 하네스** → §6.6~6.8·§2.2 역할 분담.

---

## 0. 목표 (한 문단)

v2 기업우주에서 행성 → ENTER CORPORATION 클릭 시 EQS 단일 화면(firm.html iframe)이 뜬다. 이를 **사업보고서 교육 관점의 3탭**으로 개편한다:

| 탭 | 내용 | 원형(프로토타입) | 스텝 |
|---|---|---|---|
| ② EQS 분석 | 기존 firm 상세 (M1~M5) | `integration/dossier/firm.html` (배포 중) | **Step 1** (기존) |
| ③ 현금 은하수 (+주석 전체) | 현금흐름 시각화 + getDives 딥다이브 41종(콘텐츠 27 + APPENDIX 강등 14, five=skip 17) + 5개년 차트 | **`docs/prototype/현금은하수_해방판.html` + `dc-runtime.js`** | **Step 1** (이식+AI 파이프라인) |
| ① 사업·기업 개요 | 사업보고서 기준 사업/기업 소개 | `docs/prototype/kospi50_business_tabs.html` (**아직 미확정판**) | **Step 2** (프로토타입 확정 후, §5b) |

**디자인 표준 = 현금 은하수(해방판).** ①②는 이 표준 토큰(색·폰트·배경)으로 맞춘다.
**이식 원칙 — 시각은 불변, 데이터 흐름만 재작성**: **시각·레이아웃·애니메이션·dc-runtime은 재설계·재작성 금지**(=이식 정신). 그러나 ⚠️ **해방판은 삼성 전용 하드코딩 산출물**이라(부록 A2), 탭③은 "데이터만 교체"가 불가능하고 **정적 마크업 ~90행을 데이터 구동(sc-for/보간)으로 전환 + JS 상수 전량을 데이터 주입으로 리팩터**해야 타사가 렌더된다. 이는 재설계가 아니라 **데이터 흐름의 재배선**(리터럴 → 주입)이다. 허용 범위 ⓐ 디자인 토큰 치환 ⓑ 데이터 외부화 + **마크업 데이터 구동화**(D4) ⓒ 확장 대비 매듭 가드 — 이 셋뿐. **"화면을 다시 그리고 싶다"는 유혹 = 계획 위반**(단 "리터럴을 데이터 바인딩으로 바꾸는" 재배선은 이식의 일부).

이후 **AI 확장**: 삼성전자 기준으로 만든 "기본 틀(템플릿+JSON 스키마)"에, 사업보고서 **5개년** 원문·정형계정을 저장해 두고 **자체 GPU LLM(원격 A100 80GB + vLLM)** 이 주석 수치·설명·5개년 해석을 추출/생성해 채워 48개 기업으로 확장한다.

---

## 1. 현황 진단 (2026-07-10 검증)

### 1.1 integration/v2 (셸)
- 빌드 도구 없음: React 18 UMD + Babel standalone. **`v2/src/bundle.jsx`(약 3,000줄)가 정본** — `index.html` → `adapter.js`가 동적 주입.
- 행성 클릭 → `CompanyOverviewPanel` → ENTER CORPORATION → `setCorpOverlayTicker()` → **무명 인라인 오버레이 JSX**(bundle.jsx L2956 부근). 오버레이 3요소: `<iframe src="../dossier/firm.html?ticker=<t>">` + `injectV2Theme(iframe)`(L2719-2832) · **`OverlayAiChat` 우측 고정 300px**(L2988-2993) · 하단 면책 푸터(L2995-3002).
- 오버레이 배경 `backdrop-filter: blur(18px)` + 밑에서 v2 셸 rAF 루프(L399·700·1120·2002) → 성능 §8.
- v2/CLAUDE.md 제약: v1 수정 금지 · extract_data.py 로직 수정 금지 · 빌드 도구 도입 금지 · "injectV2Theme 무변경" — 마지막은 이번 개편으로 규칙 개정(Phase 2).

### 1.2 프로토타입 ①: kospi50_business_tabs.html (382KB, 1,275줄)
- 외부 의존성 0(vanilla JS+인라인 CSS). 좌측 rail + 우측 상세 + 상단 자체 탭바(2개 disabled).
- **`const DATA`(L612)에 48개 기업 하드코딩** — rank 1~48. **이 48개 = `integration/dossier/data/firm_*.json` 48개와 티커 완전 일치 = 기업 목록 SSOT.**
- 각 항목: stock_code/corp_code(8자리)/latest_year(억원)/5년 history/snippets/business_cards/report(rcept_no — 079550 LIG넥스원만 결측).
- 색: bg `#060914`, cyan `#41dcff`, teal `#36e5bd` … → 표준과 다르므로 토큰 치환(D5).

### 1.3 프로토타입 ③: 현금 은하수 해방판 (v6 — 완성본, 1,756줄 + dc-runtime.js 60KB)
- **정본 위계 (2026-07-10 리더 확정)**: ① 자구·데이터 정본 = **`현금은하수_해방판.html` + `dc-runtime.js`**(v6 md를 입력으로 Claude Design에서 확정한 최종 산출물). 구본(`Cash Galaxy.html` 22MB · `Cash Galaxy.editable.html` 308KB)은 v4 산물 — **삭제 완료(2026-07-12)** ② v6 md(`docs/prototype/프롬프트_v6_현금은하수_구현확정판.md`) = 문법·의도 ③ 스타일 가이드 = 조문화. **자구·데이터 의문 시 해방판 html이 판정 기준.**
- 스택: **React 18.3.1(CDN) + Babel standalone(CDN) + `dc-runtime.js`(외부 참조)** — v2 셸과 CDN 캐시 공유. 인라인 SVG. Canvas/Three.js/D3 없음, 외부 차트 라이브러리 없음(전부 손 SVG).
- **레이아웃 (v6 재설계)**: 3열 그리드 `[data-grid]` = 2fr(은하수 SVG) : 3fr(재무제표 5패널) : 5fr(sticky 딥다이브 카드). 반응형(CSS 변수 `--col-*`) — **구판 1360px 고정폭·zoom 로직 소멸**.
- **은하수 (v6)**: `buildGalaxy()`(L749) — **일직선 본류 `spineX:0.48`**(L479 CONFIG) + **직교 라우팅 `ortho()`**(L780) + **굵기 2단 고정**(본류 6px/지류 3.5px, 금액 무관). `{{ galaxySvg }}` 바인딩(L1741). 골드 자본실·감가 회귀선·OCI 점선은 직교 좌표(L840·851·864·870).
- **데이터 구조 (외부화 대상)**:
  - `YEARS`(L~1062) = ['FY21'…'FY25'] + **`S` 시계열 24키 × 5점**(revenue·cogs·gross·sgna·op·pretax·tax·ni·oci·ocf·icf·capex·fin·div·buyback·dep·rnd·cash·assets·debt·equity·dsOp·eps·tci).
  - `KNOTS` **17개**(L486, row 기반 배치) + `SEGS`(본류 구간, L523) + `CF` 설정(L479).
  - **`getDives()`**(L1290-1655) — 딥다이브 **41 객체**(콘텐츠 27 + APPENDIX 강등 14; 41 중 `five=skip` 17건 — APPENDIX 14 + 콘텐츠 잔차 3). 각 객체 `{z,zc,en,name,amt,raw(포맷 문자열),color,row, what[], links[{t,row,txt,a}], lnote, why{sub,body[],viz(),cap}, five{key|twin|skip,cap,so}}`.
  - **중앙 재무제표 5패널 행이 HTML 마크업 인라인**(is-revenue 등, `title`에 백만원 원값) — 존 A~E.
  - 상단바·인트로 삼성 텍스트(FY2025 헤더 L60 등).
  - **vLine의 valley 라벨**(L1163의 '반도체 한파' 문자열 리터럴 — vLine 시그니처엔 valleyLabel 인자 없음, 순수 하드코딩) + YEARS(L1062) — D4 파라미터화 대상(→ anchor.label).
- **viz 8종**(전부 손 SVG 메서드): vLine·vTwin·vWater·vHBar·vSteps·vBubbles·vPuddle·vChips.
- **상호작용 (v6)**: JOURNEY/PINNED 2모드 + 제스처 스크롤(250ms 게이트/450ms 재동기화) + 맞물림 연결선 3종 + `data-jl`/`data-hl` 하이라이트 + 트윅 3종(particles/glowStrength/rowH).
- **삼성 수치 = FY2025**(매출 333,605,938 등 구판과 동일). **NUDGE 편집 도구 없음**(배포용).
- **구판 대비 변화**: 사행 은하수·1360px zoom·9개 배열(KNOTS/ANNOS/DISC…)·disc 뷰 토글·NUDGE — 전부 없음. **굵기 √스케일**: CONFIG.ribbon(L476-477)에 `scale:'sqrt', ref:333.6, min:6, max:44`와 `wf()` 함수(L757)가 **코드에 잔존하나 `uniform:true`로 잠겨 미사용**(2단 고정 6px/3.5px). → 구판 감사(부록 A)의 위험 5곳(cap 하드참조·noncash 파티클·DEST 가드·steps 상수·zoom)은 **구조째 소멸**이나, 굵기 로직은 "소멸"이 아니라 "비활성"이다(D10·D12 주의). → 부록 A 무효, **신규 감사 완료**(부록 A2).

### 1.4 데이터·AI 인프라
- **기업 목록 SSOT = dossier 48사**. `modules/disclosure/collector.py:37 TARGET_CORPS`(49개)는 다른 집합 — 사용 금지. `financial/batch.py:82 KOSPI_TOP_50`(48개)이 일치.
- **사업보고서 원문 미저장.** disclosure `collector.py`가 매번 메모리 로드 → 평문 슬라이싱(주석 등장 시 중단) → Groq 결과만 저장. 목적이 반대 — **주석 파서 신규 작성**.
- **정형 재무 숫자 보유 범위**: `firm_<t>.json` = 5개년, 9계정 + cogs·유동자산/부채·장기차입 등 **14필드/년, 단위 원**. `financial_local` = year=2025 단일. **galaxy가 요구하나 없는 계정**(법인세·OCI·비현금조정·운전자본·이자/세금납부·환율·기초/기말현금·배당·자사주·CF 세부) → **DART `fnlttSinglAcntAll`(전 계정)로 5개년 보강 수집**(Phase 3). LLM 아님.
- **v6 5개년 신규 수요**: S 24키를 5개년 확보해야 vLine/vTwin이 그려진다. firm_*.json이 5개년 14필드를 이미 가지므로 본표계는 커버, 나머지(rnd·dsOp 등)는 fnlttSinglAcntAll·주석 추출 5개년(§2.1·Phase 3 소스 매핑).
- `requirements.txt`에 pydantic(직접)·openai·playwright 없음 → Phase 4에서 추가.

---

## 2. 목표 아키텍처

```
[v2 셸 — bundle.jsx]
  행성 클릭 → ENTER CORPORATION
    → 오버레이(무명 JSX 개조): 탭바 3개 + OverlayAiChat(유지) + 면책 푸터(유지)
        탭① <iframe src="../dossier/business.html?ticker=t">   (lazy mount, keep-alive)
        탭② <iframe src="../dossier/firm.html?ticker=t&theme=galaxy">  (기존, ?theme= 파라미터로 팔레트)
        탭③ <iframe src="../dossier/galaxy.html?ticker=t">       (해방판 이식 + dc-runtime.js)
      · 각 페이지는 dossier/data/<종류>_<ticker>.json 만 fetch (단건)

[데이터 생산 — 신규 modules/report/ (Q1)]
  DART document API(5개년) + fnlttSinglAcntAll(5개년) → reports.db
    → 시계열 빌드 → 스토리 탐지(코드) → 회사 브리프(1호출/사) → LLM 문장화 하네스 (vLLM@A100)
    → L0 문체 게이트 + 3층 검증 통과분 → modules/report/data/publish/galaxy_<t>.json

[서빙 — integration (pull, 단방향)]
  integration/dossier/pull_report_json.py 가 publish/ 를 read-only 복사 → dossier/data/
```

### 2.1 데이터 소싱 4원칙

| 데이터 종류 | 출처 | LLM | 검증 |
|---|---|---|---|
| **본표 숫자 A** — 기존 확보(firm_*.json 14필드×5년) | firm_*.json | 금지 | 값 그대로 |
| **본표 숫자 B** — 미확보(법인세·OCI·비현금·운전자본·현금잔액·배당·자사주 등 ×5년) | **DART `fnlttSinglAcntAll`** (Phase 3) | 금지 | API 응답 + 본표 내적 정합 |
| **주석 세부 표** (유형자산 증감·판관비 구성·부문 실적 등) | 사업보고서 원문 → **LLM 추출** | 추출만 | 3층 검증(§6.3) |
| **설명 산문 + 5개년 해석** (what·why·five.cap/so) | **LLM 생성** (스토리 탐지 결과 문장화) | 생성 | §6.6~6.7 + 인용 강제 + 골든 |

> 계정→소스 매핑표(계정×연도 전수)는 Phase 3에서 `modules/report/CLAUDE.md`에 작성 — S 24키·딥다이브 각 행이 A/B/추출/파생 중 어디서 오는지 1:1로. §6.3 L2-③ 교차검증 앵커도 이 표가 정의.

### 2.2 역할 분담 확정표 (리더 질의 "GPU의 쓸모는" 답 — 2026-07-10)
> v6 재설계로 **레이아웃·그래프는 LLM도 사람도 아닌 템플릿 코드가 그린다**(row 기반 결정적 배치·고정 굵기·직교 라우팅·viz 8종은 시계열 배열만 받으면 자동). GPU는 "그리기"가 아니라 **"읽기(비정형 추출)·쓰기(산문 대량 생성)"** 전담.

| 작업 | 담당 |
|---|---|
| 레이아웃(배치·라우팅·패널) / 그래프 렌더·파라미터 | 템플릿+생성기 **코드** (LLM·사람 0) |
| 본표·시계열 숫자 | DART 정형 API (LLM 금지) |
| 주석 표 숫자 (기업마다 서식 제각각) | **LLM 추출** = GPU 용도 ① (3층 검증) |
| 스토리 사실(낙폭%·연속 연수·역설) | 코드 (story.py, §6.6) |
| 산문 ~115문장/사 (48사≈5,500, 2,600사≈30만) | **LLM 생성** = GPU 용도 ② (lint·골든이 발산 통제) |
| 앵커 의미 네이밍(1건/사)·최종 품질 판정 | **사람(리더)** — 창의 결정을 48건으로 압축 |

→ 사람 수작업은 삼성 원본 1회(완료)와 승인·검수만. 이것이 D7·D8("LLM은 숫자를 만들지 않는다, 하네스가 품질을 소유한다")의 v6 확장.

---

## 3. 기술 스택 결정

| 영역 | 선택 | 근거 |
|---|---|---|
| 프론트 | 정적 HTML + React CDN(셸·탭③) + dc-runtime.js(탭③) + vanilla(탭①) | v2 "빌드 도구 금지" + 이식 원칙. GitHub Pages 호환 |
| 탭 격리 | iframe (same-origin, `integration/` 하위) | ARCHITECTURE 이슈 #2 채택 패턴 |
| 데이터 포맷 | 탭별 per-ticker JSON (`integration/dossier/data/`) | firm_*.json 전례. 단건 fetch |
| 수집 | Python 3.11 + OpenDartReader(`document`·`list`·`fnlttSinglAcntAll`) + BeautifulSoup/lxml | disclosure·relation 패턴 참조(복제, import 금지) |
| 원문 저장 | SQLite `modules/report/data/reports.db` + `raw_cache/` | 모듈 표준. `raw_cache/`는 기존 .gitignore가 자동 제외 |
| LLM 서빙 | **SGLang on A100 80GB(원격, 주력)** — OpenAI 호환 서버(기본 포트 30000). 하네스는 노트북, LLM 호출만 원격. 폴백: llama.cpp Vulkan(Arc 140V) 8B 스모크 | A100 80GB면 32B 배치가 시간 단위(§6.5·부록 C) |
| 모델 | **기본 Qwen3-32B(AWQ/FP8)**, 대안 EXAONE-3.5-32B(A100 80GB 여유). 비교군 14B·8B. **Qwen3 thinking 비활성 필수**(서빙 엔진별 chat template 옵션 상이 — 착수 시 확인 / 폴백 `/no_think`) | 한국어+표 강점. 최종 선정은 held-out 골든(§6.4) |
| 구조화 출력 | SGLang 구조화 출력(xgrammar) / llama.cpp grammar(폴백) + **pydantic 재검증** | 서버측 강제 + 클라 이중 검증 |
| 하네스 코드 | `story.py`(스토리 탐지 §6.6) · `stylelint.py`(L0 §6.7) · `bank.jsonl`(few-shot §6.8) — 전부 CPU | 발산 통제의 코드 층 |
| 파이프라인 검증 | pytest (tests/report/) + 골든 회귀 | 프로젝트 표준 |
| 렌더 검증(L3) | **playwright(파이썬)+chromium** (Phase 4) — 자동 게이트. 시각 검수는 ui-ux-reviewer | 48사 자동화 |

> **R4 개정(2026-07-12, 커밋 `dfad073`)**: LLM 서빙 엔진을 vLLM → **SGLang**으로 확정(`.env.example`·`shared/config.py` REPORT_LLM_* 슬롯 참조). 본문 §1·§6·부록 C 등에 남은 vLLM 표기는 개정 전 서술 — 실측(Phase 4 착수) 시 §6.5와 함께 일괄 갱신.

---

## 4. 설계 결정 (D1~D12)

### D1. 탭바는 v2 오버레이(React)에 — **설정 배열(`DOSSIER_TABS`) 주도** (탭 추가 규격화)
- firm.html 안에 탭을 넣지 않는다 — firm.html 자체가 탭②.
- 오버레이(무명 인라인 JSX)를 개조하되 **탭 목록을 하드코딩하지 않고 설정 배열로** — 오버레이가 이 배열을 `map`으로 렌더(탭 버튼·lazy iframe·keep-alive·활성 판정 전부 필드로):
  ```js
  const DOSSIER_TABS = [
    // Step 1: 이 2개만
    { id:'eqs',      label:'EQS',       src:'firm.html',     context:'finance',  activeWhen:'always' },
    { id:'galaxy',   label:'현금 은하수', src:'galaxy.html',   context:'galaxy',   activeWhen:'hasData' },
    // Step 2(§5b, kospi50 확정 후): 아래 한 줄 추가
    // { id:'business', label:'사업·기업', src:'business.html', context:'business', activeWhen:'always' },
  ]
  ```
  → **탭 추가 = ①배열 한 줄 ②dossier/<id>.html ③<id>_<t>.json 파이프라인** 셋으로 규격화(bundle.jsx 재수술 불요). iframe 모델 유지(각 탭 독립 파일·빌드 없음). **탭①을 Step 2로 미루는 게 이 설계의 실효 증명** — 나중에 주석 한 줄만 풀면 됨.
- **토큰 구획**: 탭바·iframe 내부 = 현금 은하수 토큰. 오버레이 외곽 크롬(헤더·OverlayAiChat·면책 푸터) = 기존 v2 토큰 유지.
- **OverlayAiChat 3탭 공통 우측 사이드바 유지**, 탭 전환 시 `context` prop 갱신(배열의 `context` 필드). **면책은 오버레이 푸터 1곳**(§7.1-7과 합치).

### D2. 파일 배치
```
integration/dossier/
├── firm.html                    # 탭② (기존)
├── business.html                # 탭① (kospi50_business_tabs 이식)
├── galaxy.html                  # 탭③ (현금은하수_해방판 이식)
├── dc-runtime.js                # 탭③ 런타임 (해방판과 세트 — 함께 복사)
├── tokens.css                   # 공유 프리미티브 (간격·radius·타입 스케일·모션) — 셸+dossier 각자 link
├── theme-galaxy.css             # dossier 시맨틱 테마 (Mint 팔레트 + Pretendard/IBM Plex Mono)
├── extract_business_json.py     # 1회성: DATA → business_*.json 48개
├── pull_report_json.py          # publish/ → data/ 복사 (pull, 리더 소유)
├── assets/fonts/                # Pretendard·IBM Plex Mono woff2
└── data/
    ├── firm_<t>.json            # 기존 48개
    ├── business_<t>.json        # 신규 48개
    └── galaxy_<t>.json          # 초기 005930 → 파이프라인 pull로 확장
                                 #   (notes_*.json 폐기 — 주석 전체가 galaxy에 내장)

modules/report/                  # 신규 모듈 (Q1, 리더 소유)
├── CLAUDE.md                    # 규칙 + 계정→소스 매핑표(×5년) + reports.db 비커밋 사유
├── db.py · models.py · collector.py · sectioner.py · fs_enrich.py
├── series.py                    # 시계열 빌드(S 24키·파생·5점 완결성 판정)
├── story.py                     # 스토리 탐지 11종 + 앵커 클러스터 (§6.6)
├── llm.py · schemas.py · extract.py · stylelint.py · bank.jsonl · validate.py · publish.py · benchmark_extract.py
└── data/
    ├── reports.db               # ← .gitignore (커밋 제외)
    ├── raw_cache/               # 원문 (기존 패턴이 제외)
    ├── corps.csv                # 48사 시드 (모듈 SSOT)
    ├── review/                  # 리뷰 큐 + _BATCH_REPORT.md + _STYLE_REPORT.md + _STORY_COVERAGE.md ← .gitignore
    └── publish/                 # 검증 통과 JSON (커밋 — integration이 pull)
```

### D3. 디자인 토큰 = 2계층 SSOT (프리미티브 공유 + 표면별 테마 유지)
> 목표(리더 지시 2026-07-10): 셸과 dossier가 **프리미티브(공유 규격)만 일치**시키고 **팔레트·폰트는 각 표면 고유 테마 유지** — 셸=Cyan/Inter, dossier=Mint/Pretendard. `injectGalaxyTheme` 주입 해킹은 폐지.
- **`tokens.css`(신규, 공유 프리미티브만)**: 간격·radius·타입 스케일·모션 duration 등 **표면 무관 원자값**. 셸(styles.css)과 모든 dossier 페이지가 각자 `<link>`. (⚠️ CSS 변수는 iframe 경계를 못 넘으므로 **부모 상속이 아니라 각 페이지가 직접 link** — 이게 정석.)
- **시맨틱 테마(표면별, 공유 안 함)**: 셸 = Cyan(`--cyan #5eead4`)/Inter — 기존 `styles.css` 유지. dossier = Mint(`--mint #74EEC6`)/Pretendard·IBM Plex Mono — `theme-galaxy.css`(팔레트+폰트).
- **injectGalaxyTheme 폐지**: 신규 dossier 페이지(business.html·galaxy.html)는 `tokens.css` + `theme-galaxy.css`를 **정적 `<link>`** — 주입 없음. 탭②(firm.html)은 v1 fallback과 공유라 특수: `tokens.css` link + 팔레트는 **`?theme=galaxy|v2` 파라미터**로 시맨틱 레이어 선택(v2=galaxy 민트, v1=기존 v2 룩) → **injectGalaxyTheme·injectV2Theme 둘 다 폐지 가능**(Phase 2 스파이크로 v1 회귀 없음 확인; 회귀 위험 시 injectV2Theme만 v1용으로 잔존 허용).
- 탭③: 해방판 자체가 표준 — 내부 hex(이미 `:root` CSS 변수)를 그대로. `tokens.css` 프리미티브만 추가 link.
- **범용성 이점**: 팔레트·폰트 변경이 한 파일(theme-galaxy.css 또는 styles.css)에서 전파, 프리미티브(간격·스케일)는 tokens.css 한 곳. 셸까지 완전 통일(mint/Pretendard로 일원화)은 **하지 않음** — v2 셸 기존 룩 보존(standalone UI 원칙).

### D4. 해방판 이식 = 템플릿 데이터 구동화 재작성 (부록 A2 확정 — 정본 위계 §1.3)
> 핵심: 해방판은 삼성 전용 하드코딩 산출물이므로 "데이터만 교체"가 불가. **정적 마크업을 데이터 구동으로 전환 + JS 상수를 데이터 주입으로 리팩터**해야 한다. 시각·dc-runtime은 불변.
- `현금은하수_해방판.html` + `dc-runtime.js` → `dossier/`에 복사(dc-runtime.js는 **범용 엔진, 무변경**).
- **층 1 — 정적 마크업 → 데이터 구동(sc-for/보간) 재작성** (템플릿 수술 — 데이터 파일만으론 불가):
  1. **중앙 5패널 ~90행**(존 A~E, L110-411): 행별 `{display, raw_mn, sign, color, label}` 배열 → `sc-for`로 렌더. 펼침 소계·부문명 포함.
  2. **APPENDIX 14주석**(L419-432): `{note_no, title, summary, dive_key}` 배열 → `sc-for`.
- **층 2 — JS 상수 → 데이터 주입 리팩터** (→ `galaxy_<t>.json` fetch):
  3. **회사 메타** — 상단바 헤더·히어로("53.7조→57.9조")·"삼성전자와 자회사"·BS 캡션·관계기업명 (L60·67·69·170·293) → `corp.{name, fiscal_year, period, basis, cash_begin/end, equity_method_names}` 보간.
  4. **`S` 시계열 24키×5점 + `YEARS`**(L1062-1088) → `series`·`years`. 5점 완결·부호 방어는 이미 됨(A2-1).
  5. **차트 서사** — vLine valley 라벨(L1163 '반도체 한파' 리터럴)·vBubbles 4부문(L1249-1254)·vSteps/vPuddle/vHBar 삼성 수치(dive 호출부 L1230·1279·1325) → **viz 함수가 `this.S`/리터럴 대신 dive 데이터를 받도록 리팩터** + `anchor.label`·`dive.viz_data`.
  6. **`getDives()` 딥다이브 카피 전량**(L1290-1657) → `dives` 데이터(회사별 생성). `getDives()`가 하드코딩 D 객체 대신 주입 데이터를 반환하도록.
  7. **KNOTS·EQSTORY·ZONES**(L486-557) name·amt·story → 데이터. 구조(id/row/kind/xf/col)는 상수 유지.
  8. **오버뷰·에필로그**(L974·1027·1029) buildCard 카피 → 데이터(company_name 보간).
- **매듭 존재 가드**: buildGalaxy의 `K.k3`·`k5`·`k8`·`k13` 등 이름 하드참조(L763·818·837·845·869·906·938)에 **존재 여부 가드** 추가 — 손익 단계 결측 기업(cogs 없음)에서 은하수 소실 방지.
- `?ticker=` 파싱(기본 005930), fetch 실패 시 "데이터 준비 중" 패널(가짜 숫자 금지).
- 폰트 CDN → 로컬 `assets/fonts/`. React/Babel/dc-runtime.js CDN 버전 **고정**(R12), 로컬 벤더링 여부 Phase 1 결정.
- **불변**: dc-runtime·SVG 렌더 로직·CSS 변수·레이아웃 파라미터(CONFIG — **특히 `ribbon.uniform:true` 절대 불변**)·표준 계정 라벨·순수 UI 문구·SEGS. NUDGE·zoom은 해방판 미존재. √스케일 `wf`는 코드에 있으나 미사용(건드리지 말 것).
- **정본**: 부록 A2의 blocker 8카테고리 + 매듭 가드가 D4 최종 목록. 구판 5곳(cap·noncash·DEST·steps·zoom)은 해당 없음.

### D5. business_tabs 이식 = 단일 기업 뷰 변형 + 토큰 스왑
- 좌측 rail·상단 자체 탭바 제거 — 기업 선택은 v2 우주, 탭은 오버레이. `?ticker=`가 유일 입구.
- **부트스트랩 절제 필수(부록 A-2)**: rail DOM만 지우면 `$('#searchInput')` 리스너(L1260-1271)가 null TypeError로 백지 — `listRows`(L1227-1235)·`selectByCode`(L1255-1259)·이벤트 바인딩 함께 삭제, `render(선택 기업)` 호출만. workspace grid 320px(L72)→1fr.
- **업종 lens 우선순위 수정(부록 A-2)**: `industryKey`(L734-758)에서 통신·건설·소비재를 전력·소재보다 선순위로 — SK텔레콤·현대건설·KT&G power 오분류 버그(현행 배포본에도 존재).
- `const DATA` → `extract_business_json.py`로 `business_<t>.json` 48개 추출.
- 색 치환: `#060914→#05060d`, `#41dcff→#5CC7EA`, `#36e5bd→#74EEC6`, `#f7d56f→#E9C46B`, 텍스트 3단 → 표준(Phase S2 시각 검증으로 확정).

### D6. ⚠️ 사업보고서 파이프라인 = 신규 `modules/report/` (Q1)
- 경계 규칙: 원문 저장·LLM 추출은 데이터 생산 → integration 불가. disclosure(B 소유) 확장은 리더가 못 함 → 리더 소유 신규 모듈이 유일 경로.
- **부채 명시**: DART 수집 경로 증가 — 재무 이중수집(부채 #1)에 `fnlttSinglAcntAll`(×5년) 추가, 원문 수집 3중(disclosure/relation/report). ARCHITECTURE.md 부채 등재 + B·C 공유.
- **루트 CLAUDE.md 모듈 표 등재 시 `python scripts/sync_codex.py` 재실행 → AGENTS.md 함께 커밋**(CI가 `--check` 강제, ci.yml:27). v2/report CLAUDE.md는 미러 대상 아님.

### D7. LLM은 "숫자를 만들지 않는다"
- 본표 A·B·시계열은 코드가 채운다 — LLM 호출 전 "부분 완성 JSON"을 만들고 LLM은 빈 슬롯(주석 표·산문·5개년 해석)만 채운다.
- LLM 추출 수치는 **원문 백만원 정수(`raw_mn`)만** — 표시 문자열은 코드 생성. **스토리 사실(낙폭%·값)도 코드(story.py)가 payload 표시 문자열로** 넣고 LLM은 그대로 인용(§6.6).

### D8. 하네스가 품질을 소유한다
- 골든(§6.4)이 프롬프트·모델·**detector 임계·lint 규칙 변경**을 판정. 3층 검증 + L0 게이트 통과분만 publish. 불통과는 `data/review/`에 리뷰 큐 자동 생성.

### D9. 주석 = 탭③ 딥다이브 + APPENDIX 전담 (Q4 — 3탭)
- v6 해방판이 **핵심 주석 → 딥다이브 통합**(getDives), **정성·측정기법·잔액불변 주석 → APPENDIX 14건**(five=skip, 탭③ 하단)으로 이미 이원화. **탭④·notes.html 개념 폐기.**
- 타사의 딥다이브/APPENDIX 배정은 §7.3 라우팅("억지 매핑 금지")이 판정 — 삼성 구성을 강제하지 않음(기업마다 다른 것이 정상).

### D10. 타사 확장 시 은하수 레이아웃 정책 (Q3 — v6로 대폭 단순화)
- **v6 핵심: 굵기가 기본 설정에서 2단 고정**(6px/3.5px, `CONFIG.ribbon.uniform:true`). √스케일 함수(`wf`, ref 333.6)는 코드에 잔존하나 **미사용** — 구판 D10의 굵기 계수 검증·값 정규화(abs·clamp)가 **불요**, 기본 설정에서 굵기가 금액과 무관하므로 기하 왜곡 위험 없음. **⚠️ `uniform:false`로 바꾸면 삼성 ref(333.6) 기준으로 타사가 왜곡되므로 절대 전환 금지**(D12 계약). 노드 배치는 row 인덱스(결정적).
- 남는 것 = **부호 처리 + 스코프아웃 판정**(코드, `publish.py` 소유, §6.1 루프 초입 호출):
  - **흡수(스코프아웃 아님)**: fin>0(차입 조달)·icf>0(자산 회수)·bridge(OCF−NI)<0 — 도착지 문구·색 조건 분기, 값 부호로. cogs 결측(NAVER·카카오·SKT)은 원가/총이익/판관 지류·행 생략(딥다이브·패널은 배열 주도 — 신규 감사가 확인).
  - **스코프아웃(탭③ "준비 중", ①② 정상)**: 금융업 8사 + SK스퀘어(투자지주) + 최신연도(2025) OI<0(삼성SDI)·OCF<0 비금융(현대차·현대건설·고려아연·LIG넥스원·포스코퓨처엠)·NI<0(SK이노·LG화학). **판정은 최신연도 단년.**
  - **v6 추가 고려 — 5개년**: 스코프아웃은 최신연도 부호로 판정하되, **5개년 차트는 각 연도 독립**이라 개별 연도 음수(예: dsOp 2023 −14.9)는 vLine `zero:true`로 정상 표현(스코프아웃 아님). 5점 미완성 시계열만 해당 카드 `five=skip`.
  - **예상 분포**: 탭③ 제공 목표 **약 30~32사**(스코프아웃 16~18사).

### D11. 리더 보고 절차 — "템플릿으로 안 되는 것"의 공식 에스컬레이션
| 상태 | 의미 | 처리 |
|---|---|---|
| `AUTO_PASS` | L0+3층 검증 통과 | 자동 publish |
| `NEEDS_REVIEW` | 내용 검증 실패(인용·산술 불일치·문체 lint) | `data/review/<corp>.md`+스크린샷, 리더 개별 승인 |
| `TEMPLATE_MISMATCH` | **구조적 부적합**(필수 딥다이브 결측·역방향 흐름·D12 규칙 초과) | publish 중단 + **배치 보고서 필수 기재, 리더 결정 없이 진행 금지** |

- **배치 보고서** `data/review/_BATCH_REPORT.md`: 48사×상태 요약 + MISMATCH 목록(사유·원본 수치·대안) + NEEDS_REVIEW 링크. 콘솔에도 출력.
- 리더는 MISMATCH별로 ⓐ 스코프아웃 ⓑ D12 규칙 추가 ⓒ 템플릿 수정 중 결정 → §9에 누적 기록.

### D12. 확장 가변성 정책 — 미세 UI 변형은 보고 없이 자동 흡수
> 판정 근거: **신규 가변성 감사(Phase 1, 부록 A2)**. 원칙: 기업별 미세 차이는 ① 템플릿의 배열/row 주도 렌더 + ② 생성기 결정적 규칙 두 겹으로 흡수, 두 겹으로 안 되는 것만 TEMPLATE_MISMATCH(D11)로 승격. 개별 기업 수작업 미세조정 금지.
- **v6 양면성**(부록 A2): 레이아웃 산출은 row 인덱스·고정 굵기(uniform)·직교라 **런타임 가변성은 안전**(굵기 계산 미사용·사행·zoom 없음, viz 수학 음수/0 방어 완비). 그러나 데이터가 **삼성 하드코딩**이라 **이식 시 데이터 구동화 재작성이 선행**(D4) — 재작성 후에야 생성기 계약이 성립.
- **금지 사항(불변식)**: `CONFIG.ribbon.uniform:true` **불변**, `wf`/`scale`/`ref` 파라미터 손대지 말 것 — uniform=false 전환은 삼성 ref 333.6 기준 굵기라 타사 왜곡.
- **생성기 계약 (galaxy — 부록 A2 확정)**: ⓐ `series` 24키 모두 **5점 완결**(미완성 키의 five=skip) ⓑ `dive.five.key`·`links[].row`는 반드시 존재하는 series 키·패널 행 참조 ⓒ 손익 단계 결측 시(cogs 없음) 해당 KNOTS·행을 함께 생략(매듭 가드가 전제) ⓓ 부호 처리(D10) ⓔ 산문 필드 길이 상한(A7·L0-2) ⓕ 긴 라벨은 생성기가 단축형. **구판 계약(√스케일·brSpec·DEST⊆brSpec 등)은 폐기**.
- **생성기 계약 (business — 부록 A-2)**: business_cards 2~4개 · kind 21종 · 금융사 display_category '금융업' · dart_url/rcept_no 중 하나 필수.
- **사전 sanity 검증(생성기 전단)**: rev≥cogs 정합·YoY 10배 점프 감지·단위 교차(한화에어로 오류 R10). 시계열도 5점 완결·부호 일관 검증.
- Phase 1에 **가변성 스파이크**: 골든 JSON 합성 변형 3종(딥다이브 2개 제거 / 시계열 음수·결측 주입 / 라벨 2배 연장)을 galaxy.html에 렌더해 깨짐 없음 확인.

---

## 5. Phase 계획 — **Step 1(현금 은하수 트랙) 먼저, Step 2(사업 개요 탭) 나중**

> **진행 순서(리더 지시 2026-07-10)**: 하나씩 트래킹하기 위해 두 스텝으로 분리.
> - **Step 1 = 탭③ 현금 은하수 + AI 파이프라인** (Phase 0~5). 지금 진행. 기존 탭②(EQS)와 함께 2탭으로 배포.
> - **Step 2 = 탭① 사업 개요** (Phase S2). `kospi50_business_tabs.html`이 **아직 확정판이 아니라** 지금은 이식 안 함 — 프로토타입 확정 후 별도 진행(§5b). D1 설정 배열이라 나중에 저비용으로 끼워 넣음.
>
> 공통: 브랜치 `feat/dossier-tabs-p<N>`(dev에서 분기) → Phase 단위 PR → dev. Phase 종료 시 체크박스 + `integration/v2/PROGRESS.md` 갱신.
> 로컬 구동: 저장소 루트에서 `python -m http.server 8000` → `http://localhost:8000/integration/v2/index.html`.

### Phase 0 — 준비 (1~1.5일)
- [ ] **선행 조건(순서 고정)**: ① 계획서 2개(이 문서·스타일 가이드)의 **v6 편집 커밋** + **해방판 2파일(`현금은하수_해방판.html`·`dc-runtime.js`)·v6 md 커밋** — ⚠️ 2026-07-08 커밋(869b8d7)은 **구판 v3 골격만**이고 v6 내용·해방판·v6md는 미커밋이니, 이 커밋이 착수 첫 작업(건너뛰지 말 것). ② 그 브랜치를 dev로 머지 — `scripts/sync_codex.py`·CI·본 문서들이 이 브랜치에 있어, 머지 전 dev 분기 시 D6·Phase 3 실패. 이후 dev 최신화, `feat/dossier-tabs-p1` 분기.
- [ ] **타 담당자 공유 이슈 2건**(gh issue): ① R10 `firm_012450.json` revenue 단위 오류 재수집(담당 A) ② R6 DART 수집 다중화 부채(B·C). 링크를 §9에 기입.
- [ ] 폰트: Pretendard(해방판 CDN과 동일 버전) `web/static`에서 사용 웨이트(400/500/600/**700**)만 복사 → `dossier/assets/fonts/pretendard/`. IBM Plex Mono 웨이트당 latin woff2(총 3~4개). 검증: 임시 `test_fonts.html` → DevTools woff2 200.
- [ ] `tokens.css`(공유 프리미티브) + `theme-galaxy.css`(dossier Mint/Pretendard 시맨틱 테마) 작성 — D3 2계층.
- [ ] **스키마 확정(§5.1은 골격 — 실물이 정본)**: 해방판의 `S`·`getDives()`·`KNOTS`·`SEGS`·`CF`·중앙 패널 행·상단바/인트로를 **전수 역산**해 스키마 확정, §5.1 갱신. ⚠️ §5.1 예시를 그대로 베껴 검증 코드 먼저 짜지 말 것.
- [ ] **골든 데이터**: `dossier/data/galaxy_005930.json` 수작업 작성(주석 전체+APPENDIX 14+5개년 S 포함). 모든 수치 `raw_mn` 병기. **[CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md) Part B(B1 수치·B1-5 시계열·B2 딥다이브·B3 매핑·B4 APPENDIX)와 대조**. **우선순위**: 수치=스타일 가이드 B1 우선 / 카피 자구·links 필드=해방판 실물 우선(B2 문체 기준·B3 개념 지도로 실물을 "교정"하지 말 것). 시각 동등성 비교 텍스트 기준=골든 JSON.
- [ ] 필수 키 체크 스크립트 `tests/report/check_golden_keys.py`(pydantic 아님 — 키·enum·산술·**시계열 5점 완결** 스모크. pydantic은 Phase 4에서 승격).
- [ ] 골든 정합성 검토 — 교육용 단순화 항목에 `residual`/`overlap`/`skip` 플래그(검증 규칙 §6.3과 모순 없게).
- DoD: `python tests/report/check_golden_keys.py` 통과 + 골든이 §5.1 확정판·B1-5 시계열과 일치. ⚠️ **골든의 시각 정확성(표시값·색키·amt)은 Phase 1 시각 대조에서 최종 확정** — check_golden_keys는 구조 스모크만이라 Phase 0 통과 ≠ 골든 확정. (Phase 0에서 해방판 값 칩과 골든 표시값 1:1 수동 대조 체크리스트 권장 — Phase 1 재작업 감소.)

#### §5.1 galaxy_<ticker>.json 스키마 (골격 — Phase 0에서 실물 역산으로 확정)
```jsonc
{
  "schema_version": 2,   // v6
  "corp": { "ticker": "005930", "name": "삼성전자", "fiscal_year": 2025,
            "fiscal_label": "FY2025 (2025.1.1~12.31) · 연결", "rcept_no": "...", "unit": "백만원" },
  "strings": { "header": "…", "intro_lines": ["…"], "hero": "53.7조 → 57.9조" },   // 상단바·인트로
  "years": ["FY21","FY22","FY23","FY24","FY25"],
  "series": {   // S 24키 × 5점 (조원, 코드가 채움 — LLM 금지)
    "revenue": [279.6,302.2,258.9,300.9,333.6], "op": [51.6,43.4,6.6,32.7,43.6],
    "tax": [13.4,-9.2,-4.5,3.1,4.3], "rnd": [22.6,24.9,28.4,35.0,37.8], "...": "24키 전수"
  },
  "anchor": { "label": "반도체 한파", "year": "FY23", "cause_quote": "…원문 인용…", "confidence": 0.9 },
  "knots": [ { "id": "k2", "name": "매출액", "row": "is-revenue", "kind": "outflow|income|reservoir",
               "amt": "333.6", "raw_mn": 333605938 } ],   // 17개, row 기반 배치(좌표는 코드)
  "panels": {   // 중앙 5패널 행 (존 A~E) — 이름·표시값·raw_mn
    "B": [ { "row": "is-revenue", "name": "매출액", "v": "333.6", "raw_mn": 333605938, "color": "mint" } ]
  },
  "dives": {   // getDives 41 객체(콘텐츠 27 + APPENDIX 14). raw_mn은 html의 raw(포맷 문자열)가 아니라 중앙 패널 행 title(백만원)에서 회수(D7)
    "k2": { "z": "B", "name": "매출액", "amt": "333.6조", "raw_mn": 333605938,
      "what": ["…"], "links": [ { "t": "부문", "row": "…", "txt": "…", "a": "333.6" } ], "lnote": "…",
      "why": { "sub": "규정|시각화", "body": ["…"], "viz": "vBubbles", "viz_data": {…}, "cap": "…" },
      "five": { "key": "revenue", "cap": "…[숫자칩]…", "so": "한 문장", "valley": 2 } }
    // five 3형: {key,cap,so,valley?} | {twin:{a:{name,key},b:{name,key}},cap,so} | {skip:"사유"}
  },
  "appendix": [ { "n": "n16", "tag": "주16 우발부채", "what": "…", "why": "…", "five": {"skip":"…"} } ],  // 14건
  "meta": { "generated_by": "manual|pipeline@<model>@<bank_ver>@<detector_ver>@<lint_ver>",
            "validated": true, "review_flags": [], "routing": {"dive": 27, "appendix": 14} }   // 합 41
}
```
`viz` enum = `vLine|vTwin|vWater|vHBar|vSteps|vBubbles|vPuddle|vChips`. 색은 `color_key` 문자열(코드가 `--var`로 해석). **단위**: series/표시=조(코드 생성), `raw_mn`=백만원. notes_*.json 폐기(주석 전체가 이 스키마 `dives`+`appendix`에).

### Phase 1 — 탭③ 이식: galaxy.html **데이터 구동화 재작성** (3~4일 — 최대 볼륨·재작성 정확성 리스크 R14; Phase 4는 최대 복잡도)
> 부록 A2가 이 Phase의 정본 목록. **신규 가변성 감사는 완료**(부록 A2) — 남은 것은 재작성 실행.
- [ ] `현금은하수_해방판.html` + `dc-runtime.js` → `dossier/`. dc-runtime.js는 무변경.
- [ ] **층 1 (마크업 데이터 구동화, D4)**: 중앙 5패널 ~90행(L110-411) + APPENDIX 14(L419-432)를 `sc-for` + 데이터 배열로 재작성. **시각 결과 불변**(정적 영역 기준 시각 대조 — 아래 검증①).
- [ ] **층 2 (JS 상수 → 데이터 주입, D4)**: 회사 메타·`S`/`YEARS`·차트 서사(valleyLabel·vBubbles 등)·`getDives()` 카피·KNOTS/EQSTORY/ZONES·오버뷰/에필로그 → `galaxy_<t>.json` fetch. viz 함수가 리터럴 대신 dive 데이터를 받도록 리팩터.
- [ ] **매듭 존재 가드**: buildGalaxy `K.k*` 하드참조에 가드(D4). `?ticker=` 파싱, fetch 실패 폴백. 폰트 로컬화. CDN 버전 고정(R12).
- [ ] dc-runtime의 async 데이터 수용 최소 변경(데이터 로드 후 하이드레이션). **첫 반나절 스파이크** — 불가 시 R3 폴백.
- [ ] **가변성 스파이크(D12)**: 골든 합성 변형 3종(손익 단계 제거[cogs 없음] / 시계열 음수·결측·5점 미만 주입 / 라벨 2배 연장) 렌더 → 은하수 소실·NaN·겹침 0.
- 검증: ① `galaxy.html?ticker=005930` 단독 → **해방판 원본과 시각 동등성**: `particles=false` + 애니메이션 정지 상태에서 정적 영역(패널·은하수 구조·카드·차트) 스크린샷을 ui-ux-reviewer가 대조 — 텍스트·레이아웃·색·수치 동일 판정(파티클·rAF 레이어 제외, 엄밀 픽셀 diff 아님) ② 딥다이브 카드·5개년 차트(vLine/vTwin/vWater/vHBar/vBubbles/vPuddle/vSteps/vChips) 렌더 ③ JOURNEY/PINNED·제스처 스크롤·맞물림 연결선·펼침 동작 ④ 콘솔 에러 0 ⑤ 3열 그리드 반응형(좁은 폭 오버레이−300px).
- DoD: 시각 동등(①) + `galaxy.html`에서 grep으로 삼성 숫자·'삼성전자'·'반도체 한파'·부문명(DX/DS/SDC/Harman) 리터럴 잔존 **0건**(전부 galaxy_005930.json으로 이동).

### Phase 2 — v2 오버레이 셸 (Step 1 = 탭②③ 2탭) (1일)
- [ ] 오버레이(무명 JSX, bundle.jsx L2956) 개조: **`DOSSIER_TABS` 설정 배열 주도 탭바**(D1 — 배열 map, 하드코딩 금지). **Step 1에서는 배열에 ②EQS·③현금 은하수 2개만**(①business는 Step 2에서 배열 한 줄 추가). iframe lazy mount + keep-alive. **OverlayAiChat 유지**(context 갱신), **면책 푸터 유지**.
- [ ] **표시 토글 스파이크**: `display:none` vs `visibility:hidden+offscreen` — 재표시 시 ③ 스크롤 위치·sticky·제스처 상태 정상 복원되는 쪽 채택.
- [ ] **오버레이 열림 동안 셸 rAF 일시정지**(또는 배경 불투명화로 backdrop-filter 제거) — §8.
- [ ] **injectGalaxyTheme 폐지, 정적 테마 link 전환**(D3): 신규 dossier 페이지는 `tokens.css`+`theme-galaxy.css` 정적 link. firm.html은 `?theme=` 파라미터로 팔레트 선택 — v1 회귀 없음 스파이크 확인(회귀 위험 시 injectV2Theme만 v1용 잔존). corp 오버레이의 주입 호출부 제거.
- [ ] 탭 활성화: Phase 2 시점 = 전 기업 ② 활성, 삼성만 ③ 활성. (①business는 Step 2 — 탭바에 아직 없음.)
- [ ] `integration/v2/CLAUDE.md`("injectV2Theme 무변경" → 3탭·tokens.css 2계층·injectGalaxyTheme 폐지) + `DESIGN.md` 갱신.
- 검증: 탭 전환 왕복 20회 — 재로드 없음·<200ms·콘솔 0·재표시 후 ③ 정상. v2 셸 픽셀 변화 없음.
- DoD: 삼성 기준 탭②③ 완동(2탭), 오버레이 열림 중 셸 rAF 정지 확인.

### Phase 3 — modules/report/ 수집 파이프라인 (5개년, 2~2.5일) — Q1 승인 완료
- [ ] 모듈 뼈대(D2) + `data/corps.csv` 48행(dossier에서 1회 복제, 이후 모듈 SSOT).
- [ ] `models.py` (reports.db): `report_raw(rcept_no PK, ticker, corp_code8, corp_name, fiscal_year, fetched_at, raw_path)` — **5개년치 다행** · `report_section(id, rcept_no FK, section_key, note_no, title, text_html, text_md, char_len)` · `fs_account(rcept_no, sj_div, account_id, account_nm, amount, currency)` — **fnlttSinglAcntAll ×5년** · `pipeline_state(rcept_no, target, stage, status, attempts, error, updated_at)`.
- [ ] `collector.py`: corps.csv 순회 → `dart.list`로 **최신 5개 사업보고서** rcept 조회 → `dart.document`/document.xml 수집 → `raw_cache/`. idempotent. **정정공시 stub 폴백(부록 B-2)**: `sub_docs ≥ 30 && has(사업의 내용)` 아니면 직전 보고서 폴백. **최적화: 부문 5개년은 보고서당 당기+전기 2개년 포함 → 2025·2023·2021 3개로 5년 커버**(240→144건, Phase 3에서 확정).
- [ ] `fs_enrich.py`: `fnlttSinglAcntAll` **48사 × 5개년** → fs_account. **계정→소스 매핑표(×5년)를 modules/report/CLAUDE.md에 작성**.
- [ ] `series.py`: firm_*.json + fs_account + 주석 추출을 **S 24키 × 5점**으로 조립(파생 tci=ni+oci 등, 키별 소스 맵, **5점 완결성 판정 → 미완성은 five=skip 플래그**). **R&D 5개년 소스 미확정(R13)** — fnlttSinglAcntAll에 없으면 '연구개발활동' 표 또는 성격별 비용에서.
- [ ] `sectioner.py`: **sub_docs 목차 기반**(부록 B). "III.3 연결재무제표 주석" 별도 서브문서를 주석 번호 단위 2차 분할, 표 HTML 보존 + text_md 저장.
- [ ] `.gitignore`: `modules/report/data/reports.db`·`review/`·루트 `docs_cache/`(OpenDartReader 캐시) 추가(+ 예외 사유 주석). raw_cache/는 기존 패턴이 커버.
- [ ] CI 정합: `modules/report/` Black 대상 추가 결정 + DART 키 의존 테스트 `pytest.mark.skipif`.
- [ ] 루트 CLAUDE.md·ARCHITECTURE.md 모듈 표 등재 + **`python scripts/sync_codex.py` 재실행**(D6).
- [ ] pytest: 섹셔닝 단위(삼성 fixture) + 이종 3사(금융·바이오·플랫폼) 조기 테스트(R5).
- 검증: 48사 backfill → pipeline_state 전부 ENRICHED, **S 24키 5점 완결률** 리포트(미완성 키·기업 목록).
- DoD: reports.db에 48사 5개년 원문+섹션+정형계정. DART 키만 있으면 `python -m modules.report.collector`로 재현.

### Phase 4 — LLM 하네스 + 일관성 계층 (3~4일 — 최대 복잡도)
- [ ] **LLM 백엔드**: A100에 vLLM 기동(Qwen3-32B AWQ + guided_json) → 노트북 base_url 접속. 폴백 llama.cpp 8B 스모크. **첫 작업: 단건 지연 실측(thinking 비활성 확인) → §6.5 갱신.**
- [ ] `requirements.txt`에 pydantic·openai·playwright 추가 + `playwright install chromium`.
- [ ] **`story.py`(§6.6)**: 스토리 탐지 11종 + 앵커 클러스터 + vLine 파라미터(valley·zero·twin·skip). **48사 detector 드라이런 → `_STORY_COVERAGE.md`**(기업×유형 분포, S11 비율). S11>40% 기업·패턴 발견 시 규칙 추가 후 재드라이런.
- [ ] **`stylelint.py`(§6.7)**: L0 9규칙 + 문체 지문 z-score. 삼성 골든 분포로 p5~p95 캘리브레이션.
- [ ] **`bank.jsonl`(§6.8)**: 삼성 190필드 자동 유형화(딥다이브 클래스 7 × 필드 9 × 스토리 유형) + 마스킹판. source=005930|synthetic만.
- [ ] `schemas.py`(pydantic — check_golden_keys 승격) / `llm.py`(guided_json·temp 0·seed·재시도) / `extract.py`(§6.1 루프 — 브리프→카드→lint→3층→publish) / `validate.py`(§6.3) / `publish.py`(부호·스코프아웃 판정 D10 + `data/publish/`) / `benchmark_extract.py`(§6.4).
- [ ] **회사 브리프 호출**(§6.6): 앵커 이벤트 네이밍(1건/사) → 리더 승인 큐.
- [ ] **검증기 캘리브레이션**: validate·lint·detector를 골든에 먼저 실행 — 골든 통과할 때까지 임계 조정.
- [ ] **held-out 제2 골든**: 타 업종 1사(POSCO홀딩스/NAVER) 주석 3~5건 + 5개년 캡션 수작업 → few-shot 미포함 벤치 전용.
- [ ] `integration/dossier/pull_report_json.py`.
- [ ] 골든 회귀 pytest: 삼성 재생성 diff(raw_mn 100%·금칙어 0·**스토리 유형 일치 ≥90%**) + held-out 점수 + 스킬 3종. **LLM·DART 의존은 skipif** — CI는 fixture만.
- 검증: 골든 회귀 통과 + `_STORY_COVERAGE`·`_STYLE_REPORT` 생성 + 무작위 1사 수동.
- DoD: `python -m modules.report.extract --ticker 005930` 1커맨드로 검증 통과 JSON 재현.

### Phase 5 — galaxy 48사 확장 + 성능·QA 마감 (2일) — **Step 1 완료**
- [ ] 배치 실행: **galaxy = D10 부호 판정 통과 약 30~32사**. resumable(다일 허용).
- [ ] **`_BATCH_REPORT.md` 리더 검토(D11)** + **`_STYLE_REPORT.md` 48사 병렬 스캔**(§6.7) → MISMATCH 결정(§9 기록) → 리뷰 큐 소화 → publish → `pull_report_json.py`.
- [ ] 탭 활성화: dossier/data에 JSON 존재하는 ticker만 ③ 활성(스코프아웃은 "준비 중").
- [ ] 성능 마감(§8 전항목) + 48사 스모크.
- [ ] 문서 마감: ARCHITECTURE.md(모듈 표·부채·이슈 #2), 이 문서 상태, PROGRESS.md. sync_codex 재실행(CLAUDE.md 재수정 시).
- DoD: 배포 URL에서 **48사 탭② + 30~32사 탭③** 완동. dev 머지. **← Step 1 마일스톤** (탭①은 Step 2).

---

## 5b. Step 2 — 탭① 사업 개요 이식 (kospi50_business_tabs 프로토타입 **확정 후** 별도 진행)
> ⚠️ **Step 1과 분리**: `kospi50_business_tabs.html`이 아직 확정판이 아니므로 지금은 이식하지 않는다. 프로토타입 확정 후 착수. **D1의 `DOSSIER_TABS` 설정 배열 덕에 탭 추가가 저비용**(배열 한 줄 + 페이지 + JSON) — 이 분리가 D1 설계의 실효 증명. business는 galaxy/AI 파이프라인과 독립(modules/report·LLM 하네스 무의존)이라 언제든 끼워 넣을 수 있다.

### Phase S2 — 탭① 이식: business.html (프로토타입 확정 후 · 1~1.5일)
- [ ] `extract_business_json.py`: 확정 프로토타입의 `const DATA` → `business_<t>.json` 48개.
- [ ] `kospi50_business_tabs.html`(확정판) → `dossier/business.html`: rail·자체 탭바 제거(부트스트랩 절제 D5), `?ticker=` 단일 렌더, DATA→fetch, 토큰 스왑(tokens.css+theme-galaxy.css), industryKey 우선순위 수정(D5).
- [ ] `DOSSIER_TABS` 배열에 `business` 항목 추가 + 48사 활성화(D1).
- 검증: 48개 ticker 순회 스모크(fetch 200+필수 키+lens 배정표) + 3사 ui-ux-reviewer 시각 검수.
- DoD: 48사 전부 탭①. **탭①②③ 3탭 완동 — dev 머지 후 배포 URL 확인.**

---

## 6. LLM 하네스 상세

### 6.1 추출·생성 루프 (기업 단위)
```
for corp in corps.csv(48):
  series = series_build(corp)                    # S 24키·파생·5점 완결성 (코드, §Phase4 series.py)
  if scope_out(corp): mark TEMPLATE_MISMATCH ; continue   # D10 부호 판정 (코드)
  facts = story_detect(series)                   # 스토리 11종 + 앵커 (코드, §6.6)
  brief = llm.brief(corp, facts, mdna_slice)     # 회사 브리프 1호출 → 앵커 label (리더 승인 큐)
  partial = build_partial_json(corp, series, facts, brief)   # 본표·시계열·viz·색·레이아웃·five 파라미터 = 코드
  for dive in dives(corp):                        # 딥다이브 1건 = 1호출
    for attempt in 1..3:
      out = llm.card(dive, few_shot=bank.match(dive), ctx=brief, json_schema)   # what·links·why·five.cap/so 문장화
      ok, errs = L0_stylelint(out) and validate_note(out)   # §6.7 + §6.3 L1·L2
      if ok: break
      prompt += 오류 요약                          # 실패 필드만 부분 재생성
    merge_or_flag(partial, out, ok)
  ok = validate_doc(partial)                       # 문서 lint(용어 첫 등장·중복) + L2 + L3 렌더
  if ok: status=AUTO_PASS → publish 즉시
  else:  status=NEEDS_REVIEW + data/review/<corp>.md + shots/
write _BATCH_REPORT.md / _STYLE_REPORT.md / _STORY_COVERAGE.md   # D11·§6.7·리더질의
```
- **결정성**: 추출 temp 0, 생성 0.3, seed 고정. `prompt_ver`에 **bank_ver·detector_ver·lint_ver** 태그 → meta.
- **컨텍스트**: 전문 투입 금지. 주석 단위 text_md 1~3개 + 브리프. RAG 불필요.

### 6.2 프롬프트 (추출/생성 분리)
- **추출**: "수치는 원문 백만원 정수(raw_mn)만, 계산·단위변환 금지. 원문에 없으면 null. 모든 수치에 source_quote(원문 15~40자). JSON Schema만." + 유형별 예시 1건 + 대상 주석 text_md.
- **생성(산문·5개년)**: §7.1 산문 원칙 + §7.2 카드 규칙 + **story.py가 넣은 확정 사실 payload(표시 문자열)** → what·why.body·cap·so만. **viz·색·스토리 유형은 LLM이 정하지 않는다**(코드).

### 6.3 검증 3층
| 층 | 내용 | 실패 |
|---|---|---|
| L1 구조 | pydantic(타입·필수키·viz/color enum·raw_mn 정수·**series 5점**) | 재시도 |
| L2 사실 | ① source_quote ⊂ text_md(정규화 후) ② 표 내적 정합(raw_mn, residual/overlap 허용 — 골든 캘리) ③ 본표 교차(§2.1 매핑 계정만, ±0.1%) ④ **산문·cap 속 숫자 ⊂ 입력 payload** ⑤ **시계열 정합**(series 각 연도 값 vs 해당 연도 본표 대조) | 재시도 → 2회 실패 리뷰 큐 |
| L3 렌더 | playwright headless로 galaxy.html 렌더 → 콘솔 0 + 스크린샷 | 리뷰 큐 |

L0(문체 게이트, §6.7)는 L1 전단 — 실패 필드만 부분 재생성.

### 6.4 골든 테스트 = 판정 장치 (오염 방지)
- **삼성 골든**: 회귀 스모크(raw_mn 100%·금칙 0·스토리 유형 일치). few-shot 뱅크 소스라 **모델 선정 지표로는 안 씀**.
- **held-out 제2 골든**(타 업종 1사, few-shot 미포함): `benchmark_extract.py`가 raw_mn 일치율·인용 통과율·**스토리 유형 일치**·재시도를 표로 → **모델·프롬프트·detector 임계·lint 규칙 변경을 판정**. 점수 유지·개선 시에만 변경 병합(스킬 `/galaxy-bench` 게이트).

### 6.5 처리량 추정 (v6 5개년 반영 — Phase 4 첫 실측 후 갱신)
- 슬롯/사: 딥다이브 생성 카드 ~24(five skip 17 제외) × (what+why+cap+so) + 주석 추출 ~10 + 부문 추출 ~3 + 브리프 1 ≈ **호출 ~40/사** (구판 ~30 대비 5개년 해석으로 증가하나 skip 템플릿화가 상쇄).
- 대상: galaxy 약 30~32사 → **~1,300±300회**, 토큰 ~4~5M.
- **A100 vLLM 32B(동시 8~16)**: **반나절~1일** 배치(재시도·검증 포함). 노트북 폴백은 다일(스모크 전용).
- 2,600사 전망: 슬롯 3배에도 A100 1장 **2~4일** 배치 — 성립(부록 C).
- **DART API**: 5개년 원문 최대 240건(부문 최적화 시 144) + fnlttSinglAcntAll 48×5=240콜 → 총 ~500-700콜, 일일 한도 20,000의 3% — 무영향. raw_cache 60~120MB.

### 6.6 스토리 탐지의 결정화 (`story.py` — 전부 코드, LLM 0%)
> 5개년 "해석"이 기업 간 일관성 붕괴 위험이 가장 큼. **"어떤 스토리인지"는 코드가 판정, LLM은 탐지된 사실을 문장화만.** 삼성 캡션 24건이 ~10패턴으로 전부 환원됨(실증).
- **탐지 규칙 폐쇄 목록 11종**(우선순위): S1 부호특이(적자·환입·순조달) · S2 골짜기·회복(낙폭 임계 지표군별 15~40% + 회복) · S3 역설 워치리스트 6종(불황에 최대투자·불황에도 R&D·이익 무너져도 현금·환입발 역전·자사주 재개 등) · S4 연속 증감(전 구간 단조+총변화≥10%) · S5 기간 내 최대("5년 새 최대"만, "사상 최대" 금지) · S6 정점 후 감소 · S7 교차 역전(ni>op) · S8 동행 · S9 일회성 점프(|YoY|>3×중앙값) · S10 안정 · S11 무스토리 폴백("꾸준").
- **앵커 이벤트**: 핵심 지표 3개+가 같은 trough 연도 공유 시 성립(코드) → 시계열당 primary 스토리 강제 참조(기업 내 일관성). 삼성=FY23 반도체 한파(revenue·op·ni·eps·dsOp 동시).
- **StoryFact payload**: 수치 원값 + **코드가 fmt1로 포맷한 표시 문자열**("87%","6.6조","FY23") → LLM은 그대로만 인용(L2-④가 검증). `so` 인사이트 프레임 사전을 힌트로.
- **vLine 파라미터**: valley(앵커 참여+S2 시 trough 인덱스) · zero(min<0) · twin(고정 후보표) · skip(잔차·부호요동·비추세·5점 미완성 — 사유 4류형 고정 템플릿, LLM 생성 아님).
- **캘리브레이션**: 삼성 24캡션 + held-out에 detector 실행, 사람 스토리와 유형 일치 ≥90%까지 임계만 조정.
- **⚠️ 골든 예외 명시**: 삼성 골든 k2 카피(L1315)는 "사상 최대"를 쓰나 이는 **리더가 외부 지식으로 검증한 수작업 예외**(S5는 5년 창이라 "5년 새 최대"만 자동 단정 가능). **골든의 "사상 최대"는 화이트리스트 예외**로 L0-3·S5 검사 통과, **LLM 자동 생성분은 S5 규칙("사상 최대" 금지, "5년 새 최대"만) 엄격 적용**. §6.7 캘리브레이션에서 "골든 통과 = 규칙 준수"가 성립하도록 이 예외를 stylelint 화이트리스트에 등록.
- **산업 커버리지**(리더 질의): S1~S11은 시계열 **수학적 모양**을 탐지 — 산업 무관(해운 사이클=S2+S6, 배터리 성장=S4, 방산 수주=S9). **산업 의미는 회사 브리프가 부여**(2단 구조). 미커버는 S11 안전 폴백. `_STORY_COVERAGE.md` 드라이런으로 사각 조기 발견.

### 6.7 L0 문체 게이트 (`stylelint.py` — 3층 전단, 전부 정규식·사전, 비용 0)
- L0-1 종결어미 화이트리스트(격식체·명사끊김 fail) · L0-2 필드별 문장 수·길이(골든 p5~p95) · L0-3 금칙어·미래 단정(+**"사상 최대" 금지 — S5와 짝**, 단 삼성 골든 k2는 리더 검증 화이트리스트 예외) · L0-4 숫자 인용(payload만)+스토리 cap 숫자≥1 · L0-5 비유≤1(마커 사전) · L0-6 용어 6종 즉석 풀이 · L0-7 구조 마커(canonical label 자구 강제) · **L0-8 골든 오염**(삼성 고유 토큰 블랙리스트: DX/DS/SDC/Harman·333.6·6,605 — 업종 예외 화이트리스트) · L0-9 중복·복제(3-gram).
- **규칙 밖 이질감**: ① `_STYLE_REPORT.md` 교차 기업 병렬 표(같은 슬롯 48사 나란히 — 리더 스캔 공식 절차) ② 문체 지문 z-score(어미 분포·문장 길이·숫자 밀도, z>2.5 플래그) ③ LLM-judge는 플래그+15% 표본만, 판별력 캘리 통과 시에만 게이트 편입 ④ 임베딩 유사도 **보류**(2,600사 때 재검토).

### 6.8 few-shot 뱅크 (`bank.jsonl`)
- 유형화 2.5축: 딥다이브 클래스 7(RESERVOIR/IS_FLOW/CF_BRIDGE/CF_ACTIVITY/EQUITY_BS/NOTE_QUANT/NOTE_QUAL) × 필드 9 + **five 전용 스토리 유형 축(S1~S11이 1차 매칭 키)**. 삼성 190필드 자동 분류.
- **마스킹판 주입**(금액→⟨금액⟩·연도→⟨연도⟩·부문→⟨부문⟩) — 오염 구조적 예방. 호출당 2~4건.
- held-out 오염 방지: source=005930|synthetic만(로드 assert) · 프롬프트 빌더 held-out 토큰 abort 가드 · held-out 판정 범위를 "detector 임계·lint 규칙 변경"까지 확대.
- 삼성에 없는 셀(적자 캡션 등)은 리더 수작업 `synthetic` 2~3건.

### 6.9 프로젝트 스킬 3종 (`.claude/skills` — 기존 check/review 컨벤션 옆)
> 원칙: **스킬 = 절차·게이트 순서의 정본, 규칙 수치·프롬프트 = 코드가 정본**(이중 정본 금지).
- `/galaxy-gen <ticker|--batch>`: 사전조건 체크(REPORT_LLM_* env·A100·pipeline_state) → 실행 순서(collect→enrich→series→story→brief→generate→validate→publish) → 결과 요약·NEEDS_REVIEW 목록. **금지: 검증 우회 publish · 수치 수동 수정 · 골든/스타일 가이드 수정 · held-out few-shot · 비경로 명시 add.**
- `/galaxy-review`: 리뷰 큐 소화(스크린샷·diff→승인/수정/스코프아웃 3택, §9 기록) + 병렬 스타일 스캔 체크리스트. 승인은 사람.
- `/galaxy-bench`: held-out 벤치 + 이전 점수 비교 + **"점수 하락 시 변경 병합 금지" 게이트** + 3버전 태그 갱신.

---

## 7. LLM 생성 가이드라인 (프롬프트에 전문 포함)

> **정본: [CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md)**(v6 기반 — Part A 일반 문법, Part B 삼성 기준값·few-shot 소스). 아래는 LLM·생성기 규칙 요약 — 충돌 시 스타일 가이드가 우선. Phase 4 프롬프트에 §7.1(산문)·§7.2(카드) 전문 포함.

### 7.1 산문 원칙
1. 눈높이 중학생. `what[]` 1~2문장 · `why.body` 1~3 · `five.cap` 1~3 · `five.so` **정확히 1**. 자급자족(뒤 카드 전제 금지).
2. 서술형 완결("~이에요/~예요/~랍니다"), **격식체 금지**, 명사 끊기 금지.
3. 비유·비교 먼저, 항목당 1개. 배율·비율은 코드가 payload에 넣은 값만.
4. **숫자는 [브래킷 칩]**으로 감싼다(코드가 IBM Plex Mono 칩 렌더). 칩 속 숫자는 payload 표시 문자열만.
5. 용어 즉석 풀이(표준 사전: 감가상각·운전자본·지분법·비지배지분·OCI·연결).
6. 금칙: "장부이익"→"손익상 이익", 투자 조언류, 미래 단정, 이모지·연속 느낌표.
7. 면책은 오버레이 푸터 1곳(생성문에 금지).
8. 어투 few-shot(해방판 실물, 마스킹판). 질문형 헤더 관례.

### 7.2 카드·차트·5개년 가이드라인 (코드가 viz·색·스토리 유형 결정)
- **viz 8종 선택표**(콘텐츠 유형 → 함수 — LLM 아님): 5개년 단일추세→`vLine` · 5개년 두지표→`vTwin` · 기초→증감→기말→`vWater` · 구성비중→`vHBar` · 이익→현금→`vSteps` · 부문→`vBubbles`(크기=매출/밝기=이익·내부거래 제거) · 외상·재고→`vPuddle` · 등식→`vChips`.
- **색 = 의미 문법**(A2): mint 손익·cyan 현금·gold 자본·coral 유출·steel 잔액·점선 비현금. color_key만.
- **5개년(A11)**: 차트는 시계열 배열 자동 렌더(당해 강조·Δ칩·valley·zero). `five.cap`은 story.py 탐지 사실을 문장화(숫자≥1). `five.so`는 유형별 인사이트 프레임 한 문장. **5점 미완성 시계열은 skip**(사유 템플릿).
- 표 재현 금지.

### 7.3 딥다이브/APPENDIX 라우팅 — "억지 매핑 금지" (Q4 — 탭③ 내부)
- **딥다이브 채택**: 주석이 매듭·특정 숫자와 수치로 맞물릴 때만 — links·lnote 필수.
- **APPENDIX 강등**(스타일 가이드 A0-3·B4): 잔액 불변·측정기법·순수 서술(회계정책·위험관리·특수관계자·보고기간후·우발부채) — 한 줄 요약, five=skip.
- 무주석 통과 매듭(기초/기말현금·매출총이익·환율)에 억지로 붙이지 않음. 라우팅 결과(딥다이브 n/APPENDIX m)를 meta에 기록 → _BATCH_REPORT 집계.

---

## 8. 성능 최적화 체크리스트 (v6 반영)

- [ ] 탭 lazy mount + keep-alive. 첫 진입은 활성 탭 1개.
- [ ] 비활성 탭 표시 토글 방식 **Phase 2 스파이크로 결정**(display:none vs offscreen) — 재표시 시 ③ sticky·스크롤·제스처 상태 복원이 판정 기준.
- [ ] **오버레이 열림 동안 v2 셸 rAF 일시정지**(또는 배경 불투명화로 backdrop-filter 제거).
- [ ] **트윅 `particles=false` 성능 안전판**: 저사양·미달 시 배경 파티클 off(해방판 내장 — 첫 수단).
- [ ] 폰트 로컬 서브셋 + `font-display: swap`.
- [ ] JSON 단건 fetch(48개 선로딩 금지). React/Babel/dc-runtime.js CDN은 v2 셸과 캐시 공유(중복 로드 확인).
- [ ] 손 SVG 차트 다수 — 초기 렌더·리플로우 계측. 3열 그리드+우측 sticky 스크롤 성능.
- [ ] business.html 382KB → 데이터 분리 후 ~40KB. 이미지 lazy+onerror.
- [ ] 측정: 탭 전환 <200ms · 최초 로드 <1.5s · ③ 스크롤 55fps↑ · 콘솔 0 — Phase 5 ui-ux-reviewer 계측.
- [ ] 미달 시(순서): `particles=false` → `glowStrength` 하향 → 파티클 수 축소. **1차 이식에서는 손대지 않는다.**

---

## 9. 리스크 & 미결

| # | 리스크/미결 | 대응 |
|---|---|---|
| R1 | ~~Q1 신규 모듈~~ **승인 완료** | Phase 3 착수 가능. D6 절차 준수 |
| R3 | dc-runtime의 async 데이터 수용 | Phase 1 첫 반나절 스파이크. 불가 시 폴백: 빌드 스크립트가 ticker별 `<script type="application/json">` 인라인 주입 HTML 생성(최후수단) |
| R4 | ~~GPU VRAM~~ **확인 완료**: 노트북 Intel Arc 140V(배치 부적합) / **주력 A100 1장 80GB(원격)** | §3·부록 C. **Phase 4 착수 조건 — 리더 지정**: ① SSH·포트·가용 시간대 ② 서버 셋업 주체(vLLM·CUDA·권한) ③ 모델 가중치 HF 리포 + 토큰 ④ 엔드포인트 인증 + env 변수명(`REPORT_LLM_BASE_URL`/`REPORT_LLM_API_KEY`, shared/config.py) |
| R5 | 주석 HTML 구조 기업별 상이 | **하향(부록 B)**: sub_docs 목차 정형(14산업 실증). 이종 3사 조기 테스트 유지 |
| R6 | DART 수집 다중화 부채(원문 3중 + fnlttSinglAcntAll×5년) | ARCHITECTURE 부채 등재 + B·C 공유 — [#43](https://github.com/CVC-project/DiscloseAI/issues/43) |
| R7 | 금융 8사+SK스퀘어·적자/음수흐름은 은하수 부적합 | D10 자동 스코프아웃 — ③만 "준비 중", ①② 정상 |
| R8 | 대용량 산출물 커밋 사고 | raw_cache/(기존 ignore)·reports.db·review/·docs_cache/ .gitignore 추가, publish JSON만 커밋 |
| R9 | "kospi50" vs 48사 혼동 | 항상 "48사(dossier 집합)" 표기 |
| R10 | 기존 데이터 오류: `firm_012450.json`(한화에어로) 2025 revenue 단위 버그 | **financial(A) 소관 — 리더 직접 수정 금지.** A 재수집 요청 + sanity 검증이 자동 차단(D12) — [#42](https://github.com/CVC-project/DiscloseAI/issues/42) |
| R11 | 프로토타입 DATA rd_chart revenue 비율값 혼입 | Phase S2 extract에서 유효성 게이트 |
| R12 | **신규 — 해방판 CDN 버전**: React 18.3.1·Babel·dc-runtime.js CDN 로드 → 버전 드리프트 시 렌더 깨짐 | CDN URL 버전 고정. Phase 1에서 로컬 벤더링(assets/) 여부 결정(GitHub Pages 오프라인 안전 vs 캐시 공유) |
| R13 | **신규 — S 시계열 소스 구멍**: rnd·dsOp 등 일부 키가 fnlttSinglAcntAll에 없을 수 있음 | Phase 3 series.py에서 소스 맵으로 해결(연구개발활동 표·성격별 비용·주석 추출). 5점 미완성 키는 five=skip |
| R14 | **⚠️ 재작성 리스크 (부록 A2 확정)**: 해방판이 "데이터 채우는 템플릿"이 아니라 삼성 전용 하드코딩 산출물 — 탭③ 이식이 "데이터 외부화"가 아니라 **템플릿 데이터 구동화 재작성**(중앙 마크업 ~90행 sc-for 전환 + JS 상수 8카테고리 외부화 + 매듭 가드) | **완화**: dc-runtime 무변경·삼성 if 분기 0건·에러바운더리로 하드크래시 없음·viz 수학 안전 → **재작성은 지루하지만 기계적**(재설계 아님, 시각 불변). Phase 1 견적 3~4일(최대 볼륨). **시각 동등성**(정적 영역 대조)이 재작성 정확성의 게이트. (Phase 4는 하네스 다층이라 최대 복잡도 — 별개.) |

---

## 10. 새 세션 부트스트랩

1. 이 문서 전체 + [CASH_GALAXY_STYLE_GUIDE.md](CASH_GALAXY_STYLE_GUIDE.md) + `docs/ARCHITECTURE.md` §1·2·3.5 + `integration/v2/CLAUDE.md`를 읽는다.
2. Q1·Q3·Q4 **승인 완료**(문서 머리). 남은 리더 지정 = R4(A100 접속 정보 4건)뿐.
3. `git status` → dev 기준 Phase 브랜치. **타 모듈 소유 미추적 파일 add 금지** — 경로 명시 add(`integration/dossier/`·`modules/report/`·`docs/`·`tests/report/`·`integration/v2/`·`.claude/skills/` 한정).
4. 진행 상태는 이 문서 체크박스가 정본. Phase 종료 시 체크 + DoD 증거를 PR 본문에.
5. 검증 없이 다음 Phase 금지(특히 Phase 1 시각 동등성, Phase 4 골든·캘리브레이션).
6. 막히면: R3 폴백, 이식 원칙(§0 ⓐⓑⓒ). "다시 그리고 싶다" = 계획 위반.

### 진행 상태
**Step 1 (현금 은하수 + AI 파이프라인 — 지금)**
- [ ] Phase 0 준비 (스키마·골든·5개년 시계열)
- [ ] Phase 1 탭③ galaxy.html 데이터 구동화 재작성
- [ ] Phase 2 오버레이 셸 (탭②③ 2탭)
- [ ] Phase 3 modules/report 수집 (5개년)
- [ ] Phase 4 LLM 하네스 + 일관성 계층 (story·lint·bank·skill)
- [ ] Phase 5 galaxy 48사 확장·마감  ← **Step 1 마일스톤 (dev 머지·배포)**

**Step 2 (사업 개요 탭 — kospi50 프로토타입 확정 후, §5b)**
- [ ] Phase S2 탭① business.html 이식

---

## 부록 A. ⚠️ 구판(editable) 가변성 감사 — **무효 (이력 보존)**

> **2026-07-10 무효화**: 이 감사는 `Cash Galaxy.editable.html`(v4) 대상이며, v6 해방판은 구조가 재설계돼(일직선 본류·굵기 고정·row 배치·getDives·5개년·dc-runtime 외부화) **여기 발견된 위험 5곳(cap 하드참조·noncash 파티클·DEST 가드·steps 상수·zoom)이 구조째 소멸**했다. **해방판 기준 신규 감사(부록 A2)가 Phase 1에서 이를 대체**한다. business(A-2) 감사는 kospi50_business_tabs 대상이라 **여전히 유효**(D5에 반영).
> 이력 참조용 구판 요지: galaxy는 템플릿 수정 5곳 필요·business는 부트스트랩 절제+lens 우선순위 2곳·firm_*.json 3그룹(A값만/B역방향/C스코프아웃). 상세는 git 이력(v3) 참조.

### A-2. business (kospi50_business_tabs.html) — **유효 유지**
- 결측 대응 실증: raw_moves 47사 결측·가동률 44사 결측·카드 2/3/4개 혼재·LIG넥스원 전결측 — 전부 폴백 렌더. 삼성 전용 분기 0건.
- 수정 2곳: 단일 뷰 부트스트랩 절제(rail 리스너 L1260-1271) · industryKey 우선순위 버그(SK텔레콤·현대건설·KT&G) → D5.
- 생성기 계약: 카드 2~4개·kind 21종·금융사 '금융업' → D12.

## 부록 A2. 해방판 신규 가변성 감사 (2026-07-10, 2에이전트 렌더·하드코딩 전수)

> **⚠️ 핵심 발견 — 계획의 전제 정정**: 해방판은 **"생성기가 채우는 템플릿"이 아니라 "삼성전자 한 종목에 통째 하드코딩된 단일 산출물"**이다. 구판(editable)은 데이터가 JS 배열(KNOTS/ANNOS…)이라 "배열만 교체"가 가능했으나, 해방판은 **중앙 5패널 ~90행이 정적 인라인 HTML 리터럴**이고 viz 함수(vBubbles/vPuddle/vSteps 등)가 `this.S`조차 안 읽고 삼성 숫자를 함수 내부에 박아뒀다. → **탭③ 이식 = "데이터 외부화"가 아니라 "템플릿 데이터 구동화 재작성"**(§0·D4 정정). 이것이 이 프로젝트 전체의 최대 작업·최대 리스크(R14).

### A2-1. 안전판 (하드 크래시는 없다 — 재작성은 "지루하지만 기계적")
- **dc-runtime.js는 완전 범용 엔진**(삼성/재무/005930 매치 0건) — **무변경**. 재작성은 해방판 html에만.
- **삼성 전용 if 분기 0건**(`005930`·사업부명 조건 분기 없음) — 제어흐름 오작동 없음. 순수 "표현 데이터·카피의 외부화" 문제.
- **하드 크래시 방지됨**: React 에러바운더리(dc-runtime L829)가 매듭 참조 TypeError를 빨간 박스로 격리, 대부분 지점에 `if(el)`·`Set.has`·`if(y==null)` 가드. 최악은 "은하수 소실"(무증상)이지 백지 크래시 아님.
- **viz 수학은 이미 안전**: 음수(tax·dsOp)·전부 0·극단값·valley/zero 처리 방어 완비(L1140 `pad||1`, L1144 `mn<0&&mx>0` 0선). **유일 리스크 = 시계열 5점 미완성·key 결측**(vLine `Math.min(...undefined)` throw) → 생성기가 5점 완결·key 존재 보장으로 회피.

### A2-2. 재작성 대상 = 2층 (blocker 8 카테고리)

**층 1 — 정적 마크업 → 데이터 구동(sc-for/보간)으로 재작성** (데이터 파일만으론 불가, 템플릿 수술 필수):
| # | 지점 | 근거 |
|---|---|---|
| 1 | **중앙 5패널 ~90행**(존 A~E: is-revenue…eq-end) — 표시값·`title` 백만원 원값·부호·색·펼침 소계 8행·부문명 전부 리터럴 | L110-411 |
| 2 | **APPENDIX 14주석**(종속기업 308개·EPS 6,605원·신용등급 Aa2/AA− 등 요약값·주번호) | L419-432 |

**층 2 — JS 상수 → props/데이터 주입으로 리팩터**:
| # | 지점 | 근거 |
|---|---|---|
| 3 | **회사 메타** — 상단바 헤더 "삼성전자 · FY2025 · 연결"·인트로 히어로("53.7조→57.9조")·"삼성전자와 자회사"·BS 캡션 FY2025·관계기업명("삼성전기·삼성SDS") | L60·67·69·170·293 |
| 4 | **시계열 `S` 24키×5점 + `YEARS`** | L1062-1088 |
| 5 | **차트 서사** — vLine `valleyLabel`('반도체 한파')·vBubbles 4부문(DX/DS/SDC/Harman 매출·이익 리터럴)·vSteps/vPuddle/vHBar 호출부 삼성 수치 | L1163·1249-1254·1230·1279·1325 |
| 6 | **딥다이브 카피 전량** `getDives()` — what·why·five·cap·so·lnote 속 삼성 회사명·부문·이력(1969 설립·종속 308개)·인수(ZF·레인보우로보틱스)·"본체 몫 44.3조" 30여 곳 | L1290-1657 |
| 7 | **매듭·자본·존 카피** KNOTS/EQSTORY/ZONES의 name·amt·story | L486-557 |
| 8 | **오버뷰·에필로그** buildCard 계열 "삼성전자의 1년을…"·"53.7조가 57.9조가 되기까지" | L974·1027·1029 |

**buildGalaxy 매듭 이름 하드참조 가드**(K.k3·k5·k8·k9·k13 등): cogs 없는 서비스업처럼 손익 단계 제거 시 `K.k3.x` TypeError(에러바운더리가 잡으나 은하수 소실) → **매듭 존재 여부 가드 추가**(생성기 규칙 밖, 템플릿 수정). L763·818·837·845·869·906·938.

**코드 상수 유지 가능(외부화 불필요)**: 표준 계정 라벨(K-IFRS) · 순수 UI 문구(단위·범례·존 질문 L437-445) · 레이아웃 파라미터(CONFIG·xf/kind/col) · SEGS(uniform 모드라 시각 영향 적음, 단 uniform=false로 바꾸면 삼성 스케일 → 유지 권장).

### A2-3. 판정 & 반영
- **판정**: 타사 47사 확장 = 층 1(마크업 데이터 구동화) + 층 2(상수 외부화) + 매듭 가드 재작성. **시각·레이아웃·dc-runtime은 불변**(=이식 정신 유지), 바뀌는 건 데이터 흐름(리터럴 → 주입)뿐. 재설계 아님.
- **반영**: §0 이식 원칙에 "탭③은 데이터 구동화 재작성 포함" 명시 · **D4 전면 개정**(외부화 8카테고리 + 마크업 sc-for 전환 + 매듭 가드) · Phase 1 견적 상향(2일 → **3~4일, 최대 작업**) · D12 생성기 계약(5점 완결·key 존재·매듭 가드) · R14 격상.

## 부록 B. DART 실수집 스파이크 (2026-07-08 — **유효**, 5개년 주석 추가)

### B-1. 삼성전자·SK하이닉스
`dart.list → sub_docs → 서브문서 → document.xml` 전 구간 실측 성공. 최신 사업보고서: 삼성 rcept 20260310002820 · 하이닉스 20260317000635. **sub_docs 57~58건, 목차 사실상 동일** — "II. 사업의 내용" 7절, "III.3 연결재무제표 주석" **별도 서브문서**. 표 1,632~1,813개 HTML 온전. document.xml zip 0.69~0.78MB/사.
- **v6 5개년 영향**: 원문 최대 5개년 = **48사×5 ≈ 240건(≈60~120MB)**. 단 부문 5개년은 보고서당 당기+전기 2개년 → **2025·2023·2021 3개로 5년 커버(144건)** 최적화. raw_cache 커밋 제외 유지.

### B-2. 산업별 확장성 (14개 산업 대표 실측) — **13/14 구조 동일**

| 기업 | 산업 | subs | 연결주석 | 표 | 주석# | 기업 | 산업 | subs | 연결주석 | 표 | 주석# |
|---|---|--|--|--|--|---|---|--|--|--|--|
| 현대차 | 자동차 | 63 | 997KB | 1118 | 39 | 한국전력 | 전력 | 64 | 3361KB | 1153 | 47 |
| LG엔솔 | 배터리 | 57 | 1009KB | 974 | 38 | 현대건설 | 건설 | 57 | 1354KB | 1034 | 37 |
| 삼성바이오 | 바이오 | 59 | 709KB | 863 | 34 | HMM | 해운 | 57 | 662KB | 852 | 43 |
| NAVER | 플랫폼 | 58 | 1120KB | 1138 | 37 | KT&G | 소비재 | 57 | 897KB | 1077 | 34 |
| KB금융 | 은행 | 70 | 3435KB | 2390 | 45 | POSCO홀딩스 | 철강 | 60 | 1363KB | 965 | 43 |
| 삼성생명 | 보험 | 58 | 2467KB | 1767 | 37 | HD한국조선 | 조선 | 57 | 1010KB | 1144 | 50 |
| SK텔레콤 | 통신 | 57 | 943KB | 931 | 41 | 한화에어로 | 방산 | **2** | — | — | **정정 stub** |

1. **골격 전 산업 동일** → 섹셔너(목차 기반)는 산업 무관 단일 구현.
2. 금융·보험 차이는 "II. 사업의 내용" 하위 구성(제조 7절 vs 금융 5절) → 탭① 스니펫 매핑 분기 1개(Phase S2). 주석 번호 체계 동일.
3. 문서량 3~5배(금융·한전) — 주석 단위 슬라이싱이라 LLM 무영향, 저장 용량만 상향.
4. **정정공시 stub**(한화에어로 20260319000633, subs 2건) → 수집기 폴백(`sub_docs≥30 && has(사업의 내용)`, Phase 3). KB금융·삼성생명도 정정이나 전체 목차형이라 정상 — 정정 2유형 확인.

## 부록 C. GPU·기술 전략 (2026-07-10 갱신)

### C-1. 원칙: 확률적 작업만 GPU, 결정적 작업은 CPU
| 작업 | 성격 | 2,600사 규모 | 자원 |
|---|---|---|---|
| 원문 수집·파싱(HTML→섹션, ×5년) | 결정적 | BeautifulSoup — CPU 병렬 | **CPU** |
| **레이아웃·그래프 렌더(row 배치·viz 8종)** | 결정적 | 템플릿 코드 (v6: 굵기 기본 2단 고정) | **CPU/브라우저** |
| **스토리 탐지(story.py)** | 결정적 | 시계열 규칙 — 즉시 | **CPU** |
| LLM 추출·산문·5개년 해석 | 확률적 | ~10만 호출, 1~1.5억 토큰 — **전체 99%+** | **GPU** ✔ |
| 검증 L0~L2(lint·인용·산술·DB·시계열) | 결정적 | 문자열·산술 — 수 초 | **CPU** ✔ |
| 검증 L3(헤드리스 렌더) | 결정적 | ~2,600 × 1~2초 CPU 병렬 | CPU |

**검증을 GPU(LLM)에 맡기지 않는 이유**: 검증을 일부러 결정적으로 설계(§6.3) — LLM-judge로 바꾸면 검증자가 환각하는 순간 게이트 무의미. LLM-judge는 문체 샘플링 보조(§6.7-③)로만. → **생성 = GPU / 검증 = CPU + GPU 보조 판정만**(D7·D8의 하드웨어 버전).

### C-2. 가용 장비
| 장비 | 스펙 | 역할 |
|---|---|---|
| 로컬 노트북 | Intel Arc 140V(공유 16GB, CUDA 없음) | 개발·하네스 실행·8B 스모크(llama.cpp Vulkan). 배치 부적합 |
| **A100 1장 (80GB, 원격)** | 데이터센터급 | **배치 주력**: vLLM + Qwen3-32B AWQ + guided_json. 노트북이 원격 호출 |

llm.py를 OpenAI 호환 클라이언트로 → A100↔노트북↔클라우드 base_url 교체만으로 스왑.

### C-3. 단계별 GPU 활용
- **지금 (48사, Phase 4~5)**: A100 32B로 추출·생성·5개년 해석 배치 — ~4~5M 토큰, **반나절~1일**. 골든 벤치(8B/14B/32B)도 A100.
- **본선 (~2,600사)**: ~10만 호출·1~1.5억 토큰 → A100 연속 배칭 **2~4일**(5개년 슬롯 반영). 검증·파싱은 CPU 수십 분. **A100 1장으로 커버** — 연 1회 배치성이라 상시 점유 불필요. 실패·고난도는 API(Claude/Gemini) 에스컬레이션.
- **미래 (AI_DIRECTION_PLAN)**: 임베딩(RAG·학습 — 공시·주석 벡터화), 학습 LLM-judge(고빈도·저난도 → 로컬 GPU), QLoRA 도메인 파인튜닝(A100 80GB면 32B 여유 — held-out 골든이 부족 증명 시).
- price CatBoost GPU는 이득 미미 — CPU 유지.

### C-4. API/저장 영향 (v6 5개년)
- DART 콜 ~500-700(일일 한도 3%) · raw_cache 60~120MB · reports.db 섹션 텍스트 ×3~5배(5개년). 전부 커밋 제외. 프론트: zoom·사행·대형 blur 소멸(성능 개선), sticky·파티클·손 SVG 다수는 신규 계측 대상(§8).
