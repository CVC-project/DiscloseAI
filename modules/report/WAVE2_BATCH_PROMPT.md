# Wave 2 배치 프롬프트 — 신규 산업 T1 골든 8본 (브랜치 `feat/golden-wave2-industries`)

> **이 파일 전체가 각 빌드 세션에 붙여넣을 프롬프트다.** 1본 = 1세션 = 1커밋. 8본 완주 후 삭제.
> 선행 정본: [MILKYWAY_GENERATOR.md](MILKYWAY_GENERATOR.md)(하네스) · [VARIATIONS.md](VARIATIONS.md)(S0 필독) · [.claude/skills/galaxy-golden/SKILL.md](../../.claude/skills/galaxy-golden/SKILL.md)

## 목표

기존 12클러스터에는 전부 T1이 있다(삼성 T0 + T1 11본, 전원 무핀 0 완주). Wave 2는 **48사 밖 새 산업 8개**에
각각 첫 T1(구조·주석맵 견본)을 세운다. 구조는 언제나 **그 회사 사업보고서가 정의**하고(R6.9), 삼성 T0는 문체·깊이 기준이다.

**1차 T1과 다른 점 — 게이트를 처음부터 전부 켜고 빌드한다.** 1차는 무핀 계약(§12) 이전에 빌드돼
나중에 116건을 retrofit해야 했다(V-086~096, 11세션). Wave 2는 §8~§13을 처음부터 만족시켜 **retrofit 라운드를 없앤다**.

## 대상 8본 (순서 = 구조 난이도 오름차순, 앞 본의 변형을 뒤 본이 받는다)

| # | 티커 | 회사 | 신설 클러스터 | 구조 가설(S1에서 **확정**) |
|---|---|---|---|---|
| 1 | 004020 | 현대제철 | 철강 | 고로 원자재 사이클·재고 평가·운전자본형 −OCF 재검증(V-056 3회째면 승격) |
| 2 | 010950 | S-Oil | 정유 | 재고평가손익(유가 연동)·정제마진·원유 파생 헤지 |
| 3 | 097950 | CJ제일제당 | 식품 | 부문복합(식품/바이오/F&C)·해외 종속기업 다수·생물자산 가능 |
| 4 | 139480 | 이마트 | 유통 | **사용권자산·리스부채 거대**·저마진·부문(할인점/트레이더스/온라인) |
| 5 | 003490 | 대한항공 | 항공 | 리스 항공기·외화환산·**마일리지 이연수익**·유류 헤지 |
| 6 | 259960 | 크래프톤 | 게임 | cogs 구조 확인(플랫폼형 lump-opex면 V-010 대조)·무형·개발비 |
| 7 | 352820 | 하이브 | 엔터 | 무형(IP·음원)·선급금·부문(레이블/플랫폼)·종속기업 인수 이력 |
| 8 | 015760 | 한국전력 | 유틸리티 | 규제산업·대규모 차입·적자↔흑자 반전·공사부담금 이연수익(주27)·**48사 '에너지소재'에서 재배정**(제련 견본 부적합). 주16 괴물블록은 실제 거대 주석으로 검증 완료(아래 표) |

> 가설은 **가설일 뿐**이다 — S1 note-extractor로 그 회사 실주석에서 확정하라. 새 클러스터라
> `new-dive`(마일리지 이연수익·규제자산·재고평가·IP 등)가 다수 나온다: 원장 `new-dive:` 라우팅 + 신규 카드 생성이 **의무**(R6.9 방향B).

**데이터 상태(2026-08-03 실측 — Phase 2 완료)**: 8본 전부 FY2021~25 **5개년 원문 + 주석 섹셔닝 + fs_account 5개년 완비**(fs_enrich 완료, 841~1,564행).

| 티커 | series | 미완성 키 | S0 소견 |
|---|---|---|---|
| 004020 | 18/24 | capex·div·buyback·dep·rnd·dsOp | health OK |
| 010950 | 18/24 | sgna·buyback·dep·rnd·dsOp·eps | health OK |
| 097950 | 18/24 | sgna·buyback·dep·rnd·dsOp·eps | health OK |
| 139480 | **15/24** | **ocf·icf·fin·oci·tci**·buyback·dep·rnd·dsOp | ⚠️ CF 3활동 결측인데 **fs_account엔 CF 55행 실존**('재무활동현금흐름' 등) — **계정명/account_id 변이로 series 매칭 실패 = V-061 의심 2회째**. 빌드 세션에서 per-year 병합으로 골든 series 주입, 확인되면 **series 폴백 코드 승격**(2회 규칙) |
| 003490 | 18/24 | capex·buyback·dep·rnd·dsOp·eps | health OK |
| 259960 | **14/24** | **revenue·cogs·gross·sgna**·div·buyback·dep·rnd·dsOp·eps | ⚠️ **단일 CIS**(IS 0행, V-011 동형) + revenue 계정 변이('영업수익'류) — SKT(14/24)와 동급, 플랫폼형 lump-opex 유력(V-010 대조) |
| 352820 | 19/24 | div·buyback·dep·rnd·dsOp | health OK |
| 015760 | 20/24 | buyback·dep·rnd·dsOp | 괴물블록 주16(616k자)=**검증 완료, 실제 거대 주석**(종속·관계기업 목록 — 주1~47 연속·결번 0·이후 주석 전부 정상, 별도FS 유입 아님). health의 '의심' 플래그는 무시 가능 |

