# EQS/F-EQS v3 통합 구현 기준서

> 이 문서의 목적: 통합 담당자가 HTML 화면을 스크린샷 기준으로 다시 추정하지 않고, 현재 PR의 EQS/F-EQS 산식·데이터·화면 연결 구조를 그대로 재현할 수 있게 하는 구현 기준서입니다.
>
> 적용 범위: `integration/v2/index.html`의 `EQS 재무분석` 탭, `integration/dossier/firm.html`, 48개 기업의 `firm_<ticker>.json`, 금융업 전용 F-EQS 점수 데이터.

---

# PART 1 - 이번 PR에서 확정한 변경사항

## 1-1. 일반기업 EQS와 금융기업 F-EQS를 분리
- 비금융 기업은 기존 EQS 5개 모듈 `M1~M5`를 사용합니다.
- 금융 기업은 제조업형 지표가 맞지 않으므로 금융업 전용 `F1~F5`를 사용합니다.
- 화면에서는 둘 다 같은 위치에 표시되지만, 모듈 이름과 설명은 기업 유형에 따라 달라집니다.

## 1-2. 등급 컷 통일
EQS와 F-EQS 모두 같은 등급 기준을 씁니다.

| 점수 구간 | 등급 |
|---:|:---|
| 75점 이상 | A |
| 60점 이상 75점 미만 | B |
| 50점 이상 60점 미만 | C |
| 25점 이상 50점 미만 | D |
| 25점 미만 | F |

## 1-3. 동종업계 분위수 기반 점수화
- 절대 기준으로 "좋다/나쁘다"를 찍지 않고, 전 상장사 패널에서 만든 동종업계 분포와 비교합니다.
- 비교 기준은 `P10/P25/P50/P75/P90`입니다.
- 높은 값이 좋은 지표는 `P10=0점, P25=25점, P50=50점, P75=75점, P90=100점`으로 선형 보간합니다.
- 낮은 값이 좋은 지표는 반대로 `P10=100점, P25=75점, P50=50점, P75=25점, P90=0점`으로 선형 보간합니다.
- KSIC 3자리 비교군 표본이 부족하면 KSIC 2자리, 시장 전체 순으로 확장합니다.
- 금융업은 비금융 시장과 섞지 않고, 마지막 fallback도 `FINANCIAL` 내부 비교군을 사용합니다.

## 1-4. 짧은 재무 이력 보정 방식 변경
- 2개년 이력 기업은 계산 가능한 모듈을 그대로 사용합니다. 별도 감점 또는 50점 방향 보정은 하지 않습니다.
- 1개년 이력 기업은 추세형 지표를 무리하게 만들지 않습니다. 계산 가능한 모듈만 사용하고, 불가능한 모듈은 `N/A`로 둡니다.
- 목적: 신규 상장사나 짧은 이력 기업에 임의 보정점수를 만들지 않기 위함입니다.

## 1-5. M4 본업 안정성 산식 변경
M4는 영업이익률의 "수준"과 "흔들림"을 함께 봅니다.

- 최근 3개년이면 영업이익률을 `1:2:3`으로 가중평균합니다.
- 최근 2개년이면 `1:2`로 가중평균합니다.
- 수익성 점수 70%와 변동성 점수 30%를 합산합니다.
- 변동성은 `max(영업이익률) - min(영업이익률)`입니다.

```text
M4 = weighted_margin_score * 0.70 + margin_volatility_score * 0.30

weighted_margin_3y = (t-2 margin * 1 + t-1 margin * 2 + t margin * 3) / 6
weighted_margin_2y = (t-1 margin * 1 + t margin * 2) / 3
margin_volatility = max(margins) - min(margins)
```

## 1-6. 통합 화면의 EQS 상세 탭 데이터 동기화
통합 화면은 두 계층의 데이터를 읽습니다.

```text
integration/v2/index.html
  -> integration/v2/src/adapter.js
  -> integration/v2/data/loader.js
  -> integration/data/eqs_summary.json

EQS 상세 iframe
  -> integration/v2/src/bundle.jsx
  -> integration/dossier/firm.html?ticker=<ticker>&theme=galaxy
  -> integration/dossier/data/firm_<ticker>.json
```

이번 PR에서는 `eqs_summary.json`만 갱신하지 않고, 48개 `firm_<ticker>.json`까지 같은 점수로 동기화했습니다.

---

# PART 2 - 모듈별 산식 기준

## 2-1. 일반기업 EQS: M1~M5

