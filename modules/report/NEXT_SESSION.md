# 다음 세션 프롬프트 — **KOSDAQ 첫 골든(292 반도체·디스플레이 장비)** · 새 브랜치

> 이 파일은 다음 세션에 붙여넣을 핸드오프다. 갱신: 2026-08-12.
> 로드맵 근거는 [MILKYWAY_GENERATOR.md 부록 A](MILKYWAY_GENERATOR.md)(실측), 데이터 근거는 [FS_PARSE_PLAN.md §10](FS_PARSE_PLAN.md).

## 현재 상태

- **골든 20/20 · lite 23본 — 전부 KOSPI.** KOSDAQ 골든 **0본**.
- **데이터는 다 있다**: `fs_parse` 전량 완주로 `fs_account_xml` **2,590사 · 816,306행 · 217,231셀**(FY2019~2025),
  정답지 대비 G1 **299사 99.90%(16,029/16,045)** — 55사 표본에서는 100.00%(3,174/3,174).
  ⚠️ 정답지가 55사 → **299사**로 확대됐다(V-115 사고 + 리더 보존 결정). 무회귀 기준선은 **99.90%**다.
- **병목이 뒤집혔다** — 이제 부족한 건 데이터가 아니라 **해석 템플릿(골든)**이다.
  파싱된 2,590사 중 **2,111사(81%)가 골든 없는 산업**이고, 그중 KOSDAQ 미커버가 **1,464사**다.

## ✅ 240810 원익IPS — **완주** (2026-08-12, KOSDAQ 1호)

`feat/golden-kosdaq-292` 커밋 완료. dives 41 + appendix 12 · knots 18 · viz 46 · 원장 35주석 무핀 0.
게이트: `strict 0` · `--all --strict` **21본 0** · `--links 40/40` · `facts_lint 0` ·
pytest **344 passed** · 인터랙션 005930·015760·240810 각 **10 passed** ·
실브라우저 스윕(패널 104행 죽은 클릭 0 · 주석 35 무핀 0 · 1440·1280·1024 오버플로 0px · 콘솔 0).
채록 = **V-116·V-117·V-118**. `corps.csv` tier `1`(반도체장비 클러스터 산업 골든).

확인: `python -m http.server 8000` → `http://localhost:8000/integration/dossier/galaxy.html?ticker=240810`

### 이 1본이 세운 KOSDAQ 틀 (다음 본이 그대로 쓴다)

- **표시 단위는 티커 속성이다(V-117)** — `자산총계 3조 미만 → 억 원`. `build_series`가 돌려주는
  `unit_label`을 `corp.unit_label`에 그대로 실으면 렌더러·`§13`·`§18`·pytest가 함께 읽는다.
- **R&D가 판관비 밖에 있는 손익 구조** — `경상연구개발비` 본표 행이 있으면 패널 B에 `is-rnd`를 세우고
  `총이익 − 판관비 − R&D = 영업이익` 뺄셈을 카드가 직접 보여준다(`k5b`). `series.rnd`는 이제 실계정에서 온다.
- **소형사는 "capex가 현금을 삼킨다"가 아니다** — 투자활동 유출의 실체가 설비인지 **여유자금 운용**인지
  CF 세부를 열어 먼저 확인할 것.
- **`five.skip`은 반드시 설명 문자열** — 불리언 `true`면 화면 ④ 섹션이 빈 문단이 된다(체커는 통과).
- **승격 카드는 `.row` 앵커 필수**(삼성만 레거시 면제). 코어와 겹치면 ⓐ코어 흡수(`note_dive`)
  ⓑ무앵커면 APPENDIX ⓒ대체 실행 앵커 중 하나로 보낸다.

### 재사용 가능한 산출물 (gitignore, 이 머신)

`data/facts/facts_240810_b1~b6.json`(주석 36·항목 884) · `_skeleton_240810.json` ·
`_build_skeleton_240810.py`(패널 재생성기) · `_assemble_240810.py`(병합기) · `_BRIEF_240810.md`(산문 브리프) ·
`review/accuracy_240810.json` · `review/completeness_240810.md` · `review/shots_240810/`

## ▶ 다음 세션 목표 — 2순위 산업 골든 (부록 A.2)

**582 소프트웨어 143사**(SI·솔루션·보안 — 게임 골든 크래프톤이 안 맞는 집합. 용역매출·개발비 자산화가 축) →
303 자동차부품 103사 → 262/212/204.

