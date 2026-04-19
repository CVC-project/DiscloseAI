# Financial 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

<!-- 예시:
## 2026-04-16
- **작업**: Beneish M-score 계산 함수 구현
- **파일**: eqs/m2_beneish.py
- **테스트**: 5/5 통과
- **리뷰**: code-reviewer 지적사항 없음
- **도메인 메모**: 금융업(064~066) 제외 확인 완료
-->

## 2026-04-19 (/check)
- **작업**: 이번 세션 대규모 확장 — 수익성 비율·업계 비교·용어 툴팁·EQS 로직 정교화
  - **Phase 1**: `translator/ratios.py` 신규 (매출총/영업/순이익률·ROE·ROA).
    대시보드에 💰 수익성 섹션 + 📊🏛💵 재무제표 3종 5년 표.
  - **Phase 2**: `industry_groups.py` 신규 — KOSPI 50 → 11개 섹터 수동 매핑 +
    섹터 평균 집계 + JSON 캐시. pykrx는 KRX 사이트 개편 이후 미동작.
    대시보드 🏭 업계 대비 섹션 (내 회사 vs 섹터 평균 ±차이).
  - **용어 사전**: `glossary.py` 신규 — GlossaryEntry 데이터클래스(label/
    description/how/benchmark/intuition). 대시보드 ⓘ 툴팁을 카드형 섹션 UI로 재설계.
  - **2025년 사업보고서 반영**: range(2020,2025) → range(2021,2026).
    배치 + 대시보드 모두 2025 결산 기준 재생성.
  - **EQS 로직 수정**:
    - M2: 매출원가 없는 서비스 기업 자동 감지 (`_panel_has_cogs`, cogs>0 필수),
      핵심 지수 결측 시 한글 사유 표기 (매출채권/매출총이익률/매출성장/발생액).
    - M3: 단일 연도 OCF/NI ±3 winsorize, 적자 연도 과반이면 None.
    - M4: 하드 컷오프(φ≤0 즉시 0점) → 선형 매핑 [-1,1] 구간 (φ=0→50, φ=-1→0).
      최소 5년 데이터 요구(MIN_YEARS=5)로 3~4년 AR(1) 노이즈 차단.
    - 금융업 excluded: M3만 → **M2·M3 둘 다 제외**.
    - 지주사 분류(SK스퀘어·SK·HD현대·두산·삼성물산, 내부코드 "100") + M1 제외.
  - **대시보드**: ranking 표에 모듈 사유 title 툴팁, 업종별 제외 사유 분기.
- **파일**: `modules/financial/translator/ratios.py` (신규), `industry_groups.py` (신규),
  `glossary.py` (신규), `eqs/industry.py`, `eqs/m2_beneish.py`, `eqs/m3_cashflow.py`,
  `eqs/m4_persistence.py`, `eqs/score.py`, `batch.py`, `dashboard.py`,
  `translator/__init__.py`. 테스트 신규: `test_ratios.py`, `test_industry_groups.py`,
  `test_glossary.py`, `test_batch.py`. 기존 수정: `test_eqs_industry.py`,
  `test_eqs_score.py`, `test_eqs_m2.py`, `test_eqs_m3.py`, `test_eqs_m4.py`.
- **테스트**: **171/171 통과** (신규 50여 건 추가).
- **리뷰 (/check code-reviewer)**:
  - 🔴 Critical 2건 즉시 수정 완료:
    1. `_phi_to_score` 조건 순서 버그(φ>1.0 도달 불가 dead code) → 폭주 구간
       [1,2]에서 100→0 정상 매핑. regression guard 테스트 추가.
    2. `m3_cashflow.py` docstring/구현 불일치("OCF,NI 모두 양수") → docstring
       을 구현과 일치시킴 (NI>0만 필터, OCF 음수는 의도적으로 포함).
  - 🟡 Warning 2건 수정 완료:
    3. `dashboard.py` 지주사에도 "금융업 제외" 메시지 → industry_code 분기로
       "금융업 제외" / "지주·투자회사 제외" 별도 표시.
    4. `m2_beneish.py` cogs=0 케이스 서비스 감지 우회 → `cogs > 0` 조건 추가.
  - 🔵 Note 1건 개선: batch.py progress 출력에 `[지주]` 태그 추가.
  - 🟢 확인: ratios `_safe_div`, industry_groups JSON 왕복, frozen dataclass,
    모듈 간 import 금지 규칙 준수.
