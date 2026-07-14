# 현금 은하수 생성기 — Milky Way Generator (하네스 정본)

> **무엇**: 한 기업의 사업보고서를 받아 `galaxy_<ticker>.json`을 **골든 품질**(체커 PASS + 감사 PASS + 렌더 0에러)까지 찍어내는 생성 하네스의 정본. 기업을 확장할 때마다 이 문서를 참조해 **일관·무오류**로 만든다.
> **실행**: `/galaxy-golden <ticker>` — 이 스킬이 아래 파이프라인·수렴 루프를 구동한다.
> **읽는 순서(새 세션)**: ① [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) ② [modules/report/CLAUDE.md](CLAUDE.md) ③ 이 문서 ④ 카피·스키마 세목은 [CASH_GALAXY_STYLE_GUIDE.md](../../integration/dossier/CASH_GALAXY_STYLE_GUIDE.md)·[GALAXY_JSON_SCHEMA.md](../../integration/dossier/GALAXY_JSON_SCHEMA.md).
> **산문은 Claude가 주석 원문을 직접 판독·작성한다 — 외부/GPU LLM 미사용.**

## 0. 한눈에

| | |
|---|---|
| **입력** | `modules/report/data/reports.db`(수집·분할된 5개년 사업보고서) + `series.py` 24키 시계열 |
| **출력** | `integration/dossier/data/galaxy_<ticker>.json` — 렌더러 `galaxy.html`이 그대로 읽는 정본 |
| **실행자** | `/galaxy-golden` 스킬(오케스트레이터) + 서브에이전트 4종 + `check_golden.py`(기계 게이트) + `test_galaxy_interaction.py`(동작 게이트) |
| **수렴 조건** | 5게이트 전부 PASS(§2). 하나라도 FAIL이면 publish 금지 |
| **사람 개입** | 산업 골든 승인(DL 게이트, §8)에만 — 나머지는 무인 |
| **골든 2본** | 삼성 005930(제조)·SK 000660(메모리) = **문체·깊이 견본 + 회귀 기준**. 구조 기준 아님(§4) |

> 선행조건: 그 티커가 `reports.db`에 수집·분할돼 있어야 한다(`report_section`에 주석 분할 존재). 없으면 `collector → sectioner → fs_enrich` 먼저. 표준 템플릿(제조·플랫폼)만 대상 — 계정 체계가 다른 금융·지주는 스코프아웃(§8).
>
> **S0 프리플라이트 게이트**: `python -m modules.report.sectioner --health <ticker>`가 PASS해야 착수. 주석 분할 붕괴(1주석)·괴물블록(>20만자, 별도FS 유입)·번호 결번 과다(하위번호 `N.M`·`N-M` 누락)를 **빌드 전에** 차단 — 이 셋은 note-extractor가 걸려 넘어질 때까지 어떤 게이트도 못 잡던 조용한 사고라 S0에서 못박는다. FAIL이면 sectioner 보강 후 재섹션.

## 1. 파이프라인 5단계 (S1~S5) — 각 단계: 생산자 → 기계검증 → 에이전트검증 → 실패 라우팅 (R6.1)

