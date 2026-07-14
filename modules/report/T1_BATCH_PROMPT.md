# 다음 세션 프롬프트 — T1 산업 골든 6본 완주 배치

> 이 파일 전체가 **다음 세션에 붙여넣을 프롬프트**다. 완주 후 삭제. 시작점 = 커밋 `802b8d0`(정본 계층 하네스).

---

## 진행 상황 (2026-07-14 세션 — 1본 완주)

- ✅ **고려아연 010130 (에너지소재/제련) 완주** — 커밋 `14c0a42`. 5게이트 PASS(check_golden 0·무회귀 8본 0·인터랙션 7/7·정확성 REFUTED 0·완전성 콘텐츠 PASS). tier `1c→1`·galaxy_index 등록·V-056~059 채록. 첫 T1 대표 = **재현 레시피 원형**.
- ⚠️ **데이터 결함 2건 발견·처리** (프롬프트의 "6본 준비됨" 전제 일부 거짓):
  - 010130: reports.db가 **stale 섹션 tail 절단**(25노트) → `section_all(['010130'])` 재섹션 39노트 (V-058).
  - **012450 한화에어로: FY2025가 DART `[첨부정정]` 스텁**(document status 014, 본문 없음) → 주석 추출 불가 → **보류**(리더 승인 차순위 승계). 재개 시 원본 FY2025 rcept 수동 확보 필요.
- 🔄 **현대건설 000720: S1 note-extraction 진행 중**(background) — facts_000720.json 생성 예정.

### 재현 레시피 (고려아연에서 검증 — 회사마다 반복)
1. **S0**: `section_all([t])` 재섹션(staleness 방어) → `sectioner --health` → `series` 완결률. ⚠️ **raw XML 최대주번호 vs DB 대조**(법인세·EPS 노트 존재 — tail 절단 방어, health 미포착).
2. **S1**: note-extractor(회사 구조 강조) → `facts_<t>.json`. 형식 견본=facts_068270.json.
3. **S2 결정론 골격**(scratch build script): fs_account+series+facts → panels(A~E)·knots(k1~k15)·CF분해(`cf-noncash=영업창출현금−순이익`·`cf-paid=OCF−영업창출현금`)·BS/CF/sgna 서브행(top+잔차)·eqstory(eq-other=자본−기초−ni−oci+div 잔차)·dive 스켈레톤(z/zc/row/links-a/five-key/viz)·routing_ledger(전 주석). **필수 dive = series 완결(REQ_SERIES)+행 존재(COND_ROW)로 결정** — 없으면 생략(R6.9). ⚠️ **회사별 account_id 차이 흡수**(예 sgna: `dart_Total…` vs `ifrs-full_SellingGeneralAndAdministrativeExpense`).
4. **S3 프로즈**: prose-writer 6배치 병렬(IS dive·cash/CF·CF/BS·equity·appendix A·B) — 각 self-contained(facts 경로+골든 견본+series+카드 스펙). 반환 카드 JSON을 스켈레톤에 병합, knots.story는 "".
5. **S4·S5 게이트**: check_golden 0 → accuracy-verifier(REFUTED 0) → completeness-auditor(shallow 0·렌더 스윕) → `check_golden --all` 무회귀 → `GALAXY_TICKER=<t> pytest test_galaxy_interaction.py`.
6. **완주 후무**: VARIATIONS S7 채록 + 채록로그 1줄 · corps.csv `1c→1` · `build_galaxy_index.py` · DL 스크린샷(headless playwright) · 커밋(golden JSON+VARIATIONS+corps.csv+galaxy_index).
> **금칙어 주의**: 파생/원자재 회사에서 "매수/매도" 표현이 check_golden 금칙(투자조언)에 매칭 → "매입/매도 포지션"으로. **assemble 모듈화**(build/merge scratch → modules/report/assemble.py)는 여전히 미결 부채.

### 남은 배치 순서 (구조 주의)
- **현대건설 000720**(건설): 표준 IS지만 **sgna account_id 다름**(위 ⚠️)·**영업현금 마이너스(미청구공사 운전자본형 — V-056 재현, 2회째면 코드 승격)**·건설계약(주24)·미청구공사(주5 계약자산)·우발약정(주33 PF보증) 신규 dive. capex·div series 미완 → ppe·eq-div dive 생략 가능(account 매핑 확인).
- **SKT 017670**(통신): 네트워크 감가상각 큼·마케팅비. series 14/24(결측 다수 → five=skip 많음).
- **HMM 011200**(해운): 운임 사이클 극심·용선료. 영업현금 방향 주의(운임형 −OCF — V-056 재검증).
- **KT&G 033780**(소비재): 담배+건강기능(정관장)+부동산. 안정 현금흐름·고배당.

---

## 지시

정본 계층(R8)의 **T1 산업 골든 후보 6본을 완주**시켜라. 이들은 각 클러스터의 **첫 대표(구조·주석맵 견본)**를 새로 세우는 것 — 삼성(T0)은 문체 기준, 구조는 이 회사 사업보고서가 정의한다(R6.9). 완주 = 5게이트 PASS + 리더 DL 게이트(시각 승인) 대기.