- **도메인 메모**:
  - **금융업 M2 추가 제외**: 매출/매출원가 개념이 이자수익 중심 금융업과 맞지
    않아 Beneish 지수(GMI 등) 자체가 부적합. K-Beneish 계수 재추정과 별개로
    금융업은 원천 제외가 타당.
  - **지주사 M1 제외**: 단일기업 fallback이 자회사 지분법이익(비현금성)을
    '이상 발생액'으로 오인. SK스퀘어 |TA/A|=0.385로 M1=0이던 사례. cross-section
    Modified Jones가 가능해지면 재도입 검토.
  - **M4 5년 최소**: 금융지주사들의 DART 데이터가 2023~2025 3년뿐. AR(1) pair
    2개로 φ 추정 시 ±1 극단값 튀어나옴(삼성화재 φ=-1.20 등). 5년 미만은
    정직하게 '—' 표기가 옳음.
  - **M3 winsorize 근거**: 단일 연도 OCF 폭락(현대건설 2025 -0.75조)이 5년
    평균을 음수로 끌어내려 0점 만드는 현상 방지. ±3배 클립 = OCF가 NI의 3배
    안/밖인 극단만 제한. 실무에서 이 범위를 벗어나면 일회성/비경상적 요인 해석.

## 2026-04-19 (밤) — KOSPI 50 batch
- **작업**: KOSPI 시총 50개 일괄 EQS 분석 + 비교 대시보드
- **파일**: `modules/financial/batch.py` (신규), `modules/financial/dashboard.py` (build_ranking_dashboard 추가)
- **결과**: 49/50 분석 성공 (KODEX 200 ETF만 제외)
  - 평균 EQS 57.1, 분포 A:1 / B:13 / C:24 / D:7 / F:4
  - TOP3: 삼성생명(80, A) · HD현대중공업(78.7, B) · 현대모비스(78.2, B)
  - BOTTOM3: 한화오션(16.6) · SK스퀘어(24.1) · 메리츠금융지주(26.8)
- **이름 매칭의 함정**:
  - find_corp 부분매칭이 잘못된 회사를 잡는 케이스 4건(삼성물산/SK/우리금융/미래에셋증권) → ALIASES에 종목코드 명시로 보강
  - 우선주(삼성전자우)는 DART에 별도 corp_code 없음 → 본주 corp_code로 8자리 매핑 분기 추가
- **데이터 누락 이슈** (다음 라운드 처리):
  - 금융지주사들(KB·신한·하나·메리츠·삼성생명·삼성화재) 2024년 외 사업보고서 status=013(데이터 없음) 반환 — CFS·OFS 모두 동일. corp_code는 정확. 별도 endpoint 또는 매핑 보강 필요
  - 신생/분할 회사: LG에너지솔루션(2020분할)·SK스퀘어(2021분할) 자연스러운 단축 윈도우
- **대시보드**: `docs/prototype/kospi50_ranking.html` (정렬 가능 표·등급 분포·모듈 평균·점수 히스토그램)

## 2026-04-19 (저녁)
- **작업**: M4 사이클 보정 + HTML 대시보드 생성기
- **파일**: `eqs/m4_persistence.py` (robust trim), `dashboard.py`, `tests/test_eqs_m4.py` (4 추가)
- **테스트**: 107/107 통과 (M4 robust 4개 추가)
- **사이클 보정 효과** (삼성전자 검증):
  - 5년 윈도우: φ=-0.22 (사이클에 휘둘림)
  - 10년 단순: φ=+0.08 (사이클 평균화)
  - **10년 robust**: φ=+0.19 (2023년 침체 자동 trim)
  - EQS 총점 59.9 → **63.1** 개선
- **robust trim 핵심**: 가장 큰 잔차 1**행** 제거가 아닌 그 잔차를 만든 침체 **관측치**가 등장하는 모든 (x,y) 행을 제외 (안 그러면 침체 관측치가 다음 해 x로 다시 등장해 fit이 안 됨)
- **대시보드**: `docs/prototype/financial_dashboard.html` (Chart.js CDN, 게이지·레이더·시계열·번역·highlights, 다크 테마)