| # | 단계 | 생산자 | 기계 검증(코드 체커) | 에이전트 검증 | 실패 시 |
|---|---|---|---|---|---|
| **S1** | 숫자·표 | collector·sectioner·fs_enrich·series(코드) + **note-extractor**(주석 md 판독→fact JSON) | ① series 24키 완결률 ② **source_quote 원문 substring-match**(무환각 기계증명) ③ 정합 항등식: 매출−원가=총이익·ni+조정+운전자본=영업창출·창출−실납부=OCF·기초+순증=기말현금·자본워크 5행 합·자산=부채+자본 | 추출 누락 감사(실주석 목록 vs fact 커버) | sectioner 보강(옛 XML) 또는 재추출 |
| **S2** | 레이아웃 | assemble(fact→panels·knots·subrows·bsbar) | ① 렌더 스모크: 콘솔에러 0 + pv 표시 ② grp 서브행 합=부모(±0.2, 잔차 "그 외" 명시) ③ viz_data **viz별 스키마**(vSteps=rows·vWater=steps·vPuddle=ar/inv·vHBar=items·vChips=chips) ④ **기존 골든 무회귀**(pv 전값 비교) | ui-ux-reviewer: 3열·유입우/유출좌·펼침 동작 | assemble 수정(템플릿 손대면 반드시 컴파일+pv 스모크) |
| **S2.5** | 구조 확정 | — | 카드 목록을 **골든이 아니라 그 회사 데이터**로 확정(§4 보고서 기반) | — | 없는 항목 생략 / 고유 항목 new-dive 신규 생성 |
| **S3** | 산문(주석까지) | **prose-writer** — 입력: ⓐ골든 문체 견본(숫자·고유명 마스킹) ⓑfact-sheet(그 카드 허용 수치 화이트리스트) ⓒA7 카피 규칙. 카드 단위 병렬 | **prose-lint**(check_golden §2·§3): 브래킷 숫자 ⊆ fact-sheet·격식체·금칙어·연도오인·빈 브래킷·five cap 숫자≥1·타사명/타사수치 0 | — (검증은 S4) | 위반 카드만 재작성(전체 재생성 금지) |
| **S4** | 정확성 | — | 링크 a값=패널 v값·viz 내부 합 항등식·**파생수치 재계산 대조**(암산 금지) | **accuracy-verifier**(카드당 1, 적대적): 브래킷 수치를 fact·원문에서 재도출, 회계 서술 사실성 → 주장별 CONFIRMED/REFUTED | REFUTED 카드 → S3 재작성(fix_hint 첨부) |
| **S5** | 완전성 | — | check_golden: 커버리지(§4)·카드 4절 공란 0·**주석 라우팅 원장 전수**(§6)·깊이 지표(what≥2문장·카드당 브래킷≥3·콘텐츠 dive links≥2) | **completeness-auditor**: 골든 대비 "얕은 카드" 지목 + playwright 전 행 클릭 스윕(카드 열림·비지 않음) | 지목 카드 → S3, 구조 결손 → S1/S2 |

동작 QA(**S6**)는 §6. 각 단계 상세 손잡이는 `/galaxy-golden` 스킬(SKILL.md)에.

## 2. 수렴 루프 — 골든 품질까지 (실행 계약)

```
S1 → S2 → S2.5 → S3(전 카드)
repeat:
  gaps    = check_golden(ticker)                 # 기계 게이트 (구조·항등식·문체·깊이·원장)
  refuted = accuracy-verifier(변경·신규 카드만)    # 적대 게이트
  audit   = completeness-auditor(ticker)         # 깊이·주석 커버리지 게이트
  ui      = pytest test_galaxy_interaction.py    # 동작 게이트 (S6)
  regress = check_golden(기존 골든 전부)           # 무회귀 게이트 (템플릿 건드렸으면 필수)
  if 5게이트 전부 PASS: break                     # ← 골든 품질 도달, publish 허용
  각 실패를 소유 단계로 라우팅해 그 카드/구조만 수리:
    구조·패널·viz → S2 | 산문·수치·문체 → S3(fix_hint 동봉) | 추출 누락 → S1
until 카드별 3회 초과 → NEEDS_REVIEW.md(리더 큐)에 적고 다음 카드로
S7(채록): 이번 완주에서 발견한 편차를 VARIATIONS.md에 기록 — 신규 없으면 '신규 변형 없음' 1줄.
          publish는 5게이트 PASS + S7 채록까지 끝나야 완료로 친다.
```

- **루프 3층**(R6.2): ① 카드 루프(S3↔S4·S5, 위반 카드만) ② 기업 루프(`/galaxy-golden` 1호출 = 전 단계 완주) ③ 산업 확장 루프(§8).
- **발산 가드**: 같은 카드 3회 재작성 실패 → `modules/report/review/NEEDS_REVIEW.md`에 키·사유·이력 적고 진행.
- **원자성**: 중간본을 galaxy_<t>.json에 두지 말 것 — 스크래치 조립 후 **검증 통과본만** 저장(브라우저 캐시 오인 방지). 검증은 항상 fresh playwright.

## 3. 불변식 vs 변형 — Controlled Variation (R5)

**원칙**: 큰 틀(문법)은 고정, 내용이 채우는 슬롯만 규칙대로 변형. 변형은 회사별 수작업이 아니라 **같은 코드 경로**가 데이터에 따라 슬롯을 채운 결과 — 그래서 회사가 달라도 스타일이 못 튄다. 자유도마다 거동(grow/collapse/skip)과 경계를 못박아 "자유자재"가 "제멋대로"가 되지 않게 한다.

