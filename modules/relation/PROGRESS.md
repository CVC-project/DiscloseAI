# Relation 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-04-20 (오후 — viewer iteration 최종 /check)
- **작업**: 최근 5커밋(viewer 평행 엣지 offset·동적 계산·multi-layer 버그픽스·UI/UX agent) 누적 리뷰 + Critical/Suggestion 반영
- **파일**:
  - `modules/relation/viewer/index.html` — `!isA &&` 화살표 가드, `PAD 0.0→0.5`, disclosure 분기 영문 타입 교체 + 경쟁 로직 복원
  - `modules/relation/viewer/CLAUDE.md` — 그룹핑 키·법선 통일 묵시 의존 경고, "부호 상쇄"→"무효화" 표현 정정, PAD 사유 문서화
  - `CLAUDE.md` (루트) — `## Agent`에 `ui-ux-reviewer` 등재
- **테스트**: 116/116 통과 (신규 Python 변경 없음, 회귀 확인만)
- **리뷰**: code-reviewer 지적 Critical 2 + Suggestion 3 + Nitpick 3 중 6건 반영
  - [수정] C1: 그룹핑 키(`init`)와 법선 통일(`draw`)의 묵시적 이름 기준 의존 — viewer/CLAUDE.md 경고 추가
  - [수정] C2: 공시 alert(`isA`) 상태에서 `globalAlpha=1.0`으로 K-IFRS 화살표가 의도치 않게 렌더 — `!isA &&` 가드
  - [수정] S1: `PAD=0.0`으로 두꺼운 선이 Z-order상 앞 선을 덮어 레이어 공존 훼손 — `PAD=0.5` 안티앨리어싱 마진 확보
  - [수정] S2: disclosure 모드 glow 레이블이 한국어 타입(`'공급'/'종속'/'피인수'/'경쟁'`)과 비교해 항상 false — 영문(`subsidiary`·`associate`·`competition`)로 교체 + 경쟁 분류 복원
  - [수정] S3: 루트 CLAUDE.md Agent 섹션에 `ui-ux-reviewer` 누락 — 등재 완료
  - [수정] N3: viewer/CLAUDE.md "부호 상쇄" 표현이 벡터 합산 오해 소지 — "무효화"로 교체
  - [미대응] N1 `_LEGACY_HARDCODED_RAW` 정리 / N2 SKILL.md 자기참조 경로 문구 — 선택적 지적, 후속 처리
- **도메인 메모**:
  - **경쟁 로직 상태**: 현재 `graph_top50.json`에는 `competition` 타입 엣지 0건(MVP는 지분·계열만). 레이블 분기는 v2에서 경쟁 관계 수집이 추가되면 자동 작동하도록 선제 반영한 것
  - **레이어 공존의 시각적 전제**: `PAD=0.5`는 절대값이 아닌 "두꺼운 쌍(subsidiary 2.5 + associate 2.0)에서 색상 혼동을 막는 최소값". 향후 두께 체계를 바꾸면 재조정 필요
  - **묵시적 정렬 의존 경고**: `init`의 그룹핑 키를 다시 티커(`t`)로 되돌리는 시도는 [viewer/CLAUDE.md](viewer/CLAUDE.md)의 "⚠️ 주의" 블록을 먼저 볼 것 — 한화오션·한화시스템 겹침 버그 재발 위험

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
