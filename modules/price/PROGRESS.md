# Price 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-19
- **작업**: 코스피 상위 50개사 공시 기반 주가 예측 퀴즈 구현 (CLI + 브라우저 단일 파일)
- **파일**: quiz_data.py (신규), quiz.py (신규), quiz.html (신규), tests/test_quiz.py (신규)
- **테스트**: 38/38 통과 (구조·타입·일관성·엣지케이스·compute_label 검증)
- **리뷰**: 4건 지적 → 3건 즉시 수정
  - quiz_data.py 카카오 context 사실 오류 수정 (카카오페이 8월→11월 상장 예정)
  - quiz.py docstring 직접 실행 방식(`python modules/price/quiz.py`) 제거 — 프로젝트 루트 import 실패 위험
  - quiz.html "초과수익(알파)" 레이블 → "단순 초과(종목-코스피)"로 변경 — 기하적 초과수익과의 혼동 방지
  - alphaClass ±0.5 임계값 의미 없음 지적 → 교육용 퀴즈 특성상 현행 유지 (미수정)
- **도메인 메모**: kospi_change_pct는 동기간 실제 지수 데이터 기반 근사치. 단순 초과(종목 변동률 - 코스피 변동률)로 표시하며, 이벤트 스터디의 정식 CAAR(누적 초과수익률) 계산과는 다름. 향후 CatBoost 피처 구성 시 기하적 초과수익률로 전환 검토 필요.

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
