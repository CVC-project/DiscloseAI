# 다음 세션 프롬프트 — Wave 2 종료 후 트랙 선택 · 브랜치 `feat/golden-wave2-industries`

> 이 파일은 다음 세션에 붙여넣을 핸드오프다. 갱신: 2026-08-06.

## 🎉 현재 상태 — 섹터 20/20 완성

**골든 20본 전원 `--strict` §1~§19 갭 0.** 삼성 005930(T0) + T1 19사.
Wave 2 신규 산업 8본이 전부 끝났다 — 철강 004020(V-102) · 정유 010950(V-104) · 식품 097950(V-105) ·
유통 139480(V-107) · 항공 003490(V-109) · 게임 259960(V-111) · 엔터 352820(V-112) ·
**유틸리티 015760(V-113, 08-06)**. 8본 모두 **`--strict` 첫 조립 0**(retrofit 라운드 0)으로 완주했다.

- `WAVE2_BATCH_PROMPT.md`는 **삭제**했고, 반복 방지 체크리스트 29항은
  **[BUILD_CHECKLIST.md](BUILD_CHECKLIST.md)로 승격 이관**했다(신규 골든 착수 시 필독).
- 이번 세션에 **`check_golden --strict` §19 신설**(V-112 C 승격) + `facts_lint` 인코딩 수정.
- 확인 URL: `python -m http.server 8000` → `http://localhost:8000/integration/dossier/galaxy.html?ticker=015760`

## ✅ 리더 판단 대기 — **없음**

발견하면 채록하고 **고치는 데까지 간다**(V-110 교훈). 대기열에 넣는 건 ⓐ진짜 갈림길(작업 *순서* 등)
ⓑ리더만 아는 사업 판단일 때뿐이다.

## 🆕 직전 세션(한국전력 V-113)에서 새로 박힌 것 — 착수 전 필독

1. **viz가 0장이어도 `--strict` 19개 절이 전부 통과한다.** 산문 배치 프롬프트에 viz 지시를 빼먹었더니
   58장 전부 `why.viz=null`인 채 게이트 0이 나왔다(직전 골든은 25~39장). `VIZ_ITEM_FIELDS`(V-112 A)는
   **viz가 지정된 카드만** 보므로 '한 장도 없음'은 사각이다. → **S2 조립 때 viz를 코드로 배정**하고,
   완주 보고에 `viz N장`을 반드시 적을 것.
2. **`strings.intro_lines`는 정확히 2줄로 저작하라.** 렌더러는 `[0]`·`[1]`만 바인딩하는데 §16은 `≥2`만
   요구해, 3줄을 쓰면 3번째가 조용히 죽고 게이트는 0이다(V-109 C·V-110의 3회째).
3. **§19는 '창 밖 근거'만 차단한다** — `N ≥ 5`인데 `처음`·`첫` 표지가 없을 때만 발화하므로,
   **"2년 만에"처럼 창 안 거리로 잘못 센 서술은 못 잡는다**(한전 strings에서 실제로 통과, 실제는 3년).
   경과연수는 **series 배열로 손으로 재계수**하는 습관을 유지할 것.
4. **은닉 제4형** — 재무상태표가 금융/비금융 뭉치로만 묶여 개별 계정 자체가 없는 회사가 있다.
   차입금·사채 [129.77조]가 이름 없이 뭉치 안에 있었다. 처방은 뭉치 행 앵커 + `hl`, 또는 **흐름 행 앵커**
   (`n23`→`cf-fin-lease`, V-111③ 2회째). 패턴표 참조.
5. **S0 가설은 실주석이 반증한다(2회째)** — 핸드오프가 기타자본 [12.71조]를 신종자본증권으로 지목했으나
   실제는 **법률상재평가적립금**이었다. 가설을 산문에 그대로 실으면 REFUTED 확정이다.
6. **병렬 서브에이전트의 임시 스크립트는 고유 파일명으로** — 공용 스크래치에서 `build_facts.py` 같은
   범용 이름을 4명이 동시에 써 서로의 파일을 덮어썼다. 호출 프롬프트에 명시할 것(2회째면 계약 승격).
7. **모든 서브에이전트 호출 프롬프트에 이 한 줄을 유지할 것** (V-113에서도 재발 0):
   > 저장소 안의 파일을 삭제·이동하지 말 것. 임시 파일은 지정된 스크래치 경로에만 만들고, 정리도 하지 말 것.
8. **prose-writer에는 Write 도구가 없다**(`tools: Read`) — 산출물은 인라인으로 돌아오니 **출력 축약을
   프롬프트에 명시**하라(`what/links/lnote/why/five` + n카드는 `tag`/`amt`까지). note-extractor·
   accuracy-verifier·completeness-auditor는 Bash가 있어 파일 출력이 된다.

---

## ▶ 다음 트랙 — 셋 중 하나를 골라 착수 (리더 선택)

### 트랙 A. T2 클러스터 확장 (**별도 브랜치** 필수)
20클러스터의 나머지 기업을 각자 T1을 견본으로 캐스케이드(MILKYWAY §8.5).
현재 미작성 기업이 남은 섹터: **중공업방산 11사 · 2차전지화학 3 · 반도체 2 · 자동차 2 · 건설 2 ·
바이오 1 · 플랫폼 1 · 에너지소재 1**. 착수 전 `corps.csv`의 `cluster`·`tier`로 대상 확정.