## 2026-04-19
- **작업**: DART OpenAPI 수집기 구현 + 실제 삼성전자(00126380) 5년치 EQS 산출
- **파일**: `modules/financial/collector.py`, `tests/test_collector.py`
- **테스트**: 103/103 통과 (collector mock 테스트 19개 추가)
- **데이터**:
  - corp_code 매핑 11.6만 건 (상장 3,959개) → `modules/financial/data/CORPCODE.xml` 캐시
  - 삼성전자 2020~2024 연결재무제표 (CFS) 5년치
- **검증**: 삼성전자 EQS=59.9/C, M2=88.5(분식위험낮음)·M3=86.4(OCF/NI 2.04)
  - M4=0.0 — 2023년 반도체 침체로 영업이익 1/8 토막 → AR(1) φ가 음수로 추정. 사이클 산업 한계로 차후 보완 필요
- **도메인 메모**:
  - DART 응답은 `account_id`(IFRS taxonomy) 우선 매핑, 없으면 `account_nm` 한글명 fallback
  - 연결(CFS) 시도 후 status=013이면 별도(OFS)로 자동 재시도
  - 같은 필드 중복 매칭 시 첫 값 우선 (CFS·OFS 혼합 응답 보호)

## 2026-04-18 (check)
- **작업**: `/check` — code-reviewer + test-generator 병렬 실행 결과
- **테스트**: 71/71 통과 (기존 45 + 신규 26: `test_ols_unit.py`, `test_score_aggregate.py`, `test_translator_patterns.py`)
- **리뷰**: 도메인 정확성 4건 지적
  1. `m2_beneish.py` DEPI — K-IFRS PPE는 순액 → 원논문(총취득원가) 분모와 체계적 차이, 한계 주석 필요
  2. `m2_beneish.py` GMI — 총이익률 음수(cogs>revenue) 케이스에서 분식 신호가 묻힐 수 있음
  3. `m5_piotroski.py` F5 — 원논문은 LTD/평균자산 **비율** 기준, 현재 코드는 절대금액 비교
  4. `m4_persistence.py` `_phi_to_score` docstring 오기재 (φ=0→50점이라 적혔지만 실제는 0점)
- **추후 개선**: M3 OCF 음수 해 추세 영향, score._aggregate 외부 weights 키 누락 시 silent fallback
- **도메인 메모**: 1·3은 K-IFRS/한국 데이터 정합성 정책(CPA 팀 결정), 2·4는 다음 커밋에서 즉시 수정 가능

## 2026-04-18
- **작업**: EQS 5개 모듈 + 종합 점수 + 재무제표 번역기 + highlights 1차 구현
- **파일**:
  - `eqs/types.py` (FirmYear/FirmPanel/EQSResult 컨테이너)
  - `eqs/_ols.py` (numpy 의존 없는 단변량/다변량 OLS)
  - `eqs/industry.py` (금융업 064~067 분류 + M3 제외 규칙)
  - `eqs/m1_accruals.py` (수정 Jones, cross-section + 단일기업 fallback)
  - `eqs/m2_beneish.py` (Beneish 8지수 + K-Beneish 계수 분리, 임계값 -1.78)
  - `eqs/m3_cashflow.py` (OCF/NI 평균·추세·변동성 가중)
  - `eqs/m4_persistence.py` (AR(1) φ + 일회성 비중 페널티)
  - `eqs/m5_piotroski.py` (9개 binary criteria)
  - `eqs/score.py` (가중 합산 + A/B/C/D/F 등급, 금융업 가중치 재배분)
  - `translator/translate.py` (손익/재무상태/현금흐름 한국어 한 줄 요약)
  - `translator/highlights.py` (8개 규칙 기반 ⚡ 주목 포인트 상위 3개)
- **테스트**: 45/45 통과 (`pytest tests/`)
- **검증**: HEALTHY 패널 → 91.8/A, MANIPULATOR 패널 → 47.7/D
- **도메인 메모**:
  - K-Beneish는 현재 미국 계수를 그대로 사용 — 한국 상장사 데이터 확보 후 `BENEISH_KR` 재추정 예정
  - M1 단일기업 fallback은 |TA/A|를 신호로 사용 (cross-section 산업 표본 8개 이상 모이면 정확한 |DA/A|로 교체)
  - 금융업(064~067) 패널은 자동으로 M3 제외 + 남은 4개 모듈에 가중치 재배분