⚠️ 착수 전 `fs_enrich --tickers <티커>` **필수**(인자 없이 돌리면 전량 — V-115).
⚠️ 신규 채록은 **V-119부터**.

## 실행 규약

**브랜치**: `feat/golden-kosdaq-292` — **이미 생성돼 있다**(2026-08-12). `dev`가 85커밋 뒤라
`feat/report-fs-parse` 위에서 팠다(dev에서 파면 골든 20본 베이스라인이 없다). main 직접 push·force push 금지.

선행 정본을 이 순서로 읽는다:
[MILKYWAY_GENERATOR.md](MILKYWAY_GENERATOR.md)(하네스 + **부록 A 로드맵**) → [VARIATIONS.md](VARIATIONS.md)(S0 전체 정독) →
[BUILD_CHECKLIST.md](BUILD_CHECKLIST.md)(29항) → [.claude/skills/galaxy-golden/SKILL.md](../../.claude/skills/galaxy-golden/SKILL.md)

### S0 재확인만 (전부 완료 — 값만 대조하고 넘어갈 것)
```bash
export PYTHONUTF8=1
python -m modules.report.sectioner --health 240810     # → OK
python -m modules.report.series 240810                 # → 완결 22/24 (미완 buyback·dsOp)
python -m modules.report.facts_lint 240810             # → 주석 36 · 항목 884 · ERROR 0
```
⚠️ **`fs_enrich`를 다시 돌리지 말 것** — 이미 932행 적재됐다. 돌려야 한다면 **반드시 `--tickers 240810`**
(인자 없이 실행하면 전 2,651사 재수집이 돈다 — 이제 argparse가 막지만, V-115 참조).
`corps.csv` cluster=`반도체장비`·tier=`1c`, `sector_golden_map.csv` 292 행, `report_240810.json`은 **이미 있다**.

### 완주 정의
```bash
python -m modules.report.facts_lint 240810              # ERROR 0
python -m modules.report.check_golden 240810 --strict   # §1~§19 갭 0(무핀 0 포함)
python -m modules.report.check_golden 240810 --links    # 계정셀 링크 실측 → 보고
python -m modules.report.check_golden --all --strict    # 골든 20본 0 (lite 24본 379건은 기존 baseline)
GALAXY_TICKER=240810 python -m pytest tests/report/test_galaxy_interaction.py
python -m pytest tests/report/ -q
```
\+ **accuracy-verifier REFUTED 0** · **completeness 삼성 T0 패리티** · **라이브 렌더 스윕**(클릭 사이 **Esc** 필수 ·
APPENDIX 나브 접힘 0@1440·1280·1024 · 1024px 가로 오버플로 0 · 콘솔 0 · **원문 TOC 전 주석 착지 실패 0** ·
**viz 박스가 실제로 그려지는지 눈으로 확인**)

완주 후: VARIATIONS 정본 §4에 **V-117부터** 채록(V-116이 이 티커의 S0~S2 채록이다 — 증상→원인→**게이트가 왜
못 잡았나**→처리) + 채록 로그의 240810 행을 **미완주 → 완주**로 갱신 · `corps.csv` tier `1c`→`1` ·
`build_galaxy_index.py` · 1커밋.

> ⚠️ **KOSDAQ 첫 본이라 변형이 쏟아질 것으로 예상한다.** 기존 20본에서 안 나온 실패는 전부
> VARIATIONS에 채록하고, **2회 반복되면 코드·조문으로 승격**한다(MILKYWAY §9).
> 특히 소형사에서 흔한 것: 부문정보 없음 · 성격별 비용(cogs/gross 결측) · 연결 미작성(별도만) ·
> 주석 수 적음 · 분기 급변동. `five=skip` 남발 대신 **그 회사 보고서가 정의하는 구조**를 따를 것(§4).

## 보고 규약 (컨텍스트 절약 — 리더 지시 2026-08-03)

- **착수** 1줄: `[티커/회사] S0: health OK · series N/24 · 주석 M개`
- **단계 전환** 1줄: `S1 fact N건 / S2 dive N장 / S3 산문 N카드`
- **게이트**: 숫자만 — `strict 0 · --all 20본 0 · accuracy REFUTED n건(정정) · links N/N · viz N장 · pytest N + 인터랙션 N/M`
- **완주**: 5줄 이내 + localhost URL
- **상세 보고는** ⓐ게이트 3회 미수렴 ⓑ리더 판단 필요한 구조 결정 ⓒ데이터 결함 ⓓ코드 승격 후보(2회+) **일 때만**
- **금지**: 파일 내용·JSON·카드 목록 덤프 · 카드별 산문 나열 · 진행 과정 서술 · 이미 문서에 있는 규칙 재설명

