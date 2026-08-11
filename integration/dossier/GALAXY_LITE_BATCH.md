# GALAXY_LITE_BATCH — 표준-델타 lite 확장 실행 계획 (새 세션 부트스트랩)

> **한 줄**: 삼성전기 프로토(완주)를 견본으로, 골든 표준이 있는 클러스터의 잔여 기업에 lite 델타 뷰를 확장한다.
> 설계 정본: [GALAXY_LITE_PLAN.md](GALAXY_LITE_PLAN.md) — **착수 전 §1(EQS 차별)·§2.1(결측)·§6(문체·카드)·§6.5(선정 기준)·§6.6(스토리 스레드) 필독**.
> 원장 필독: [../DECISIONS.md](../DECISIONS.md) FN-019~021 · [../v2/UX_DECISIONS.md](../v2/UX_DECISIONS.md) UX-041~044.
> 견본(골든 아님 — lite의 골든): `data/galaxy_lite_009150.json` + `data/facts_lite_009150.json` + `data/notes_lite_009150.json`

## 0. 왜 lite 확장인가 (효율 근거 — 리더 질문 2026-08-11 답)

| 축 | 골든 1본 | lite 1본 (삼성전기 실측) |
|---|---|---|
| 세션 | 1본 = 1세션 전체 | 1세션에 3~5본 가능 |
| 서브에이전트 | ~34회 (V-113) | **1~2회** (fact 추출만, sonnet) |
| 산문 | 24,250자 (LLM) | ~2,500자 (카드 9장, 그중 LLM은 4장) |
| 수치 생산 | LLM 슬롯 채움 + accuracy-verifier 카드당 1회 | **전부 코드** + 코드 게이트 2종 |
| 조회 시 토큰 | 0 | 0 |

→ **대략 15~30배 효율.** 단 전제: 그 클러스터에 T1 골든(표준)이 있어야 성립 — 표준 없는 섹터는 lite로 때우지 않고 신규 골든 선행(리더 확정, PLAN §9).

## 1. 대상 (Wave 순서)

### Wave L1 — corps.csv cluster 부여 잔여 기업 (빌더가 지금 그대로 동작)
`modules/report/data/corps.csv`에서 `cluster` 있음 · `tier` 공란 · 골든/스코프아웃 아님 · **galaxy_lite 미존재** 기업.
**실측 확정 22사 (2026-08-11)** — 이들은 fs_account 55사 안이라 현금흐름 gap-fill(§2.1)도 그대로 작동한다:

| 클러스터(표준) | 대상 |
|---|---|
| 중공업방산 11 (한화에어로 012450) | 두산 000150 · LS ELECTRIC 010120 · 삼성중공업 010140 · 두산에너빌리티 034020 · 한화오션 042660 · 현대로템 064350 · LIG넥스원 079550 · HD현대일렉트릭 267260 · 한화시스템 272210 · 효성중공업 298040 · HD현대중공업 329180 |
| 2차전지화학 3 (LG화학 051910) | 포스코퓨처엠 003670 · 삼성SDI 006400 · LG에너지솔루션 373220 |
| 자동차 2 (현대차 005380) | 기아 000270 · 현대모비스 012330 |
| 건설 2 (현대건설 000720) | HD한국조선해양 009540 · 삼성물산 028260 |
| 반도체 1 (삼성전자 005930) | 한미반도체 042700 |
| 플랫폼 1 (NAVER 035420) | 카카오 035720 |
| 에너지소재 1 (고려아연 010130) | SK이노베이션 096770 |
| 바이오 1 (셀트리온 068270) | 삼성바이오로직스 207940 |

> ⚠️ 배치 순서 권고: 반도체(한미반도체)부터 — 표준·견본이 같은 클러스터라 문체 비교 검증이 가장 쉽다. 그다음 대형주(기아·삼성SDI·카카오) → 중공업방산 11사 일괄.

### Wave L2 — 섹터→표준 매핑 확장 (별도 결정 후)
cluster 미부여 기업은 `companies_index.json` 섹터(25종) → 골든 표준 매핑 테이블을 먼저 확정해야 한다(PLAN §9-4).
직접 대응 없는 섹터(기계·장비, 전기전자부품 등)는 **신규 골든 빌드 선행** — 이 문서 비범위.
L2는 fs_account 밖이므로 현금흐름 결측 시 "데이터 준비 중" 표기로 착지(FN-021) — 수집 확대는 별도 트랙.

## 2. 사전 배선 (첫 세션 1회만 — Phase 0)

