# Relation 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-20
- **작업**: Phase 2 전체 구현 (수집→변환→그래프→시각화 파이프라인) + /check 리뷰 반영
- **파일**:
  - ingest: `_http.py`, `dart.py`, `ftc.py`, `filing.py`
  - transform: `filters.py`, `kifrs.py`, `dedupe.py`
  - graph: `build.py`, `export.py`
  - viewer: `index.html` (프로토타입 fork)
  - common: `names.py`
  - storage: `models.py` (RelationRaw 추가)
  - skills: `relation-{collect,graph,audit}.md` (모듈 로컬 초안)
  - tests: 10개 파일, 116 케이스
- **테스트**: 116/116 통과
- **리뷰**: code-reviewer 지적 5건 중 3건 즉시 수정
  - [수정] `filters.is_personal_shareholder` — relate 빈 문자열 시 개인 판별 누락 (경로 B 추가)
  - [수정] `filing.py` — 동적 `__import__`로 dart.py 상수 참조 → `_TOP50_CSV` 직접 선언
  - [수정] `dart.py collect()` — idempotency 추가 (동일 bsns_year + source_type 먼저 DELETE)
  - [대응 보류] `kifrs` ratio=None 엣지 — 현재 CLI 실행 순서가 filters→kifrs→dedupe로 고정되어 실무 영향 없음. 향후 `run` 명령에서 순서 강제 명시 필요
  - [대응 보류] rl 콜론 구분자 — top50 기업명에 콜론 포함 없어 실질 문제 없음. 향후 구분자 교체 고려
  - [추가 개선] `_LEGAL_SUFFIXES`에 `"co"` 추가로 "Samsung Co" 같은 경우 정규화 개선
- **도메인 메모**:
  - **K-IFRS 1024호 분류 결과**: 93 엣지 = ftc_group 62 + associate 15 + investment 11 + subsidiary 5
  - **삼성 8개사** (005930·028260·032830·207940·009150·006400·010140·000810) 공정위 완전연결 28개 ✓
  - **현대차→기아 34.53%** associate ✓ (K-IFRS 관계기업)
  - **공정위 미지정 top50**: 한미반도체 1개 (자산 5조 미만, 정상)
  - **고아 노드 15개** — 금융지주(KB/신한/하나/우리/메리츠)·공기업(한국전력)·독립(HMM·KT&G·한미반도체·LIG) 등 예상 범위
  - **NAME_ALIASES 전략**: 공정위 정식 법인명("삼성에스디아이") → KRX 약칭("삼성SDI"), normalize 후 소문자·공백제거 키로 비교
  - **레이어 공존**: 같은 기업 쌍에 ftc_group(공정위)과 K-IFRS 지분 엣지 **공존 유지** — 학습자가 "공정위 계열 vs K-IFRS 특수관계자" 정의 차이를 시각적으로 대조 가능
