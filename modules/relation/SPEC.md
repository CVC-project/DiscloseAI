# DiscloseAI — Relation 모듈 MVP (지분·계열, 코스피 상위 50개)

> **이 문서의 역할 — SPEC (Single Source of Truth)**
>
> Relation 모듈의 Phase 1·2 전체 상세 명세. 함수 시그니처·테스트 fixtures·완료 기준·리스크 포함.
> **설계 변경 시에만** 업데이트 (자주 갱신되는 진행 상태는 [PLAN.md](PLAN.md)에).
>
> 관련 문서:
> - [PLAN.md](PLAN.md) — 진행 상태 체크리스트 + Phase 개략 (매 세션마다 갱신)
> - [CLAUDE.md](CLAUDE.md) — 루트 지도 (세션 시작 시 자동 로드)
> - 서브폴더 각 `CLAUDE.md` — 해당 폴더 작업 시 on-demand 로드
>
> 다음 세션 재개 순서: ① [PLAN.md](PLAN.md) 읽어 현재 Phase 확인 → ② 필요 시 본 SPEC.md의 해당 Phase 2X 섹션 상세 참조 → ③ 작업할 폴더의 `CLAUDE.md` 자동 로드.

## Context

**왜 이 작업을 하는가**
- DiscloseAI의 4대 핵심 기능 중 "기업 우주" + "공시 파문"은 기업 간 관계 그래프가 데이터의 근간. 공시 발생 시 파급효과를 시각화하려면 "누가 누구와 얼마나 연결됐는지"가 선결 조건.
- PRD 원안은 2,600개 전수 + 4종 관계(지분·계열·공급·경쟁)이지만 대회 마감(2026-05-08)까지 약 3주. 공급·경쟁은 한국 공개 데이터가 빈약하고 파싱 공수가 과다.
- 결정: **MVP 범위 = 코스피 시총 상위 50개(삼성전자우·KODEX200 제외) × 지분+계열 2종만**. 공급·경쟁은 v2로 연기.

**최종 목표 산출물 (Phase 1 + Phase 2)**
1. 50개 기업 × 지분·계열 엣지가 담긴 `graph_top50.json`
2. JSON을 fetch로 로드해 파문·클러스터링을 그리는 `modules/relation/viewer/index.html`
3. 모든 수집·파싱·그래프 구축·테스트가 자동화된 파이프라인

**이번 세션(Phase 1) 범위만**: 폴더·스켈레톤·CLAUDE.md 6개 초안·`top50.csv` 초안·의존성 갱신까지. **실제 수집·분류·그래프 로직은 Phase 2a~2h 세션에서 폴더별로 파고드는 방향**. "빈 집을 짓되 각 방의 설계도는 완비" 전략.

---

## 데이터 소스 — 삼성전자(005930) 기준 구체 예시

**시각화 원칙: 노드는 "상장 법인"만.** 개인 주주(이재용·홍라희 등)·공익재단·비상장 특수관계법인은 hyslrSttus 응답에서 받지만 **노드 생성 안 함**. target이 `top50.csv` 종목코드 리스트에 있을 때만 엣지 생성(자연 필터). 개인·비상장 메타데이터는 로컬 DB에 `source_type="hyslrSttus"`로만 기록하여 감사 추적(audit trail)에 사용하고, 그래프 export에서는 제외.

### 1. 지분 관계 (DART OpenAPI 정형 API 2개)

| 엔드포인트 | 의미 | 삼성전자 예시 응답 (노드화 대상만 굵게) |
|---|---|---|
| `hyslrSttus.json` | **들어오는 지분** (최대주주 및 특수관계인) | 이재용 1.63%·홍라희 0.69% (개인, 제외) / 삼성생명공익재단 0.08% (비상장 법인, 제외) / **삼성물산 5.01%** / **삼성생명 8.51%** ← top50 소속이므로 엣지 생성 |
| `otrCprInvstmntSttus.json` | **나가는 지분** (타법인 출자현황) | 삼성디스플레이(비상장, 제외) / **삼성SDI 19.58%** / **삼성바이오로직스 43.44%** / **삼성물산 17.64%** |

- 요청: `corp_code=00126380` (DART 내부 8자리 코드, 종목코드 005930과 다름), `bsns_year=2024`, `reprt_code=11011`(사업보고서)
- 인증: 쿼리스트링 `?crtfc_key={DART_API_KEY}`
- 50개 × 2개 엔드포인트 = **100회 호출** (일일 한도 10,000 대비 여유)
- **엣지 생성 규칙**: target의 종목코드(또는 기업명 정규화)가 `top50.csv`에 있을 때만 엣지 생성. 양방향 호출 결과 중복 제거(같은 엣지가 A→B에서도 B→A에서도 나올 수 있음, higher ratio 채택).

### 2. 계열 관계 (4단계 폴백: 공정위 API → K-IFRS 지분율 분류 → 주석 파싱(미포함 한정) → 수동 보정)

**정확도 우선 전략**: 교육용 자료이므로 K-IFRS 법정 분류를 최대한 충실히 따르되, 공정위 API가 커버하는 공식 계열은 중복 파싱 없이 재사용하여 공수 절약.

#### 단계 1: 공정위 OpenAPI (공식 계열) — `source_type="ftc"`, `relation_type="ftc_group"`
공정위 기업집단포털(egroup.ftc.go.kr)은 공공데이터포털(data.go.kr)과 연계되어 OpenAPI 제공. **data.go.kr 인증키 1개로 여러 API 호출 가능** (API별 "활용신청"만 각각). `.env`에 `FTC_API_KEY=` 1개만 추가.

**실제 활용신청 완료된 10종** (2026-04-19). MVP 구현 우선순위:

| 구분 | API | 용도 |
|---|---|---|
| **MVP 필수** | 지정된 대규모기업집단 조회 서비스 | 기업집단 코드·명 목록 — 반복 호출 진입점 |
| **MVP 필수** | 지정된 대규모기업집단 소속회사 조회 서비스 | 기업집단코드 → 소속회사 매핑 — **계열 엣지 생성의 핵심** |
| **MVP 필수** | 사용 가능 공개년월 조회 서비스 | 최신 지정 데이터 기준 시점 (연 1회 5월 지정) |
| **MVP 보조** | 지주회사 자회사 및 손자회사 현황 | SK·LG·한화 등 지주사 구조 보강 |
| **MVP 보조** | 특수관계인 내부지분 현황 | DART `hyslrSttus`와 **교차 검증** (교육용 "공정위 vs DART" 대조) |
| **MVP 보조** | 지정된 대규모기업집단 자산순위 | 노드 크기·정렬 메타데이터 보강 |
| v2 연기 | 대규모기업집단 소속회사 재무현황 | financial 모듈 영역과 중복 |
| v2 연기 | 대규모기업집단 소속회사 참여업종 | top50.csv sector 수동 매핑으로 이미 대체 |
| v2 연기 | 계열 편입/제외/유예 변경내역 | 시계열 애니메이션용 |
| v2 연기 | 기업집단별 순환출자 현황 | 고급 분석 |

**MVP에서 제외**: 소속회사 주주현황·소속회사 개요 — 활용신청하지 않음 (애초 권장 API였으나 사용자 선택으로 제외). DART 크로스체크는 "특수관계인 내부지분" API로 대체.

**구현 우선순위 (Phase 2b)**: MVP 필수 3종 먼저 → 작동 확인 후 MVP 보조 3종 추가. v2 연기 4종은 스켈레톤만 유지.

- **엣지 생성**: 같은 group_code에 속한 50개 기업끼리 완전연결(undirected). 예: 삼성 그룹 8개사 간 C(8,2)=28개 엣지.
- **커버 예상**: 50개 중 ~47~49개 (삼성·SK·현대차·LG·한화·포스코·두산·카카오·NAVER·메리츠·LIG·HD현대·효성·영풍·HMM·KT&G·미래에셋·에코프로 등 공정위 자산 5조+ 공시대상기업집단은 대부분 포함). **공정위가 공식 확정한 계열 정보이므로 중복 파싱 불필요.**

