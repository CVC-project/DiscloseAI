# Financial 모듈 — 도메인 규칙

## 담당 범위
재무제표 수집 + EQS(이익 품질 점수) 5개 모듈 계산 + 재무 요약

## EQS 5개 모듈
- M1 이익실체: 수정 Jones 모델 / 지주사 fallback(임계 0.40 완화 + 자본누적 일치도)
- M2 회계투명: Beneish M-score / TATA+SGI fallback(서비스·금융업용)
- M3 현금뒷받침: OCF/NI 비율 추세 / 금융업 소득안정성 fallback / 적자빈발 현금창출력 fallback
- M4 이익안정: AR(1) + 일회성 비중 / 3~4년 단축 fallback(ROA CV + 방향일관성)
- M5 재무체력: Piotroski F-score

## 업종 처리
- 금융업(064~067): M2→TATA+SGI fallback, M3→소득안정성 fallback
- 지주사(내부코드 100): M1→지주사 fallback
- 서비스/플랫폼(COGS 없음): M2→TATA+SGI fallback
- 적자빈발(>50%): M3→현금창출력(CROA) fallback
- 단축이력(3~4년): M4→ROA CV+방향일관성 fallback
- 업종 제외(excluded_modules)는 폐지 — 모든 종목에서 5개 모듈 산출

## 데이터 소스
- DART OpenAPI: 재무제표 (rate limit: 10,000건/일)
- DB 저장 테이블: shared/models.py의 FinancialData 참조
