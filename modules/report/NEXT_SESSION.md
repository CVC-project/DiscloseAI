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

## ▶ 이번 세션 목표 — 원익IPS 240810 골든 **S3부터 이어서 완주**

> ⚠️ **2026-08-12 세션이 S0~S2를 이미 끝냈다.** 아래 "완료분"을 다시 하지 말 것.
> 브랜치 `feat/golden-kosdaq-292` (dev가 85커밋 뒤라 `feat/report-fs-parse` 위에서 팠다).

### 완료분 (재실행 불요 — 전부 실측 확인됨)

| 단계 | 상태 | 산출물 |
|---|---|---|
| S0 프리플라이트 | ✅ | `sectioner --health` OK · `corps.csv` cluster=`반도체장비`/tier=`1c` · `sector_golden_map.csv`에 292 추가 · `report_240810.json`(재무제표 4본·주석 35) |
| `fs_enrich` | ✅ | fs_account **932행**(FY21~25) — ⚠️ **V-115** 참조, `--tickers` 필수 |
| `series` | ✅ | **22/24** (미완 `buyback`·`dsOp`만) |
| **S1 fact-sheet** | ✅ | `data/facts/facts_240810_b1~b6.json` — **주석 36 · 항목 884 · `facts_lint` ERROR 0·WARN 0 PASS** |
| **S2 골격** | ✅ | `data/facts/_skeleton_240810.json` — panels **A1·B16·C11·D40·E5** + series + corp. **항등식 9종 전부 오차 0.00억 PASS**. 재생성기: `data/facts/_build_skeleton_240810.py` |

### 이번 세션이 할 일 — S2.5 → S3 → S4 → S5 → S6 → S7

1. **S2.5 구조 확정** — 골격의 40개 BS 행 · 36개 주석을 놓고 dive 목록을 확정(§4 보고서 기반).
   ⚠️ 이 회사 고유 구조는 **§ 아래 "KOSDAQ 첫 본에서 실측된 것"** 참조.
2. **S3 산문** — prose-writer로 카드별. 브래킷은 **억원**으로 쓴다(단위 결정 아래 참조).
3. **S4~S6** — accuracy-verifier · completeness-auditor · 인터랙션 pytest · 라이브 스윕.
4. **S7** — VARIATIONS 채록 로그의 240810 행을 **미완주 → 완주**로 갱신 + `corps.csv` tier `1c`→`1`.

### KOSDAQ 첫 본에서 실측된 것 (S2.5·S3 입력 — 추정 아님)

- **손익 구조가 다르다** — `경상연구개발비`가 판관비와 **별개 본표 행**이다:
  `총이익 3,828.4 − 판관비 1,415.7 − R&D 1,674.6 = 영업이익 738.1억`(FY23·24·25 오차 0.00억).
  R&D가 **매출의 18.4%**. 패널 B에 `is-rnd` 행이 이미 있다.
- **투자활동 −1,785억의 실체는 설비가 아니다** — capex는 **257억**뿐이고 대부분이
  **상각후원가측정금융자산 취득 1,992억**(여유자금 운용). 대형 KOSPI 골든의
  *"capex가 영업현금을 삼킨다"* 서사를 그대로 쓰면 **틀린다**.
- **무차입 경영** — 부채비율 20%(부채 1,946억 / 자본 9,700억), 단기차입 2,000억을
  빌렸다가 2,000억 그대로 갚아 **순증 0**.
- **수주형 구조** — 계약자산 534억(유동 454+비유동 80) · 계약부채 1,091억 · 재고 2,727억(자산의 23%).
- **품질보증충당부채 156억** — 장비 납품 후 무상보증이 구조적 비용(주23에 롤포워드 있음).
- **5개년 사이클** — 매출 12,323 → 10,115 → 6,903 → 7,482 → **9,098억**,
  영업이익 1,641 → 976 → **−181(적자)** → 106 → 738억, EPS 3,007 → 1,854 → −282 → 426 → 1,727원.
  **FY23이 밸리** — `anchor`는 여기.
- **OCF 1,566억이 5년 최대**인데 순이익은 840억 — 감가상각 340억·재고평가손실 162억 등 비현금 조정 609억.

### ⚠️ 미결 1건 — 리더 판단 대기 (단위 표시)

렌더러가 `단위: 조 원`을 **하드코딩**(`galaxy.html:69`)해 영업이익 738억이 패널에 **`0.074`** 로 뜬다.
`meta.unit_label`을 읽어 라벨만 바꾸는 **후방호환 설계**가 가능하나(기존 20본은 필드 부재 → 조 기본)
공용 템플릿 변경이라 2026-08-12 세션이 **단독 결정하지 않았다**.
→ 현재 방침: **패널 단위는 조 유지 · 산문 브래킷은 억원**(기존 골든이 소액을 그렇게 쓴다 — 015760 `[2,469억원]`).
결정이 내려오면 V-116 ⑤로 승격한다.

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