### 트랙 B. 렌더러 트랙 (콘텐츠 무관 · 전 골든 동형)
1. **dead-click 2~3행**(V-059) — 그룹헤더 행에서 펼침 캐럿이 정중앙 클릭을 가로챈다. 처방 후보: 캐럿 `marginLeft:auto`.
2. **900px 나브 접힘**(V-103) — 1440·1280·1024는 전 골든 0이나 900px에서는 공통으로 접힌다.
3. **`five.valley`가 `anchor.label`을 그대로 찍는 문제**(V-111 B → strict 게이트 **기각 확정**) —
   실측 6본 12건이 정당한 불일치라 등식 강제 불가. 처방은 **dive별 `valleyLabel` 도입**.
4. **JOURNEY 하이라이트 데드존**(V-111 C) — 인터랙션 테스트가 결정론적으로 skip되는 구간.
5. **`intro_lines` 3번째 줄 바인딩**(V-113 B) — 게이트(`≥2`)와 렌더러(`정확히 2`)의 비대칭 해소.

### 트랙 C. 데이터 부채 정리
1. **`series.py` `gross` 실계정 승격 캐스케이드**(V-112 후속) — 파생 `revenue−cogs`가 실계정과 어긋나는 게
   **11본**(000660·000720·003490·005380·010130·011200·012450·033780·051910·097950·139480)에 퍼져 있고
   그 11본은 **k4 산문이 전부 옛 파생값을 인용**한다. 데이터+산문 동시 수리가 필요하다.
2. **viz 하한 게이트**(V-113 A) — `--strict`에 '흐름 dive 중 viz 지정 ≥ N'. **기존 골든 실측 후 임계 결정.**
3. **`strings.header`·`hero` 중복 저작 정리**(V-110 후단) · **`report_<t>.json` 완전성 계측**(V-109 사각 A).
4. **클러스터 미부여 2,596사** — `corps.csv`의 `cluster` 열은 55사에만 붙어 있다. 순수화학·제약·조선·
   미디어광고·호텔레저·기계 등은 **섹터 정의 자체가 아직 없다**(신규 클러스터 선정이 별도 과제).
5. **금융 8사·지주 4사 스코프아웃** — 계정 체계가 달라 별도 변형 템플릿 대상(MILKYWAY §8.5).

---

## 실행 규약 (트랙 A를 고른 경우)

선행 정본을 이 순서로 읽는다:
[MILKYWAY_GENERATOR.md](MILKYWAY_GENERATOR.md)(하네스) → [VARIATIONS.md](VARIATIONS.md)(S0 전체 정독) →
[BUILD_CHECKLIST.md](BUILD_CHECKLIST.md)(29항) → [.claude/skills/galaxy-golden/SKILL.md](../../.claude/skills/galaxy-golden/SKILL.md)

### S0 프리플라이트
```bash
export PYTHONUTF8=1
python -m modules.report.sectioner --health <ticker>
python -m modules.report.series <ticker>
python integration/dossier/build_report_source.py <ticker>   # 패널 C 소스(체크리스트 28항)
```

### 완주 정의
```bash
python -m modules.report.facts_lint <t>                 # ERROR 0
python -m modules.report.check_golden <t> --strict      # §1~§19 갭 0(무핀 0 포함)
python -m modules.report.check_golden <t> --links       # 계정셀 링크 실측 → 보고
python -m modules.report.check_golden --all --strict    # 전 골든 무회귀(현재 20본 0)
GALAXY_TICKER=<t> python -m pytest tests/report/test_galaxy_interaction.py
python -m pytest tests/report/ -q                       # 현재 219 passed, 3 skipped
```
\+ **accuracy-verifier REFUTED 0** · **completeness 삼성 T0 패리티** · **라이브 렌더 스윕**(클릭 사이 **Esc** 필수 ·
APPENDIX 나브 접힘 0@1440·1280·1024 · 1024px 가로 오버플로 0 · 콘솔 0 · **원문 TOC 전 주석 착지 실패 0** ·
**viz 박스가 실제로 그려지는지 눈으로 확인**)

완주 후: VARIATIONS 정본 §4에 **V-114부터** 채록(증상→원인→**게이트가 왜 못 잡았나**→처리) + 채록 로그 1줄 ·
`corps.csv` tier 승격 · `build_report_source.py <t>` · `build_galaxy_index.py` · 1커밋.

## 보고 규약 (컨텍스트 절약 — 리더 지시 2026-08-03)

- **착수** 1줄: `[티커/회사] S0: health OK · series N/24 · 주석 M개`
- **단계 전환** 1줄: `S1 fact N건 / S2 dive N장 / S3 산문 N카드`
- **게이트**: 숫자만 — `strict 0 · --all 20본 0 · accuracy REFUTED n건(정정) · links N/N · viz N장 · pytest 219 + 인터랙션 N/M`
- **완주**: 5줄 이내 + localhost URL
- **상세 보고는** ⓐ게이트 3회 미수렴 ⓑ리더 판단 필요한 구조 결정 ⓒ데이터 결함 ⓓ코드 승격 후보(2회+) **일 때만**
- **금지**: 파일 내용·JSON·카드 목록 덤프 · 카드별 산문 나열 · 진행 과정 서술 · 이미 문서에 있는 규칙 재설명

## 주의

- 인코딩 `PYTHONUTF8=1`. 로컬 서버 `python -m http.server 8000`.
- `reports.db`(shared/data/)·`facts/`·`raw_cache/`는 gitignore — `--strict` §7·§10·§13·`--links`·`facts_lint`는
  **이 머신에서만** 유효(CI skip).
- **main 직접 push·force push 금지.** T2 확장은 **별도 브랜치**에서.
- ⚠️ **세션 한도**로 서브에이전트가 중도 실패할 수 있다 — 실패하면 그 단계를 **직접** 수행하거나 재실행할 것.
