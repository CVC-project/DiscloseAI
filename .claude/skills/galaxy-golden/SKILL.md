---
name: galaxy-golden
description: 한 기업의 galaxy_<ticker>.json을 골든 품질(체커 PASS + 감사 PASS)까지 S1~S5 루프로 완주시키는 드라이버. GPU 미사용 — note-extractor·prose-writer·accuracy-verifier·completeness-auditor 서브에이전트 오케스트레이션.
auto-invocable: false
---

# /galaxy-golden <ticker> — 기업 골든 루프 (MILKYWAY_GENERATOR)

한 기업을 **사업보고서 추출 → 레이아웃 → 산문 → 정확성 → 완전성**의 5단계로 완주시킵니다.

## 수렴 루프 (골든 품질까지 — 이 의사코드가 실행 계약)
```
S1 → S2 → S2.5 → S3(전 카드) → S8(원문 동반 — build_report_source.py <t>)
repeat:
  gaps = check_golden(ticker) --strict            # 기계 게이트(§8 원문 정합·amt·승격 .row 포함, V-068·069)
  refuted = accuracy-verifier(변경·신규 카드만)     # 적대 게이트
  audit = completeness-auditor(ticker)            # 깊이·주석 커버리지 + 삼성 T0 패리티 게이트
  ui = pytest test_galaxy_interaction.py (S6)     # 동작 게이트
  regress = check_golden(기존 골든 전부)            # 무회귀 게이트(템플릿 건드렸으면 필수)
  if 전부 PASS: break                              # ← 골든 품질 도달
  각 실패를 소유 단계로 라우팅해 그 카드/구조만 수리:
    구조·패널·viz → S2 | 산문·수치·문체 → S3(fix_hint 동봉) | 추출 누락 → S1 | 원문 오라벨 → S8(생성기)
until 카드별 3회 초과 → NEEDS_REVIEW.md(리더 큐)에 적고 계속
종료 = 5게이트 전부 PASS (하나라도 FAIL이면 절대 publish 금지)
```

> **V-062~069 캐스케이드 계약(신규·T1 필수)** — 골든은 **사업보고서 원문 포함**이 기본이다. 실체 주석(패널 행 있음)은 `appendix`가 아니라 `dives{}`에 **키 `n<그회사 주번호>`**로 승격하고 **`row`(주 앵커)+`hl`(발광 행)**을 선언(V-069 — 삼성 정적 테이블 건드리지 말 것). 코어 dive 흡수 주석은 `meta.note_dive`. amt는 **6칙**(R6.6c), 서브행 색은 **무채 기본**(A5 값색 4칙). ⚠️ **승격 판정 = fs_account BS 실계정 유무(V-082)** — 충당부채·순확정급여·이연법인세·투자부동산·사용권자산·관계기업 등 실계정(material ≥0.05조·전용 주석)은 **패널 행을 신설해서라도** 앵커하고 승격(잔차 흡수·부록 잔류 금지). ⚠️ **주석 라우팅 = R6.10(V-084)** — 클릭 착지는 저작된 경로(n{N}·note_dive·원장 명시타깃)로만 결정된다. **산문 "(주N)" fuzzy 스캔 폐기**(오핀 근절): `dive:cited`는 진짜 홈이면 `note_dive` 저작(대상 카드 자기 산문이 주N 인용), 포인터성이면 **무핀**(원문만, 삼성 T0 계약). 절차 상세 = **MILKYWAY §8.6**(D1~D5). `check_golden --strict`가 원문 정합·amt·승격 구조·**§10 BS 실계정-행-앵커·§11 주석 착지 결정론·§12 무핀 0(삼성 T0 패리티)**을 기계 검출한다. ⚠️ **§12: 전 주석이 카드/딥다이브로 착지해야 완주**(무핀=원문만 뜨는 주석 0). 무핀은 전용 카드 승격(new-dive:n{N}+산문) 또는 note_dive 연결로 해소(V-085).

> ⚠️ **subagent 프롬프트는 self-contained** — 에이전트는 이 대화를 못 봅니다. fact-sheet 발췌·골든 견본 원문·series 배열·카드 키를 **프롬프트에 직접 포함**해 호출하세요.
> ⚠️ **R6.3 규칙 10**이 이 스킬의 헌법입니다([MILKYWAY_GENERATOR.md](../../../modules/report/MILKYWAY_GENERATOR.md) §5). 특히: 파생수치 암산 금지 · 템플릿 수정 시 컴파일+pv 스모크 · 원자적 쓰기(최종본만 저장).

## S0 프리플라이트 게이트 (먼저 통과해야 착수)
- **정본 계층 확인(R8, MILKYWAY §8.5)** — `modules/report/data/corps.csv`에서 이 티커의 `cluster`·`tier`를 본다. **T2면 같은 클러스터 T1(산업 골든)을 구조·주석맵 견본으로** 삼고(T0 삼성은 문체 기준), `tier=scope-out`(금융·지주)이면 중단·보고. T1 착수(리더 DL 게이트)면 그 클러스터의 견본을 새로 세우는 것.
- **[VARIATIONS.md](../../../modules/report/VARIATIONS.md) 먼저 읽기** — 기존 채록(수집 버그·산업 구조·기업 고유·포맷)을 이번 회사에 선제 적용. 예: 하위번호 주석(V-002)·단위 혼재(V-030)·플랫폼 손익(V-010).
- **`python -m modules.report.sectioner --health <ticker>` PASS 필수** — 주석 분할 붕괴·괴물블록·번호 결번(하위번호 누락)을 빌드 전 차단. FAIL이면 sectioner 보강 후 `section_all([ticker])` 재섹션. (이번 세션 3종 조용한 사고의 자동 게이트 — MILKYWAY_GENERATOR §0.)