| 영역 | 불변식 (일관성) | 변형 자유도 (적응성) | 변형 거동·경계 |
|---|---|---|---|
| **은하수 SVG** | spineX 0.48·직교 라우팅·굵기 2단·**유입 우/유출 좌**·기초·기말 저수지 앵커·본류 매듭 순서(A3) | 중간 매듭 유무·지류 개수·지류 길이 | 없는 매듭은 생략(빈 자리 금지)·지류는 항상 올바른 쪽·본류 끊김 없이 재연결 |
| **재무 5패널** | 5존(A~E)·CF 3활동 동등위계·자본변동표엔 자본변동만·**합계 정합 철칙(A6)** | 존별 행 유무·개수·결측 계정(예: cogs 없음)·펼침 group 수 | 없는 행 생략(placeholder 금지)·하위 합 잔차는 "그 외 ±0.x조"로 흡수·대분류=하위합 항상 성립 |
| **딥다이브 카드** | 카드 골격(what/links/why/five)·색 배지·sticky·억지 매핑 금지(A0) | 카드 총수·viz 분포·five=skip 비율·links 개수 | 주석이 유기적일 때만 카드 채택(padding 금지)·미완성 시계열은 five=skip(빈 차트 금지) |
| **APPENDIX** | 하단 위치·한 줄 요약(what/why, five=skip) | 항목 개수(회사마다 다름) | 리스트가 개수대로 늘고 줆·형식 동일 |
| **5개년 차트** | A11(당해 강조·valley·zero선·"5년 새 최대"만) | vLine/vTwin/skip·음수 구간 유무 | 데이터 완결 시만 렌더·미완결 skip·타입은 콘텐츠가 결정(LLM 선택 금지) |
| **셸·토큰** | 3열 그리드·색=의미(A2)·폰트·엣지·반응형 CSS var | (회사 무관 — 고정) | — |

- **변형 상한 = 표준 템플릿이 흡수하는 데까지.** 계정 체계가 근본적으로 다른 금융·지주는 변형이 아니라 **별도 템플릿**(§8 스코프아웃). 하나의 템플릿을 억지로 늘려 은행 재무제표까지 담지 않는다.
- **강제 방법**: 불변식은 `check_golden` L0 규칙이 골든·전사에 검사(위반 0). 변형 거동(생략·skip·잔차 흡수)은 생성기가 **규칙으로** 실행 — 회사별 예외 분기 금지.

## 4. 보고서 기반 원칙 — 골든은 문체 견본, 구조는 사업보고서가 정의 (R6.9)

- **방향A (골든에 있고 회사에 없음)**: 골든에 있어도 그 회사 보고서에 근거(series 완결·주석·패널 행)가 없으면 그 항목은 **아예 생략** — 0/— placeholder 표시 금지. check_golden §1이 "근거 없는 dive 존재"를 FAIL로 잡는다(기대 집합 = REQ_SERIES(series 근거) ∪ COND_ROW(행 근거), 골든 참조 없음). 억지 인용은 **유령 인용 검사**(실주석에 없는 주N)가 적발.
- **방향B (회사에만 있음)**: 그 회사 고유 주석은 원장(§6)이 MISSING으로 노출 → `new-dive:<key>` 라우팅 + **신규 카드 생성**(패널 행·A7/A8 문법 산문·데이터 받쳐주면 viz)이 의무. §7이 "new-dive 미생성"을 FAIL로 잡는다. 골든 밖 신규 dive는 커버리지 위반이 아니다.
- 회귀: `tests/report/test_report_driven.py` 4케이스(cogs 없는 가상사에서 k3 비요구 · 근거 없는 k3 존재 시 FAIL · 신규 dive 허용 · 양 골든 무회귀). **4/4 PASS**.
- 함의: 산업 골든은 구조 레지스트리가 아니라 **문체·깊이 견본 + 회귀 기준**. 구조는 언제나 그 회사 사업보고서가 정의한다(§3 Controlled Variation의 체커 강제형).

## 5. 실수 방지 규칙 10 — 이 하네스의 헌법 (R6.3)

세션 복기에서 뽑은, 재발 방지를 위해 루프에 박아 넣은 규칙:

