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
- DB 저장 테이블: `modules/disclosure/models.py`의 **`disclosure_local`**(공시) + **`financial_statement`**(분기 재무, Groq 공시분석 맥락용, ticker 6자리). 로컬 SQLite 정본. `shared/models.py`는 미래 운영 이관용(미사용).
- ⚠️ `financial_statement`는 financial 모듈의 `financial_local`(연간)과 재무 데이터가 **이중 존재**. 같은 DART 이중 수집·식별자 불일치(8/6자리)는 알려진 이슈 — 추후 팀 논의. 상세: [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) "알려진 문제 & 열린 선택지".
