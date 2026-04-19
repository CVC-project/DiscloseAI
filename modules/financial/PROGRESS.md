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