1. **파생 수치 암산 금지** — 비현금조정 +19.7(암산)→+18.8(원문 재합산) 사고. 모든 파생값은 S1 항등식 체커가 계산·검증.
2. **source_quote substring-match** — "원문에 그 문자열이 실제로 있는가"가 무환각의 기계 증명.
3. **산문 숫자 화이트리스트** — 브래킷 숫자 ⊆ fact-sheet. few-shot 누출(타사 세율·타사명)의 구조적 차단.
4. **템플릿 수정 = 컴파일+pv 스모크 동반** — 괄호 1개 누락이 클래스 eval 전체를 죽여 renderVals까지 침묵 붕괴한 사고. 수정 후 즉시 "매출액 보이는가" 스모크.
5. **렌더 검증은 "카드가 열리고 내용이 비지 않는가"까지** — diveCard가 links 없어 throw→빈 카드 사고. JSON 존재 ≠ 렌더 성공.
6. **체커 규칙 파라미터화** — 어떤 주번호는 한 회사 잔재였으나 다른 회사의 정당 주번호. 잔재 스캔은 회사별 화이트리스트로.
7. **viz_data는 viz별 스키마 선검증** — steps/rows 형식 불일치로 빈 박스 렌더 사고.
8. **잔차는 명시적 "그 외" 행** — 합계 정합 철칙(A6)의 실행형.
9. **원자적 쓰기·최종본만 커밋** — 이터레이션 중간본이 브라우저 캐시로 노출돼 "깨진 화면" 오인 사고.
10. **방어적 렌더러 유지** — 불완전 JSON 1개가 전체 뷰어를 죽이지 않게(getter 기본값+빌더 try/catch). 단, 조용한 degrade는 체커(규칙 5)가 잡는다.

## 6. 주석 라우팅 원장(R6.6) · 인터랙션 QA(R6.7)

**주석 라우팅 원장** — "모든 실주석이 처리됐는가": 그 회사 사업보고서의 **실주석 전수**(reports.db 기준)가 `meta.routing_ledger`에 매핑돼야 한다 — `dive:cited`(본문 인용)·`appendix:nX`·`row:<id>`(패널 행)·`new-dive:<key>`(고유 항목 신규)·`excluded`(+reason 필수). check_golden §7이 원장 누락·MISSING·사유 없는 제외·**유령 인용**(실주석에 없는 주N — corp.rcept_no 기준)·appendix 미실존·new-dive 미생성을 전부 FAIL로 잡는다.

**S6 인터랙션 QA** — `tests/report/test_galaxy_interaction.py`(playwright, `GALAXY_TICKER` 환경변수): ①A9-② 제스처당 정거장 ≤1칸(**정거장 좌표계=knots 순서**로 측정 — DOM 행 좌표계는 오탐) ②A9-③ 450ms 유휴 후 단번 재동기화 허용 ③스크롤 멈춤 없음 ④핀→Esc 해제 ⑤펼침 토글 왕복 ⑥APPENDIX 카드 본문 비지 않음 ⑦1024px 가로 오버플로 0 ⑧콘솔 에러 0. 오라클은 스타일가이드 자구 수준으로 정밀해야 오탐 없이 진짜 버그(멈춤·씹힘·다중 전환)를 잡는다.

## 7. 모델 티어링 — 비용 효율화 (R6.8)

| 작업 | 실행자 | 모델 | 근거 |
|---|---|---|---|
| 수집·분할·series·체커·항등식·렌더 스윕·인터랙션 QA | **코드**(pytest·check_golden) | — | 결정론·무료 — 최대한 코드로 |
| S1 note-extractor / S5 completeness-auditor | 서브에이전트 | **sonnet** | 표 판독·대조 위주(창의성 불요) |
| S3 prose-writer / S4 accuracy-verifier | 서브에이전트 | **상속(최상위)** | 골든 깊이 산문·적대 검증 = 품질 병목, 여기만 고급 모델 |
| 오케스트레이션(`/galaxy-golden`) | 메인 세션 | 상속 | 판단·라우팅 |

절감 장치: 카드 루프는 **위반 카드만** 재작성 · fact-sheet 캐시(재추출 불요) · 렌더/문체/정합은 전부 코드 체커가 선차단해 에이전트 호출 최소화.

## 8. 자산 지도(R6.5) · 산업 확장(R6.2 ③)

