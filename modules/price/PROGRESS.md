# Price 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-20
- **작업**: quiz_data.py 15개 문항 사실관계 검증 및 수정 (웹 검색 + yfinance 재계산)
- **파일**: modules/price/quiz_data.py, tests/test_quiz_data.py (신규)
- **테스트**: 157/157 통과
- **리뷰**: 5건 지적 → 4건 즉시 수정
  - id=5 SK하이닉스 인수 금액 9조 원 → 10.2조 원 (title·context·context 마지막 줄 3곳)
  - id=15 카카오 category "물적분할" → "규제리스크" (자회사 IPO+규제 복합 이벤트)
  - type hint `list[dict]` → `list[dict[str, Any]]` 미수정 (교육용 정적 데이터로 현행 유지)
  - id=13 NAVER 공시/보도 source 구분 필드 미추가 (구조 변경 범위 커 현행 유지)
- **도메인 메모**: yfinance 재계산 기준은 공시 전일 종가 → 공시 후 N거래일 종가. 검증 결과 수정된 change_pct: 4번 현대차(+19.4→+26.7%), 8번 SK이노베이션(-9.8→-6.0%), 11번 기아(+39.8→+11.4%), 12번 삼성물산(악재-8.5 → 수혜+15.3%, M&A 프리미엄 매수세로 주가 상승 확인), 15번 카카오(-14.2→-28.4%). 미해결 항목: 2번 한전·6번 두산중공업·7번 셀트리온·9번 삼성바이오·14번 현대모비스 날짜/수치 불일치 — KIND 원문 확인 필요.

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
