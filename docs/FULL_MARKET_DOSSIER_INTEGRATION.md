# 전 상장사 사업·EQS 탭 확장 구현 기준

이 문서는 `integration/v2/index.html`의 기존 전 상장사 행성 UI를 유지하면서,
회사 오버레이의 `사업·기업` 탭과 `EQS 재무분석` 탭을 전 상장사 대상으로 확장하기 위한
데이터 계약과 재생성 절차를 정리한다.

## 1. 유지하는 프론트 구조

`integration/v2/src/bundle.jsx`의 오버레이 구조는 유지한다.

```jsx
{ id: 'business', label: '사업·기업', src: 'business.html', context: 'business' }
{ id: 'eqs', label: 'EQS 재무분석', src: 'firm.html', context: 'finance' }
```

회사를 클릭하면 기존처럼 iframe이 열린다.

```text
integration/dossier/business.html?ticker={종목코드}
integration/dossier/firm.html?ticker={종목코드}
```

즉, 이번 확장은 HTML을 새로 만드는 방식이 아니라 iframe이 읽는 JSON을 전 상장사로 넓히는 방식이다.

## 2. 입력 데이터

### 사업보고서 요약 원천

```text
modules/disclosure/data/fulltext/{corp_code}/{rcept_no}/summary.json
```

사용 필드:

- `corp_code`, `corp_name`, `rcept_no`
- `products`
- `segments`
- `financial_highlights`
- `investor_notes`
- `glossary_terms`

### 회사 마스터

```text
integration/dossier/data/company_master.json
```

사용 목적:

- `corp_code`와 `ticker` 매핑
- 회사명, 시장, KSIC 업종명, 금융업 여부 확인

### EQS 상세 원천

```text
integration/dossier/data/firm_{ticker}.json
```

사용 목적:

- `firm.html` 상세 화면의 원천 데이터
- `integration/data/eqs_summary.json` 생성 원천

## 3. 출력 데이터

### 사업·기업 탭

```text
integration/dossier/data/business_{ticker}.json
```

기존 48개 수작업 파일은 기본적으로 덮어쓰지 않는다.
나머지 기업은 `summary.json`을 현재 `business.html` 계약에 맞게 변환한다.

핵심 필드:

- `name`, `stock_code`, `corp_code`
- `report`: DART 접수번호와 사업보고서 링크 구성 정보
- `snippets`: 사업개요, 사업부문, 제품, 투자자용 설명
- `business_cards`: 행성 주변 사업·제품 카드
- `custom_report_ideas`: 사업보고서 핵심 요약 카드
- `sector`, `display_category`, `badge_label`

### EQS 재무분석 탭

```text
integration/dossier/data/firm_{ticker}.json
integration/data/eqs_summary.json
```

`firm_{ticker}.json`은 iframe 상세 화면이 직접 읽는다.
`eqs_summary.json`은 `integration/v2/data/loader.js`가 행성 노드에 EQS/F-EQS 점수를 주입할 때 사용한다.

## 4. 생성 스크립트

### 사업 탭 JSON 생성

```bash
python integration/dossier/build_full_market_business_json.py
```

동작:

- `summary.json` 최신 보고서를 회사별로 하나 선택한다.
- `company_master.json`으로 `corp_code -> ticker`를 매핑한다.
- 기존 `business_*.json`이 있으면 보존한다.
- 없는 기업만 새로 생성한다.

기존 48개까지 다시 만들고 싶으면:

```bash
python integration/dossier/build_full_market_business_json.py --overwrite-curated
```

### EQS 요약 인덱스 생성

```bash
python integration/dossier/build_full_market_eqs_summary.py
```

동작:

- `firm_*.json` 전체를 읽는다.
- v2 메인 로더가 필요한 가벼운 점수 인덱스 `integration/data/eqs_summary.json`을 만든다.
- 일반기업 EQS와 금융업 F-EQS를 모두 같은 파일에 담는다.

### placeholder 생성

```bash
python integration/dossier/ensure_full_market_dossier_placeholders.py
```

동작:

- `integration/data/companies_index.json`의 모든 티커를 확인한다.
- 사업보고서 요약 또는 재무 패널이 없는 기업에는 `_placeholder: true` JSON을 생성한다.
- 점수를 꾸며내지 않고 `N/A` 상태로 표시한다.
- 목적은 iframe 404를 막고 데이터 공백을 명확히 보여주는 것이다.

## 5. 현재 생성 결과

이번 작업 기준:

- `companies_index.json`: 2,651개 기업
- `business_*.json`: 2,761개
- `firm_*.json`: 2,743개
- 사업 탭 placeholder: 65개
- EQS 탭 placeholder: 60개
- `eqs_summary.json`: 2,680개 점수 행
  - 일반 EQS: 2,562개
  - 금융 F-EQS: 118개

`business_*.json`과 `firm_*.json` 개수가 `companies_index`보다 큰 이유는
마스터·DART 수집 데이터에는 있으나 현재 전 상장사 행성 UI 목록에는 없는 종목이 일부 포함되어 있기 때문이다.
프론트 기준 누락은 `companies_index` 대비 0개다.

## 6. 품질 원칙

사업·기업 탭은 다음 원칙으로 요약한다.

- 기존 48개 수작업 사업 카드 품질은 보존한다.
- 나머지 기업은 사업보고서 요약 원천을 기반으로 자동 생성한다.
- 제품명과 사업부문을 불필요하게 반복하지 않는다.
- 원문을 그대로 길게 붙이지 않고 초보 투자자가 읽을 수 있는 문장으로 압축한다.
- 금융업, 지주사, 바이오, 제조업 등 업종 성격에 따라 카드의 의미가 다르게 보이도록 한다.
- 데이터가 없으면 추정하지 않고 placeholder로 표시한다.

## 7. 검증 명령

```bash
python -m py_compile ^
  integration/dossier/build_full_market_business_json.py ^
  integration/dossier/build_full_market_eqs_summary.py ^
  integration/dossier/ensure_full_market_dossier_placeholders.py
```

프론트 커버리지 확인:

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path(".")
companies = json.loads((root/"integration/data/companies_index.json").read_text(encoding="utf-8"))
tickers = {str(c["t"]) for c in companies if c.get("t")}
business = {p.stem.replace("business_", "") for p in (root/"integration/dossier/data").glob("business_*.json")}
firm = {p.stem.replace("firm_", "") for p in (root/"integration/dossier/data").glob("firm_*.json")}
print("business missing", len(tickers - business))
print("firm missing", len(tickers - firm))
PY
```

기대 결과:

```text
business missing 0
firm missing 0
```
