# Integration 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-05-05 (Phase I — Disclosure v2 흡수: 데이터 갱신 + "오늘의 개념" 5번째 섹션 파싱)

- **작업 범위**: `feat/disclosure-chat-gemini` PR (#23, 5 commits) dev merge 후 integration 흡수
- **흡수 대상**:
  - disclosure.db 데이터 갱신 (collector 분석 품질 개선 + 정기보고서 92건 추가)
  - generate_report.py 의 새 5번째 섹션 `[오늘의 개념]` (collector prompt에 추가됨, 180건 중 31건 보유)
- **Stage 1 — 데이터 sync**: `git merge origin/dev` 후 `python -m modules.integration.extract_data` 재실행. `disclosures.json` 갱신 (180 disc / 252 stmt 동일 건수, summary 내용 갱신)
- **Stage 2 — 5섹션 파서 확장** (`_parseDiscSummary`): regex `\[(Cash|Risk|Hidden Agenda|Verdict)\]` → `\[(Cash|Risk|Hidden Agenda|Verdict|오늘의 개념)\]`. `out` 객체에 `concept` 필드 추가. `hasStructured` 판정에 concept 포함
- **Stage 3 — 카드 렌더 추가** (`_renderDiscSections`): "📖 오늘의 개념" cyan/teal accent (#5eead4) 카드 추가. 큰 폰트(14·15px) + 작은 폰트(10px) 양쪽 버전 자동
- **명시적 비범위** (PR이 우리에게 강제하지 않음, 후속 phase 검토):
  - generate_report.py 의 카드 톤 디자인 (배경색 분리 카드)
  - generate_report.py 의 "💬 질문하기" Gemini 채팅 버튼 차용
  - 메타그룹 분류 (자금조달·정기보고서·사업이벤트·지배구조) 그룹 헤더
- **검증**: pytest 482 passed / black clean / Playwright (기아 2026-04-09 IR 공시에서 cash·risk·hidden·verdict·concept 5섹션 모두 정상 렌더링, 후속 추천 "다음엔 이것도 알아보세요" 포함)


## 2026-05-05 (/check — Phase H 리뷰 후속 fix)
- **작업**: code-reviewer 지적 3건 반영
  - `closeFullTimemachine`에 `_tmCnIdx = 0` 추가 — `_tmStartScenario`와 리셋 대칭 확보 (유지보수성 ↑)
  - `_tmChatSend` 키 모달 분기에서 `_tmChatBusy = true` 임시 set + 콜백에서 false 복원 — 빠른 연타 시 중복 모달 race 방지
  - `_chatInit` 키 안내 메시지 `innerHTML` → `createElement + addEventListener`로 전환 — XSS 패턴 정리
- **파일**: `modules/integration/dashboard.html` (~25줄 수정)
- **테스트**: 482/482 통과 (기존 470 + 신규 `tests/test_integration_price_scenarios.py` 12건)
- **리뷰**: 보안·우선순위·재진입 루프·금융 도메인 면책 모두 OK. 3개 minor 지적 모두 반영
- **도메인 메모**: `_getGeminiKey()`가 `chat_config.local.js`의 `'YOUR_API_KEY_HERE'` placeholder도 가드 — 부분 설정 케이스 누락 없음 ✓

## 2026-05-05 (Phase H — Price v2 흡수: DART URL 갱신 + Gemini 키 모달 + 방어적 상태 리셋)

- **작업 범위**: price v2 PR (#20, commit `c9bdd10`)의 3가지 변경을 integration에 흡수:
  1. DART URL 교체 (id 2 HD현대중공업·id 11 삼성전자) — `dsaf001/main.do?rcpNo=...` (404) → `dsab007/search.ax?textCrpNm=...` (검색 페이지)
  2. localStorage 기반 Gemini API 키 입력 모달 — 하드코딩 키 제거 + 사용자 입력 UI (price 측은 timemachine.html에만 적용, 우리는 메인 채팅 + 타임머신 chat-first 모두 적용)
  3. 토글 버그 수정 정신 차용 — price 측은 quiz.html `startQuiz()`에서 `cardnewsScreen` 숨김 누락 1줄 fix. 우리는 다른 패턴이라 직접 적용 안 되나, 같은 정신으로 4개 잠재 누수 지점에 방어적 리셋

### Stage 1 — DART URL 갱신
- `git merge origin/dev` 으로 price v2 흡수 (FF merge, 3 files: quiz.html / quiz_data.py / timemachine.html)
- `python -m modules.integration.extract_data` 재실행 → `data/price_scenarios.json` 갱신 (12 시나리오 그대로, id 2·11의 `dart_url` 교체 확인)

### Stage 2 — localStorage 기반 Gemini 키 모달
- 신규 헬퍼 (`dashboard.html` ~L5072): `_getGeminiKey()` (chat_config > localStorage 우선순위), `_saveGeminiKey()`, `_clearGeminiKey()`, `_showKeyModal(onSaveCb)`, `_applyGeminiKey()`, `_clearGeminiKeyAndClose()`
- 모달 UX: price `timemachine.html` v2 디자인 차용. cyan/teal gradient CTA, password input, "키는 브라우저(localStorage)에만 저장" 안내, Google AI Studio 링크. z-index 10200 (기존 fullTimemachine 9999, finalModal 10100 위)
- 진입점:
  - 채팅 사이드바 헤더에 🔑 아이콘 버튼 (analyze·disclosure·timemachine 모드 모두 혜택)
  - 타임머신 chat-first toolbar에 🔑 API 키 버튼
  - `_chatSubmit` (메인 채팅) / `_tmChatSend` (타임머신) — 키 미존재 시 모달 자동 호출 + 저장 콜백으로 재시도
  - `_chatInit` 키 미설정 안내 → "키 입력 모달 열기" 클릭 가능 링크
- `_chatCallGemini` / `_tmGeminiCall` — `window.GEMINI_API_KEY` 직접 참조 → `_getGeminiKey()` 사용
- chat-first 입력란: 이전 keyMissing 시 disabled → 항상 활성 + 전송 시 모달

### Stage 3 — 방어적 상태 리셋
- `_tmStartScenario` 시작 부분에 5개 상태 리셋 추가: `_tmChatBusy=false` / `_tmCnIdx=0` / orphan `#tmFinalModal` 제거 / orphan `#geminiKeyModal` 제거 / `__tmIntroTimer` `__tmSystemMsgTimer` clearTimeout
- `closeFullTimemachine` 에도 동일 리셋 (overlay 닫힘 시 잔재 제거)
- `_tmRenderChatFirst` 의 `setTimeout` 호출을 `window.__tmIntroTimer` `window.__tmSystemMsgTimer` 로 추적

### 검증
- pytest 470 passed / black --check clean
- Playwright E2E:
  - 키 모달 — sidebar 🔑 클릭 → 모달 → 빈 입력 시 input border 빨강 + 모달 유지 → "AIzaSy_TEST_KEY_..." 입력 → 저장 → localStorage 저장 + 모달 종료 ✅
  - 카드뉴스 idx 리셋 — 슬라이드 3 이동 → 닫기 → 재오픈 → "1 / 6" 부터 시작 (`_tmCnIdx`: 2 → 0) ✅
  - Orphan 모달 정리 — 최종예측 모달 열린 상태에서 closeFullTimemachine 호출 → 모달 자동 제거. 재오픈 시 잔재 없음 ✅
  - chat-first 송신 → 키 모달 자동 호출 + 입력란 항상 활성 ✅

### 명시적 비범위
- price 모듈 자체 수정 (CLAUDE.md 규약: 리더는 read-only)
- localStorage 키 암호화 (XSS 위험 안내문으로 대체, price v2 결정 따름)

## 2026-05-02 (Phase G — 제대로 된 타임머신 MVP: 4-phase quiz UX + Gemini 자유대화 + 탭 전용 UI)

- **작업 범위**: 타임머신 모드를 우측 슬라이드 정적 패널 1장(매수/관망/매도 즉시 정답) → **풀스크린 4-phase quiz UX + Gemini 자유대화 + 탭 전용 하단 3분할 콘텐츠 패널**로 전면 개편. 사용자 직접 지시:
  1. 행성 클릭 → cat hop + 말풍선 → cat 클릭 → 풀스크린 4-phase 진입 (행성 직접 진입 경로)
  2. 타임머신 탭 좌하단 관계 legend 숨김 + 화면 하단 3분할 콘텐츠 패널 (카드뉴스·퀴즈·타임머신) — **다른 탭은 무영향**
  3. 패널 카드 클릭 → 카메라 fly + cat hop + 말풍선 → cat 클릭 → 풀스크린 진입 (카드 진입 경로)
  4. 다중 시나리오 행성(삼성전자 id=3·11) → 행성 직접 클릭 시 시나리오 선택 picker 카드 2개 표시. 카드 진입은 단일 시나리오 강제

### Stage 1 — 데이터 인덱싱 + 클릭 분기 (dashboard.html)
- `scenarioByTicker` 단건 매핑(`Object.fromEntries`) → `scenariosByTicker` 배열 매핑으로 변경. 같은 ticker 다중 시나리오 보존
- 노드에 `n.tmAll = scenarios[]` 추가. `n.tm` 단일 객체는 legacy `showTimemachine` 폴백 호환을 위해 첫 시나리오로 유지
- 콘텐츠 활성화 화이트리스트(JS 상수): `TM_CARDNEWS_IDS=[11]` / `TM_QUIZ_IDS=[1,2,3,4,5,8,10,11,12,13,14,15]` / `TM_FREECHAT_IDS=[1,2,3]` (price.quiz_data 기반)
- 신규 state: `tmFocusNode`, `tmFocusScenario`, `_tmPanelsRendered`. 클릭 핸들러에서 timemachine 모드 분기를 `_enterTimemachineFocus(clicked)` 호출로 교체 (gather 우회 즉시 패널 → 카메라 pan + cat hop)
- mascot 애니메이션 로직에 `_focusNode = gatherMode?.center || tmFocusNode` 일원화. `_hitMascot`도 timemachine focus 감지하도록 확장
- 말풍선: 시나리오 보유 → "타임머신을 체험하려면 나를 클릭해줘" / 미보유 → "이 기업의 시나리오는 아직 준비되지 않았습니다" + cat 클릭 비활성

### Stage 2 — 타임머신 탭 전용 UI (CSS + HTML)
- `body.mode-tm` 클래스 토글(setMode에서 자동) → `body.mode-tm .legend.legend-edge { display:none }` (좌하단 관계 범례만 숨김, 다른 탭 영향 X)
- `#tmContentPanels` 신규 — 3-column grid (`grid-template-columns: 1fr 1fr 1fr`), 화면 하단 고정, 채팅 사이드바 폭 따라 right offset 동기 (`var(--chat-sidebar-w)`). 좁은 화면(<1100px) 세로 스택
- 각 패널 좌측 border 컬러 차별화: 카드뉴스 amber / 퀴즈 violet / 타임머신 cyan. timemachine.html picker 디자인 차용 (날짜·카테고리 badge·난이도·회사명·제목·CTA)
- 카운트 뱃지 (`(N건)`) — TM_CARDNEWS_IDS·TM_QUIZ_IDS·TM_FREECHAT_IDS 화이트리스트로 자동 계산

### Stage 3 — 풀스크린 타임머신 오버레이 (HTML/CSS)
- `<div id="fullTimemachine">` + `#fullTimemachineCard` (fullDisclosure 미러). 통합 셀렉터에 추가: `#fullAnalysisCard, #fullDisclosureCard, #fullTimemachineCard` + `body.chat-open` 시 right offset 동기
- 본문(`#fullTimemachineBody`) 4 phase: tmPhaseA(배경) / tmPhaseB(자유대화) / tmPhaseC(결정 3버튼) / tmPhaseD(정답 reveal)
- CSS: tm-section 카드, tm-decision 3색 버튼(녹/회/적), tm-big-num 38px, tm-match badge(ok/no), tm-chat 메시지(user/assistant/system), tm-hints 5칩, tm-picker 2열 grid

### Stage 4 — JS 로직 (13 신규 함수, dashboard.html 내)
- `_renderTmPanels()` — 12건 시나리오 마스터 → 화이트리스트 기반 3패널 분배. setMode('timemachine') 진입 시 1회 (이미 렌더되면 skip)
- `_tmCardClick(sid)` — 카드 클릭. ticker로 노드 찾기 → `_panTo` 카메라 fly → `tmFocusNode = node`, `tmFocusScenario = sc` 저장 (cat 클릭 시 단일 강제)
- `_enterTimemachineFocus(node)` — 행성 직접 클릭 진입. 카메라 fly + tmFocusNode set, tmFocusScenario null (picker 분기 가능 상태)
- `_exitTimemachineFocus()` — 배경 클릭/탭 전환 시 focus 해제
- `openFullTimemachine(node, forcedScenario?)` — 진입점. forcedScenario가 있으면 즉시 시작 / `tmAll.length === 1` 시 시작 / `length >= 2` 시 picker
- `_tmShowPicker(scenarios)` / `_tmStartScenarioById(sid)` — 다중 시나리오 picker 렌더 + 카드 클릭 시 단일 진입
- `_tmStartScenario(sc)` — 4 phase 컨테이너 렌더 + Phase A→B→C 호출
- `_tmRenderBackground(sc)` — Phase A 배경 카드 (date·category·title·context)
- `_tmRenderChat(sc)` — Phase B 자유대화. TM_FREECHAT_IDS 미포함이면 phase 자체 생략. 포함 + chat_config 키 미설정이면 안내(graceful fail). 5개 힌트 칩 + 입력란 + Enter 전송
- `_tmGeminiCall(sc, history)` / `_tmBuildSystem(sc)` / `_tmExtractText(data)` — Gemini 호출 (window.GEMINI_API_KEY, chat_config.local.js 인프라 차용). system prompt에 시점 제약("공시일 이후 사건 절대 언급 금지") + 정답 사전공개 금지 강제
- `_tmRenderDecision(sc)` — Phase C 3버튼 (수혜/중립/악재)
- `_tmReveal(userChoice)` — Phase D. 결정 버튼 비활성화 + chosen 표시 → change_pct·kospi_change_pct·excess(종목-코스피)·정답·일치 여부 badge·explanation·refUrl
- `_tmChatSend()` / `_tmChatAppend(role, text)` / `_tmHintClick(el)` — 자유대화 입출력
- `closeFullTimemachine()` / `_fullTimemachineEsc(e)` — ESC + × 닫기, tmChatHistory 초기화

### 보안 처리
- timemachine.html(price 모듈)의 하드코딩 API 키(`AIzaSyBj1VUf...`)는 사용 안 함. dashboard 채팅 사이드바와 동일한 `window.GEMINI_API_KEY` (chat_config.local.js, gitignored) 단일 출처
- 키 미설정 시 graceful fail — 자유대화 phase만 비활성, 결정·정답은 정상 동작

### 검증
- `pytest tests/` 470 passed, 8 skipped (회귀 없음)
- `black --check modules/integration/` clean
- Playwright E2E:
  - 타임머신 탭 진입 → `body.mode-tm` 클래스 / 좌하단 legend display:none / 하단 3패널 display:grid / 카운트 (1·12·3) ✅
  - LG화학 퀴즈 카드 클릭 → 카메라 fly → cat 도착 → 말풍선 "타임머신을 체험하려면 나를 클릭해줘" ✅
  - cat 클릭 → 풀스크린 오버레이 진입 → Phase A(배경)·B(API 키 안내)·C(3버튼) 렌더 ✅
  - "악재" 클릭 → Phase D reveal: -11.2% / KOSPI -6.7% / 초과 -4.5%p / 정답 악재 / "당신의 선택과 일치" 뱃지 / lesson / 관련기사 링크 ✅
  - 삼성전자 행성 직접 클릭 → cat hop → cat 클릭 → 시나리오 picker 카드 2장 (감산결정·자사주소각) ✅
  - KB금융 (시나리오 미보유) 행성 클릭 → cat 말풍선 "준비되지 않았습니다" / cat 클릭 시 overlay display:none 유지 ✅
  - 기업분석 탭 복귀 → `body.mode-tm` 제거 / legend display:block / 하단 3패널 display:none ✅

### 명시적 비범위 (이번 PR 제외)
- **카드뉴스 6슬라이드 통합** (id 11 cardnews_samsung_buyback.html) — 후속 PR. MVP는 카드뉴스 패널에 1건만 노출, 클릭은 quiz UX로 진입
- **사용자 점수 누적 / localStorage** — Phase D는 매번 일회성
- **시나리오 추가 수집** — quiz_data.py 12건 그대로
- **modules/price/timemachine.html 자체 수정** — 하드코딩 API 키는 별도 PR (price 모듈 담당)

## 2026-05-01 (Phase F — 메인 화면 인터랙션: 섹터 줌 · 모임 효과 · 고양이 인터랙션 · 공시 풀스크린)

- **작업 범위**: 메인 대시보드 UX 개편 4가지. 사용자 직접 지시 (auto mode):
  1. 섹터 탭 클릭 → 해당 은하 중심으로 카메라 줌인 (이전엔 정적, 마우스 스크롤 직접 이동 필요)
  2. 기업분석/공시 모드에서 행성 클릭 → 즉시 패널 안 띄우고 **연결 기업이 클릭 행성 주위로 모이는 효과** + 비연결 노드 fade out + 모인 기업은 작은 반짝이는 별로 (규모 무관)
  3. 고양이 마스코트가 클릭 행성 위로 이동 → 모드별 말풍선 ("재무제표/공시를 확인하려면 나를 쓰다듬어줘") → **고양이 클릭 시** 패널/오버레이 호출
  4. 공시 화면을 우측 슬라이드 패널 → analyze와 동일한 풀스크린 오버레이로 (`openFullDisclosure`)
- **타임머신 모드는 본 변경 제외** (사용자 명시) — 기존 즉시 패널 동작 유지

### Stage 1 — 섹터 카메라 트윈 (filter() 확장 + _panTo)
- 신규 `_camTween` state + `_easeInOutCubic` + `_panTo(toX, toY, toZm, dur=600)` + `_camForWorldCenter(wx, wy, zm)` (코드: dashboard.html ~L361-L394)
- draw() 시작에 트윈 진행도 보간 (~L800)
- `filter(f, btn)`: f가 sector 키면 `sectors[f].cx/cy * SPAN` 계산 → 화면 중앙에 두는 (camX, camY) 도출 + 줌 레벨 1.5x. f='all'이면 baseZm=0.62 원래 뷰
- 사용자가 마우스 드래그 시작하면 트윈 자동 취소 (`_cancelCamTween`)

### Stage 2 — 모임 효과 (gatherMode + 렌더 광환)
- 신규 `gatherMode` state: `{center, members: Map<node, {fromX, fromY, toX, toY}>, startTime, dur:600}` (~L283-L320)
- `_enterGatherMode(centerNode)`: edges에서 centerNode와 연결된 모든 노드 수집 (모든 섹터 횡단, Set 중복 제거) → 원형 오빗 위치 계산 (10개 이상이면 두 링으로 분배, baseR = max(180, sz*60))
- 렌더: edges 루프 직전에 `_gatherSnapshot` 으로 멤버 좌표 임시 mutate (트윈 진행도 적용) → 렌더 후 원위치 복구. 엣지는 center↔member만 표시, 다른 엣지 숨김
- 노드 분기 확장: `(n.sz < STAR_THRESHOLD || isGatherMember) && !isS && !isH` → gather 멤버는 sz 무관 작은 별. 비-(center↔member) 노드는 globalAlpha=0.12

### Stage 3 — 고양이 마스코트 인터랙션
- gather 활성 시 자동 hopping(`pickNextNode`) 차단, `mascot.targetNode = gatherMode.center` 강제 (~L1226)
- 마스코트 도착(progress >= 1) 시 말풍선 렌더 (`_drawSpeechBubble` 신규, ~L595): 둥근 사각 + 꼬리 + 펄스 애니메이션, zm 역수 보정으로 화면상 일관 크기. 모드별 텍스트 분기 (analyze: "재무제표를 확인하려면…" / disclosure: "공시를 확인하려면…")
- mousedown 핸들러 재구성 (~L1450): 1) 마스코트 hit 우선 (`_hitMascot`, 반경 38) → `_onMascotClick` 호출 → 모드별 패널/오버레이. 2) 노드 hit → analyze/disclosure는 `_enterGatherMode` (timemachine은 즉시 `showTimemachine`). 3) 배경 → gather 활성이면 `_exitGatherMode` 아니면 closePanel + drag 시작

