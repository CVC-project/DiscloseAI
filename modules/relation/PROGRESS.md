# Relation 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-07-21 — V0+U0 착수 (전 상장사 확장 · 브랜치 feat/relation-universe-v0)
- **작업**: universe/valuechain PLAN.md 재검토(코드 실측 보정, v1.4/v1.1) 승인 후
  V0(shared 승격+스키마)·U0(레지스트리+시총+섹터) 연속 실행. §6.1 드라이버 절차대로
  체크박스 이어달리기.
- **파일**:
  - 보안: `modules/report/llm.py`, `scripts/monitor_eqs_batch.ps1` — GPU 서버 IP·계정 평문 제거
  - V0 shared 승격: `shared/data/reports.db`(이동) + 경로 10곳(`modules/report/db.py` 외
    3파일, 테스트 1, 에이전트/스킬 문서 4+미러) + 루트 `CLAUDE.md`·`docs/ARCHITECTURE.md`
    §2·§3.5 예외 명문화
  - V0 스키마: `storage/models.py` — CompanyRegistry·CompanyAlias·ValueChainEdge·
    SectorIOEdge·VcChunk·VcPipelineState·LinkFailQueue 7테이블 신설 +
    RelationLocal에 status/superseded_by/rcept_no + UNIQUE 인덱스 (추가식,
    기존 50노드/93엣지 무손실)
  - U0 신규: `universe/registry.py`, `universe/marketcap.py`, `universe/sectors.py`,
    `universe/data/ksic_sector_map.csv`
  - `modules/relation/ingest/dart.py` — `fetch_dart_stock_to_corp_map()` 분리(재사용)
  - `modules/report/data/corps.csv` — 48→2,651행 확장(기존 48행 tier/cluster 보존)
  - `tests/report/test_report_pipeline.py` — `test_corps_csv_48`→`_full_universe` 개정
- **테스트**: report 43/43 · relation 114/114 PASS (전부 회귀, 신규 유닛테스트는 후속)
- **U0 게이트 판정** (게이트 재정의 후 — `universe/validate.py`, pytest 5/5 고정):
  - ✅ G1 registry ≥ 2,500 → **2,651사** (KOSPI 833 + KOSDAQ 1,818)
  - ✅ G2 named400 == 400 → **400** (KOSPI 200 + KOSDAQ 200)
  - ✅ G3 오염 0 → named400 **전부 보통주**(종목코드 끝자리 전부 0, 우선주 명칭 0건)
  - ✅ G4 섹터 미매핑 0 → **0건** (528 고유 KSIC 코드 → 25섹터, 전량 매핑)
  - ✅ G5 시총 근거 → named400 **전부 market_cap_krw 확보**
  - ✅ galaxy 파이프라인 회귀 무손상 → PASS (43/43 + check_golden 005930 PASS)
  - **게이트 재정의(리더 결정)**: 구 "KOSPI200 교집합 ≥90%"는 잘못 지정된 프록시.
    Wikipedia에서 실제 KOSPI200 200종목을 확보해 **정량 교집합을 실제로 계산 → 84%**
    (168/200). 90% 미달이지만 **오염이 아니라 방법론 차이**: 우리=순수 시총 상위 200,
    KOSPI200=시총+유동성+섹터균형+리츠/펀드 제외. 불일치 64건 전수 확인 결과 전부
    실제 기업·펀드(우리쪽 32엔 맥쿼리인프라·SK리츠 등 인프라펀드 3 + 최근 IPO
    시프트업·케이뱅크 등, 지수쪽 32엔 오뚜기·대상·하이트진로 등 시총 200위 밖
    중견주), **ETN·우선주·SPAC 오염 0건**. 순수 시총 선정으론 ~84%가 구조적 천장이라
    게이트를 **의도(오염 없는 건강한 유니버스)**로 재정의 → G1~G5로 직접 검증(전부 PASS).
    KOSPI200 교집합 84%는 `validate.kospi200_crosscheck()`의 정보용 참조로 보존.
- **도메인 메모**:
  - **pykrx·KRX 전면 차단**: KRX(data.krx.co.kr)가 이 환경 IP를 모든 엔드포인트에서
    `LOGOUT`으로 차단 — pykrx·getJsonData·OTP GenerateOTP 전부(세션 쿠키 확보해도 동일).
    데이터센터 IP 블랙리스트로 추정(GPU 서버가 IP 허용 필요했던 것과 같은 부류).
    **대체 경로 확정**: 상장목록=KIND 정적 다운로드(`kind.krx.co.kr/corpgeneral/
    corpList.do`), 시총=네이버금융 시가총액순 페이지(정렬·페이지네이션, 인증 불요),
    KOSPI200 구성종목(정보용)=English Wikipedia "KOSPI 200" 표 — 전부 실측 검증됨.
    ⚠️ Wikipedia는 반기 리밸런싱 stale 가능 → 정보용 크로스체크로만 사용(하드 게이트 아님).
  - **KIND 원본 데이터에 중복 행 37건**(동일 종목코드 2회 등장) — corp_code 기준
    upsert로 자연 해소, 별道 처리 불필요.
  - **KSIC 매핑 v1의 알려진 단순화**: 2차전지·디스플레이는 KSIC 고유 division이
    아니라 각각 26(전자부품)·20(화학)에 흡수됨 — 필요시 U2에서 상품명 휴리스틱
    보강 검토.
  - **report 수집 배치**: 2,651사 5개년 원문 수집을 백그라운드 개시(idempotent,
    DART 일 1만 건 한도 내 3~5일 예상). 이 세션 종료 시점 진행 상황은 `shared/data/
    reports.db`의 `report_raw` 행 수·distinct ticker로 확인(다음 세션이 자동 이어감
    — corps.csv 순회 로직 자체가 already-collected 스킵).
  - **다음 세션**: report 수집 배치 진행 확인 → U1(DART 2종 전수 확장·FTC 스타
    전환·filters Registry 교체·V-1 계약 체커) 착수. universe/valuechain PLAN.md
    §6.0 순서 그대로 이어감(계획 재수립 불필요).

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
