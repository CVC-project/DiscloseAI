# Integration 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

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