lite 완성 기업이 v2 셸에서 열리려면 탭 배선이 필요하다 (현재 탭②는 골든 `galaxy_index.json`만 본다):
1. `build_galaxy_lite_index.py` 신설 — `data/galaxy_lite_*.json` 스캔 → `data/galaxy_lite_index.json` 매니페스트 (build_galaxy_index.py 패턴 복제)
2. `integration/v2/src/bundle.jsx` — `liteTickers` state 추가(매니페스트 fetch), 탭②의 `activeWhen:'hasData'` 판정을 `galaxyTickers ∪ liteTickers`로, **iframe src를 티커에 따라 분기**(골든→`galaxy.html`, lite→`galaxy_lite.html`). 골든이 우선(둘 다 있으면 골든)
3. UX-043의 "대표 은하수" 목록은 골든 전용 유지 (lite는 대표가 아니라 학습 대상)
4. 캐시버스트 7개소 상향 (FN-004·FN-009) + 골든 20본 탭 무회귀 확인

## 3. 1사 처리 루프 (S1~S6)

```
S1 빌드(토큰 0):   python integration/dossier/build_galaxy_lite.py <ticker>
                   → 표준 자동 해석·규칙 카드 5장·8상·주석 후보. selfcheck FAIL이면 여기서 멈추고 원인 기록
S2 소재 선정(코드): PLAN §6.5 이상 신호로 주석 후보 중 3~5개 선택
                   (성장 괴리·이익 집중·조달 구조 변화·미가동 투자·우발 요소 — 13계정 증가율 비교로 판정)
S3 fact 추출:      note-extractor 서브에이전트 1회(배치) → data/facts_lite_<t>.json
                   (rcept_no는 S1 산출 JSON의 corp.rcept_no. source_quote는 원문 그대로 — 재작성 금지)
S4 카드 작성:      '눈여겨볼 곳' 2~4장 → data/notes_lite_<t>.json
                   견본: notes_lite_009150.json — 스키마·nums 선언·order/bridge(서사: 조달→사용→마찰→구조) 그대로
S5 게이트:         python integration/dossier/inject_lite_notes.py <t>   (FAIL 카드만 수정 재실행)
S6 렌더 스모크:    galaxy_lite.html?ticker=<t> — 6단 렌더·스토리 스레드·표준 딥다이브 링크·콘솔 에러 0
```

세션 말미: `build_galaxy_lite_index.py` 재실행 → 일괄 커밋(1커밋 = 그 세션 완주분) → 로컬 서버 URL 보고.

## 4. 작성 규칙 (프로토에서 확정된 것 — 위반 = 게이트 반려)

- **문체**: 경어체(~예요/~해요)·격식체 금지·숫자만 `[브래킷]`(제목 포함 텍스트 브래킷 금지). **비유(골짜기·강줄기·존·저수지·항로) 금지** — 직관 서술 (UX-041)
- **수치**: 산문의 모든 브래킷은 nums에 근거 선언(fact/ratio/share/series/norm/std_norm) — 게이트가 재도출·원문 substring 대조. bridge에는 새 수치 금지
- **EQS 중복 금지**: 점수·비율 나열·업계평균 카드 없음 (PLAN §1 금지 목록)
- **결측**: 0 채움 금지 · '미공시' 단어 금지(FN-021 — 기본 문구 "데이터 준비 중")
- **표준 딥링크**: 델타 카드는 빌더가 자동, notes 카드는 `std_focus`에 표준 dives의 주석 키(n7·n12·ppe 등 — 표준 JSON에서 실존 확인 후) 부여
- **환경**: 대형 heredoc 금지(bash EOF 깨짐 — 스크래치 .py 파일로) · 신규 HTML은 `<meta charset>` (FN-019)

## 5. 세션 운영

- **1세션 = 3~5사** (S3 fact 추출은 기업별 병렬 가능, S4는 순차 권장 — 컨텍스트 절약)
- 보고 규약: 착수 1줄 / 기업당 완주 1줄(게이트 숫자만) / 세션 말미 5줄 이내 (NEXT_SESSION 관례 준용)
- 리더 피드백 발생 시 즉시 원장 라우팅(UX-### / FN-###), 같은 판단 2회 = PLAN 조문 승격
- 브랜치: `feat/galaxy-lite-wave1` (dev 파생) — 완주분 push 여부는 세션 말미 리더 확인

## 6. 완료 정의 (Wave L1)

- [ ] Phase 0 배선 + 골든 20본 무회귀
- [ ] L1 대상 전수(≈22사) lite JSON + 게이트 PASS + 렌더 스모크
- [ ] `galaxy_lite_index.json` 반영 — v2 셸에서 해당 기업 탭② 활성 확인
- [ ] 표본 3사 리더 검수 (문체·서사·딥링크) → 통과 시 Wave L2 매핑 결정으로