### 먼저 읽기 (순서)
1. `modules/report/MILKYWAY_GENERATOR.md` — 하네스 정본. **특히 §8.5 정본 계층(R8)**.
2. `modules/report/VARIATIONS.md` — **S0 필수 정독**(V-001~055). 완주 골든 6본의 구조 편차를 선제 적용: 제조형(V-046 build_mfg 논리)·기타영업손익(V-013)·순손실(V-023)·금융하이브리드(V-050)·APPENDIX 실수치 규칙(V-048)·viz 코드배정(V-052)·그림자 dive 금지(V-053).
3. `modules/report/data/corps.csv` — 이 6본의 `cluster`·`tier(1c)` 확인.
4. `.claude/skills/galaxy-golden/SKILL.md` — S1~S5 손잡이.

### 데이터 상태 (착수 전 확인됨 — 큰 head start)
6본 모두 **reports.db 주석 분할·fs_account 5개년·series 완결이 이미 있음**(collector/sectioner/fs_enrich 불요). **facts_*.json만 미생성** → S1(note-extractor)부터 시작.

| 순서 | 티커 | 회사 | 클러스터 | 주석 | series | 회사별 구조 주의(S1에서 확정) |
|---|---|---|---|---|---|---|
| 1 | 012450 | 한화에어로스페이스 | 중공업방산 | 81 | 19/24 | **최대 클러스터(12사) 대표 — 최우선**. 방산·항공엔진 수출 급증, **장기공사 진행기준 매출·수주잔고**, 부문(방산/에너지/항공). 미청구·초과청구공사 주석 |
| 2 | 010130 | 고려아연 | 에너지소재 | 89 | 20/24 | 아연·연·금·은 **제련**(순수 제조). 원자재 **파생상품 헤지**(가격위험), LME 연동. 트로이카드라이브 신사업 |
| 3 | 000720 | 현대건설 | 건설 | 115 | 17/24 | **건설 = 진행기준 공사수익·미청구공사(계약자산)·초과청구(계약부채)** 핵심. 해외 프로젝트·현대ENG 연결. ⚠️ S0로 지주 여부·series 완결 확인(부적격이면 차순위 승계) |
| 4 | 017670 | SK텔레콤 | 통신 | 124 | 14/24 | **통신 = 네트워크 설비 감가상각 큼·마케팅비**. 무선/유선/미디어 부문, ARPU. series 14/24(통신 특유 결측 다수 → five=skip 많을 것). SK스퀘어 분할 이력 |
| 5 | 011200 | HMM | 해운 | 125 | 20/24 | **해운 = 운임 사이클(변동 극심)·컨테이너선·용선료**. 과거 급등락(코로나 운임 스파이크) → 5개년 차트 서사 주의. 산은 관리 이력 |
| 6 | 033780 | KT&G | 소비재 | 107 | 19/24 | 담배(국내/수출) + 건강기능(정관장) + 부동산. 안정적 현금흐름·고배당. 부문 명암 |

> 회사별 주의는 **가설** — S1 note-extractor로 그 회사 실주석에서 확정하라. 새 클러스터라 **new-dive(수주잔고·미청구공사·운임 등)**가 나올 수 있음(원장 §7 new-dive 라우팅 + 신규 카드 생성 의무).

### 완주 루프 (회사마다 — `/galaxy-golden <ticker>` 또는 수동 S1~S5)
1. **S0**: `python -m modules.report.sectioner --health <t>` PASS + corps.csv 티어/클러스터 확인.
2. **S1**: note-extractor → `facts_<t>.json`(source_quote 원문 substring 전수 검증). 완주 4본 facts를 형식 견본으로.
3. **S2~S3**: 제조형은 build_mfg 논리(V-046) 재현 — 셀트리온/현대차/LG JSON을 구조 템플릿으로. 패널·knots·dives·appendix 조립 + 산문(APPENDIX는 V-048 실수치+링크 규칙, viz는 V-052 코드배정, 부문은 k2에 vBubbles=V-053).
4. **S4~S5**: check_golden `<t>` 갭 0 · accuracy-verifier(브래킷 재도출) · completeness-auditor(얕은 카드·주석 커버리지·렌더 스윕).

### 완주 게이트 (회사마다 전부 PASS)
- `python -m modules.report.check_golden <t>` 갭 0
- `GALAXY_TICKER=<t> pytest tests/report/test_galaxy_interaction.py` PASS
- **딥다이브 전행 열림** — evaluate-click, **클릭 사이 Esc 필수**(V-049 교훈). 콘솔에러 0(favicon 제외)
- **전 골든 무회귀**: `python -m modules.report.check_golden --all` (T1 신규는 렌더러 미변경이라 무회귀, galaxy.html 손대면 필수)
- 인코딩: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`. 서버: `python -m http.server 8000`.

### 완주 후 의무 (회사마다)
1. **VARIATIONS S7 채록** — 새 편차 V-### + 채록 로그 1줄(신규 없어도 명시).
2. **corps.csv**: 그 티커 `tier` `1c`→`1`(완주).
3. **제품 자동 등록**: `python integration/dossier/build_galaxy_index.py`(매니페스트 갱신 → v2 3탭에 자동 노출).
4. **커밋**: galaxy_<t>.json + VARIATIONS + corps.csv + galaxy_index.json (facts는 비커밋 — .gitignore 확인).
5. **DL 게이트**: T1은 리더 시각 승인(contact-sheet 스크린샷) 대상 — 완주 보고에 렌더 스크린샷 경로 첨부.

### 배치 종료
6본 완주 후 `NEXT_SESSION.md` 갱신(T1 12본 완주 → 다음은 T2 클러스터 확장), 이 프롬프트 파일 삭제.
