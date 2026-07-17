# 다음 세션 프롬프트 — T1 골든 잔여 완성 (브랜치 `feat/report-phase5`)

> 이 파일 전체가 **새 세션에 붙여넣을 프롬프트**다. 잔여 5본 완주 후 갱신/삭제.
> 시작점 커밋 `72c13d7`(V-076, origin 푸시됨). `git log --oneline -8`로 최신 확인.

## 지금 상태 (2026-07-17)
- **골든 완주 9본**(`check_golden --all` 0): 삼성 005930(**T0 정본**) + **V-062~069 삼성패리티** SK 000660·LG 051910·현대차 005380·셀트리온 068270·NAVER 035420(V-070~075)·**한화에어로 012450(V-076, 이번 세션)** + **구표준(V-056~061, 패리티 미달)** 현대건설 000720·고려아연 010130.
- 직전 세션: **한화에어로 012450 첫 "처음부터 빌드" 완주** — 첨부정정 원본 복구(정정대상=영업보고서뿐, 원본 rcept 20260316001112), **collector `final=False` 근본수정=코드 전사**(이후 첨부정정 회사 자동 복구).

## 목표 = 잔여 골든 최종 완성 (2종)
1. **미착수 3본 — 처음부터 빌드**(012450 레시피 그대로): **SKT 017670**(통신)·**HMM 011200**(해운)·**KT&G 033780**(소비재).
2. **구표준 2본 — V-062~069 패리티 uplift(캐스케이드 §8.6)**: **고려아연 010130**·**현대건설 000720**(galaxy JSON은 있으나 원문 3-way·승격 dive·값색·amt 6칙 미반영).

## 먼저 읽기 (순서)
1. `modules/report/MILKYWAY_GENERATOR.md` — **§8.6**(캐스케이드 D1~D5)·**§6**(R6.6a~d 3-way·amt 6칙·값색·원문 라우팅)·**§8.5**(정본 계층).
2. `modules/report/VARIATIONS.md` — **V-062~076 정독**(특히 **V-076=012450 처음빌드 레시피** + V-070~075 캐스케이드 교훈).
3. 메모리 `t1_batch_data_state`·`phase4_milkyway_build_state` — 데이터 결함·collector fix·완주 상태.
4. `modules/report/T1_BATCH_PROMPT.md` — 회사별 구조 가설(§ 남은 배치 순서).

## 회사당 절차 = `/galaxy-golden <ticker>` (또는 수동 S0→S8→수렴)
- **S0**: `python -m modules.report.sectioner --health <t>` PASS · `python -m modules.report.series <t>` 완결률 · corps.csv tier. ⚠️ **데이터 준비 먼저 확인** — 미수집/구섹션이면 `collector`→`section_all([t])`(collector는 이제 첨부정정 자동 복구). ⚠️ **raw XML 최대주번호 vs DB 대조**(tail 절단·법인세/EPS 노트 존재).
- **S1**: note-extractor → `facts_<t>.json`(source_quote 전수 substring 검증). ⚠️ **후속사건·사업결합 표는 열(취득/양도/대상법인)을 정확 매핑**(V-076 교훈 — 012450 n47 KAI/한화오션 4.99% 오귀속이 원천 오매핑이었음).
- **S2**: 결정론 골격(현대차 005380/012450 템플릿 재투영, fs_account+series+facts). 패널 A~E·knots 17·CF분해(cf-noncash·cf-wc·cf-paid)·자본워터폴·dive 골격·routing_ledger(전 주석 3-way)·note_dive·appendix. ⚠️ **패널 행라벨 정확**(bs-e-1 비지배 vs bs-e-2 이익잉여금 — V-076 링크 오앵커 교훈)·소계행 `(계)`·자본/부채 항목이 자산존 grp에 섞이지 않게.
- **S2.5**: 보고서기반 new-dive — **HMM=운임/용선료·컨테이너**·**SKT=네트워크 설비/마케팅비**·**KT&G=담배(국내/수출)·건강기능(정관장)·부동산 부문**. 신규 카드는 고유 앵커(그림자 dive 금지 V-053).
- **S3**: 카드별 prose-writer 6배치 병렬. **프롬프트 self-contained**(정확한 행라벨·amt·series 배열·facts 발췌·골든 견본). amt 6칙(R6.6c)·값색 4칙(A5)·what 2문장+실수치 브래킷·links≥2·five(series 있으면 key). 반환 JSON은 구조 앵커(row/hl/note_no/badge) 보존해 병합.
- **S8**: `python integration/dossier/build_report_source.py <t>` → report_<t>.json(단일 CIS 회사는 4본 bs/cis/eq/cf).

## 수렴 5게이트 (회사마다 전부 PASS)
- `check_golden <t> --strict` 0(§8 원문·amt·승격·§9 bottom-up 커버리지) · `check_golden --all` 0(무회귀)
- **accuracy-verifier**(브래킷 원문 재도출, REFUTED 0) · **completeness-auditor**(삼성 T0 패리티·얕은카드·렌더 스윕, NEEDS_WORK면 S3 수리)
- `GALAXY_TICKER=<t> pytest tests/report/test_galaxy_interaction.py` 9/9 · 라이브 스윕(클릭 사이 **Esc**, 콘솔 0)

## 완주 후무 (회사마다)
1. VARIATIONS **V-### 채록**(증상→처리→교훈, 신규 없어도 명시) + 채록 로그 1줄
2. corps.csv `tier` `1c`→`1`(구표준 uplift는 이미 1)
3. `python integration/dossier/build_galaxy_index.py`(제품 등록)
4. **커밋**(golden_<t>.json + report_<t>.json + report_index + galaxy_index + VARIATIONS + corps) + **push** + DL 스크린샷(리더 시각승인)

## 회사별 구조 가설 (S1에서 확정)
- **SKT 017670**(통신): 네트워크 감가상각 큼·마케팅비, series 14/24(five=skip 다수), SK스퀘어 분할 이력, 무선/유선/미디어 부문.
- **HMM 011200**(해운): 운임 사이클 극심(코로나 스파이크 5개년 서사)·용선료, 영업현금 방향 주의(운임형 −OCF, V-056 재검증), 산은 관리 이력.
- **KT&G 033780**(소비재): 담배+건강기능(정관장)+부동산, 안정 현금흐름·고배당(배당성향 높음).
- **고려아연/현대건설 uplift**: 기존 galaxy JSON(V-056~061)을 §8.6 D1~D5로 삼성패리티 캐스케이드 — 승격 dive `n<주>`(.row/.hl)·note_dive·값색 무채화·amt 6칙·원문 3-way·dive:cited 인용.

## 주의
- 인코딩 `PYTHONUTF8=1`. `reports.db`·`facts/`·`raw_cache/`는 gitignore(로컬 전용, --strict·§7은 이 머신만).
- 커밋/푸시는 리더 지시대로. **main 직접 push·force push 금지**.
- 렌더 확인: `python -m http.server 8000` → `http://localhost:8000/integration/dossier/galaxy.html?ticker=<t>`.
