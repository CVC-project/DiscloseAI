# FS_PARSE_PLAN — 원문 XML에서 재무제표 본표 파싱 (fs_account 전 상장사 확장)

> **한 줄**: 이미 로컬에 있는 사업보고서 원문 27GB에서 재무제표 본표를 파싱해, `fs_account`를 55사 → 최대 2,590사로 넓힌다.
> 배경 원장: [../../integration/DECISIONS.md](../../integration/DECISIONS.md) **FN-025** (firm JSON 매출 오염 269사)
> 소관: `modules/report/` — 리더 소유. financial 모듈 코드는 건드리지 않는다.

## 1. 왜 하는가 (2026-08-11 실측으로 확정된 문제)

lite·EQS가 쓰는 13계정은 `firm_<t>.json`에서 오고, 그 원재료는 financial 모듈의 `eqs_v3_panels_2021_2025.json`이다. 그런데:

| 사실 | 실측 |
|---|---|
| firm JSON 매출이 오염된 기업 | **비금융·비지주 269사** (`\|영업이익\| > 매출`), 매출 급락후급반등 20사 |
| 원인 | financial `collector.py`가 `이자수익`을 조건 없이 revenue로 매핑 + **첫 값 우선**이라, DART 응답에서 이자수익 행이 먼저 오면 진짜 매출을 밀어냄 (FN-025) |
| 오염 사례 | 카카오 FY23 매출 0.19조(정답 7.557조) · **골든 한화에어로 FY25 0.22조**(정답 26.70조) |
| 재생성 가능 여부 | **불가** — `modules/financial/data/universe/`가 비어 있어 패널 파일이 로컬에 없다 |
| 우리 대안(`fs_account`) | **55사뿐** — `fs_enrich.py`가 DART API 재호출 방식이라 골든 클러스터에만 돌렸다 |

**그런데 원문은 이미 다 있다.**

| 자산 | 실측 (2026-08-11) |
|---|---|
| 원문 XML | `modules/report/data/raw_cache/` — **2,590사 · 12,090건 · 27GB** |
| `report_raw` | 2,590사, **5개년 보유 2,225사** |
| `report_section` | 428,420건 — 단 **주석만** 파싱됨(`III.3.연결주석`·`III.5.별도주석`·`II.사업의내용`) |
| 재무제표 본표 | **파싱 안 됨** — 그러나 XML 안에 그대로 있다 |

**결정적 확인**: 카카오 FY2023 원문(`raw_cache/035720/20240418000375.xml`, 8.6MB)에서
`구분 / 제29(당)기 / 제28(전)기 / 제27(전전)기 … 영업수익 7,557,001,757,272 …` 를 직접 확인했다.
→ **정답이 우리 파일 안에 있다. 재수집도, financial 모듈 수정 대기도 필요 없다.**

## 2. 설계

```
modules/report/data/raw_cache/<ticker>/<rcept_no>.xml   (입력 — 이미 있음)
        │
        ▼  fs_parse.py (신설)         ※ LLM 미사용, 규칙 파싱만 (D7)
   연결재무제표 본표 추출 → 계정 × (당기·전기·전전기)
        │
        ▼
   fs_account_xml  (신설 테이블 — 기존 fs_account를 오염시키지 않는다)
        │
        ▼  대조 검증 (55사 정답지)
   일치율 측정 → 임계 통과 시 fs_account로 승격/병합
```

### 왜 별도 테이블인가
기존 `fs_account` 55사는 **DART API 산출 = 정답지**다. 파서 결과를 같은 테이블에 섞으면 검증 기준이 사라진다.
파일럿 단계에서는 `fs_account_xml`에 쌓고, 일치율이 임계를 넘은 뒤에 병합 규칙을 정한다.

### 한 보고서에 3개년이 들어 있다
사업보고서 본표는 `당기 / 전기 / 전전기` 3열이다 → **FY25 보고서 1건으로 23·24·25**를 얻는다.
따라서 5개년을 채우는 데 보고서 2건(FY25 + FY22)이면 충분하고, 이는 **report_raw 5개년 미보유 365사의 커버리지도 끌어올린다**.

### 뽑을 계정 (galaxy/lite 13계정 + 골든이 쓰는 확장분)
`revenue · cogs · operating_income · net_income · operating_cashflow · investing_cashflow · financing_cashflow · total_assets · total_liabilities · total_equity · current_assets · current_liabilities · long_term_debt`
여력이 되면 골든이 쓰는 것(법인세·OCI·기초/기말현금·배당·자기주식)도 — 우선순위는 13계정.

### 규율
- **연결(CFS) 우선, 없으면 별도(OFS)** — 어느 쪽을 썼는지 행에 남긴다(`sj_div` 활용 또는 컬럼 추가)
- **계정명 우선순위를 명시한다** — `매출액/영업수익/수익(매출액)/매출` > `이자수익/수수료수익/보험수익`.
  FN-025의 재발 방지 조문: **조건 없는 별칭은 그 계정을 부수적으로 보고하는 회사에서 본래 값을 덮어쓴다.**
  first-wins로 두지 말고 **우선순위 정렬 후 최상위 1건**을 택할 것.
