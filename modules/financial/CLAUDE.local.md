# Financial 모듈 — 도메인 규칙

## 담당 범위
재무제표 수집 + EQS(이익 품질 점수) 5개 모듈 계산 + 재무 요약

## EQS 5개 모듈
- M1 발생액 품질: 수정 Jones 모델
- M2 분식 확률: Beneish M-score (K-IFRS 재추정 = K-Beneish)
- M3 현금흐름 괴리: OCF/NI 비율 추세
- M4 이익 지속성: AR(1) + 일회성 비중
- M5 재무 건전성: Piotroski F-score

## 업종 예외
- 금융업(업종코드 064~066): M3 제외, BIS비율 등 별도 기준
- 보험업(067)도 금융업 예외 적용 고려

## 데이터 소스
- DART OpenAPI: 재무제표 (rate limit: 10,000건/일)
- DB 저장 테이블: shared/models.py의 FinancialData 참조
