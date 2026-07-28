# Business Dossier Data Contract

`integration/dossier/business.html`의 사업·기업 탭은 HTML만으로 완성되지 않고,
`integration/dossier/data/business_<ticker>.json` 파일을 함께 읽어 화면을 구성한다.

## 업종 라벨 필수 필드

각 `business_<ticker>.json`에는 다음 3개 필드를 최상위에 둔다.

| 필드 | 용도 | 예시 |
| --- | --- | --- |
| `sector` | 넓은 업종 또는 EQS/사업 분류 기준 | `반도체/전자부품` |
| `display_category` | 화면 중앙 행성, 회사 리스트에 표시되는 구체 업종 | `종합반도체` |
| `badge_label` | 왼쪽 회사 목록의 짧은 pill 라벨 | `메모리`, `금융업`, `조선` |

이 필드가 없으면 배포 화면에서 `업종 미분류`가 표시될 수 있다.

## 생성·복구 명령

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts\sync_business_categories.py
```

정상 결과:

```text
updated=<변경된 파일 수>
missing_category_fields=0
```

## 화면 fallback

현재 `business.html`은 다음 순서로 업종을 읽는다.

1. `display_category`
2. `sector`
3. `percentile._sector`
4. `업종 미분류`

그래도 머지 기준 데이터에는 `display_category`, `sector`, `badge_label`을 명시적으로 넣는 것을 원칙으로 한다.

## 검수 포인트

- 삼성전자 `005930`: `sector=반도체/전자부품`, `display_category=종합반도체`
- SK하이닉스 `000660`: `sector=반도체/전자부품`, `display_category=메모리반도체`
- KB금융 `105560`: `sector=금융/보험`, `display_category=금융업`
- 현대차 `005380`: `sector=자동차`, `display_category=완성차`