## 사전 조건 (아니면 먼저 해결)
- `modules/report/data/reports.db`에 그 티커의 수집·분할 완료(`report_section`에 note_no 분할 존재). 없으면: `python -m modules.report.collector` → `.sectioner` (옛 XML 포맷이면 sectioner 보강부터).
- `python -m modules.report.series <ticker>` 완결률 확인 — 표준 템플릿 회사(제조·플랫폼)만 진행. 완결 0~수 개(금융·지주)는 D10 스코프아웃: 중단하고 보고.
- 렌더 확인용 `python -m http.server 8000` 기동.

## S1 — 숫자·표 (fact-sheet)
1. **note-extractor** 호출(핵심 주석부터: 판관비·부문/품목·법인세·유형자산·차입·배당·CF·EPS·자본·충당·우발·후속 + 그 회사 대형 주석). 출력: `modules/report/data/facts/facts_<ticker>.json`.
2. 기계 검증: source_quote가 원문 text_md에 실제 substring인지 스크립트로 전수 대조. 불일치 항목은 재추출.
3. series + fact로 항등식 사전 검산(매출−원가=총이익 등 — check_golden §4와 동일식).

## S2 — 레이아웃 (panels·knots·서브행)
1. 골든 골격 재투영 + fact 기반 서브행(grp) 구성 — 잔차는 "그 외/기타 (잔차 포함)" 행으로 **명시**.
2. 렌더 스모크: fresh playwright로 콘솔 에러 0 + `is-revenue`에 실값 표시(pv 생존 확인) + **삼성(005930) 무회귀**.
3. galaxy.html을 만졌다면: 수정 직후 반드시 스모크(괄호 1개가 클래스 eval 전체를 죽인 전례).

## S2.5 — 보고서 기반 구조 확정 (R6.9, 골든 흉내 금지)
카드 목록은 **골든이 아니라 그 회사 데이터**가 정의합니다 (check_golden §1이 강제):
- **골든에 있는데 이 회사에 없음**(series·주석 근거 부재) → 카드·매듭·행 **생략** — 0/— placeholder 절대 금지.
- **이 회사에만 있음**(원장 MISSING으로 노출) → 원장에 `new-dive:<key>` 라우팅 후 **신규 카드 생성**: 패널 행 추가(S2) + prose-writer에 견본 없이 A7·A8 문법으로 작성 지시(S3) + 데이터가 받쳐주면 viz 배정. 신규 매듭이 필요하면 은하수 SEGS 위상은 kind 규칙(R2 side 결정)으로 파생.

## S3 — 산문 (카드 수는 S2.5가 확정 — 골든 41장은 상한이 아니라 참고)
1. 카드마다 **prose-writer** 호출 — 프롬프트에 ⓐ그 카드의 fact 발췌(화이트리스트) ⓑseries 배열 ⓒ골든 같은 카드 원문(견본) ⓓ카드 키·row·주번호를 포함. 독립 카드는 병렬 호출 가능.
2. 반환 JSON을 galaxy_<ticker>.json의 dives/appendix에 병합. knots.story = 해당 dive what[0] 동기화.
3. viz는 코드가 배정: 데이터가 받쳐주는 것만(vHBar=세부표 있음, vSteps=정산 검산 완료, vWater=기초→기말 roll, vChips=등식). viz_data는 렌더러 실형식(vSteps=rows·vWater=steps·vPuddle=ar/inv).

## S4 — 정확성 (적대 검증)
1. 카드마다 **accuracy-verifier** 호출(카드 JSON + fact 발췌 + series 동봉).
2. REFUTED 카드만 → fix_hint를 붙여 S3 prose-writer 재호출(전체 재생성 금지).
3. 기계층: `python -m modules.report.check_golden <ticker>` — FAIL 갭도 같은 방식으로 라우팅(구조 갭은 S2, 텍스트 갭은 S3).

## S5 — 완전성 (최종 게이트)
1. **completeness-auditor** 호출(ticker + 골든 기준 명시).
2. shallow 카드 → S3 재작성, uncovered_notes → S1 추가 추출 후 해당 카드 보강, render 이슈 → S2.
3. 종료 판정은 상단 **수렴 루프 의사코드**의 5게이트(check_golden·verifier·auditor·S6 인터랙션·기존 골든 무회귀) 전부 PASS.

## S7 — 변형 채록 (완주의 마지막 의무)
완주마다 `modules/report/VARIATIONS.md`에 ① 새 편차 V-### 항목(증상→원인→처리→적용 범위, 2회 반복 패턴은 코드로 승격) ② 채록 로그 표 1줄 — **신규 없어도 '신규 변형 없음' 명시**. 채록 없이는 완주 보고 금지. VARIATIONS.md는 galaxy JSON과 같은 커밋에 포함.

## 루프 규율
- **카드 루프 상한 3회**: 같은 카드가 3회 재작성에도 실패하면 `modules/report/review/NEEDS_REVIEW.md`에 카드 키·사유·시도 이력을 적고 다음 카드로(리더 큐).
- 중간본을 galaxy_<ticker>.json에 두지 말 것 — 스크래치에서 조립해 **검증 통과본만** 저장(브라우저 캐시 오인 사고 방지).
- 완료 시: PASS 리포트(체커 결과·항등식·스크린샷 경로) 요약 + git 커밋은 galaxy_<ticker>.json + **VARIATIONS.md(S7 채록)**(fact·review는 비커밋 — .gitignore 확인).

## 산업 확장 (별도 호출)
새 산업(주석 구조가 다른 클러스터)의 **첫 회사**는 완주 후 리더 DL 게이트(contact-sheet 승인)를 거쳐 산업 골든으로 승격 — 이후 같은 클러스터는 그 골든을 견본으로 이 스킬을 반복.