## 대기 중인 백로그 (이번 세션 대상 아님)

### 신규 골든 2~4순위 (부록 A.2)
582 소프트웨어 143사 → 303 자동차부품 103사 → 262/212/204 (132/104/94).
**별도 유형**: 701 연구개발업 62사 + 적자형 229사 — 매출 미미·적자가 정상이라 **새 서술 유형 설계** 필요.
**별도 트랙**: 금융 118사 — top line 정의부터 다름.

### 렌더러 부채 (콘텐츠 무관 · 전 골든 동형)
1. **dead-click 2~3행**(V-059) — 그룹헤더 행에서 펼침 캐럿이 정중앙 클릭을 가로챈다. 처방 후보: 캐럿 `marginLeft:auto`.
2. **900px 나브 접힘**(V-103) — 1440·1280·1024는 전 골든 0이나 900px에서는 공통으로 접힌다.
3. **`five.valley`가 `anchor.label`을 그대로 찍는 문제**(V-111 B → strict 게이트 **기각 확정**) —
   실측 6본 12건이 정당한 불일치라 등식 강제 불가. 처방은 **dive별 `valleyLabel` 도입**.
4. **JOURNEY 하이라이트 데드존**(V-111 C) — 인터랙션 테스트가 결정론적으로 skip되는 구간.
5. **`intro_lines` 3번째 줄 바인딩**(V-113 B) — 게이트(`≥2`)와 렌더러(`정확히 2`)의 비대칭 해소.

### 데이터 부채
1. **`series.py` `gross` 실계정 승격 캐스케이드**(V-112 후속) — 파생 `revenue−cogs`가 실계정과 어긋나는 게
   **11본**(000660·000720·003490·005380·010130·011200·012450·033780·051910·097950·139480)에 퍼져 있고
   그 11본은 **k4 산문이 전부 옛 파생값을 인용**한다. 데이터+산문 동시 수리가 필요하다.
2. **viz 하한 게이트**(V-113 A) — `--strict`에 '흐름 dive 중 viz 지정 ≥ N'. **기존 골든 실측 후 임계 결정.**
3. **`strings.header`·`hero` 중복 저작 정리**(V-110 후단) · **`report_<t>.json` 완전성 계측**(V-109 사각 A).
4. ~~`strings.overview` 키 부재~~ — **해소(2026-08-12, PR #117 lint 수습)**. 원인은 빌더가 아니라
   **테스트 glob 과대매칭**이었다: V-110 게이트는 골든 렌더러(galaxy.html) 필드의 계약인데 glob이
   `galaxy_lite_*`(별도 렌더러·별도 스키마 — overview·epilogue·knots 자체가 없음)까지 삼켰다.
   `_goldens()`에서 lite 제외 → **전체 pytest 1,257 passed / 0 failed**.
5. **`[첨부정정]` 재수집 104건** — [fs_parse_failures.csv](data/fs_parse_failures.csv)가 입력.
   `report_raw`는 (ticker,fy)당 rcept 1건이라 폴백할 원본이 로컬에 없다 → **collector 재수집**으로만 풀린다.
6. **financial `collector.py` 근본 수정 미완** — 조건 없는 이자수익 별칭 + first-wins가 **그대로다**.
   다음 수집에서 FN-025 오염이 재발한다. financial(A) 소관이라 담당자 PR 필요.

## 주의

- 인코딩 `PYTHONUTF8=1`. 로컬 서버 `python -m http.server 8000`.
- `reports.db`(shared/data/)·`facts/`·`raw_cache/`는 gitignore — `--strict` §7·§10·§13·`--links`·`facts_lint`는
  **이 머신에서만** 유효(CI skip).
- **main 직접 push·force push 금지.** 신규 골든은 **별도 브랜치**에서.
- ⚠️ **세션 한도**로 서브에이전트가 중도 실패할 수 있다 — 실패하면 그 단계를 **직접** 수행하거나 재실행할 것.
- ⚠️ **"준비됨" 전제를 믿지 말고 S0에서 실측할 것.** 이번 핸드오프의 `fs_account 0행`이 그렇게 발견됐다.