#### 단계 2: K-IFRS 1024호 기반 지분율 자동 분류 — `source_type="ownership"`
이미 수집한 지분 데이터(hyslrSttus·otrCprInvstmntSttus)로 K-IFRS 특수관계자 분류를 자동 생성. 공정위 "계열"(동일인 지배 개념)과 **별개의 레이어**로 제공 — 학습자가 "지분율 → 관계 유형" 판정 로직을 시각에서 배울 수 있음.

| 지분율 | relation_type | K-IFRS 의미 | 시각 |
|---|---|---|---|
| > 50% | `subsidiary` | 지배기업-종속기업 (control) | 실선 굵게, 진한 빨강 `#ef4444` |
| 20% ~ 50% | `associate` | 관계기업 (significant influence) | 실선 중간, 주황 `#f97316` |
| 5% ~ 20% | `investment` | 유의적 투자 (MVP는 선택적 표시) | 얇은 점선, 회색 `#94a3b8` |
| < 5% | (제외) | 일반 투자 | 엣지 없음 |

- **공정위 계열 엣지와 공존 가능**: 같은 두 기업 사이에 `ftc_group`(계열) + `subsidiary`(지배) 엣지가 둘 다 있을 수 있음. 학습자가 "공정위 정의 vs K-IFRS 정의 차이"를 볼 수 있음.
- **교육 라벨**: 호버 시 툴팁에 "삼성전자 → 삼성바이오로직스: 43.4% (관계기업). 20% 넘으면 K-IFRS상 유의적 영향력이 인정됩니다" 같은 설명 자동 생성.

#### 단계 3: 공정위 미포함 기업 한정 주석 파싱 — `source_type="dart_filing"`
공정위 API 결과에서 group_code가 null로 남은 기업(예상 1~3개, 한미반도체 등)에 한해 **DART 사업보고서 주석의 "특수관계자" 섹션**을 HTML 파싱. 공정위 커버 기업은 중복 파싱하지 않음.

- **대상 선정**: 단계 1 완료 후 자동 식별 — `SELECT * FROM company_node WHERE group_name IS NULL`
- **파싱 방법**:
  1. DART `document.json?rcept_no={사업보고서접수번호}`로 ZIP 다운
  2. 내부 XML 중 "III. 재무에 관한 사항" → "주석" → "특수관계자 공시" 섹션 추출
  3. HTML 테이블에서 기업명·관계(지배/종속/관계/공동) 컬럼 파싱
  4. 파싱된 기업명을 top50 ticker로 정규화 매칭 (기업명 → corp_code 매핑 테이블 활용)
- **예상 공수**: 대상이 1~3개이므로 +2~3시간. 회사별 포맷 예외가 적음(대상 자체가 적으므로).
- **실패 시 fallback**: 파싱 실패하면 단계 4(수동 보정)로 내려감.

#### 단계 4: 수동 보정 — `source_type="manual"`
단계 1·2·3을 거치고도 group_name이 비어있거나 CPA 감각으로 보정이 필요한 경우만 `modules/relation/data/manual_overrides.csv`에 수동 기입. 실전에서 0~2건 예상.

#### 데이터 소스 우선순위 정리
```
동일 기업 쌍 (A, B) 에 대해:
  ftc_group (공식 계열) ─┐
  subsidiary/associate (K-IFRS 지분) ─┤→ 모두 별도 엣지로 저장, viewer에서 레이어 선택 가능
  dart_filing (공정위 미포함 주석) ──┤
  manual (수동 보정) ────────────────┘
```

---

## 저장 설계 (로컬 SQLite 우선)

### 스키마 갱신 범위
- **지금**: `modules/relation/storage/models.py`의 `RelationLocal`에 컬럼 추가 (ratio, source_type, bsns_year, group_name) + `CompanyNode` 신설. 로컬 범위 한정.
- **다음 PR**: MVP 검증 완료 후 `shared/models.py` 동기화 (프로젝트 리드 역할로 별도 PR).

### 파이프라인 계층 ↔ 폴더 매핑
```
① ingest/       DART·FTC·주석 원천 획득  → RAW JSON 캐시(data/raw_cache/) + RelationRaw 테이블
        ↓
② transform/    필터·K-IFRS 분류·중복제거 → RelationRaw를 읽어 RelationLocal 테이블로 마이그레이션
        ↓
③ graph/        MultiDiGraph 구축         → RelationLocal + CompanyNode → in-memory nx.MultiDiGraph
        ↓
④ graph/export  JSON 스냅샷              → data/graph_top50.json (프로토타입 호환 스키마)
        ↓
⑤ viewer/       Canvas 렌더              → 브라우저에서 fetch
```

### 테이블 3개 (`storage/models.py`)
- `CompanyNode`(신규): corp_code, corp_name, ticker, market_cap, sector, group_name, is_target
- `RelationRaw`(Phase 2a 선행 작업으로 신설): source_name(String 무제약), target_name(String 무제약), raw_response(JSON/Text), source_type, bsns_year, ratio, created_at. ingest 단계가 원본 기업명 그대로 저장 → transform이 ticker 매칭 후 RelationLocal로 마이그레이션
- `RelationLocal`(컬럼 확장): source_corp(String(6) ticker), target_corp(String(6) ticker), relation_type("ftc_group"/"subsidiary"/"associate"/"investment"/"dart_filing"/"manual"), ratio(Float), detail(String), source_type, bsns_year, group_name

---

## 우주맵 시각화 (`modules/relation/viewer/index.html`)

### 전략: "프로토타입 스키마 호환 JSON"
기존 `docs/prototype/corporate_universe_v5.html`의 `raw=[]` 구조를 유지하되 `rl:['대상명:타입:상세']` 3-필드로 확장. 기존 `physics()`, `draw()`는 거의 그대로 재사용.

### `viewer/index.html` — 프로토타입 fork 시 3곳만 변경
1. `const raw=[...]` → `let raw=[]; fetch('../data/graph_top50.json').then(r=>r.json()).then(d=>{raw=d; init(); tick();});`
2. `init()` 내부 `r.split(':')` → 3-split로 수정, `edges.push({a,b,type,ratio,detail})`
3. `draw()` 엣지 루프에 `relation_type`별 분기 추가 (viewer/CLAUDE.md의 스타일 표 참조):
   - `subsidiary`: 실선 `#ef4444`, 2px
   - `associate`: 실선 `#f97316`, 1.5px
   - `investment`: 점선 `[2,3]`, `#94a3b8`, 0.8px
   - `ftc_group`: 점선 `[4,2]`, `#fbbf24`, 1px
   - `dart_filing`: 점선 `[6,2]`, `#facc15`, 1px
   - `manual`: 점선 `[2,2]`, `#a78bfa`, 0.8px

원본 `docs/prototype/corporate_universe_v5.html`은 건드리지 않음 (다른 팀원 참고용).

### sectors 확장
기존 8개(반도체/디스플레이/2차전지/바이오/자동차/금융/플랫폼/에너지)에 50개 기업 분포를 보고 4개 추가:
- **중공업·방산** (한화에어로·HD현대중공업·두산에너빌리티·한화시스템·한국항공우주·현대로템 등)
- **건설** (현대건설·HD한국조선해양)
- **통신** (SK텔레콤)
- **기타** (KT&G·HMM)

---

## Harness 구조 — 파이프라인 단계별 폴더 조직

