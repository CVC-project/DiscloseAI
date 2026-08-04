# 다음 세션 프롬프트 — Wave 2 신규 산업 T1 골든 8본 (브랜치 `feat/golden-wave2-industries`)

> 이 파일은 다음 세션에 붙여넣을 핸드오프다. 갱신: 2026-08-04.

## 현재 상태

- **골든 20본 목표 중 16본 완주**: 삼성 005930(T0) + T1 15사. 전원 `--strict` §1~§15 갭 0.
- **Wave 2 진행 4/8 완주** — 철강 현대제철 004020(V-102) · 정유 S-Oil 010950(V-104) · 식품 CJ제일제당 097950(V-105) · **유통 이마트 139480(V-107, 08-04)**.
  남은 4본: **항공 대한항공 003490** · 게임 크래프톤 259960 · 엔터 하이브 352820 · 유틸리티 한국전력 015760.
  **PR 없이 본당 1커밋 push만**(리더 지시). T2 확장은 이 브랜치 범위 밖.
- **이마트 139480 완주 요약**: 영업이익 [3,225억](매출의 1.1%)인데 이자비용 [5,180억] — 지분 정리 일회성 [4,782억]이 메워 두 해 만에 흑자전환(빼면 세전 [-1,019억]). 감가상각 [1.49조]가 영업이익의 [4.6배]라 영업현금 [1.32조]. **리스부채 [3.33조]가 재무상태표에 별도 행 없이 기타단·장기금융부채에 포함** → 행 신설 대신 `n26` hl로 해결(신규 처방). `--strict` **첫 시도 0**(Wave2 4본 연속) · `--all` 16본 0 · accuracy 15→0 · BS 계정셀 **44/44** · 나브 접힘 0@1440·1280·1024 · pytest 91 + 10/10.

## ✅ 리더 판단 대기 — **전량 해소(2026-08-04 "다 승격")**

대기 5건 + V-107 신규 3건을 **코드·계약으로 승격 완료**(V-108, 커밋 `a6d92858`). **이제 대기 항목은 없다.**

| 승격물 | 내용 |
|---|---|
| `series.py` per-year 병합 폴백 | account_id 후보 → 계정명 정규식 순으로 **연도별** 회수, 부호 반전 키 abs 정규화. 이마트 15/24→**20/24 자동 회복**, 완결 키 감소 0본 (V-061 5회+) |
| `series.py` tax 파생 금지 | `pretax−ni`는 IFRS5 중단영업에서 깨진다 — 계속영업 실계정만. pytest가 재도입 차단 (V-105 ③) |
| `check_golden --strict` **§14** | anchor 자기정합 — `shared_keys`의 키를 `five.key`로 쓰는 카드의 `five.valley` == `anchor.valley_index` (V-107 C) |
| `check_golden --strict` **§15** | Zone C/E **헤드라인** 행 라벨 ≤22자(서브행 면제). T0 실측 21자 캘리브레이션 (V-103·V-106 A) |
| `check_golden --strict` **§10 개정** | **잔액 0 + 전용 캡션·전용 주석 → 무임계로 행 요구**. 소액(0<x<MAT_A)은 종전 임계 유지 (V-106 B) |
| `check_golden --links` | 패널 D ↔ 원문 BS 캡션 매칭 **실측**(게이트 아님 — 완주 보고에 N/N 기재) (V-104⑪) |
| `facts_lint.py` **신설** | fact-sheet 스키마 초과 키 · source_quote 원문 대조 · **순수 수치 파이프 행에서 단일 값 추출 경고**(열 밀림) · cols 합계 검산 (V-078·V-105🔧·V-107 A) |
| 계약 문서 | note-extractor 5항(다열 표 헤더-값 zip) · prose-writer **5-1항(합계 라인을 특정 사건 금액으로 쓰지 말 것, 3회째)** · WAVE2 체크리스트 **26·27항** |

---

## ▶ 다음 본 — 대한항공 003490 (5/8), S0부터 시작

### S0 프리플라이트 실측 (08-04, 이미 확인 — 재확인만)

```
sectioning health: OK ✅
series 19/24 · 미완성 5: capex · buyback · rnd · dsOp · eps
rcept_no 20260318001125 · 주석 46개(주1~46, 결번 0)
fs_account FY2025: BS 63 · IS 0 · CIS 30 · CF 118 · SCE 153
```

- ⚠️ **IS 0행 = 단일 CIS 회사**(V-011 동형). `sj_div` 가정 금지 — 조립·체커에서 `is→cis` 폴백은 자동이지만 **패널 B는 CIS에서 뽑아야** 한다. (이마트는 IS가 실존해 패턴이 갈렸으니 습관으로 가지 말 것.)
- ⚠️ **CF 118행·SCE 153행**은 Wave2 최다다. CF 세부가 많으면 `cf-*` 서브행 그룹핑에서 잔차 '그 외' 행 설계가 중요하다.
- **미완성 5키 처리**: `capex`·`eps`는 **per-year 병합 폴백이 이미 코드에 있으니** 그래도 안 되면 계정명 변이를 `series.ALT_NAME`에 추가하는 게 맞는지 먼저 보고. `buyback`·`rnd`·`dsOp`는 근거 없으면 `five=skip`(R6.9 방향A).

### 구조 가설 (S1에서 실주석으로 **확정** — 가설은 가설일 뿐)