### Stage 4 — 공시 풀스크린 오버레이 (`openFullDisclosure`)
- analyze의 `fullAnalysis` 패턴 미러. iframe 없이 inline 렌더 (분석은 회사별 정적 HTML 있지만 공시는 dashboard 데이터 직접 사용이 더 깔끔)
- HTML: `#fullDisclosure` 오버레이 + `#fullDisclosureCard` (top 5vh / left 6vw). 헤더 (회사명·티커·섹터·DART 링크·닫기 버튼) + 본문 영역 (`#fullDisclosureBody`)
- CSS: `#fullAnalysisCard, #fullDisclosureCard` 통합 셀렉터 + chat-open 시 right:372px (사이드바 회피)
- 공시 카드 렌더: Phase 3에서 만든 `_parseDiscSummary` / `_renderDiscSections` / `_escHtml` 그대로 재사용. high_impact 뱃지·dilution_ratio·분기 재무 8건 표
- ESC 키로 닫기, body click outside card 영역도 닫기
- `_onMascotClick`이 disclosure 모드에서 `openFullDisclosure(center)` 호출, 함수 미정의 시 `showDisclosure` 폴백

### 검증
- `pytest tests/` 470 passed / 8 skipped (회귀 없음)
- `black --check modules/integration/` clean
- Playwright E2E:
  - 반도체 탭 → zm 0.62→1.50 부드러운 이동 + 전체 → 0.62 복귀 ✅
  - 삼성전자 클릭 → gather, 7개 멤버 (삼성바이오로직스·삼성SDI·삼성중공업 등) ✅
  - 현대차 클릭 → 5개 멤버로 재구성 ✅
  - 배경 클릭 → gather 해제 ✅
  - disclosure 모드 + 마스코트 클릭 → `openFullDisclosure(center)` 호출 ✅
  - 풀디스클로저 화면: 회사명·DART 링크·공시 3건 카드(4섹션 분리)·분기 재무 표 정상 ✅