### 설계 원칙 (PRD 4.4.2 Harness Engineering)
1. **"지도를 주되 백과사전 X"** — 루트 CLAUDE.md는 짧게, 서브폴더 CLAUDE.md는 on-demand 로드
2. **Single Responsibility** — 폴더 1개 = 파이프라인 단계 1개. "공정위 API 변경" → `ingest/ftc.py`만, "K-IFRS 임계값 변경" → `transform/kifrs.py`만
3. **Progressive Disclosure** — 작업 시 필요한 폴더 CLAUDE.md만 로드되어 context 절약
4. **"에이전트가 볼 수 없으면 존재하지 않음"** — API 파라미터·K-IFRS 조문·색상 규칙 등을 각 CLAUDE.md에 명시
5. **확정 규칙 = 코드 상수 / 권장 규칙 = CLAUDE.md** — SUBSIDIARY_THRESHOLD=50 같은 임계값은 Python 상수로, "기업명 정규화 예외" 같은 휴리스틱은 마크다운으로

### 폴더 구조

```
modules/relation/
├── CLAUDE.md                        ← 루트(~40줄): 담당 범위, 데이터 흐름, 진입점, 외부 의존
├── CLAUDE.local.md                  ← 개인 설정 (.gitignore, 기존)
├── PROGRESS.md                      ← /check가 기록 (기존)
├── __init__.py
├── __main__.py                      ← CLI 진입점: python -m modules.relation <cmd>
│
├── ingest/                          ← 단계 1: 원천 데이터 획득 (순수 I/O, 가공 없음)
│   ├── CLAUDE.md                    ← DART·FTC 파라미터 표, rate limit 정책, 재시도 규칙
│   ├── __init__.py
│   ├── dart.py                      ← hyslrSttus + otrCprInvstmntSttus 호출
│   ├── ftc.py                       ← 공정위 OpenAPI 호출
│   └── filing.py                    ← 공정위 미포함 기업의 사업보고서 주석 다운·파싱
│
├── transform/                       ← 단계 2: 정제·분류 (도메인 규칙 집약)
│   ├── CLAUDE.md                    ← K-IFRS 1024 임계값, 개인·비상장 필터, 기업명 정규화
│   ├── __init__.py
│   ├── filters.py                   ← 개인·공익재단 제외, top50 target 매칭
│   ├── kifrs.py                     ← 지분율 → subsidiary/associate/investment 분류 (상수 정의)
│   └── dedupe.py                    ← 양방향 엣지 중복 제거 (higher ratio 채택)
│
├── graph/                           ← 단계 3: 그래프 구축 (in-memory)
│   ├── CLAUDE.md                    ← MultiDiGraph 스키마, 노드·엣지 속성, 레이어 공존 규칙
│   ├── __init__.py
│   ├── build.py                     ← RelationLocal → MultiDiGraph 로드
│   └── export.py                    ← nx.node_link_data → graph_top50.json (프로토타입 호환)
│
├── viewer/                          ← 단계 4: 프레젠테이션
│   ├── CLAUDE.md                    ← Canvas 2D API, sectors 색상 규칙, relation_type별 스타일 표
│   └── index.html                   ← 프로토타입 fork + fetch 로더 + relation_type 분기 + K-IFRS 툴팁
│
├── storage/                         ← 저장 계층 (로컬 SQLite)
│   ├── CLAUDE.md                    ← RelationLocal·CompanyNode 스키마, Supabase 이전 계획
│   ├── __init__.py
│   ├── models.py                    ← (기존 ../models.py에서 이동 + 컬럼 확장)
│   └── db.py                        ← (기존 ../db.py에서 이동)
│
├── skills/                          ← 도메인 스킬 **초안** (모듈 로컬, Phase 2g에서 작성)
│   ├── relation-collect.md          ← 개발 중 — 승격 PR로 .claude/skills/로 이동 예정
│   ├── relation-graph.md
│   └── relation-audit.md
│
└── data/                            ← 데이터 파일
    ├── top50.csv                    ← 50개 기업 마스터 (commit)
    ├── manual_overrides.csv         ← 수동 보정 (commit, 실전 0~2건)
    ├── relation.db                  ← SQLite (gitignored)
    └── graph_top50.json             ← graph/export.py 결과물 (gitignored)
```

### 테스트 구조 (1:1 대응)
```
tests/relation/
├── conftest.py                      ← fixtures: 삼성전자 샘플 응답, 공정위 샘플, DB 세션
├── test_ingest/
│   ├── test_dart.py                 ← hyslrSttus·otrCprInvstmntSttus 모킹
│   ├── test_ftc.py                  ← 공정위 API 모킹 (삼성 그룹 8개사 매칭)
│   └── test_filing.py               ← 주석 HTML 샘플 파싱
├── test_transform/
│   ├── test_filters.py              ← 개인 제외·top50 매칭 검증
│   ├── test_kifrs.py                ← 43% → associate, 51% → subsidiary 등 경계값
│   └── test_dedupe.py               ← A→B 5%, B→A 19% 쌍에서 19% 채택
├── test_graph/
│   ├── test_build.py                ← MultiDiGraph 노드·엣지 생성
│   └── test_export.py               ← JSON 스키마 검증, 같은 쌍 다중 relation_type 공존
└── test_storage/
    └── test_models.py               ← CompanyNode·RelationLocal 컬럼 CRUD
```

### CLI 진입점 (`modules/relation/__main__.py`)

```bash
# 초기화
python -m modules.relation init                    # 로컬 DB + 스키마 생성

# 단계별
python -m modules.relation collect dart            # DART 수집 (--corp 005930 옵션)
python -m modules.relation collect ftc             # 공정위 수집
python -m modules.relation collect filing          # 주석 파싱 (공정위 미포함만)
python -m modules.relation collect all             # 3개 순차

python -m modules.relation transform               # 정제·분류·중복제거
python -m modules.relation graph                   # MultiDiGraph 구축
python -m modules.relation export                  # graph_top50.json 생성

# 통합
python -m modules.relation run                     # collect all → transform → graph → export
python -m modules.relation audit                   # 무결성 체크 (도메인 검증)
```

### 도메인 Skill — "모듈 내 개발 → 안정화 → 전역 승격" 2단계 전략

**문제**: `.claude/skills/`는 프로젝트 전역 공간이라 draft 상태 스킬을 여기 바로 두면 다른 팀원 세션(financial/disclosure/price)에도 노출됨. 관련 코드와의 응집도도 깨짐.

**해결**: 스킬도 모듈 로컬 자산으로 취급. `modules/relation/skills/`에서 개발·검증 후 안정화되면 `.claude/skills/`로 이동하는 별도 PR로 승격.

```
개발 단계:
  modules/relation/skills/relation-collect.md
                         /relation-graph.md
                         /relation-audit.md
           ↓ 안정화 + self-테스트 통과
승격 PR (리더 역할):
  .claude/skills/relation-collect/SKILL.md  (전역에서 /relation-collect로 호출 가능)
  .claude/skills/relation-graph/SKILL.md
  .claude/skills/relation-audit/SKILL.md
```

| Skill | 호출 | 자동 | 기능 |
|---|---|---|---|
| `/relation-collect` | 수동 | false | `python -m modules.relation collect all` 실행 + 결과 요약 |
| `/relation-graph` | 수동 | false | `python -m modules.relation transform && graph && export` + node/edge 카운트 리포트 |
| `/relation-audit` | 자동 가능 | true | 삼성 그룹 완전연결·기아·현대차 상호지분·고아 노드 검사 |

**승격 기준 (Phase 2g에서 체크)**:
- 스킬이 참조하는 CLI 명령이 실제로 동작함 (`--help` 이상의 실제 실행 통과)
- 해당 폴더(ingest/transform/graph 등)의 테스트가 모두 통과
- 최소 1회 수동 호출로 기대 출력 확인

**모듈 로컬 단계의 한계**: `modules/relation/skills/`는 Claude Code가 자동 로드하지 않음. 해당 단계에서는 "문서/초안"으로만 기능하고, 실제 `/relation-collect` 호출 테스트는 승격 PR 이후에만 가능. → 초안 검증은 "스킬 파일을 수동으로 읽어 내용대로 명령을 실행"하는 방식으로 수행.

