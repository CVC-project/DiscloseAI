# Price 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-17
- **작업**: 주가 수집·라벨링·공시연결 파이프라인 구현 + VKOSPI 저변동 필터
- **파일**: collector.py, labeler.py, linker.py, vkospi_collector.py, volatility_filter.py, models.py
- **테스트**: 65/65 통과 (test_collector, test_labeler, test_linker) + 25/25 (test_vkospi)
- **리뷰**: 7건 지적 → 5건 즉시 수정
  - 기준 종가를 공시 당일이 아닌 다음 거래일로 변경 (이벤트 스터디 관행)
  - _detect_market에 KOSPI→KOSDAQ 폴백 로직 추가
  - save_prices 전체 테이블 스캔 → corp_code 필터 적용
  - fetch_unlinked_disclosures notin_() → NOT EXISTS 서브쿼리로 교체
  - link_single fetch_prices 이중 호출 제거
- **도메인 메모**: DART 공시는 장 마감 후(16:00~) 접수되므로 공시 당일 종가 제외가 회계적으로 타당. 5일 변동률은 누적 초과 수익률(CAAR)이 아닌 단순 기준일 대비 종가 비율 사용 — 이후 CatBoost 피처 구성 시 재검토 필요.