미완성 키는 R6.9대로 **five=skip 또는 dive 생략**이 기본이고, fs_account에 실값이 있는데 매칭만 실패한 키(이마트 CF류)만 per-year 병합으로 살린다.

## S0 — 프리플라이트 (착수 전, 생략 금지)

```bash
export PYTHONUTF8=1
python -m modules.report.sectioner --health <ticker>     # deep 포함: stale 꼬리 절단까지(V-100)
python -m modules.report.series <ticker>                 # 24키 완결률 — 미완결 키는 five=skip
```
- `--health` FAIL이면 **`section_all(['<ticker>'])` 재섹션 후 재검**(V-058·V-100). 괴물블록이면 별도FS 유입 의심.
- `VARIATIONS.md` 전체 정독 — 해당 층위(수집/구조/고유/포맷)의 기존 항목을 **이번 회사에 선제 적용**한다.
- 단일 CIS 회사(sj_div에 IS 없음, V-011) 여부 확인 — 조립·체커에서 sj_div 가정 금지.

## S1~S8 — 빌드 (`/galaxy-golden <ticker>` 또는 수동)

MILKYWAY §8.6 D1~D5 레시피를 그대로. 요약: fact 추출(note-extractor) → 결정론 골격 조립(panels·knots·CF분해·
dive 스켈레톤·routing_ledger 전 주석) → 산문(prose-writer, 카드 단위 병렬) → 게이트 수렴 → 원문 동반 생성(S8) → 채록(S7).

## ⚠️ 반복 방지 체크리스트 — 1차 T1 11본에서 실제로 터진 것들

**착수 시 1회, 산문 작성 후 1회 훑는다.** 각 항목 뒤 괄호는 발생 티커·횟수.

**수치·단위 (accuracy-verifier 적발 1위)**
1. **10배 오환산 = 최다 반복** (현대건설 7·HMM 2·한화 1·고려아연 1·SKT 1) — 주석마다 단위가 다르다(천원/백만원). `fact_mn`이 `unit` 필드를 읽게 하고 **고정 나눗셈 금지**(V-061). 카드 총계와 구성 합이 안 맞으면 100% 단위 사고다.
2. **flow vs stock 혼동** (HMM n15) — 취득액(당기 발생)과 기말잔액을 나란히 놓아 합계를 오인시키지 말 것.
3. **파생값 암산 금지**(R6.3-1) · **tci는 CIS 원값**으로(round(ni)+round(oci) ≠ round(ni+oci), V-061).
4. **링크 `a`값 = 패널 실값**, 부호 관례 유지(is-opex는 음수 표기 — SKT n19/n20 부호 누락 사고).

**계정 귀속·회계 사실**
5. **k15(기말현금)에 남의 계정 섞지 말 것** (HMM·한화·SKT 3회) — 사용제한 금융자산·단기금융상품은 현금및현금성자산이 **아니다**. "이 중"으로 서두를 열면 그 상위 계정에 속한다는 뜻이 된다.
6. **유동/비유동 혼동** (KT&G n6·고려아연 n11) — 선급비용·리스부채 등은 유동분만 보고 전체를 말하지 말 것.
7. **회계 사실 오류 4형** — 영업권은 상각 대상이 아니다(손상만, KT&G n11) · FVOCI는 금융**자산** 분류이고 부채는 상각후원가(LG n8) · IFRS5 중단영업손익 귀속(현대차 n8) · **인과 비약 금지**(한화 n7 "0원=팩토링 안 씀" → 실제는 위험·보상 이전 방식 문제; HMM n12 소멸된 전환권을 원인으로).
8. **주석 번호 오인용** (SKT n14·셀트리온 n3) — 인용 전 그 주번호의 실제 제목을 원문에서 확인.