### 신규·수정 파일 요약

| 상태 | 경로 | 비고 |
|---|---|---|
| 신규 | `modules/relation/CLAUDE.md` | 루트 지도 |
| 신규 | `modules/relation/__main__.py` | CLI (argparse) |
| 신규 | `modules/relation/ingest/{CLAUDE.md, __init__.py, dart.py, ftc.py, filing.py}` | 단계 1 |
| 신규 | `modules/relation/transform/{CLAUDE.md, __init__.py, filters.py, kifrs.py, dedupe.py}` | 단계 2 |
| 신규 | `modules/relation/graph/{CLAUDE.md, __init__.py, build.py, export.py}` | 단계 3 |
| 신규 | `modules/relation/viewer/{CLAUDE.md, index.html}` | 단계 4 |
| 신규 | `modules/relation/storage/{CLAUDE.md, __init__.py}` | 저장 래퍼 |
| 신규 | `modules/relation/data/{top50.csv, manual_overrides.csv}` | 마스터 데이터 |
| 신규 | `tests/relation/{conftest.py, test_ingest/, test_transform/, test_graph/, test_storage/}` | 1:1 테스트 |
| 신규 | `modules/relation/skills/{relation-collect, relation-graph, relation-audit}.md` | **모듈 로컬** 스킬 초안 (Phase 2g에서 작성) |
| 승격 PR | `.claude/skills/{relation-collect, relation-graph, relation-audit}/SKILL.md` | 안정화 후 별도 리더 PR로 전역 이동 (Phase 2 이후) |
| 이동 | `modules/relation/models.py` → `modules/relation/storage/models.py` (+ 컬럼 확장) | 책임 분리 |
| 이동 | `modules/relation/db.py` → `modules/relation/storage/db.py` | 책임 분리 |
| 수정 | `requirements.txt` | `requests>=2.31`, `networkx>=3.2`, `pandas>=2.1`, `beautifulsoup4>=4.12`(주석 HTML 파싱용), `lxml>=5.1` 추가 |
| 수정 | `.env.example` + `shared/config.py` | `FTC_API_KEY` 추가 — 리더 권한 |
| 수정 | `modules/relation/CLAUDE.local.md` | 기존 유지, 하위 참조 추가 |

### 건드리지 않음
- `shared/models.py` (MVP 검증 후 별도 PR로 동기화)
- `docs/prototype/corporate_universe_v5.html` (원본 보존, viewer/index.html이 fork)
- 타 팀원 모듈 (`modules/financial`, `disclosure`, `price`)

---

## 재사용 자산

