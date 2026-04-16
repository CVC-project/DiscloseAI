# Disclosure 모듈 — 도메인 규칙

## 담당 범위
DART 공시 수집 (과거 배치 + 실시간 폴링) + 공시 쉬운 설명 생성

## DART API 규칙
- 일일 한도: 10,000건
- 과거 데이터: 배치 수집 (야간)
- 실시간: 1~5분 간격 폴링

## 공시 유형 분류
- 유상증자, CAPEX, M&A, 지분취득, 실적발표 등 범주형 분류
- 분류 기준은 DART 공시 유형 코드 참조

## 데이터 소스
- DART OpenAPI: 수시공시, 정기공시
- DB 저장 테이블: shared/models.py의 DisclosureData 참조