**구조·라우팅 (체커가 잡지만 미리 알면 왕복이 준다)**
9. **`note_dive`는 `dives{}`만 타깃 가능** — appendix는 원장 직접 라우팅으로(SK V-087·셀트리온 V-093 2회).
10. **원장 `to` 화이트리스트**: `dive:cited`·`appendix:`·`row:`·`new-dive:`·`excluded` 접두만. `existing-dive:` 같은 임의 값은 즉시 차단(한화 V-096).
11. **`excluded`는 사실상 폐기**(V-075) — 정성·소액 주석도 관련 카드에 `(주N)` 한 구절로 연결.
12. **§10 잔액 주석은 무임계로 `dives` 승격** — 투자부동산·충당부채·순확정급여·이연법인세·관계기업 등은 APPENDIX에 두면 FAIL(SKT n13 실사례). APPENDIX는 **무앵커 주석 전용**.
13. **§11 착지 결정론** — `note_dive[N]=key`면 **그 카드 자신의 산문**에 `(주N)` 인용 필수. fuzzy 산문 스캔 재도입 절대 금지(R6.10).
14. **§12 무핀 0** — 전 주석이 카드/note_dive로 착지. `dive:cited`만으로는 무핀이다.
15. **§13 CF 운전자본 분리(신규 V-099)** — 본표에 '영업활동으로 인한 자산·부채의 변동' 집계 라인이 있으면 `cf-wc` 행 필수·값 대조. 없으면 강제 안 함(근거 부재).
16. **그림자 dive 금지**(V-053) — 두 dive가 같은 `row`를 공유하면 뒤엣것은 클릭 미도달.

**표기·문체**
17. **amt 6칙**(R6.6c) — 제목반복 금지·양면 병기·최소 수식어·서술 금지·순액 헤드라인 금지·다행 언급.
18. **행 라벨 = 원문 계정명**(R6.6a) — 의역·영문약어 축약 금지, 괄호 의역도 금지(허용: `(계)`).
19. **값 색 4칙**(A5) — 서브행 무채 기본, 의미 앵커만 예외.
20. **금칙어**: "매수"(→매입·인수: 염가**인수**차익, LG V-092)·"사상 최대"·투자조언류.
21. **APPENDIX도 실수치+링크**(V-048) — 숫자 없는 주석은 인접 실계정과 결과값(0원 포함)을 브래킷화(한화 n7 선례).
22. **부문 합 = 연결**(내부거래 정산 명시, 3회 반복) · 부문 영업이익 미공시면 매출총이익으로 정직 명기(V-053).
23. **viz_data 라벨 절단은 렌더 스윕만 검출**(현대차) — completeness 단계의 실브라우저 스윕을 건너뛰지 말 것.

## 완주 게이트 (티커마다 전부 PASS — 하나라도 FAIL이면 publish 금지)

```bash
python -m modules.report.check_golden <t> --strict     # §1~§13 갭 0 (무핀 0·BS앵커·착지·CF운전자본 포함)
python -m modules.report.check_golden --all            # 전 골든 무회귀
GALAXY_TICKER=<t> python -m pytest tests/report/test_galaxy_interaction.py
python -m pytest tests/report/ -q                      # 하네스 회귀(체커·섹셔너 테스트 포함)
```
+ **accuracy-verifier** REFUTED 0(신규·수정 브래킷 전수) + **completeness-auditor** 삼성 T0 패리티
+ **playwright 라이브 스윕**(원문 TOC 전 주석 클릭→기대 카드 착지, 승격 행 클릭, 콘솔 에러 0.
**클릭 사이 Esc 필수**(V-049), 캐시버스터 `&v=`)

## 완주 후 의무 (티커마다)

1. **S8 원문 동반**: `python integration/dossier/build_report_source.py <t>` → `report_<t>.json`
2. `python integration/dossier/build_galaxy_index.py` (매니페스트 — v2 3탭 자동 노출)
3. **VARIATIONS S7 채록** — **V-099부터 이어지는 단일 시퀀스**(신규 변형 없어도 '신규 변형 없음' 명시) + 채록 로그 1줄
4. `corps.csv`: `tier` `1c`→`1`
5. **1커밋 + push**(PR 없음 — 리더 지시). 패턴: `feat(golden): <회사> T1 완주 — <클러스터> 첫 대표 (V-1xx)`
6. **DL 게이트**: contact-sheet 스크린샷을 리더에게 제시(T1 승격 필수 관문, §8.5)

## 주의

- 인코딩 `PYTHONUTF8=1`. 로컬 서버 `python -m http.server 8000`.
- `reports.db`·`facts/`·`raw_cache/`는 gitignore(로컬 전용) — `--strict` §7·§10·§13은 로컬에서만 유효(CI skip).
- **main 직접 push·force push 금지.** 커밋은 `feat/golden-wave2-industries`에만.
- 원자성: 중간본을 `galaxy_<t>.json`에 두지 말 것 — 검증 통과본만 저장(R6.3-9).