| 모듈 | 화면 이름 | 핵심 질문 | 산식/판정 |
|---|---|---|---|
| M1 | 현금이익률 | 이익이 실제 현금으로 뒷받침되는가 | 최근 최대 3개년 누적 영업현금흐름 / 누적 영업이익 |
| M2 | 매출 회수 건전성 | 매출보다 미수채권이 과하게 빨리 늘었는가 | 매출채권·계약자산 증가율 - 매출 증가율 |
| M3 | 부채 건전성 | 부채 부담이 동종업계 대비 높은가 | 부채총계 / 자본총계 |
| M4 | 본업 안정성 | 본업 수익성이 높고 덜 흔들리는가 | 최근 가중평균 영업이익률 70% + 영업이익률 변동성 30% |
| M5 | 자본 성장성 | 주주의 몫인 자본이 성장했는가 | 3개년이면 2년 자본 CAGR, 2개년이면 1년 자본성장률 |

## 2-2. M2 상세 기준
M2는 매출 증가보다 매출채권이나 계약자산이 더 빠르게 늘어나는지를 봅니다.

```text
revenue_growth = current_revenue / previous_revenue - 1
receivable_growth = current_receivable_like / previous_receivable_like - 1
M2_raw_gap = receivable_growth - revenue_growth
```

- `current_receivable_like`는 매출채권을 기본으로 합니다.
- 계약자산이 있는 수주산업은 `매출채권 + 계약자산`을 사용합니다.
- `M2_raw_gap`이 작거나 음수면 매출 회수가 상대적으로 양호한 신호입니다.
- 금융업은 매출채권 중심 회수 구조가 아니므로 F-EQS로 분리합니다.

## 2-3. 금융업 F-EQS: F1~F5

| 모듈 | 화면 이름 | 핵심 질문 | 산식/판정 |
|---|---|---|---|
| F1 | 주주환원 | 배당 매력이 있고 DPS가 유지·성장했는가 | 3년 가중평균 배당수익률 70% + DPS 유지·성장 점수 30% |
| F2 | ROE 품질 | 자기자본 대비 이익을 잘 내는가 | 최근 3년 ROE 가중평균 |
| F3 | 자본 완충력 | 손실을 버틸 자본 여력이 있는가 | 자본총계 / 자산총계 |
| F4 | 이익 전환 | 영업이익이 최종 순이익으로 잘 남는가 | 순이익 / 영업이익 |
| F5 | 자본 성장성 | 주주의 몫이 커지고 있는가 | 최근 자본총계 CAGR |

## 2-4. F1 상세 기준
F1은 금융주를 볼 때 초보 투자자가 직관적으로 이해하기 쉬운 배당 매력과 배당 지속성을 함께 봅니다.

```text
F1 = dividend_yield_score * 0.70 + dps_continuity_score * 0.30

dividend_yield_weighted_average =
  (t-2 dividend_yield * 1 + t-1 dividend_yield * 2 + t dividend_yield * 3) / 6
```

`dividend_yield_score`는 금융업 내부 분위수로 0~100점화합니다.

`dps_continuity_score`는 DPS 변동성이 아니라 유지·성장 여부를 봅니다.

- 1년 이상 DPS 지급: 기본 35점
- 2년 이상 DPS 지급: 기본 60점
- 3년 연속 DPS 지급: 기본 75점
- 전년 대비 10% 이상 삭감: 삭감 1회당 -20점
- 전년 대비 5% 이상 성장: 성장 1회당 +7.5점
- 3년 연속 지급하면서 삭감이 없으면 +10점
- 최종 점수는 0~100점 범위로 제한합니다.

---

# PART 3 - 데이터 파일과 화면 연결

## 3-1. 기준 데이터 파일

| 파일 | 역할 | PR 포함 여부 |
|---|---|---|
| `modules/financial/data/eqs_data.json` | 48개 화면 기업의 EQS/F-EQS 기준 데이터 | 포함 |
| `integration/data/eqs_summary.json` | v2 통합 화면의 기업 노드/요약 EQS 데이터 | 포함 |
| `integration/dossier/data/firm_<ticker>.json` | EQS 상세 iframe이 읽는 기업별 데이터 | 포함 |
| `modules/financial/data/financial_feqs_*.json` | 금융업 F-EQS 산출 결과/입력/보정값 | 포함 |
| `modules/financial/data/remote_eqs_cache/` | 전 상장사 원천 패널·대용량 캐시 | 제외 |

## 3-2. 대용량 캐시 제외 기준
`remote_eqs_cache`에는 전 상장사 DART 패널과 보정 산출 중간 파일이 들어갑니다.