- **환경변수 패턴**: [shared/config.py:9](shared/config.py#L9)의 `DART_API_KEY` 그대로 재사용 (`from shared.config import DART_API_KEY`) + `FTC_API_KEY` 신규 항목을 같은 파일에 추가 (리드 권한 수정)
- **로컬 DB 패턴**: [modules/relation/db.py:7-22](modules/relation/db.py#L7-L22)의 `init_local_db()` / `get_local_session()`을 `storage/db.py`로 이동 후 그대로 사용
- **dart-fss 라이브러리**: `get_corp_list()` → corp_code 8자리 매핑에만 활용 (ingest/dart.py 내부). 지분 엔드포인트는 지원 빈약하므로 `requests` 직접 호출
- **NetworkX API**: `nx.MultiDiGraph`(같은 쌍에 relation_type 다른 엣지 공존), `G.add_edge(u, v, relation_type=..., ratio=..., detail=...)`, `nx.node_link_data(G)` → D3/Canvas 바로 호환 JSON
- **프로토타입 엔진**: `init()`, `physics()`, `draw()` ([docs/prototype/corporate_universe_v5.html:231-233](docs/prototype/corporate_universe_v5.html#L231-L233)) 로직을 viewer/index.html로 fork. 원본은 보존.
- **Harness 템플릿**: 이 폴더 구조(ingest/transform/graph/viewer/storage)는 `financial/`·`disclosure/`·`price/` 팀원이 동일 패턴으로 차용 가능 — 팀 표준 참조 구현

---

## 네(리더·C 팀원)가 해야 할 일

### 사람만 할 수 있는 것
1. **DART 인증키 발급·입력**: opendart.fss.or.kr 회원가입 → 인증키 신청 → `.env`에 `DART_API_KEY=` 입력 ✅ **완료됨**
2. **공공데이터포털(FTC) 인증키 + 10개 API 활용신청** ✅ **완료 (2026-04-19)**
   - MVP 필수 3 + MVP 보조 3 + v2 연기 4 = 10종 활용신청 승인
   - `.env`에 `FTC_API_KEY=` 추가 완료
3. **50개 기업 CSV 검수**: Claude가 초안을 만들면 corp_code(8자리 DART 코드) ↔ ticker(6자리) 매핑이 틀린 곳 없는지 CPA 눈으로 확인 (특히 LIG디펜스·메리츠금융지주·효성중공업 등 분할·상호 변경 이력 있는 곳)
4. **manual_overrides.csv 보정**: 공정위 API 호출 후 group_name=null로 남는 독립기업 리스트를 Claude가 제시하면 CPA 감각으로 그룹 귀속 판단 (예: 메리츠금융지주→메리츠, LIG디펜스→LIG 등)
5. **수집 결과 도메인 검증**: 수집 후 RelationLocal 조회하여 삼성전자↔삼성SDI 19.58%, 기아↔현대차 33.88%, 삼성바이오로직스↔삼성물산 43.06% 등 본인이 아는 대주주 지분율이 실제와 맞는지 확인
6. **시각 QA**: viewer.html 열어서 삼성 8개사·SK 그룹·현대 그룹 클러스터가 실제로 인접 배치되는지 눈으로 확인 (개인 주주가 노드로 나타나지 않는지 포함)

### Claude가 자동으로 할 것
- Harness 골격(폴더 5개 + CLAUDE.md 5개 + CLI 진입점) 생성
- 50개 기업 corp_code 매핑 초안 작성 (dart-fss `find_by_stock_code` 활용)
- DART·공정위 API 호출·응답 파싱·로컬 DB 저장 (ingest/)
- K-IFRS 지분율 자동분류·중복제거 (transform/)
- NetworkX MultiDiGraph → JSON export (graph/)
- viewer/index.html fork·수정 (relation_type별 스타일 + K-IFRS 툴팁)
- pytest 테스트 1:1 대응 자동 생성 및 실행
- `modules/relation/skills/relation-*.md` 도메인 스킬 3개 초안 작성 (이후 별도 PR로 `.claude/skills/`로 승격)
- `/check` 실행 시 코드 리뷰 + PROGRESS.md 기록

---

## 작업 순서

**사용자 방침**: "일단 폴더 구조 + 최소 스켈레톤까지 만들고, 개발하면서 각 폴더를 파고드는 방향."

### Phase 1 — Harness 스켈레톤 (이번 세션 범위)

이번 세션의 목표는 **폴더·파일 뼈대 + 각 CLAUDE.md 초안까지**. 실제 로직은 다음 세션부터.

1. **Step 0 (30분) — 폴더 구조 생성**
   - `modules/relation/` 아래 `ingest/`, `transform/`, `graph/`, `viewer/`, `storage/`, `data/` 폴더 생성
   - 각 폴더에 빈 `__init__.py`
   - 기존 `modules/relation/models.py`·`db.py`를 `storage/`로 이동

2. **Step 1 (1시간) — CLAUDE.md 6개 초안 작성**
   - `modules/relation/CLAUDE.md` — 루트 지도 (~40줄): 담당 범위, 데이터 흐름 다이어그램, 서브폴더 1줄씩 요약, CLI 진입점, 외부 의존(DART/FTC), 하위 CLAUDE.md 목록
   - `ingest/CLAUDE.md` — DART·FTC 파라미터 표, rate limit 정책, 재시도 규칙
   - `transform/CLAUDE.md` — K-IFRS 1024 임계값(상수 SUBSIDIARY_THRESHOLD=50 등), 개인·비상장 필터, 기업명 정규화
   - `graph/CLAUDE.md` — MultiDiGraph 스키마, 노드·엣지 속성, relation_type 레이어 공존 규칙
   - `viewer/CLAUDE.md` — Canvas 2D API, sectors 색상, relation_type별 스타일 표
   - `storage/CLAUDE.md` — 테이블 스키마, 로컬 SQLite 위치, Supabase 이전 계획

3. **Step 2 (30분) — 빈 파일 스켈레톤**
   - `__main__.py` — argparse 기반 CLI 진입점 초안 (명령만 정의, 구현은 `raise NotImplementedError`)
   - `ingest/{dart.py, ftc.py, filing.py}` — 함수 시그니처 + docstring만
   - `transform/{filters.py, kifrs.py, dedupe.py}` — 함수 시그니처 + 상수 정의
   - `graph/{build.py, export.py}` — 함수 시그니처
   - `viewer/index.html` — 비어 있는 HTML (프로토타입 참조 주석)
   - `storage/{models.py, db.py}` — 이동된 기존 파일 + CompanyNode 테이블 추가·RelationLocal 컬럼 확장

4. **Step 3 (30분) — 마스터 데이터 초안**
   - `data/top50.csv` — 50개 기업 corp_code·ticker·market_cap 초안 (사용자 검수 대상)
   - `data/manual_overrides.csv` — 빈 헤더만

5. **Step 4 (30분) — 의존성·환경**
   - `requirements.txt`에 `requests>=2.31`, `networkx>=3.2`, `pandas>=2.1`, `beautifulsoup4>=4.12`, `lxml>=5.1` 추가
   - `shared/config.py`에 `FTC_API_KEY = os.getenv("FTC_API_KEY", "")` 추가 (리더 권한)
   - `.env.example`에 `FTC_API_KEY=` 줄 추가 — settings.json의 `Edit(.env.*)` deny로 차단되므로 사용자 수동 추가 필요
   - ⚠️ `.env` 실파일은 `DART_API_KEY`만 있고 `FTC_API_KEY=`는 **사용자가 직접 IDE에서 추가** (Claude 편집 차단)

6. **Step 5 (30분) — 검증**: 스켈레톤만으로 `python -m modules.relation --help`가 에러 없이 실행되는지 + 기존 smoke test `pytest tests/test_smoke.py`가 여전히 통과하는지 → `feat/relation` 커밋

**Phase 1 총 예상**: 약 3.5시간. 이 시점의 산출물 = "빈 집". 각 방의 설계도(CLAUDE.md)는 완비, 가구(실제 로직)는 Phase 2에서 하나씩 채움.

---

### Phase 2 이후 — 실제 구현 (다음 세션부터)

한 폴더씩 "파고든다". 한 폴더 완료 시마다 `/check`로 테스트·커밋.

> 이 섹션은 Phase 2 전체의 **실행 가이드**. 각 Phase 2X는 의존성·산출물·하위 Step·함수 시그니처·테스트 fixtures·완료 기준을 포함해 Claude가 다음 세션에서 단독으로 재개할 수 있도록 작성됨.

#### 의존성 그래프

```
2a (dart.py)   ─┐
2b (ftc.py)    ─┤→ 2d (transform) → 2e (graph) → 2f (viewer) → 2g (skills) → 2h (/check+PR) → 2i (스킬 승격 PR)
2c (filing.py) ─┘

2a, 2b는 독립 병렬 가능. 2c는 2b(CompanyNode.group_name) 실행 후 식별 가능.
단 각 단계는 자체 fixture로 단위 테스트 독립. 실제 수집·스모크는 순서 준수.
```

#### 공통 인프라 (Phase 2a 시작 전 선행 작업)

| 새 자산 | 위치 | 역할 |
|---|---|---|
| HTTP 유틸 | `modules/relation/ingest/_http.py` | `requests.Session` + 재시도 3회(1·2·4초 backoff) + rate limit 0.2초 + DART status 핸들링(`000` ok, `013` 데이터없음, `800` 인증실패, `900` 원본없음) + RAW 캐시 |
| 기업명 정규화 | `modules/relation/common/names.py` | `normalize_company_name(name)` 공용 함수 (ingest·transform 양쪽 사용, 순환 의존 회피) |
| RAW 테이블 | `storage/models.py`의 `RelationRaw` | 원본 기업명 그대로 저장 (source_name·target_name 무제약 String). Phase 2d transform이 ticker 매칭 후 `RelationLocal`로 이동 |
| RAW 캐시 | `modules/relation/data/raw_cache/` | API 재호출 회피용 (.gitignore 이미 적용) |

**선행 작업 체크**:
- [ ] `storage/models.py`에 `RelationRaw` 테이블 추가 (source_name String, target_name String, raw_response JSON, source_type, bsns_year, created_at)
- [ ] `ingest/_http.py` 작성 (dart_get, ftc_get 두 함수)
- [ ] `common/__init__.py` + `common/names.py` 작성

---

### Phase 2a — ingest/dart.py (2.5h)

**의존**: 공통 인프라(`_http.py`, `RelationRaw`)
**산출물**: DART RAW 응답 캐시 + `RelationRaw` 테이블에 원본 데이터 저장 + `top50.csv`의 `corp_code` 컬럼 갱신

**하위 Step**
1. **2a.1 — corp_code 매핑 (one-off)**: CLI 서브커맨드 `python -m modules.relation map-corp-codes` 신설 → dart-fss `get_corp_list()` 1회 호출 → top50 ticker 각각 `find_by_stock_code()` → `top50.csv`의 `corp_code` 컬럼 채워서 저장. 이후 commit
2. **2a.2 — fetch_shareholders**: `hyslrSttus.json` 호출, 우선주 포함 저장 (필터는 transform)
3. **2a.3 — fetch_investments**: `otrCprInvstmntSttus.json` 호출
4. **2a.4 — collect()**: top50 순회 → fetch × 2엔드포인트 → `RelationRaw` INSERT
5. **2a.5 — 단위 테스트**: fixture + monkeypatch로 `_http.dart_get` 치환
6. **2a.6 — 삼성전자 실제 스모크**: `python -m modules.relation collect dart --corp 005930`

**함수 시그니처**
```python
# ingest/dart.py
BASE_URL = "https://opendart.fss.or.kr/api"

def fetch_shareholders(corp_code: str, bsns_year: int, reprt_code: str = "11011") -> list[dict]:
    """hyslrSttus → [{nm, relate, stock_knd, trmend_posesn_stock_qota_rt, ...}].
    status='013' → 빈 리스트. status='800' → RuntimeError.
    """

def fetch_investments(corp_code: str, bsns_year: int, reprt_code: str = "11011") -> list[dict]:
    """otrCprInvstmntSttus → [{inv_prm, trmend_blce_qota_rt, invstmnt_purps, ...}]."""

def collect(corp: str | None = None, bsns_year: int = 2024) -> dict:
    """Returns: {'shareholders_rows': int, 'investments_rows': int, 'errors': [...]}"""
```

**테스트 fixtures**
- `tests/relation/fixtures/dart_hyslrSttus_005930.json` (삼성전자 실제 응답 캡처)
- `tests/relation/fixtures/dart_otrCprInvstmntSttus_005930.json`
- `tests/relation/fixtures/dart_status_013.json` (데이터 없음 응답)

**완료 기준**
- [ ] `top50.csv`의 `corp_code` 컬럼 50개 모두 채워짐 + commit
- [ ] 단위 테스트 4개 이상 (정상 응답 파싱 / status=013 빈 결과 / status=800 예외 / RelationRaw INSERT 개수)
- [ ] `collect --corp 005930` 실행 시 stdout에 "이재용 1.63%, 삼성물산 5.01%..." + RelationRaw 10행+
- [ ] black 포매팅 통과

---

### Phase 2b — ingest/ftc.py (4h, MVP 보조 3종 포함)

**의존**: 공통 인프라 + CompanyNode 스키마
**산출물**: CompanyNode.group_name 채워짐 + `RelationLocal`에 `ftc_group` 엣지 생성 + MVP 보조 3종 결과는 보조 데이터로 저장

**하위 Step**
1. **2b.1 — `_http.ftc_get` 보강**: `resultType=json` 자동 주입 + `pageNo`·`numOfRows` 페이징 헬퍼 `ftc_get_all_pages`
2. **2b.2 — fetch_available_months**: 최신 YYYYMM 확정 (2025-05 기준 예상)
3. **2b.3 — fetch_designated_groups(yyyymm)**: 전체 ~90개 기업집단
4. **2b.4 — fetch_group_companies(group_code, yyyymm)**: 각 집단의 소속회사
5. **2b.5 — top50 교차 매칭**: 소속회사명 정규화 → top50 ticker 매칭 → `CompanyNode.group_name` UPDATE
6. **2b.6 — ftc_group 엣지 생성**: `group_name` 같은 top50 ticker 쌍에 대해 `itertools.combinations`로 무방향 엣지, source/target은 정렬된 순서로 저장 (중복 방지)
7. **2b.7 — MVP 보조 3종 구현**:
   - `fetch_holding_subsidiaries(holding_code, yyyymm)` → 지주회사→자회사 관계를 보조 테이블(`FtcHoldingRelation` 또는 RelationLocal의 별도 source_type="ftc_holding")로 저장
   - `fetch_special_relation_shares(group_code, yyyymm)` → DART hyslrSttus와 크로스체크용. 결과는 `audit/` 리포트용(엣지 생성은 하지 않고 비교 리포트만)
   - `fetch_group_asset_ranking(yyyymm)` → `CompanyNode.market_cap` 보강 또는 별도 `ftc_asset_rank` 컬럼
8. **2b.8 — 단위 테스트**: 삼성 그룹 8개사 완전연결 28개 엣지 검증
9. **2b.9 — 실제 스모크**: `python -m modules.relation collect ftc`

**함수 시그니처 (MVP 필수 3종)**
```python
# ingest/ftc.py
BASE_URL = "https://apis.data.go.kr/1130000"

def fetch_available_months() -> list[str]: ...
def fetch_designated_groups(yyyymm: str) -> list[dict]:
    """Returns: [{group_code, group_name, dominance_person}, ...]"""
def fetch_group_companies(group_code: str, yyyymm: str) -> list[dict]:
    """Returns: [{corp_name, biz_reg_num, join_date, ...}, ...]"""

def collect() -> dict:
    """Returns: {'groups_matched': int, 'companies_matched': int,
                 'ftc_group_edges': int, 'missing_group_count': int,
                 'supplementary': {'holding_edges': int, 'asset_rank': bool,
                                   'special_share_xcheck': int}}"""
```

**테스트 fixtures**
- `tests/relation/fixtures/ftc_available_months.json`
- `tests/relation/fixtures/ftc_designated_groups_202505.json`
- `tests/relation/fixtures/ftc_group_companies_samsung_202505.json`
- `tests/relation/fixtures/ftc_group_companies_sk_202505.json`
- `tests/relation/fixtures/ftc_holding_subsidiaries_sk_202505.json` (보조)

**완료 기준**
- [ ] `CompanyNode.group_name` 50개 중 47+ 채워짐 (한미반도체 등 독립만 null)
- [ ] 삼성 그룹 내 top50 8개사 간 `ftc_group` 엣지 28개 생성 검증
- [ ] MVP 보조 3종 중 **최소 지주회사 자회사 현황** 구현 완료 (나머지 2종은 best-effort)
- [ ] `collect ftc` 실행 시 missing_group_count 출력 (Phase 2c의 대상 식별용)

---

### Phase 2c — ingest/filing.py (2.5h)

**의존**: Phase 2b 완료 (CompanyNode.group_name IS NULL 기업 식별 필요)
**산출물**: `source_type="dart_filing"` 엣지 (공정위 미포함 기업 한정). 실패 시 manual_overrides.csv로 fallback 로그

**하위 Step**
1. **2c.1 — identify_missing_groups**: `CompanyNode WHERE group_name IS NULL`
2. **2c.2 — get_latest_rcept_no**: DART `list.json?corp_code=...&pblntf_detail_ty=A001&last_reprt_at=Y` → 사업보고서 접수번호
3. **2c.3 — download_filing(rcept_no)**: `document.json` → ZIP 바이너리 (재시도 2회)
4. **2c.4 — extract_related_party_html**: ZIP 내 XML 중 '특수관계자' 첫 출현 섹션 추출
5. **2c.5 — parse_related_party_section**: BeautifulSoup 테이블 파싱 → `[{name, relation_kind}]`, relation_kind 정규화 (지배/종속/관계/공동/기타)
6. **2c.6 — dart_filing 엣지 생성**: normalize_company_name + match_to_top50 → 매칭된 쌍만 엣지
7. **2c.7 — 실패 fallback**: 파싱 실패 시 warning 로그 + manual_overrides.csv 추가 요청 안내

**함수 시그니처**
```python
def identify_missing_groups() -> list[dict]: ...
def get_latest_rcept_no(corp_code: str, bsns_year: int = 2024) -> str | None: ...
def download_filing(rcept_no: str) -> bytes: ...
def extract_related_party_html(zip_bytes: bytes) -> str | None: ...
def parse_related_party_section(html_fragment: str) -> list[dict]:
    """Returns: [{'name': str, 'relation_kind': Literal['지배','종속','관계','공동','기타']}]"""
def collect() -> dict: ...
```

**테스트 fixtures**
- `tests/relation/fixtures/filing_related_party_hanmi.html` (한미반도체 등 주석 섹션만 추출한 샘플)
- `tests/relation/fixtures/filing_empty.html` (섹션 없음 케이스)

**완료 기준**
- [ ] 미포함 기업 식별 로직 정상 (예상 대상 1~3개)
- [ ] 파싱 성공 시 dart_filing 엣지 생성, 실패 시 명확한 로그 + 다음 기업으로 진행 (전체 중단 X)
- [ ] 모든 미포함 기업 파싱 실패해도 `collect filing` 자체는 exit 0

---

### Phase 2d — transform/ (2h)

**의존**: `RelationRaw` 데이터 존재 (Phase 2a 수집 완료)
**산출물**: `RelationLocal` 테이블에 ticker 기반 최종 엣지. 개인·재단·미매칭 제거됨, K-IFRS 분류 적용, 중복 제거됨

**하위 Step**
1. **2d.1 — common/names.py**: `normalize_company_name(name)` 공용 유틸 + `NAME_ALIASES` dict
2. **2d.2 — filters.py**: `is_personal_shareholder`, `is_foundation`, `match_to_top50`, `apply()` (RelationRaw → RelationLocal 마이그레이션)
3. **2d.3 — kifrs.py**: `classify_ownership(ratio)` + `apply()` (지분 엣지의 relation_type 재분류)
4. **2d.4 — dedupe.py**: 양방향 지분 중복 제거 (`apply()`)
5. **2d.5 — 통합 실행 순서**: `filters.apply() → kifrs.apply() → dedupe.apply()`

**함수 시그니처**
```python
# common/names.py
def normalize_company_name(name: str) -> str: ...

# transform/filters.py
PERSONAL_RELATIONS = {"본인", "친인척", "친족", "인척"}
FOUNDATION_KEYWORDS = ("재단", "공익", "장학회", "문화재단")

def is_personal_shareholder(name: str, relate: str) -> bool: ...
def is_foundation(name: str) -> bool: ...
def match_to_top50(normalized_name: str, ticker_map: dict[str, str]) -> str | None: ...
def apply() -> dict:
    """RelationRaw 스캔 → RelationLocal INSERT.
    Returns: {'kept': int, 'dropped_personal': int, 'dropped_foundation': int, 'dropped_unmatched': int}"""

# transform/kifrs.py (상수는 이미 정의됨)
def classify_ownership(ratio: float) -> str | None:
    """>50% → subsidiary, [20,50] → associate, [5,20) → investment, <5 → None"""
def apply() -> dict: ...

# transform/dedupe.py
def apply() -> dict:
    """Returns: {'kept': int, 'removed_bidirectional': int}"""
```

**경계값 테스트 (필수)**
- kifrs: `50.0 → associate`, `50.01 → subsidiary`, `20.0 → associate`, `19.99 → investment`, `5.0 → investment`, `4.99 → None`
- filters: "(주)삼성전자"·"삼 성 전 자"·"주식회사 삼성전자" 모두 "삼성전자"로 정규화

**완료 기준**
- [ ] 경계값 6개 테스트 모두 통과
- [ ] 이재용·홍라희(개인) / 삼성생명공익재단(재단) 모두 dropped 카운트에 반영
- [ ] RelationLocal의 source_corp·target_corp 전부 6자리 ticker 형식 (String(6) 제약 충족)
- [ ] 양방향 중복 제거 후 같은 (A, B, relation_type) 쌍이 1개만 존재

---

### Phase 2e — graph/ (1h)

**의존**: Phase 2d 완료 (RelationLocal 최종 상태)
**산출물**: `modules/relation/data/graph_top50.json` (프로토타입 호환 스키마)

**하위 Step**
1. **2e.1 — build.py**: CompanyNode + RelationLocal → `nx.MultiDiGraph`. 노드 속성(n/t/s/sz/mc/group) + 엣지 속성(relation_type/ratio/detail/source_type)
2. **2e.2 — export.py**: 각 노드 dict + 해당 노드에서 나가는 엣지를 `rl` 배열로 ("대상명:relation_type:detail" 3-split 문자열). ratio 내림차순 정렬
3. **2e.3 — 자체 검증**: 노드/엣지 카운트 + 고아 노드 목록 stdout 출력

**함수 시그니처**
```python
# graph/build.py
def build_graph() -> nx.MultiDiGraph: ...

# graph/export.py
def export_json(output_path: Path | None = None) -> Path: ...
```

**완료 기준**
- [ ] 노드 ≥ 48, 엣지 ≥ 30
- [ ] 모든 link의 source/target이 nodes 집합에 존재
- [ ] 노드 id가 전부 6자리 ticker 형식 (개인·재단 배제)
- [ ] 같은 (A, B) 쌍에 ftc_group + subsidiary 등 여러 relation_type 엣지 공존 확인

---

### Phase 2f — viewer/ (2h)

**의존**: `data/graph_top50.json` 존재 (Phase 2e 완료)
**산출물**: `modules/relation/viewer/index.html` — 프로토타입 fork + fetch 로더 + 6가지 relation_type 스타일 + K-IFRS 툴팁

**하위 Step**
1. **2f.1 — 프로토타입 fork**: `cp docs/prototype/corporate_universe_v5.html modules/relation/viewer/index.html`
2. **2f.2 — 데이터 로딩 교체**: line ~141-188의 `const raw=[...]` → `let raw=[]; fetch('../data/graph_top50.json').then(...)`
3. **2f.3 — init() 파서 수정**: `r.split(':', 2)` → `r.split(':', 3)` + edges에 type/ratio/detail 저장
4. **2f.4 — draw() 스타일 분기**: `EDGE_STYLES` 객체 정의 + 엣지 루프에 `setLineDash`/`strokeStyle`/`lineWidth` 분기
5. **2f.5 — sectors 확장**: 기존 8개 + 4개(중공업·방산/건설/통신/기타)
6. **2f.6 — K-IFRS 툴팁**: hover 시 relation_type별 교육 메시지
7. **2f.7 — 로컬 서버 확인**: `python -m http.server 8000` → 브라우저 시각 QA

**EDGE_STYLES 확정**
```js
const EDGE_STYLES = {
  subsidiary:  { color: '#ef4444', width: 2.0, dash: [] },
  associate:   { color: '#f97316', width: 1.5, dash: [] },
  investment:  { color: '#94a3b8', width: 0.8, dash: [2,3] },
  ftc_group:   { color: '#fbbf24', width: 1.0, dash: [4,2] },
  dart_filing: { color: '#facc15', width: 1.0, dash: [6,2] },
  manual:      { color: '#a78bfa', width: 0.8, dash: [2,2] },
};
```

**완료 기준**
- [ ] 브라우저에서 렌더링 성공 (노드 50개 + 엣지 30+ 표시)
- [ ] 삼성 8개사 클러스터·SK 그룹·현대 그룹 시각적으로 인접 배치 확인
- [ ] 호버 시 K-IFRS 툴팁 정상 표시
- [ ] 개인 주주 노드가 화면에 나타나지 않음 (자연 필터 확인)
- [ ] 스크린샷 캡처 → Phase 2h PR 본문에 첨부

---

### Phase 2g — skills/ (30m)

**의존**: Phase 2a~2f 구현 완료 + CLI 명령 동작 확인
**산출물**: `modules/relation/skills/` 하위 3개 `.md` (모듈 로컬 스킬 초안)

**파일 3개**: `relation-collect.md`, `relation-graph.md`, `relation-audit.md`

각 파일 YAML frontmatter (name, description, auto-invocable) + 본문(절차·기대 출력·에러 대응). `relation-audit`은 `auto-invocable: true`, 나머지는 false.

**완료 기준**
- [ ] 3개 파일 작성
- [ ] 각 스킬 내용대로 수동 실행하여 기대 출력 확인 (1회)
- [ ] 승격 전 검증: CLI 명령이 모두 실제 동작

---

### Phase 2h — /check + PR (1h)

**하위 Step**
1. **2h.1 — `/check` 실행**: pytest tests/relation/ 전체 + black --check + code-reviewer agent + PROGRESS.md 기록
2. **2h.2 — 커밋 분할 (권장: Phase 단위 5커밋)**:
   - `feat(ingest): dart.py + corp_code 매핑 + 테스트`
   - `feat(ingest): ftc.py 3+3 API + 삼성 그룹 검증 + 테스트`
   - `feat(ingest): filing.py 주석 파싱 + fallback`
   - `feat(transform+graph): K-IFRS 분류 + MultiDiGraph + JSON export`
   - `feat(viewer+skills): 프로토타입 fork + 도메인 스킬 3개 초안`
3. **2h.3 — push + PR 생성**: `gh pr create --base dev --head feat/relation`

**PR 본문 템플릿**
```
## Summary
- DART 지분 관계 수집 (hyslrSttus + otrCprInvstmntSttus)
- 공정위 API 6종 (필수 3 + 보조 3) → ftc_group 엣지
- 사업보고서 주석 파싱 (공정위 미포함 기업)
- K-IFRS 지분율 자동분류 + 양방향 중복 제거
- NetworkX MultiDiGraph → 프로토타입 호환 JSON
- viewer 완성 (6가지 relation_type 스타일)
- viewer 스크린샷 첨부

## Test plan
- [x] pytest tests/relation/ 전체 통과
- [x] /relation-audit 무결성 체크 통과
- [x] 로컬 브라우저 렌더링 확인
```

---

### Phase 2i — 스킬 승격 PR (15m, 별도 브랜치 권장)

**하위 Step**
1. **2i.1 — 승격 조건 체크**: Phase 2h PR이 CI green + viewer 동작 + audit 통과
2. **2i.2 — 별도 브랜치**: `feat/relation-skills-promotion` (feat/relation에서 fork)
3. **2i.3 — 파일 이동**: `modules/relation/skills/*.md` → `.claude/skills/{name}/SKILL.md` (각 스킬마다 폴더)
4. **2i.4 — 원본 삭제 or README로 변경**: 이력 보존 위해 `modules/relation/skills/README.md`에 "승격됨, 실제 정의는 `.claude/skills/` 참조" 한 줄
5. **2i.5 — 별도 PR**: `gh pr create --base dev --head feat/relation-skills-promotion` (리더 셀프 리뷰)

**완료 기준**
- [ ] `/relation-collect` 등 3개 스킬이 전역에서 호출 가능
- [ ] feat/relation PR과 독립 merge 가능

---

### Phase 2 전체 총괄

**총 예상**: 약 13.5시간 (보조 API 3종 포함 기준)

**세션 분할 권장**
- **세션 B** (3~4h): 선행 작업(`_http.py`, `common/names.py`, `RelationRaw`) + Phase 2a + Phase 2b 필수 3종
- **세션 C** (3h): Phase 2b 보조 3종 + Phase 2c
- **세션 D** (2h): Phase 2d (transform 전체)
- **세션 E** (3h): Phase 2e + Phase 2f + 시각 QA
- **세션 F** (1.5h): Phase 2g + Phase 2h + Phase 2i

각 세션 시작 시 `modules/relation/PLAN.md` 읽고 해당 Phase 2X의 하위 Step 체크리스트부터 진행.

### 리스크·완화
| 리스크 | 완화 |
|---|---|
| DART API 일일 한도 초과 | 수집 호출 최대 300건 (50기업 × 2엔드포인트 × 최대 3년). 한도 10,000 대비 여유 큼. |
| 공정위 API 응답 포맷 예상과 다름 | 각 API 1회 샘플 호출로 스키마 확인 후 fixture 업데이트. 실제 개발 전에 30분 탐색 시간 배정. |
| 사업보고서 주석 파싱 실패 | best-effort + manual_overrides.csv fallback. 한미반도체 등 1~3개만 대상이라 실패해도 커버리지 영향 미미. |
| top50.csv의 group_name 초안이 공정위 지정과 불일치 | Phase 2b 수집 후 공정위 결과로 덮어쓰기. 초안은 이해 돕는 참고용. |
| viewer 렌더링이 프로토타입과 달리 깨짐 | 원본 프로토타입 수정 금지. fork 후 변경 3곳만(데이터 로딩·init·draw). 문제 시 해당 부분만 롤백. |

### 진행 중 원칙
- 한 폴더 미완성 시 다음으로 넘어가지 말고 그 폴더 CLAUDE.md 먼저 정리 → 다음 세션의 나(또는 Claude)가 짧은 시간에 복구 가능
- 각 폴더 완료 시마다 해당 폴더 테스트만 실행(`pytest tests/relation/test_ingest/ -v`)으로 회귀 빠르게 감지
- Phase 2a 시작 전 **선행 작업 3건**(_http.py / common/names.py / RelationRaw 테이블) 필수 완료

---

## 검증 (Verification)

### Phase 1 완료 기준 (이번 세션)
- [ ] `modules/relation/` 아래 ingest/transform/graph/viewer/storage/data 6개 폴더 존재
- [ ] 루트 `modules/relation/CLAUDE.md` + 서브폴더 5개 `CLAUDE.md` 총 6개 파일 작성
- [ ] `python -m modules.relation --help` 에러 없이 실행 (argparse 명령 목록 출력)
- [ ] `from modules.relation.ingest import dart, ftc, filing` 등 import 에러 없음
- [ ] 기존 `pytest tests/test_smoke.py` 여전히 통과 (회귀 없음)
- [ ] `feat/relation` 브랜치에 "feat: relation 모듈 Harness 스켈레톤" 커밋

### Phase 2 완료 후 검증

1. **단위 테스트 (폴더별 1:1 대응)**
   ```bash
   python -m pytest tests/relation/ -v
   ```
   - `test_ingest/test_dart.py`: hyslrSttus·otrCprInvstmntSttus 모킹. 원본 수집 단계에서는 개인·비상장 포함(필터는 transform에서)
   - `test_ingest/test_ftc.py`: 공정위 API 응답 샘플에서 "삼성" 그룹 8개사 매칭
   - `test_ingest/test_filing.py`: 공정위 미포함 기업 식별 + 샘플 HTML에서 특수관계자 섹션 추출
   - `test_transform/test_filters.py`: 개인(이재용·홍라희)·공익재단(삼성생명공익재단) → 필터 후 제외
   - `test_transform/test_kifrs.py`: 경계값 43.4% → `associate`, 50.01% → `subsidiary`, 19.58% → `investment`, 4.99% → 엣지 없음
   - `test_transform/test_dedupe.py`: A→B 5% + B→A 19% 쌍에서 19% 채택
   - `test_graph/test_build.py`: MultiDiGraph에 같은 쌍이 relation_type 다르게 공존
   - `test_graph/test_export.py`: JSON `nodes` ≥ 48, `links` ≥ 30, 모든 link source/target이 nodes에 존재, 노드 id 전부 6자리 ticker
   - `test_storage/test_models.py`: CompanyNode·RelationLocal CRUD

2. **End-to-end 스모크**
   ```bash
   python -m modules.relation init                        # 로컬 DB 생성
   python -m modules.relation collect dart --corp 005930  # 삼성전자만
   python -m modules.relation collect ftc                 # 공정위 전체
   python -m modules.relation transform                   # 필터·분류
   python -m modules.relation graph && export             # JSON 생성
   python -m http.server 8000                             # 브라우저
   # → http://localhost:8000/modules/relation/viewer/index.html
   ```
   - stdout: "삼성물산 5.01% (associate)", "삼성SDI 19.58% (investment)" 등
   - viewer: 삼성 8개사 클러스터·K-IFRS 툴팁 표시 확인

3. **도메인 검증 (사람) — `/relation-audit` skill**
   - 삼성전자 나가는 지분 6~8개(삼성SDI·삼성바이오로직스·삼성물산 등) 출력
   - 기아(000270) ↔ 현대차(005380) 상호 지분 양방향 (현대차→기아 33.88%, 기아→현대차 ~4.9%)
   - 삼성 그룹 8개사 완전연결 (`ftc_group` 28개 엣지) 확인
   - 고아 노드(연결 0개) 목록 출력 — 한미반도체 등이 포함되는 것이 정상

4. **CI**
   - feat/relation → dev PR 시 GitHub Actions `black --check` + `pytest tests/relation/` 통과
   - CI 빨간 X면 merge 불가 ([docs/MERGE_PROCESS.md:112](docs/MERGE_PROCESS.md#L112))

---

## v2 이후 연기 사항 (기록용)

- **공급 관계**: DART 사업보고서 "주요 매출처/매입처" 섹션 비정형 파싱 (LLM 활용) — 대회 이후
- **경쟁 관계**: KRX WICS subsector 기반 점선 엣지 — 대회 직전 시간 여유 시 추가 가능
- **주석 파싱을 50개 전수로 확장**: 현재는 공정위 미포함 기업 1~3개만 대상. 전수 적용 시 공정위 API 결과와 K-IFRS 주석을 대조하여 불일치(공정위는 계열인데 주석엔 특수관계자 아님 등) 감사 가능
- **주석의 특수관계자 거래금액·비중**: 현재는 관계 유형(지배/종속/관계/공동)만 파싱. 거래금액까지 추출하면 엣지 굵기를 거래량 기준으로도 표현 가능
- **Supabase 이전**: 로컬 SQLite → Supabase PostgreSQL 동기화 스크립트 (shared/models.py 갱신 후)
- **2,600개 전수 확장**: 같은 collector 그대로, top50.csv 만 KOSPI·KOSDAQ 전체로 교체
- **시계열 지분 변동**: `hyslrChgSttus.json` 추가 수집 → 애니메이션 구현