### 명시적 비범위
- 시각 디자인(별빛 더 추가·행성 강화·차트 색상 등) — Phase E와 동일하게 보류
- timemachine 탭의 모임/고양이 효과 — 사용자 결정으로 추후
- gather 해제 시 멤버 위치 역방향 트윈 — 현재 즉시 snap (개선 여지)

## 2026-05-01 (Phase E — v2 데이터 + 내용 동기화)

- **작업 범위**: 4개 모듈 v2 PR(#14·#15·#16·#17·#18, 모두 dev에 merge됨) 결과를 integration JSON·dashboard에 반영. **시각 디자인은 현재 톤 유지**(별빛·행성·그라디언트 추가 X) — 사용자 명시 보류. 신규 AI 컨셉(P1·P2·12.x)도 별도 영역.
- **데이터 재추출** (`python -m modules.integration.extract_data`):
  - `eqs_summary.json` 47 rows (avg EQS 68.1, v2 점수). 모든 row가 `dart_url`·`percentile`·`history`·`market_cap` 보유
  - `disclosures.json` 180 disc / 252 stmt. **180/180이 Gemini `[Cash]`/`[Risk]`/`[Hidden Agenda]`/`[Verdict]` 4섹션 완비**
  - `price_scenarios.json` 12 scenarios (id 6/7/9 제거, 신규 11=삼성 자사주소각·2=HD현대중공업 포함). 12/12 refUrl + dart_url
- **dashboard.html 수정** (총 6곳, 시각 효과 추가 없이 텍스트·구조만):
  1. **EQS v2 라벨 동기화** (`mods` 배열 L1298): 발생액 품질→**현금이익률**, 분식 확률→**매출회수 건전성**, 현금흐름 괴리→**부채 건전성**, 이익 지속성→**본업 안정성**, 재무 건전성→**자본 성장성**. `glossary.py` `GlossaryEntry.label` 단일 출처
  2. **EQS v2 내러티브 동기화** (`_eqsNarration` L1635-1651): 5개 모듈 × good/mid/bad 15개 텍스트를 v2 정의(현금이익률 R≥1.0, 매출회수 D, 부채비율 업종 임계, OM 평균+변동폭, 자본 CAGR)로 재작성. `glossary.py` `intuition`+`benchmark` 차용
  3. **공시 summary AI 4섹션 파싱·렌더** (신규 `_parseDiscSummary`·`_renderDiscSections`·`_escHtml` 헬퍼 + `showDisclosure` 재작성): 정규식으로 `[Cash]`/`[Risk]`/`[Hidden Agenda]`/`[Verdict]` 분할 → 라벨만 작은 색상(기존 mods 팔레트 #4ade80/#f87171/#a78bfa/#fbbf24) + 본문 #aaa, 배경 박스 추가 X. 비구조 평문은 기존 300자 컷 폴백 유지
  4. **채팅 context 동기화 누락 보강**: `showAnalyze`/`showDisclosure`/`showTimemachine` 진입 + `closePanel` 종료 시 `_chatSetContext` 호출. 이전엔 `openFullAnalysis` 성공 경로에서만 갱신되어 fallback 패널·공시·타임머신 모드 클릭은 chip이 stale 상태로 남았음
  5. **timemachine 미준비 안내 동적화** (L1495 fallback 블록): 하드코딩된 "현재 체험 가능한 기업은 15개입니다: 삼성전자·SK하이닉스·…" → `nodes.filter(x => x.has_quiz)` 기반 자동 계산. 현재 12개로 정확 표시 (15→12 변경은 quiz_data.py 정리 결과)
- **이미 구현되어 있던 것** (검증만): DART 사업보고서 외부 링크(L1209·1287, commit 07b1040), `_sparkline`·`_percentileBadge`(L1313·1315·1319·1321), Gemini 채팅 사이드바 자체(L126-231 + 1852-2152, commit b713372)
- **검증**:
  - `pytest tests/` 470 passed, 8 skipped (회귀 없음)
  - `black --check modules/integration/` clean
  - Playwright: 삼성전자 노드 → 풀스크린 분석 우회 후 우측 패널 fallback 확인. v2 라벨 5/5 노출, v1 잔재 0건. disclosure 패널에서 4 AI 섹션 100% 매칭, "원문 보기 ▾" 토글 동작. SK스퀘어(quiz 없음) 클릭 시 timemachine 미준비 화면이 동적 "12개" 표시
- **명시적 비범위** (다음 PR로): 갤럭시 시각 효과(별빛 30개·SVG 행성·슈팅스타·헤일로), EQS 점수 그라디언트, 차트 색상 통일, sparkline SVG 시각 강화, AI 분석 진한 색상 박스, AI_DIRECTION.md의 P1·P2·12.x 신기능
- **외부 의존**: financial v2 collector가 investing/financing cashflow를 메웠는지(Phase D의 "데이터 수집 중" 뱃지 자동 사라졌는지)는 추후 확인

## 2026-04-22 (Phase C — 통합 대시보드 신설)

- **작업**: 4개 모듈(relation·financial·disclosure·price) 데이터를 localhost 단일 대시보드로 통합
- **배경 — Phase 구조**:
  - Phase A (2026-04-21, PR #8): `.gitignore` 수정으로 `modules/*/data/*.db`·`*.json` 추적 허용 + v6 galaxies 디자인 relation viewer 이식
  - Phase B (2026-04-22, PR #9·#10·#11): 담당자 3명 DB 공유. financial·disclosure 완료, price는 `quiz_data.py` 15건(DB 없음)
  - Phase C (이번 세션): `modules/integration/` 폴더 신설
- **파일**:
  - `__init__.py` (패키지 마커)
  - `CLAUDE.md` (리더 소유 규약 + 데이터 소스 계약 + 업데이트 플로우)
  - `PROGRESS.md` (이 파일)
  - `extract_data.py` (DB·Python 상수 → JSON 배치 추출)
  - `dashboard.html` (v6 galaxies + 4개 fetch + 통합 패널)
  - `data/eqs_summary.json`·`disclosures.json`·`price_scenarios.json` (extract 결과)
- **데이터 소스 (extract 대상)**:
  - `modules/financial/data/financial.db` — `financial_local` 테이블
  - `modules/disclosure/data/disclosure.db` — `disclosure_local` + `financial_statement`
  - `modules/price/quiz_data.py` — `QUIZ_LIST` 상수 (15건)
  - `modules/relation/data/graph_top50.json` — dashboard가 직접 fetch (변환 불필요)
- **설계 결정**:
  - **방법 B (정적 JSON fetch) 채택**. shared DB(Supabase) 적재 결정 전까지 유지. 향후 FastAPI 승격 시 dashboard.html의 fetch URL만 교체하면 됨 (방법 C)
  - relation viewer(`modules/relation/viewer/index.html`)는 **유지** — relation 단독 뷰 역할. integration은 그 확장판
  - 경계 예외: integration에서만 타 모듈 import·DB 읽기 허용 (수정·삭제 금지)
- **limitations**:
  - price 커버리지 **15/50 = 30%**. 나머지 35개 기업은 `has_quiz=false` 플래그로 timemachine 모드에서 "데이터 없음(수집 중)" 뱃지 표시
  - shared DB(Supabase) 미적재. 공식 서빙 구조는 Phase D 이후

## 2026-04-22 (Phase D — eqs 메타 주입 + 외부 링크 + 누락값 안내)

- **작업 (commit `07b1040`)**:
  - `docs/prototype/eqs_data.json`(49건)에서 `market_cap`·`dart_url`·`industry_code`·`latest_year` 주입 → 시총 1,262조 → **1,425.2조**(2025 스냅샷) 갱신
  - `showAnalyze` h2를 DART 사업보고서 링크로 감싸기 (dart_url 있을 때만)
  - `is_financial_biz` flag (industry_code '064'~'067') 기반 "금융업 별도기준" 뱃지
  - 분석 연도 뱃지 "2025년 재무 기준" 표시
  - `build_news_url(company, date, category)`로 네이버 뉴스 검색 URL 자동 생성 → timemachine에 "📰 관련 기사 보기" 버튼
- **작업 (commit `53eba5f`, 이번 세션 후속 fix)**:
  - 공시 카드 summary 300자 컷 → **"더보기 ▾" / "접기 ▴" 토글** 구현 (전문 확인 가능)
  - `financial_local.investing_cashflow`·`financing_cashflow` 전수 NULL 상태 → `-조` 대신 **"데이터 수집 중"** 회색 뱃지로 명시 (financial 담당자 수집 반영 대기)
- **검증**: Playwright 전수 통과 (Samsung DART 링크·1425.2조 표시·더보기 토글 양방향·뱃지 표시), pytest 570/570, black clean
- **외부 데이터 소스 추가**:
  - `docs/prototype/eqs_data.json` — financial 담당자의 프로토타입 산출물 (market_cap 원 단위·dart_url). financial.db에 해당 컬럼이 없기 때문에 **유일한 최신 소스**

## 향후 업데이트 시 체크리스트 (팀원 공유용)

팀원이 자기 모듈 데이터 갱신 → git merge → **리더가 integration 재생성** 순서.

1. `git checkout dev && git pull`
2. `git checkout feat/integration-dashboard` (또는 후속 브랜치)
3. `git merge origin/dev`
4. `python -m modules.integration.extract_data` — JSON 3개 재생성
5. `python -m http.server 8000` → 브라우저로 육안 확인
6. 이상 없으면 `git add modules/integration/data/*.json && git commit -m "data(integration): <모듈> 업데이트 반영"`
7. PR 생성 → 본인 승인 후 merge

## 의존성 계약 (스키마 안정성)

`CLAUDE.md`의 "데이터 소스 계약" 표 참조. 각 모듈 담당자가 스키마를 바꿀 경우 integration 쪽에도 영향을 주므로 **PR 본문에 스키마 변경 명시** 필수.
