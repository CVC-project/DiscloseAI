# Phase 4 (LLM 하네스) 실행 계획 — galaxy 30~32사 확장 (Step 1)

> **성격**: 이 문서는 **실행 순서·검증·세션 절단**만 정의한다. 하네스 **설계 정본**은 [integration/dossier/DOSSIER_TABS_PLAN.md](../../integration/dossier/DOSSIER_TABS_PLAN.md) §6 (설계를 재발명하지 말 것).
> **읽는 순서(새 세션)**: ① docs/ARCHITECTURE.md ② [modules/report/CLAUDE.md](CLAUDE.md) ③ 이 문서 ④ DOSSIER_TABS_PLAN.md의 지정 절만(§6.1~6.8·D7·D10·D11 — 79KB 전체 읽지 말 것).
> **최종 갱신**: 2026-07-13 (트랙 B 디자인 통일 완료 후, Phase 4 착수 직전 상태).

## 현재 상태 (착수 전 스냅샷)

- ✅ **GPU 서빙(R4) 완료**: A100 원격 + SGLang(Qwen/Qwen3-32B-AWQ, xgrammar) `report-llm.service` 상시화. SSH 터널 → `REPORT_LLM_BASE_URL=http://127.0.0.1:30000/v1`(shared/config.py). 단건 지연 ~0.84s 실측.
- ✅ **트랙 B(디자인 통일)·v1 폐지 완료** (PR #45·#47, dev 머지): UI는 v2 단일, 3탭·셸 폰트(Pretendard+IBM Plex Mono)·엣지(얇고 각진)·팔레트(mint)·산업군 동적 테마·인트로 제거까지 끝남. 디자인 정본 = 루트 [DESIGN.md](../../DESIGN.md).
- ✅ 완성: collector·sectioner·fs_enrich·db·models, 골든 `integration/dossier/data/galaxy_005930.json`, `GALAXY_JSON_SCHEMA.md`, `tests/report/check_golden_keys.py`, `corps.csv`(48사).
- ⚠️ **Phase 3 backfill 미실행**: `reports.db` 4테이블 0행, `raw_cache/`·`publish/` 없음 — Phase 4의 입력이 아직 없음 (**최대 병목**).
- ⚠️ **series.py `build_series()` 스켈레톤** (SOURCE_MAP 24키만 완비).
- ❌ Phase 4 신규 파일 부재: story·stylelint·bank.jsonl·schemas·llm·extract·validate·publish·benchmark_extract + `integration/dossier/pull_report_json.py` + 스킬 3종. requirements.txt에 pydantic·openai·playwright 없음.

### 착수 시 확정된 리더 결정 (이 세션 반영)
- **held-out 제2 골든 = NAVER(035420)** — 삼성(제조)과 가장 이질적인 플랫폼 업종으로 일반화 판정. 구조 차이(cogs 결측)는 `benchmark_extract.py`가 NAVER에 존재하는 슬롯만 채점. NAVER를 프롬프트·임계 캘리브레이션에 사용 금지(오염 방지).
- **원문 공유 = Google Drive 도입 안 함** — 로컬 `modules/report/data/`(raw_cache·reports.db는 gitignore, DART 키로 재현) + publish/만 커밋. 800사 원문(~1~2GB) 보관 채널은 그때 재검토.
- **산업군 변형 템플릿(금융·지주)** = Step 1 아님. D10 스코프아웃으로 16~18사 자동 제외("준비 중"), 변형 템플릿은 Step 3(Claude Code 제작 → 리더 시각 검증 → 골든 확정).
- **착수 브랜치**: `dev`에서 새 작업 브랜치(예: `feat/report-phase4`). ⚠️ 작업 트리에 `modules/price/data/`(빈 price.db, 미추적)만 남음 — 커밋 제외.

## 단계 (G0~G8, 의존성 순)

- **G0 프리플라이트** (0.5h): 새 브랜치(dev 분기). requirements.txt에 pydantic·openai·playwright + `playwright install chromium`. DART 키·SGLang(`curl http://127.0.0.1:30000/v1/models`) 접속 확인.
- **G1 Phase 3 backfill 실행** (반나절, 코드 완비 — 실행만): `python -m modules.report.collector` → `sectioner` → `fs_enrich`. 500~700 DART 콜(한도 3%). idempotent, 백그라운드+G3 병행. **R5 스파이크 내장**: 이종 3사(KB금융·삼성바이오·NAVER) 주석 분할 수를 플랜 부록 B-2 실측과 대조. DoD: `pipeline_state` 48사 COLLECTED/SECTIONED/ENRICHED.
- **G2 series.py 완성** (1일): **R13 조기 프로브 먼저**(SQL로 rnd·dep 계정 존재 판정 — 코드 작성 전) → `build_series()` 구현(A: firm_*.json → B: fs_account → D: 파생, N(rnd·dsOp)은 주입 슬롯) → **삼성 22키를 골든과 ±0.05조 대조 pytest**(단위·부호 규약 확정) → 48사 완결률 리포트.
- **G3 골든-only 3종** (1일, G1·G2와 병렬): `schemas.py`(check_golden_keys pydantic 승격 — 실물 dives 27+appendix 14), `stylelint.py`(L0 9규칙, 골든 위반 0까지 캘리), `bank.jsonl`(골든 190필드 유형화+마스킹, synthetic 셀은 G7 이월).
- **G3' llm.py** (0.5일, 병렬): SGLang OpenAI 호환 클라이언트(xgrammar json_schema·추출 temp0/생성 0.3·seed 고정·재시도 3·동시성 8·**usage 레저**). 구조화 출력 10콜 스모크.
- **G4 story.py**: §6.6 스토리 11종+앵커 클러스터+vLine. series 산출 확정(G2) 후.
- **G5 수렴점** (1~1.5일): `validate.py`(3층, L3는 http.server+playwright 렌더) → `publish.py`(D10 스코프아웃+minify) → `extract.py`(§6.1 루프, `--dry-run` 콜 계획 플래그) → `integration/dossier/pull_report_json.py`(publish→data 복사 + **manifest `galaxy_index.json`**). DoD: `python -m modules.report.extract --ticker 005930` 무인 완주.
- **G6 게이트 1 — 삼성 골든 재현** (0.5~1일): detector·lint·validate를 골든에 실행 → 전부 통과까지 임계 조정 → 골든 회귀 pytest(raw_mn 100%·금칙 0·스토리 유형 ≥90%). story 48사 드라이런 → `_STORY_COVERAGE.md`. `/galaxy-gen` 스킬.
- **G7 게이트 2 — held-out 벤치(NAVER)** (0.5일+리더 수작업 1블록): held-out 골든 수작업(코드가 정형 스켈레톤, 리더는 산문) + `benchmark_extract.py`(NAVER 존재 슬롯만 채점) + **오염 3중 가드 pytest**(bank source assert·프롬프트 held-out abort·L0-8). 이후 프롬프트·모델·임계 변경은 이 게이트 통과 필수. `/galaxy-bench` 스킬.
- **G8 Step 1 마일스톤** (1~2일): `extract --batch`(첫 5사 파일럿 → 전량, resumable, 기업당 60콜·런 10M 토큰 가드) → 리뷰 큐(`/galaxy-review`) → `pull_report_json.py` → **bundle.jsx `GALAXY_TICKERS` 하드코딩을 manifest fetch로 대체**(실패 폴백 `['005930']`) → 30~32사 L3 스크린샷 전수 + v2 실브라우저 스모크 → dev 머지.

## 세션 분할 (≈6~8일)

| 세션 | 내용 | 커밋 |
|---|---|---|
| S1 | G0+G1+G2 (backfill 백그라운드 + series) | requirements / series.py+테스트 |
| S2 | G3 (schemas·stylelint·bank) — S1과 병행 | 3종 |
| S3 | G3'+G4 (llm·story) | 2커밋 |
| S4 | G5 (validate·extract·publish·pull) — 최대 세션 | 2커밋 |
| S5 | G6 (삼성 재현·캘리·/galaxy-gen) | 1PR |
| S6 | G7 (held-out·benchmark·오염 가드·/galaxy-bench) | 1PR |
| S7 | G8 전반 (배치 실행·리포트) | 비커밋(review/) |
| S8 | G8 후반 (리뷰 큐·publish/pull·탭 활성화·문서 마감) | 2커밋 |

## 리스크 체크포인트

1. **R13 소스 구멍**(rnd·dsOp 미존재) → S1 SQL 프로브로 코드 작성 전 판정. 최종 안전판 `five=skip`(설계 내장).
2. **토큰 폭주** → usage 레저 + `--dry-run` + 기업당 60콜·런 10M 토큰 abort + 5사 파일럿.
3. **NEEDS_REVIEW 과반(>15사)** → 실패 클래스 분포 진단 → 레버: 임계 재캘리 → 부분 재생성 → bank 보강 → 프롬프트(벤치 게이트) → 모델 스왑(EXAONE) → **최종 안전판 = AUTO_PASS분만 부분 배포**(per-ticker 활성 구조).
4. **held-out 오염** → 3중 가드 pytest가 CI 상시 감시.
5. **대용량 커밋 사고** → gitignore 완비 확인. 세션별 경로 명시 add.

## 코스피 ~800사 확장 대비 (지금 공짜로 심을 것)

① manifest 방식 탭 활성화(G8) ② publish JSON minify ③ 유일 공급 관문 = pull_report_json.py 유지(publish를 git 밖으로 옮겨도 스크립트 1곳 수정) ④ 스코프아웃 명단을 corps.csv `scope_hint` 열로 ⑤ extract `--only-missing`·`--limit` 증분 플래그 ⑥ 800사 원문 보관 채널 그때 재검토. — 나중에: DB Postgres 이전, LFS, 임베딩 문체 게이트, KOSDAQ 시드.

## 착수 시 새로 결정할 것 (플랜이 명시적으로 미룬 것)

- R13 실소스(rnd·dsOp가 fnlttSinglAcntAll에 없으면 연구개발활동 표/성격별비용/부문 주석 중 — G1 실데이터로 확인)
- L0/detector 임계 실수치(골든 p5~p95 캘리브레이션)
- bank.jsonl synthetic 셀 2~3건(삼성에 없는 적자·순조달 캡션, 리더 수작업)
- schemas.py는 실물(dives 27+appendix 14 분리) 기준

---

## 리더 스코프 확정 — 현금 은하수(탭③) 전담 (2026-07-13)

> 이번 세션 변동사항: **business_tab(탭①)은 팀원에게 위임**, 리더(나)는 **현금 은하수(cash milky way, 탭③)만 담당**. 아래는 내가 하는 부분만 확정한 것 — 하네스 적용부터 디자인 레이아웃·검토 게이트까지.

### R1. 역할 분담

| 소유 | 범위 | 대상 파일 |
|---|---|---|
| **리더(나)** | 현금 은하수 = **데이터 생산 하네스** + **표현(디자인 레이아웃)** | `modules/report/*`(하네스) · `integration/dossier/galaxy.html`(정본 템플릿) · `design/prototypes/현금은하수_해방판.html`·`dc-runtime.js` · `integration/dossier/CASH_GALAXY_STYLE_GUIDE.md`·`GALAXY_JSON_SCHEMA.md` |
| **팀원** | business_tab = 탭① 사업·기업 개요 (§5b, DOSSIER_TABS_PLAN) | `design/prototypes/kospi50_business_tabs.html`(확정) → `integration/dossier/business.html`(이식) · `business_*.json`·`extract_business_json.py` |

- **경계**: business는 galaxy/AI 하네스와 **무의존**(D1의 `DOSSIER_TABS` 배열에 나중에 한 줄 추가로 합류). 팀원 작업이 내 하네스·galaxy 템플릿을 건드리지 않는다. business_*.json 스키마·이식은 팀원 소관 — 나는 무관여.
- 따라서 **G0~G8은 전부 리더 몫** — 애초에 G0~G8은 100% 현금 은하수 트랙이고 business_tab은 §5b(플랜 밖)라, 위임으로 **하네스 계획(G0~G8·세션 분할)은 변경 없음**. 바뀐 건 아래 **디자인 레이아웃 트랙(R2)이 리더 전용으로 명시된 것**뿐.

### R2. 디자인 레이아웃 트랙 (리더 전용 — 하네스와 병행)

> 기존 플랜은 "해방판 = 완성 정본, 이식만" 전제였다. 리더는 여기에 **디자인 레이아웃을 능동적으로 확정·검토하는 트랙**을 추가한다. 목표 질문 = **"정해진 템플릿이 회사마다 다른 사업보고서 내용·형식에 맞게 잘 휘어지되 큰 틀은 유지되는가."** — 무엇이 고정이고 무엇이 변형인지의 구체 명세 = **R5**.

세 가지 디자인 대상:
1. **전체 사업보고서 디자인** — 탭③ 페이지 뼈대: 초심자 0단계 인트로(A1) → **3열 그리드**(2fr SVG : 3fr 5패널 : 5fr sticky 카드, A3·A5) → 5패널(A~E) → 딥다이브 → APPENDIX. 해방판 기반, 잔여 조정만 확정.
2. **주석 디자인** — 딥다이브 카드 골격(헤더→what→links/lnote→why{viz}→five, A8) + **APPENDIX 14 하단 렌더**(five=skip, D9 이원화). 주석 표는 재현 금지·직관 우선.
3. **cash milky way 레이아웃 — 유입=본류 오른쪽 / 유출=본류 왼쪽**.
   - ⚠️ **이미 해방판 CONFIG에 구현됨**: `galaxy.html` `tributary: { outDx:-58(유출=좌), inDx:120(유입=우) }`. 즉 신규 레이아웃이 아니라 **이 방향 규칙을 A3 명문 불변식으로 승격**하는 작업(현재는 코드에만 존재, 스타일가이드 A3 문구엔 "색·라우팅으로만 표현"이라 좌/우가 안 적혀 있음).
   - 스타일가이드 A3에 좌/우 방향 규칙 1줄 추가 + 성공기준/detector에 "유입 우·유출 좌 라우팅 유지"를 불변식으로 편입.
   - **✅ 결정(2026-07-13, 리더 승인)**: `side` 필드 **안 넣음** — 매듭 `kind`에서 쪽(유입=우/유출=좌)을 렌더러 규칙으로 파생 + **삼성 전용 하드코딩 ID(k3·k5·k13: 감가상각 회귀선·자본 갈래)를 `kind` 구동으로 대체**. R5 원칙(변형은 규칙으로, 회사별 예외 금지). 구현·검증 시점 = **A3/A5 명문화 직후, schemas.py 동결(G3) 전** — 삼성 골든 재현 불변(픽셀 동일) + 첫 타사 렌더(DL-2)에서 일반화 검증.

### R3. 디자인 레이아웃 검토 게이트 (리더 검토 방법)

> 검토 원칙: 리더는 **실렌더 스크린샷**으로 본다(코드/JSON 아님). 산출물 = validate.py L3와 **같은 렌더러**(`http.server` + playwright, G0에서 설치)로 뽑은 PNG. 여러 회사를 **나란히(contact-sheet)** 놓아 "같은 템플릿, 다른 내용" 적응성을 눈으로 판정. 승인 전까지 스키마·문구를 동결하지 않는다.

| 게이트 | 시점 | 검토 데이터 | 리더가 보는 것(산출물) | 통과 조건 |
|---|---|---|---|---|
| **DL-1 초안** | **G3(schemas) 동결 전** | 골든 삼성 005930만 | galaxy.html 렌더 스크린샷(2 breakpoint: 1440·1024) + 유입우/유출좌·3열·인트로·카드·APPENDIX 체크리스트 | 3대상(전체·주석·유입우/유출좌) 레이아웃 리더 승인 → A3/A5 명문화 + `side` 필드 요부 확정 |
| **DL-2 적응성** | **G6·G7 후** | 삼성(골든) + NAVER(held-out) + **R5 변형 축을 극단으로 미는 2사**(주석 최다/최소·결측·부문수 극단) | 4사 나란히 contact-sheet 스크린샷 + **R5 축별 체크리스트** | 같은 템플릿이 R5 변형 자유도 전 축에서 **틀 유지 + 슬롯만 변형** = 리더 승인 → 미달 시 템플릿 보정 후 재검토 |
| **DL-3 전수** | **G8** | 30~32사 | G8 L3 전수 스크린샷 중 **이상치만** 리더 표본 검토 | 활성/보류(per-ticker) 판정 — AUTO_PASS만 배포(R3 안전판과 동일) |

- **반복 방식**: Claude Code가 스크린샷+체크리스트 생성 → 리더가 승인/주석(annotate) → Claude Code가 galaxy.html·스타일가이드 보정 → 재렌더. **디자인 원본(galaxy.html·해방판·스타일가이드)은 리더의 구체 승인 뒤에만 수정**(방법·초안 제시까지는 손대지 않음).
- 검토 큐 스킬(선택): G6 `/galaxy-gen`·G8 `/galaxy-review`에 스크린샷 contact-sheet 출력을 붙여 DL 게이트와 통합.

### R4. 세션 분할 반영(디자인 트랙 삽입점)

| 기존 세션 | 디자인 트랙 추가 |
|---|---|
| S2(G3 전) | **DL-1** 먼저 — galaxy.html 초안 렌더 → 리더 승인 → A3/A5 명문화·`side` 확정 후 schemas.py 동결 |
| S5~S6(G6·G7) | **DL-2** — held-out 포함 4사 적응성 검토 |
| S8(G8 후반) | **DL-3** — 전수 스크린샷 표본 검토 → 활성 판정 |

### R5. 불변식 vs 변형 자유도 — Controlled Variation 명세 (UI/UX 일관성의 핵심)

> **원칙**: 유입 우/유출 좌는 여러 변형 축의 **하나**일 뿐. 진짜 규칙은 **"큰 틀(문법)은 고정, 내용이 채우는 슬롯만 규칙대로 변형"**. 변형은 회사별 수작업이 아니라 **같은 생성기·같은 코드 경로**가 데이터에 따라 슬롯을 채운 결과 — 그래서 회사가 달라도 스타일이 못 튄다(일관성 보장). 자유도마다 **거동(grow/collapse/skip)과 경계**를 못박아 "자유자재"가 "제멋대로"가 되지 않게 한다.

| 영역 | 불변식 (절대 안 변함 = 일관성) | 변형 자유도 (내용 따라 변함 = 적응성) | 변형 거동·경계 (안 깨지게) |
|---|---|---|---|
| **은하수 SVG** | spineX 0.48·직교 라우팅·굵기 2단·**유입 우/유출 좌**·기초·기말 저수지 앵커·본류 매듭 순서(A3) | 중간 매듭 유무(영업외·자사주 등)·지류 개수·지류 길이 | 없는 매듭은 본류에서 생략(빈 자리 안 둠)·지류는 항상 올바른 쪽·본류 세그먼트 끊김 없이 재연결 |
| **재무제표 5패널** | 5존(A~E) 구조·CF 3활동 동등위계·자본변동표엔 자본변동만·**합계 정합 철칙(A6)** | 존별 행 유무·행 개수·결측 계정(예: cogs 없음)·세부 펼침 group 수 | 없는 행 생략(placeholder 금지)·하위 합 잔차는 "그 외 ±0.x조"로 흡수·대분류=하위합 항상 성립 |
| **딥다이브 카드** | 카드 골격(what/links/why/five)·색 배지·sticky·억지 매핑 금지(A0) | 카드 총수·viz 종류 분포·five=skip 비율·links 개수 | 주석이 유기적일 때만 카드 채택(아니면 미채택 — padding 금지)·미완성 시계열은 five=skip(빈 차트 금지) |
| **APPENDIX** | 하단 위치·한 줄 요약(what/why, five=skip) | 항목 개수(삼성 14 ≠ 타사) | 리스트가 개수대로 늘고 줆·항목 형식 동일 |
| **5개년 차트** | A11 규칙(당해 강조·valley·zero선·"5년 새 최대"만) | vLine/vTwin/skip 선택·음수 구간 유무 | 데이터 완결 시만 렌더·미완결 skip·타입은 콘텐츠가 결정(LLM 선택 금지) |
| **셸·토큰** | 3열 그리드·색=의미(A2)·폰트·엣지·반응형 CSS var | (회사 무관 — 고정) | — |

- **변형 상한 = 표준 템플릿이 흡수하는 데까지.** 위 자유도는 "제조·플랫폼 표준 형식" 안의 변형(행 유무·개수·결측). **계정 체계가 근본적으로 다른 금융·지주**(매출원가 없고 이자수익 중심 등)는 변형이 아니라 **별도 변형 템플릿(Step 3)** — 지금은 D10 스코프아웃(16~18사 "준비 중"). 하나의 템플릿을 억지로 늘려 은행 재무제표까지 담지 않는다(늘리다 깨지는 것 = 일관성 붕괴 방지).
- **강제 방법**: 불변식은 `stylelint.py` L0 규칙 + detector가 골든·전사에 검사(위반 0). 변형 거동(생략·skip·잔차 흡수)은 생성기(series·extract·story·publish)가 **규칙으로** 실행 — 회사별 예외 분기 금지. `GALAXY_JSON_SCHEMA.md`·A3·A5에 이 명세를 반영, held-out(NAVER)이 표준 템플릿 변형 자유도의 **일반화 증명**.
- DL-2가 이 명세의 **눈 검증** — 변형 축을 극단으로 미는 회사(주석 최다·최소, 결측 많은 NAVER, 부문 극단)를 골라 "틀 유지 + 슬롯만 변형"을 contact-sheet로 확인.


---

## R6. 하네스 전환 — GPU 산문 포기, Claude Code(스킬·서브에이전트) 검증 루프 (2026-07-13)

> **결정**: 산문·주석 생성에서 **GPU LLM(SGLang/Qwen) 제외**. 근거 = SK 골든 실증: GPU는 단위변환 오류·수치 환각(선수금 1.2조)·few-shot 누출(삼성 세율 23.3%)·격식체·일반론을 반복했고, 최종 골든은 **Claude가 주석 원문을 직접 판독·직접 작성**해 완성됨(41장, 체커 PASS). llm.py·터널은 폐기하지 않되(전송계층 검증 완료) **산문 파이프라인에서 배제** — 향후 기계적 보조(표 파싱 후보 등)로만 재검토.
> **대체 아키텍처** = Claude Code 오케스트레이터 + 스킬(단계 진입점) + 서브에이전트(카드 단위 병렬) + **기계 체커(코드)** 의 3중 루프. 사람(리더)은 산업 골든 승인 게이트에만.

### R6.1 파이프라인 5단계 — 각 단계: 생산자 → 기계검증 → 에이전트검증 → 실패 라우팅

| # | 단계 | 생산자 | 기계 검증(코드 체커) | 에이전트 검증 | 실패 시 |
|---|---|---|---|---|---|
| S1 | **숫자·표 완성** | collector·sectioner·fs_enrich·series(코드) + **note-extractor 서브에이전트**(주석 md 판독→fact JSON) | ① series 24키 완결률 ② **source_quote 원문 substring-match**(무환각 기계증명) ③ 정합 항등식: 매출−원가=총이익 · ni+조정+운전자본=영업창출 · 창출−실납부=OCF · 기초+순증=기말현금 · 자본워크 5행 합 · 자산=부채+자본 | 추출 누락 감사(주석 목록 vs fact 커버) | sectioner 보강(옛 XML 포맷) 또는 재추출 |
| S2 | **레이아웃 완성** | assemble(fact→panels·knots·subrows·bsbar) | ① 렌더 스모크: 콘솔에러 0 + pv 표시 ② grp 서브행 합=부모(±0.2, 잔차는 "그 외" 명시) ③ viz_data **viz별 스키마 검증**(vSteps=rows·vWater=steps·vPuddle=ar/inv·vHBar=items·vChips=chips) ④ **삼성 골든 무회귀**(pv 전값 비교) | ui-ux-reviewer: 3열·유입우/유출좌·펼침 동작 | assemble 수정(템플릿 수정 시 반드시 컴파일+pv 스모크 동반) |
| S3 | **산문 완성(주석까지)** | **prose-writer 서브에이전트** — 입력: ⓐ골든 스타일 견본(숫자·고유명 마스킹) ⓑ**fact-sheet(그 카드에 허용된 검증 수치 화이트리스트)** ⓒA7 카피 규칙. 카드 단위 병렬(41장) | **prose-lint**: ① 브래킷 숫자 ⊆ fact-sheet(환각 차단) ② 격식체·금칙어(투자조언·사상최대) ③ 연도오인(기준/현재) ④ 빈 브래킷 ⑤ five cap 숫자≥1·so 1문장 ⑥ 타사명·타사수치 0 | — (검증은 S4) | 위반 카드만 재작성(전체 재생성 금지) |
| S4 | **정확성 검증** | — | ① 링크 a값=패널 v값 ② viz 내부 합 항등식 ③ 파생수치 재계산 대조(암산 금지 — 19.7→18.8 교훈) | **accuracy-verifier 서브에이전트**(카드당 1, 적대적): 브래킷 수치를 fact·주석 원문에서 재도출, 회계 서술의 사실성 판정 → 주장별 CONFIRMED/REFUTED | REFUTED 카드 → S3 재작성(사유 첨부) |
| S5 | **완전성 검증** | — | check_golden(일반화판): 27+14 커버리지 · 카드 4절(what/links/why/five) 공란 0 · 주석맵 커버(그 회사 실주석 목록 대비) · **깊이 지표**(what≥2문장·카드당 브래킷≥3·콘텐츠 dive links≥2) | **completeness-auditor**: 골든 대비 "설명이 얕은 카드" 지목 + playwright 전 행 클릭 스윕(카드 열림·비지 않음) | 지목 카드 → S3, 구조 결손 → S1/S2 |

### R6.2 루프 3층

1. **카드 루프**(S3↔S4·S5): 위반·REFUTED·얕음 카드만 개별 재작성 → 재검증. 수렴 조건 = 갭 0. 발산 가드 = 카드당 3회 초과 시 NEEDS_REVIEW 큐(리더).
2. **기업 루프**(S1→S5): `/galaxy-golden <ticker>` 한 호출 = 전 단계 + 카드 루프 완주 → 산출: galaxy_<t>.json + 검증 리포트(체커 결과·항등식·스크린샷). PASS만 publish.
3. **산업 확장 루프**: ① report_section 주석 타이틀 시그니처로 48사 **기계 클러스터링**(제조/메모리/플랫폼/바이오…; 금융·지주는 D10 스코프아웃 유지) ② 클러스터당 대표 1사를 **산업 골든**으로 — 여기만 리더 DL 게이트(contact-sheet 승인) ③ 승인된 산업 골든이 그 클러스터의 스타일 견본·주석맵·fact-sheet 스키마가 되어 나머지 기업 자동 확장(전 체커 PASS 필수, 실패는 리뷰 큐).

### R6.3 세션 복기 → 루프에 박아 넣은 규칙 10 (실수 재발 방지)

1. **파생 수치 암산 금지** — 비현금조정 +19.7(암산)→+18.8(원문 재합산) 사고. 모든 파생값은 S1 항등식 체커가 계산·검증.
2. **source_quote substring-match** — "원문에 그 문자열이 실제로 있는가"가 무환각의 기계 증명. GPU 시절 환각(선수금)을 이것으로 차단.
3. **산문 숫자 화이트리스트** — 브래킷 숫자 ⊆ fact-sheet. few-shot 누출(삼성 23.3%·삼성전기)의 구조적 차단.
4. **템플릿 수정 = 컴파일+pv 스모크 동반** — 괄호 1개 누락이 클래스 eval 전체를 죽여 renderVals까지 침묵 붕괴한 사고. 수정 후 즉시 "매출액 97.1 보이는가" 스모크.
5. **렌더 검증은 "카드가 열리고 내용이 비지 않는가"까지** — diveCard가 links 없어 throw→빈 카드 사고. JSON 존재≠렌더 성공.
6. **체커 규칙 파라미터화** — 주22·주30은 삼성 잔재 패턴이었으나 SK의 정당 주번호. 잔재 스캔은 회사별 화이트리스트로.
7. **viz_data는 viz별 스키마 선검증** — vSteps steps/rows 형식 불일치로 빈 박스 렌더 사고.
8. **잔차는 명시적 "그 외" 행** — 합계 정합 철칙(A6)의 실행형.
9. **원자적 쓰기·최종본만 커밋** — 이터레이션 중간본이 브라우저 캐시로 노출돼 "깨진 화면" 오인 사고. 검증은 항상 fresh playwright.
10. **방어적 렌더러 유지** — 불완전 JSON 1개가 전체 뷰어를 죽이지 않게(getter 기본값+빌더 try/catch). 단, 조용한 degrade를 체커(5)가 잡는다.

### R6.4 스킬·서브에이전트 구성 (구축 대상)

- 스킬: `/galaxy-extract` `/galaxy-assemble` `/galaxy-prose` `/galaxy-verify` `/galaxy-golden`(기업 루프 드라이버) `/galaxy-batch`(산업 확장)
- 서브에이전트: `note-extractor`(읽기전용) · `prose-writer` · `accuracy-verifier`(적대) · `completeness-auditor` · 렌더 검증은 기존 `ui-ux-reviewer` 재사용
- 산출 폴더: fact-sheet·검증 리포트 = `modules/report/data/facts/`·`review/`(비커밋), publish JSON만 커밋 — 기존 경계 규칙 유지.
- **G3'(llm.py)·G7(벤치)의 GPU 전제 무효화**: bank.jsonl(few-shot 뱅크)→골든 스타일 견본으로 대체, benchmark_extract→S4 accuracy-verifier로 대체. held-out(NAVER) 원칙은 유지 — **플랫폼 클러스터의 산업 골든**으로 승격.

### R6.5 현재 자산 매핑 (이미 있는 것)

| 자산 | 상태 | R6에서의 역할 |
|---|---|---|
| collector·sectioner·fs_enrich·series(+pytest 20) | ✅ | S1 코드 생산자 |
| 삼성 골든 + **SK 골든**(체커 PASS) | ✅ | 제조·메모리 클러스터의 스타일 견본·회귀 기준 |
| check_sk.py | ✅ 프로토타입 | S5 check_golden으로 일반화(회사 파라미터화) |
| galaxy.html 데이터 구동(pv·sub·bsbar·appendix) + 방어 렌더 | ✅ | S2 렌더러 |
| write_sk_golden.py(수작업 스크립트) | ✅ | S3 prose-writer 프롬프트·fact-sheet 계약의 원형 |
| llm.py·SSH 터널 | 보류 | 산문에서 제외, 기계 보조 후보로만 |

### R6.6 주석 라우팅 원장 — "모든 실주석이 처리됐는가" (구현 완료)

- **원칙**: 그 회사 사업보고서의 **실주석 전수**(reports.db 기준)가 `meta.routing_ledger`에 매핑돼야 한다: `dive:cited`(본문 인용) / `appendix:nX` / `row:<id>`(패널 행 커버) / `excluded`(+reason 필수, 잔액성 소액 등).
- check_golden §7이 기계 검증: 원장 누락·MISSING·사유 없는 제외·**유령 인용**(본문 주N이 실주석에 없음 — corp.rcept_no 기준) 전부 FAIL.
- 실증: 도입 즉시 SK 미커버 11건(리스·관계기업·이연법인세 등) 노출 → 정당 인용 5건 추가 + 잔액성 4건 명시 제외, **SK corp.rcept_no가 삼성 것으로 남은 메타 버그**도 유령 인용 검사로 적발·수정. 양 골든 원장 완비 PASS.

### R6.7 S6 인터랙션 QA — UI/UX 동작 검증 (구현 완료)

- `tests/report/test_galaxy_interaction.py` (playwright, GALAXY_TICKER 환경변수): ①A9-② 제스처당 정거장 ≤1칸(**정거장 좌표계=knots 순서**로 측정 — DOM 행 좌표계는 오탐) ②A9-③ 450ms 유휴 후 단번 재동기화는 허용 스펙 ③스크롤 멈춤 없음 ④핀→Esc 해제 ⑤펼침 토글 왕복 ⑥APPENDIX 카드 본문 비지 않음(빈 카드 회귀) ⑦1024px 가로 오버플로 0 ⑧상호작용 전 과정 콘솔 에러 0. 양 골든 7/7 PASS.
- 교훈: 첫 실행의 "17칸 점프"는 버그가 아니라 A9-③ 정상 동작 — **오라클은 스타일가이드 자구 수준으로 정밀해야** 오탐 없이 진짜 버그(멈춤·씹힘·다중 전환)를 잡는다. /galaxy-golden S5에 이 스위트 통과를 게이트로 편입.

### R6.8 모델 티어링 — 비용 효율화

| 작업 | 실행자 | 모델 | 근거 |
|---|---|---|---|
| 수집·분할·series·체커·항등식·렌더 스윕·인터랙션 QA | **코드**(pytest·check_golden) | — | 결정론·무료 — 최대한 코드로 |
| S1 note-extractor / S5 completeness-auditor | 서브에이전트 | **sonnet** | 표 판독·대조 위주(창의성 불요) |
| 기존 test-generator | 서브에이전트 | haiku | 유지 |
| S3 prose-writer / S4 accuracy-verifier | 서브에이전트 | **상속(최상위)** | 골든 깊이 산문·적대 검증 = 품질 병목, 여기만 고급 모델 |
| 오케스트레이션(/galaxy-golden) | 메인 세션 | 상속 | 판단·라우팅 |
- 절감 장치: 카드 루프는 **위반 카드만** 재작성(전량 재생성 금지) · fact-sheet 캐시(재추출 불요) · 렌더/문체/정합은 전부 코드 체커가 선차단해 에이전트 호출 수 최소화.

### R6.9 보고서 기반 원칙 — 골든은 문체의 견본이지 구조의 견본이 아니다 (구현 완료)

- **방향A (골든⊃회사)**: 골든에 있어도 그 회사 보고서에 근거(series 완결·주석·패널 행)가 없으면 그 항목은 **아예 생략** — 0/— placeholder 표시 금지. check_golden §1이 "근거 없는 dive 존재"를 FAIL로 잡는다(기대 집합 = REQ_SERIES(series 근거) ∪ COND_ROW(행 근거), 골든 참조 제거).
- **방향B (회사⊃골든)**: 그 회사에만 있는 주석은 원장이 MISSING으로 노출 → `new-dive:<key>` 라우팅 + 신규 카드 생성(패널 행·A7/A8 문법 산문·viz)이 의무. §7이 "new-dive 미생성"을 FAIL로 잡는다. 골든 universe 밖 신규 dive는 커버리지 위반이 아니다.
- 회귀: `tests/report/test_report_driven.py` 4케이스 — cogs 없는 가상사에서 k3 비요구(A)·근거 없는 k3 존재 시 FAIL(B)·신규 dive 허용(C)·양 골든 무회귀. **4/4 PASS**.
- 함의: 산업 골든의 역할 재정의 — 구조 레지스트리가 아니라 **문체·깊이 견본 + 회귀 기준**. 구조는 언제나 그 회사 사업보고서가 정의한다(R5 Controlled Variation의 체커 강제형).