| 자산 | 역할 |
|---|---|
| collector·sectioner·fs_enrich·series(+pytest 20) | S1 코드 생산자 |
| 삼성·SK 골든(체커 PASS) | 제조·메모리 클러스터 문체 견본·회귀 기준 |
| check_golden.py | S4·S5 기계 게이트(회사 파라미터화) |
| galaxy.html 데이터 구동(pv·sub·bsbar·appendix)+방어 렌더 | S2 렌더러 |
| `/galaxy-golden` 스킬 + 서브에이전트 4종(note-extractor·prose-writer·accuracy-verifier·completeness-auditor) + ui-ux-reviewer 재사용 | 오케스트레이션·검증 |

**산업 확장 루프**: ① report_section 주석 타이틀 시그니처로 48사 **기계 클러스터링**(제조/메모리/플랫폼/바이오…) ② 클러스터당 대표 1사를 **산업 골든**으로 — 여기만 리더 **DL 게이트**(contact-sheet 스크린샷 승인: 같은 템플릿이 변형 축 전부에서 "틀 유지 + 슬롯만 변형"인지 눈으로 판정) ③ 승인된 산업 골든이 그 클러스터의 문체 견본·주석맵이 되어 나머지 기업 자동 확장(전 체커 PASS 필수, 실패는 리뷰 큐).

**스코프아웃**: 계정 체계가 다른 **금융·지주(16~18사)**는 표준 템플릿 변형이 아니라 별도 변형 템플릿 대상 — 지금은 "준비 중"으로 제외(`series` 완결 0~수 개면 `/galaxy-golden`이 중단·보고).

## 9. 변형 레지스트리 — 자기 기록으로 전 기업 커버 ([VARIATIONS.md](VARIATIONS.md))

**원칙**: 기업을 만들 때 마주치는 편차는 그때그때 고치고 끝이 아니라 **채록이 파이프라인의 일부**다. 리더 지시 없이도 하네스가 스스로 기록한다 — 누적 레지스트리가 곧 "모든 기업 커버"의 지도.

- **S0(착수 전 읽기)**: 새 티커 착수 전 VARIATIONS.md 전체를 읽고, 해당 층위(수집/구조/고유/포맷) 기존 항목을 이번 회사에 선제 적용·점검한다.
- **S7(완주 후 쓰기)**: 완주마다 ① 새 편차를 V-### 항목으로 채록(증상→원인→처리→적용 범위) ② 채록 로그 표에 회사 1줄 추가 — **신규 변형이 없어도 '신규 변형 없음'을 명시**(빠뜨림과 무발견을 구분). 이게 없으면 완주가 아니다.
- **승격 규칙**: 같은 패턴 **2회 이상** → 레지스트리에 머물지 말고 코드·체커·스키마로 승격(`→ 코드화` 표기). 1회짜리 기업 고유 사건(③층)은 코드화하지 않고 레지스트리+해당 galaxy JSON에만 반영.
- **층위**: ①수집·분할(sectioner류 — 대부분 즉시 코드화) ②계정 구조(산업 클러스터 — 2회 확인 시 assemble 규칙화) ③기업 고유(일회성 사건·특수 항목 — 산문·차트 주의사항) ④문서·데이터 포맷(단위·번호 체계 — 계약·체커에 반영).

## 부록. 확장 로드맵·미결정

- **held-out 일반화 증명 = NAVER(035420)** — 삼성(제조)과 가장 이질적인 플랫폼(cogs 결측). 플랫폼 클러스터 산업 골든 후보. 프롬프트·임계 캘리브레이션에 **사용 금지**(오염 방지).
- **원문 공유**: 로컬 `modules/report/data/`(raw_cache·reports.db는 gitignore, DART 키로 재현) + publish JSON만 커밋. 800사 원문(~1~2GB) 보관 채널은 그때 재검토.
- **코스피 ~800사 대비(지금 공짜로 심을 것)**: publish JSON minify · 유일 공급 관문 `pull_report_json.py` 유지 · 스코프아웃 명단 `corps.csv scope_hint` 열 · manifest(`galaxy_index.json`) 탭 활성화. 나중에: DB Postgres 이전·LFS·임베딩 문체 게이트·KOSDAQ 시드.
- **리스크**: 토큰 폭주(위반 카드만 재작성+fact 캐시로 억제) · NEEDS_REVIEW 과반(실패 클래스 진단→임계 재캘리→부분 재생성) · held-out 오염(프롬프트에 NAVER 유입 금지).
