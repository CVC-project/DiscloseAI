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
