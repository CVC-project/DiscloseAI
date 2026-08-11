# 다음 세션 프롬프트 — **KOSDAQ 첫 골든(292 반도체·디스플레이 장비)** · 새 브랜치

> 이 파일은 다음 세션에 붙여넣을 핸드오프다. 갱신: 2026-08-12.
> 로드맵 근거는 [MILKYWAY_GENERATOR.md 부록 A](MILKYWAY_GENERATOR.md)(실측), 데이터 근거는 [FS_PARSE_PLAN.md §10](FS_PARSE_PLAN.md).

## 현재 상태

- **골든 20/20 · lite 23본 — 전부 KOSPI.** KOSDAQ 골든 **0본**.
- **데이터는 다 있다**: `fs_parse` 전량 완주로 `fs_account_xml` **2,590사 · 816,306행 · 217,231셀**(FY2019~2025),
  정답지 55사 대비 **G1 일치율 100.00%**. firm JSON 매출 오염도 **67사·132셀 보정** 완료(FN-025 해소).
- **병목이 뒤집혔다** — 이제 부족한 건 데이터가 아니라 **해석 템플릿(골든)**이다.
  파싱된 2,590사 중 **2,111사(81%)가 골든 없는 산업**이고, 그중 KOSDAQ 미커버가 **1,464사**다.

## ▶ 이번 세션 목표 — 원익IPS 240810 골든 1본 완주

**왜 이 회사인가** (리더 결정 2026-08-12):
- 292 특수 목적용 기계 = 미커버 **163사(KOSDAQ 145)**로 갭 최대.
- 이미 완주한 반도체 골든(삼성전자·SK하이닉스)의 **하류 밸류체인**이라 서술 재사용이 가장 크다.
- 원익IPS는 FY2024 매출 7,482억·영업이익 106억으로 **KOSDAQ 중형 흑자 제조**의 전형.
  (SFA 056190은 매출 2조지만 영업적자 −484억, 피엔티 137400은 2차전지 장비라 클러스터가 어긋난다.)
- **이 1본의 진짜 목적은 산업 커버가 아니라 "KOSDAQ 소형·중형 제조" 서술 틀을 세우는 것**이다.
  기존 20본은 전부 대형 KOSPI라 틀이 안 맞는다 — 매출 중앙값이 9배 차이(6,352억 vs 699억),
  적자비율 39.7% vs 20.3%. 이 틀이 서야 2~4순위 산업 골든이 KOSDAQ 1,761사에 쓰인다.

## ⚠️ 착수 전 선결 1건 — **`fs_account`가 비어 있다** (실측 완료, 추정 아님)

`series.py`는 경계 단방향 원칙상 **`fs_account`(reports.db)만** 읽는다 — firm_json은 integration 소유라 안 읽는다.
그런데 `fs_enrich`(DART API)는 골든 클러스터 **55사에만** 돌렸다. 240810 실측:

```
report_raw 5개년(2021~2025) ✓ · sectioner --health OK ✓ · report_section 182건 ✓
fs_account_xml 384행 ✓ · firm_json ✓
fs_account 0행  →  series 완결 0/24 (24키 전부 미완성)
```

**경로 확정 — (a) 즉시 착수** (리더 결정 2026-08-12, 병행 방침):

```bash
python -m modules.report.fs_enrich --tickers 240810   # DART 키 필요, 1사면 수 분
```

구조적 해결(= `fs_parse` 전 계정 확장 + `series.py`가 `fs_account_xml`을 소스로 인정)은
**별도 plan으로 분리했다** — [ACCOUNT_SOURCE_PLAN.md](ACCOUNT_SOURCE_PLAN.md) R1~R2.
그쪽은 R0(읽기 전용 실측)이 병행으로 돌므로 이 세션은 신경 쓰지 않는다.

이유: R1~R4는 이 선결 조건을 구조적으로 없애지만, KOSDAQ 서술 틀이 안 맞으면 그 비용이 헛돈다.
틀을 먼저 검증하는 게 순서다.

## 실행 규약

**브랜치**: `feat/golden-kosdaq-292` 를 `dev`(또는 리더 지정)에서 새로 판다. main 직접 push·force push 금지.

선행 정본을 이 순서로 읽는다:
[MILKYWAY_GENERATOR.md](MILKYWAY_GENERATOR.md)(하네스 + **부록 A 로드맵**) → [VARIATIONS.md](VARIATIONS.md)(S0 전체 정독) →
[BUILD_CHECKLIST.md](BUILD_CHECKLIST.md)(29항) → [.claude/skills/galaxy-golden/SKILL.md](../../.claude/skills/galaxy-golden/SKILL.md)

### S0 프리플라이트
```bash
export PYTHONUTF8=1
python -m modules.report.fs_enrich --tickers 240810   # ← 선결 (a) 선택 시. DART 키 필요
python -m modules.report.sectioner --health 240810
python -m modules.report.series 240810                # 완결 N/24 를 보고에 적을 것
python integration/dossier/build_report_source.py 240810
```
`corps.csv`에 240810은 있으나 `cluster`·`tier`가 **비어 있다** — 착수 시 `cluster=반도체장비`(신규) 부여를 함께 결정할 것.
신규 클러스터를 만들면 [sector_golden_map.csv](data/sector_golden_map.csv)에 `반도체장비,prefix,292,...` 한 줄을 더해
`fs_parse --scope sector-golden` 범위도 같이 넓어진다.

### 완주 정의
```bash
python -m modules.report.facts_lint 240810              # ERROR 0
python -m modules.report.check_golden 240810 --strict   # §1~§19 갭 0(무핀 0 포함)
python -m modules.report.check_golden 240810 --links    # 계정셀 링크 실측 → 보고
python -m modules.report.check_golden --all --strict    # 전 골든 무회귀(현재 20본 0)
GALAXY_TICKER=240810 python -m pytest tests/report/test_galaxy_interaction.py
python -m pytest tests/report/ -q
```
\+ **accuracy-verifier REFUTED 0** · **completeness 삼성 T0 패리티** · **라이브 렌더 스윕**(클릭 사이 **Esc** 필수 ·
APPENDIX 나브 접힘 0@1440·1280·1024 · 1024px 가로 오버플로 0 · 콘솔 0 · **원문 TOC 전 주석 착지 실패 0** ·
**viz 박스가 실제로 그려지는지 눈으로 확인**)

완주 후: VARIATIONS 정본 §4에 **V-114부터** 채록(증상→원인→**게이트가 왜 못 잡았나**→처리) + 채록 로그 1줄 ·
`corps.csv` cluster·tier 부여 · `build_report_source.py 240810` · `build_galaxy_index.py` · 1커밋.

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
4. **`strings.overview` 키 부재** — `tests/report/test_strings_knots_gate.py`가 전 `galaxy_lite_*.json`에서
   실패한다(현재 **24건**, 브랜치 기존 baseline). 빌더 스키마 ↔ 테스트 요구 불일치라 한쪽을 맞춰야 한다.
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