- **리스 항공기·엔진**이 사용권자산·리스부채의 뼈대. 이마트 V-107③ 선례(리스부채가 BS 별도 행 없이 기타금융부채에 포함)를 **먼저 확인**할 것 — 있으면 `n{리스}` + hl 처방을 그대로 재사용.
- **마일리지 이연수익**(고객충성제도) — 이마트 `n27 포인트 이연수익`·`giftcard 상품권`과 같은 계열의 **선수금성 계약부채**. 규모가 크면 전용 카드(new-dive) 후보.
- **외화환산·유류 헤지** — 항공유·항공기 리스료가 달러라 환산손익과 파생이 크다. **위험회피회계는 현금흐름위험회피 한정으로 OCI 경유**(V-104⑦·V-107 n17 정정 2회 — 계약별 지정 내역이 주석에 없으면 "전 계약 CFH"라고 단정하지 말 것).
- 아시아나 인수 관련 **사업결합·영업권**이 있으면 그해 서사의 축이 될 수 있다. **합계 라인을 특정 거래 금액으로 쓰지 말 것**(체크리스트 26항).

---

## 실행

**[WAVE2_BATCH_PROMPT.md](WAVE2_BATCH_PROMPT.md)를 읽고 그대로 실행한다.** 진행 위치는 `git log --oneline -5`와 `corps.csv` tier(1=완주·1c=대기)로 파악.

### 이번 세션에 특히 달라진 점 (V-108 승격 반영)

1. **S1 직후 `python -m modules.report.facts_lint 003490` — ERROR 0 확인이 의무**. WARN(순수 수치 파이프 행에서 단일 값)은 눈으로 검토한다.
2. **note-extractor 호출 프롬프트에 항목 스키마를 예시와 함께 명시**할 것 — 이마트에서 이 방식으로 **8배치 1,705항목 드리프트 0**을 냈다(`{name, value, value_key, unit, period, source_quote, src}` + 다열은 `cols{}`).
3. **`--strict`에 §14·§15가 추가**됐다. 조립 직후 Zone C/E 헤드라인 라벨을 **22자 이하**로 잡고(T0 표준: `영업활동 자산·부채의 변동 (운전자본)` 21자 · `이자·법인세 실납부 등` 12자), `anchor.shared_keys`에 넣은 지표는 그 지표를 `five.key`로 쓰는 카드의 `valley`와 **같은 해**를 가리키게 할 것.
4. **완주 보고에 `check_golden 003490 --links` 수치를 넣는다**(이마트 44/44 선례).

### 완주 정의

```bash
python -m modules.report.facts_lint 003490                      # ERROR 0
python -m modules.report.check_golden 003490 --strict           # §1~§15 갭 0(무핀 0 포함)
python -m modules.report.check_golden 003490 --links            # 계정셀 링크 실측 → 보고
python -m modules.report.check_golden --all --strict            # 전 골든 무회귀(현재 16본 0)
GALAXY_TICKER=003490 python -m pytest tests/report/test_galaxy_interaction.py
python -m pytest tests/report/ -q                               # 현재 91 passed
```
\+ **accuracy-verifier REFUTED 0** · **completeness 삼성 T0 패리티** · **라이브 렌더 스윕**(클릭 사이 **Esc** 필수 · APPENDIX 나브 접힘 0@1440·1280·1024 · 콘솔 0)

완주 후: VARIATIONS 정본 §4에 **V-109부터** 채록(증상→원인→**게이트가 왜 못 잡았나**→처리) + 채록 로그 1줄 · `corps.csv` 1c→1 · `build_report_source.py 003490` · `build_galaxy_index.py` · **1커밋 push**(PR 금지). 승인 대기 없이 다음 본(크래프톤 259960)으로.

---

## 보고 규약 (컨텍스트 절약 — 리더 지시 2026-08-03)

- **착수** 1줄: `[티커/회사] S0: health OK · series N/24 · 주석 M개`
- **단계 전환** 1줄: `S1 fact N건 / S2 dive N장 / S3 산문 N카드`
- **게이트**: 숫자만 — `strict 0 · --all 17본 0 · accuracy REFUTED n건(정정) · links N/N · pytest 91 + 10/10`
- **완주**: 5줄 이내 + localhost URL
- **상세 보고는** ⓐ게이트 3회 미수렴 ⓑ리더 판단 필요한 구조 결정 ⓒ데이터 결함 ⓓ코드 승격 후보(2회+) **일 때만**
- **금지**: 파일 내용·JSON·카드 목록 덤프 · 카드별 산문 나열 · 진행 과정 서술 · 이미 문서에 있는 규칙 재설명

## 주의

- 인코딩 `PYTHONUTF8=1`. 로컬 서버 `python -m http.server 8000`.
- `reports.db`(shared/data/)·`facts/`·`raw_cache/`는 gitignore — `--strict` §7·§10·§13·`--links`·`facts_lint`는 **이 머신에서만** 유효(CI skip).
- **main 직접 push·force push 금지.** 커밋은 `feat/golden-wave2-industries`에만.
- 서브에이전트는 **self-contained 프롬프트**(대화 맥락을 못 봄) — fact 발췌·series·카드 키·견본 원문을 프롬프트에 직접 넣을 것.

## 잔여 리더 트랙 (이 브랜치 밖)

1. **T2 클러스터 확장** — 기존 12 + 신규 8클러스터의 나머지 기업(각 T1 견본 캐스케이드, §8.5). 별도 브랜치.
2. dead-click 2~3행 렌더러 버그(V-059) · 900px 나브 접힘(V-103) — 전 골든 동형·콘텐츠 무관, 렌더러 트랙.