- **파생·합산 금지** — 원문에 합계 행이 없으면 만들지 않는다(미발견으로 기록)
- 출력 행마다 `rcept_no`를 남겨 추적 가능하게 (기존 fs_account 스키마와 동일)

## 3. 검증 (착수 전에 합의할 것 — 이게 이 작업의 성패)

**정답지**: 기존 `fs_account` 55사 × 5개년 × 13계정.

| 게이트 | 기준 |
|---|---|
| G1 정확도 | 55사 교집합에서 **값 일치율 ≥ 99%** (허용오차 0, 원 단위 정수 비교) |
| G2 커버리지 | 파싱 성공 기업 수 · 계정별 결측률 리포트 |
| G3 sanity | `\|영업이익\| > 매출` 0건, 매출 급락후급반등 0건 (FN-023 R14·R15와 동일 규칙) |
| G4 회귀 | 기존 `fs_account` **불변**(별도 테이블이므로 자동), 완주 lite 22사 재빌드 바이트 동일 |

G1이 임계 미달이면 **전량 확장하지 않는다** — 실패한 계정·기업 패턴을 먼저 분류한다.

## 4. 단계

| 단계 | 내용 | 산출 |
|---|---|---|
| P0 | XML 구조 실측 — 본표가 어느 태그·섹션에 있는지, 표 형식 변형이 몇 종인지 샘플 20사로 파악 | 구조 노트 |
| P1 | `fs_parse.py` 초안 + `fs_account_xml` 테이블 | 파서 |
| P2 | **55사 파일럿** → G1 일치율 측정, 불일치 전수 분류 | 일치율 리포트 |
| P3 | 임계 통과 시 2,590사 전량 파싱 (배치, 진행상황 `pipeline_state` 활용) | fs_account_xml |
| P4 | integration: firm JSON 매출 보정 — 오염 269사에 파싱값 적용, `meta.revenue_fix`에 근거 기록 | firm JSON |
| P5 | 카카오 lite 해금 + 한화에어로 EQS 탭 정정 확인 (골든 series 26.7조와 대조) | 검증 |

P4는 `integration/dossier/` 소관이라 별도 커밋으로 분리한다.

## 5. 다음 세션 부트스트랩 프롬프트

```
modules/report의 fs_parse(D안)를 진행하자.

준비:
- git fetch 후 origin/feat/galaxy-lite-wave1 에서 feat/report-fs-parse 브랜치 파생
  (D안의 배경인 FN-025·완주 lite 22사가 이 브랜치에만 있다)
- modules/report/FS_PARSE_PLAN.md 가 이 세션의 실행 정본이다. 착수 전에 이 문서와
  거기 명시된 배경(integration/DECISIONS.md FN-025, FN-023의 R14·R15)을 읽어.
- 참고 코드: modules/report/fs_enrich.py(현행 API 방식·계정 매핑) ·
  modules/report/sectioner.py(원문 XML → 섹션 파싱, 본표는 대상 밖) ·
  modules/report/models.py(FsAccount 스키마)

이번 세션 범위: P0 ~ P2 (전량 확장은 다음)
1. P0 — 샘플 20사 XML로 본표 위치·표 구조 변형 실측. 연결/별도 구분, 3개년 열 배치,
   계정명 변형(매출/매출액/영업수익/수익(매출액))을 눈으로 확인하고 구조 노트로 남길 것
2. P1 — fs_parse.py + fs_account_xml 테이블 신설. LLM 금지, 규칙 파싱만.
   계정명은 반드시 우선순위 정렬 후 최상위 1건 선택 (first-wins 금지 — FN-025가 그래서 터졌다)
3. P2 — 55사 파일럿 후 G1(일치율 ≥ 99%) 측정. 불일치는 전수 분류해서 표로 보고.
   임계 미달이면 전량 확장하지 말고 원인 분류까지만 하고 멈출 것

규율:
- 파생·합산 금지(원문에 합계 행이 없으면 미발견) · 0 채움 금지
- 기존 fs_account 55사는 정답지다 — 절대 덮어쓰지 말 것
- cp949 콘솔 크래시 방지: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
- 대형 heredoc 금지(스크래치 .py 파일로)
- 보고는 단계별 1줄 + 말미 5줄 이내. 일치율은 숫자로.

세션 말미: 일치율 리포트 → 커밋 → push 여부는 내 확인 후
```

## 6. 열린 질문 (리더 판단 필요)

1. **병합 정책** — 파싱값이 기존 API값과 다를 때 어느 쪽을 정본으로? (권고: API값 우선, 파싱값은 결측 보충용. 단 API값이 R14/R15에 걸리면 파싱값 우선)
2. **EQS 탭 일관성** — firm JSON을 보정하면 EQS 점수 자체(GPU 산출)는 그대로인데 화면 매출만 바뀐다. 점수와 표시값이 어긋나는 구간을 어떻게 표기할지.
3. **financial 모듈 수정 요청 여부** — D안이 성공해도 근본(collector.py first-wins)은 남는다. 다음 수집 때 같은 오염이 재발한다.