- GitHub PR에는 넣지 않습니다.
- 서버 또는 GPU Disk에 보관하는 재생성용 캐시입니다.
- `.gitignore`에 `modules/*/data/remote_eqs_cache/`를 추가했습니다.

## 3-3. 화면에서 점수가 보이는 위치

1. v2 통합 화면의 기업 카드와 EQS 요약값
   - `integration/data/eqs_summary.json`
   - `integration/v2/data/loader.js`
2. `ENTER CORPORATION` 이후 EQS 재무분석 탭
   - `integration/dossier/firm.html`
   - `integration/dossier/data/firm_<ticker>.json`
3. 금융업 기업의 모듈명
   - 일반 M1~M5 대신 F1~F5 표시

## 3-4. 캐시 우회
브라우저가 예전 `firm_<ticker>.json`을 잡고 있으면 새 점수가 안 보일 수 있습니다.
그래서 `integration/v2/src/bundle.jsx`에서 EQS iframe URL에 버전 파라미터를 붙였습니다.

```jsx
../dossier/firm.html?ticker=<ticker>&theme=galaxy&v=eqs-feqs-m4-20260728
```

---

# PART 4 - 재생성 명령

아래 명령은 repo root에서 실행합니다.

```powershell
$env:PYTHONIOENCODING='utf-8'

python scripts\build_eqs_v3_calibration.py `
  --panels modules\financial\data\remote_eqs_cache\panels_2021_2025.json `
  --output modules\financial\data\remote_eqs_cache\eqs_v3_calibration.json `
  --min-peers 20

python scripts\score_eqs_v3.py `
  --panels modules\financial\data\remote_eqs_cache\panels_2021_2025.json `
  --calibration modules\financial\data\remote_eqs_cache\eqs_v3_calibration.json `
  --output modules\financial\data\remote_eqs_cache\eqs_v3_scores.json

python scripts\export_eqs_v3_subset.py `
  --input modules\financial\data\eqs_data.json `
  --scores modules\financial\data\remote_eqs_cache\eqs_v3_scores.json `
  --output modules\financial\data\eqs_data.json `
  --comparison-output modules\financial\data\remote_eqs_cache\screen_eqs_v3_comparison.json `
  --method v3_all_krx_percentile_m4_weighted_margin_2021_2025

python scripts\build_financial_feqs.py --skip-dividend-fetch
python -m integration.extract_data
python scripts\sync_dossier_eqs_v3.py
```

## 4-1. 동기화 확인

```powershell
python scripts\sync_dossier_eqs_v3.py --check
```

정상 출력:

```text
canonical=48, stale_or_updated=0, unmatched=0
```

---

# PART 5 - 검증 기준

## 5-1. 필수 검증 명령

```powershell
node --check integration\v2\data\loader.js
python -m py_compile scripts\sync_dossier_eqs_v3.py modules\financial\eqs\score.py modules\financial\eqs\calibration.py modules\financial\eqs\m4_persistence.py modules\financial\eqs\financial_feqs.py scripts\build_financial_feqs.py
python -m pytest -q
git diff --check
```

이번 PR 검증 결과:

```text
478 passed, 41 skipped
sync_dossier_eqs_v3.py --check: canonical=48, stale_or_updated=0, unmatched=0
```

## 5-2. 대표 기업 확인값

| 기업 | ticker | 방식 | 총점 | 등급 | 확인 포인트 |
|---|---:|---|---:|:---|---|
| 삼성전자 | 005930 | EQS M1~M5 | 72.2 | B | M4: 3년 가중평균 영업이익률 +10.6% |
| KB금융 | 105560 | F-EQS F1~F5 | 56.5 | C | F1~F5 금융 전용 모듈 표시 |

## 5-3. 로컬 확인 URL

```text
http://localhost:8000/integration/v2/index.html?v=eqs-feqs-m4-20260728
```

---

# PART 6 - 머지 담당자 체크리스트

- `integration/data/eqs_summary.json`와 `integration/dossier/data/firm_<ticker>.json`가 같이 들어왔는지 확인합니다.
- `scripts/sync_dossier_eqs_v3.py --check`가 `stale_or_updated=0`인지 확인합니다.
- 금융업 기업에서 M1~M5가 아니라 F1~F5가 표시되는지 확인합니다.
- `remote_eqs_cache`는 PR에 포함하지 않습니다.
- 통합 화면에서 EQS 탭을 새로고침해도 같은 점수가 유지되는지 확인합니다.
