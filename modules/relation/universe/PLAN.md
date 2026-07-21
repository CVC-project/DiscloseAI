# Universe — 전 상장사(~2,600) 지배구조 레이어 + Universe 시각화 스케일링

> 상태: **계획 수립 완료 · 실행 대기**
> 작성: v1.0 (2026-07-21) — 리더 승인 결정 4건 반영(시각화 범위·문서 위치·V0 결합·시각 문법 불변)
> 개정: v1.1 (2026-07-21) — 착수 전 코드 실측 재검토 반영: ① 엣지 렌더 현행 정정
> (활성 선택 노드만 — hover는 glow) ② U1 전제 정밀화(top50 게이트 3곳 실측)
> ③ manual_overrides 미구현 실태 ④ FTC 클리크형 실측 ⑤ 팔레트 이중 소스 불일치
> ⑥ **시각화 엣지 검증 하네스 V 신설(§5.5)** ⑦ 통합 실행 순서·드라이버 절차(§6)
> ⑧ GPU 서버 접속 복구(2026-07-21) — U4 전제 현황 갱신. EgoView 진입 = v2 셸 단일 확정.
> 소유: relation 모듈(데이터) · integration(화면, 리더). §0.5 경계 참조.
> 전제: [../valuechain/PLAN.md](../valuechain/PLAN.md) **Phase V0**(reports.db shared 승격 · CompanyRegistry ·
> 전 상장사 수집)가 공유 선행 단계 — 본 문서는 V0 산출물을 **참조만** 하고 중복 정의하지 않는다.
> 관련: [../PLAN.md](../PLAN.md)(지배구조 v1 top50) · [../CLAUDE.md](../CLAUDE.md)(모듈 규칙) ·
> [../../../integration/CLAUDE.md](../../../integration/CLAUDE.md)(데이터 소스 계약) · 루트 [DESIGN.md](../../../DESIGN.md)

---

## 0. 목표 / 비목표

### 제품 목표
지배구조 관계망을 top50 → **전 상장사(코스피+코스닥, ~2,600사)** 로 확장한다.
화면은 3단 LOD:

1. **LOD-0 Universe** — 섹터 은하 + **시총 상위 400(코스피 200 + 코스닥 200) 명명 노드**
2. **LOD-1 섹터 진입** — 해당 섹터의 명명 노드 + 잔여 기업 **배경 dots**
3. **LOD-2 Ego** — 기업 클릭 시 **앵커 중앙 ego 1-hop 재구성 뷰** (전 상장사 도달, 지배구조/밸류체인 레이어 토글)

사용자 여정 불변식: Universe(400 named) → 섹터(named+dots) → 검색(2,600 전체) → ego re-root —
**어느 진입로로든 전 상장사에 도달 가능**해야 한다.

### 비목표 (Non-goals)
- ❌ 2,600 노드 전체 엣지 한 화면 렌더 — 헤어볼 금지 (valuechain §0 비목표와 동일 원칙)
- ❌ 개인·비상장 노드 — 기존 원칙 유지: DB 기록만, export 제외 (../CLAUDE.md 핵심 원칙 #1)
- ❌ 시각 문법 변경 — REL_STYLES 6종·실선/파선/점선·화살표 의미론 불변 (U-D12). 확장은 섹터 색 추가뿐
- ❌ T2 서술 추출 지배구조 엣지 — U4 이연. GPU 서버 필요 (★v1.1: 2026-07-21 IP 허용 후
  접속 복구 — 차단 해제. 다만 U4는 로드맵 순서상 여전히 최후순위)

---

## 0.5 실행 주체·경계

| 주체 | 담당 | 경계 규칙 |
|---|---|---|
| **relation 모듈** | 수집·분류·registry·export 산출물 전부 (`universe.json` · `ego/<ticker>.json` · `sectors.json` · `companies_index.json` · `ksic_sector_map.csv`) | integration 파일 수정 금지 |
| **integration (리더)** | bundle.jsx SectorMap LOD·EgoView·`SECTOR_PALETTE`/`SECTOR_DEF` 확장, extract_data.py 동기화 단계 등록 | relation 데이터 read-only |
| **GPU/A100** | 없음 — U0~U3은 전부 CPU·API 경로 | U4(T2 추출)에서만 등장 (★v1.1: 서버 접속 복구됨 — 로드맵 순서만 준수) |

핵심 경계: **`SECTOR_PALETTE`(bundle.jsx)와 `SECTOR_DEF`(adapter.js)는 integration 소유 상수**다.
relation은 신규 섹터 목록(`sectors.json`)만 공급하고, **색 배정은 integration이 DESIGN.md
절차(색=의미, 임의 변경 금지)로 수행**한다. KSIC→섹터 매핑표는 relation 소유 데이터
(integration은 읽기만).

---

## 1. 확정된 설계 결정

| # | 결정 | 근거 |
|---|---|---|
| U-D1 | 정형 지분 엣지 1차 원천 = **DART API `hyslrSttus` + `otrCprInvstmntSttus` 전 상장사 확장** — fetch 계층(`ingest/dart.py:150,180`)은 corp_code 파라미터 범용. ★v1.1 실측: top50 전제는 **3곳에 묶여 있어 함께 교체** — ① `collect()`의 `_load_top50()` 순회(top50.csv 마스터) ② `map_corp_codes()`의 `is_target=True` 하드코딩(dart.py:110-133) ③ `transform/filters.py:98-100`의 `ticker_map` 게이트(U1 표의 "E2E 단절 지점"). 호출량: 최신 연도 ~5,200건(2,600×2) = 하루 완주, **5개년 백필 ~2.6만 건 = 일 1만 한도 내 3일 배치** | 정형·결정적·기수집 파이프라인 재사용. 원문 파싱보다 싸고 빠름 |
| U-D2 | reports.db 기반 **특수관계자 주석 파서(valuechain V1 T1 파서와 공용)는 보완 원천** — U-D1 미포착분(주석 전용 관계·과거 백필) 전용. **파서는 1벌 구현, 소비자 2곳**(ValueChainEdge / RelationLocal) | 이중 구현 금지 (수집 삼중 구현 부채 #43 재발 방지) |
| U-D3 | 공정위 원천은 **공시대상기업집단(~88집단) 한정임을 명시** — 비집단 2,000여 사의 "계열" 개념은 존재하지 않으므로 ftc_group 엣지 부재가 정상 | 커버리지 오해 차단 |
| U-D4 | ftc_group 엣지는 **스타 토폴로지**(동일인·대표회사 → 소속 상장사)로 저장 — 집단 내 클리크(O(n²)) 금지. "같은 집단" 강조는 노드 `group` 속성으로 표현. ★v1.1 실측: 현행 `ingest/ftc.py:149-168`은 `combinations` **완전연결(클리크형)** — 스타 전환은 기존 동작 **변경**임(§7 화면 밀도 리스크 참조) | 삼성 계열 상장사 ~17곳 클리크 = 136엣지 폭발 방지 |
| U-D5 | 기업 마스터 = **valuechain V0 CompanyRegistry 단일 정본** + universe 컬럼 추가: `market_cap_krw / cap_asof / sector_id / universe_tier(named400\|dot) / universe_rank`. 기존 CompanyNode는 graph/build.py의 Registry 전환 후 은퇴. **V0 마이그레이션 착수 전 스키마 합의 → 마이그레이션 1회로 완결** | 마스터 이중화 금지 (valuechain §2.2와 단일 정본) |
| U-D6 | 시총 원천 = **pykrx**(KRX 정보데이터시스템, 키 불요), 실패 시 yfinance 폴백. top-400 = KOSPI 상위 200 + KOSDAQ 상위 200, **분기 1회 재선정**, 시총 스냅샷은 M1 동기화 루프에 편승 | GPU 서버 profiles.json은 서버 접속 불가로 원천 부적격 |
| U-D7 | 섹터 분류 = **KSIC 중분류 → 섹터 id 매핑 CSV**(`universe/data/ksic_sector_map.csv`, relation 소유). 기존 16 섹터 유지 + 신규 ~6~9개(제약, 기계·장비, 전기전자부품, 게임, 지주, 화장품, 섬유·의류, 레저·교육, 기타). **KSIC 원천 = DART 기업개황 `company.json`의 `induty_code`** — 전 상장사 일회 수집(~2,600 호출), 이후 M1 루프 편승 갱신. 신규 섹터 색은 integration이 배정(§0.5) | 매핑표=데이터(relation), 색=화면(integration) — 경계 준수 |
| U-D8 | **데이터 정책과 렌더 정책 분리**(valuechain D7 준용): relation.db에는 2,600사 엣지 전부 저장. top-400·dots·Top-N은 export와 뷰가 자를 뿐 | 선정 기준 변경 시 재수집 불필요 |
| U-D9 | export 산출물 **4종**: ① `universe.json`(섹터 집계 + dots 좌표 + 400 named — 기존 `{n,t,s,sz,mc,group,rl}` 노드 스키마 유지, rl은 400 상호 간만) ② `ego/<ticker>.json` ×2,600 + 매니페스트(dossier `galaxy_<ticker>.json` 지연 fetch 패턴, 합계 ~5MB) ③ `sectors.json`(섹터 목록 handoff) ④ `companies_index.json`(2,600 경량 검색 인덱스). **기존 `graph_top50.json` 계약은 전환 완료(U4)까지 불변** | 정적 파일 서빙 전제(백엔드 없음) — dossier가 동일 패턴 검증 완료 |
| U-D10 | `ego/<ticker>.json`은 **레이어 통합 스키마** — `layers.governance`(지배구조 1-hop) + `layers.valuechain`(상류/하류 — valuechain V1 이후 채움). **작성자는 `universe/export.py` 단독**(RelationLocal + ValueChainEdge 둘 다 읽음) | 두 레이어 뷰 분기 방지 — 계약 1개, 작성자 1곳 |
| U-D11 | Universe·섹터 레벨의 엣지 렌더는 **활성(클릭 선택) 노드의 엣지만**(★v1.1 정정 — 현행 SectorMap 실측: 엣지는 `activeCompanyCode` 가드 안에서만 그려지고 hover는 glow 배율만 변경, bundle.jsx:982·:1087. hover 시 엣지 표시는 현행 동작이 아니며 U2의 **선택 과제**) — 상시 전체 엣지 도포 금지. 섹터 간 집계 흐름선은 U4(valuechain V4 합류) | 렌더 예산 + 헤어볼 금지 |
| U-D12 | **시각 문법 불변**: REL_STYLES 6종 + 지분(실선·화살표=출자 방향)/계열(파선)/주석(점선) + 지분·계열 이중 평행선 그대로. 확장은 SECTOR_PALETTE **항목 추가뿐** | 리더 확정 요구 — 기존 학습된 범례 문법 보존 |
| U-D13 | 멱등·정정 처리는 **valuechain §4.5 M1~M5 그대로 준용** — RelationLocal에 `UNIQUE(source_corp, target_corp, relation_type, bsns_year)` upsert 키 + `status(active\|superseded) / superseded_by / rcept_no` 컬럼 추가. 기존 `DELETE→INSERT` 재수집은 멱등 upsert로 전환(M4 pytest 강제) | 규칙 중복 서술 금지 — 참조로 통일 |
| U-D14 | **레이어별 시각 문법 분리** — 지배구조와 밸류체인은 **동시 렌더 금지(레이어 토글)** + 문법 축 분리로 오독 차단: 지배구조 = 색=관계유형 6종, 실선+삼각 화살촉=지분(**화살표=출자 방향**), 파선/점선=계열/주석 (현행 불변). 밸류체인 = 색=흐름 단일색 계열(관계색 6종과 미충돌 — integration 배정), 선 스타일=**신뢰등급**(T1 실선/T2 옅은 실선/T3 점선, valuechain §5), 화살표=**물자 흐름 방향**(위→아래)이며 **화살촉 모양을 지배구조와 다르게**(오픈 셰브런 or 이동 대시). 범례는 레이어 전환 시 전용 범례로 교체(혼합 범례 금지) | "실선"이 레이어마다 다른 의미(지분 vs T1)가 되는 충돌을 토글+전용 범례로 해소 |

---

## 2. 데이터 아키텍처

### 2.1 DB 토폴로지 — 하나의 relation.db 공유 (valuechain §2.2와 정합)

지배구조 레이어와 밸류체인 레이어는 **같은 relation 모듈의 두 레이어**이므로 단일
`relation.db`가 정본이다(valuechain §2.2 "신규 테이블 전부 relation.db" 결정과 동일).
ego export(U-D10)가 두 레이어를 조인해 단일 JSON을 만들므로 단일 DB가 정합에도 유리하다.
경계는 **테이블 쓰기 소유**로 명확화한다:

| 테이블 | 쓰기 주체 (단독) | 읽기 |
|---|---|---|
| RelationLocal | 지배구조 파이프라인 (ingest/transform) | graph·universe export |
| ValueChainEdge · VcChunk · VcPipelineState · SectorIOEdge | valuechain 파이프라인 | universe export(ego) |
| CompanyRegistry · CompanyAlias | universe/registry.py (M1 루프) | 양쪽 레이어 전부 |
| LinkFailQueue | 양쪽 (append-only 큐) | 검수 도구 |

- **동시 실행 규칙**: SQLite 단일 쓰기 락 대응 — **WAL 모드 활성** + 장기 배치
  (U1 지분 수집 vs valuechain 라벨링·추출)는 **직렬 실행 원칙**.
- 원문 코퍼스는 `shared/data/reports.db`(쓰기=report 모듈 단독, D11) — 본 문서는 읽기만.

### 2.2 원천 × 엣지타입 매트릭스 (2,600사 기준)

| relation_type | 원천 | 규모 감각치 | 비고 |
|---|---|---|---|
| ftc_group | 공정위 API (~88집단, 상장 소속사만) | 수백 (스타 토폴로지, U-D4) | 비집단사 0이 정상 (U-D3) |
| subsidiary / associate / investment | DART `otrCprInvstmntSttus` + `hyslrSttus` 전 상장사 (U-D1) | 원시 1.5만~3만 행 → 상장사 간 필터 후 **5천~1만 엣지** | K-IFRS 임계값 분류(`transform/kifrs.py`) 그대로 스케일 |
| dart_filing | 특수관계자 주석 파서 (valuechain T1 공용, U-D2) | 수천 | 동일 쌍 정형 엣지 **부재 시만** 생성 (기존 규칙 일반화) |
| manual | manual_overrides | 소수 | ★v1.1 실측: 현재 CSV 스캐폴드만 존재(데이터 0행·로더 코드 0건, filters.py:92 주석) — U1에서 **신규 구현** 항목(기존 기능 아님) |

- **dedup·우선순위**: 레이어 공존 원칙 유지(graph/CLAUDE.md). 같은 층 내 중복
  (hyslrSttus A→B vs otrCpr A→B)은 기존 "higher ratio 채택"(`transform/dedupe.py`).
  표시 우선순위는 adapter.js `TYPE_PRIORITY` 불변. 정정공시는 M3 supersede.
- **엔티티 링킹**: 2,600사 규모에서 동명·구사명 충돌 급증 — CompanyAlias 사전 +
  LinkFailQueue(M2 수동 보정 루프) 준용.

### 2.3 스키마 변경 (`storage/models.py`)

- RelationLocal: `UNIQUE(source_corp, target_corp, relation_type, bsns_year)` +
  `status / superseded_by / rcept_no` 추가 (U-D13).
- CompanyRegistry: universe 컬럼 5종 추가 (U-D5) — **valuechain V0 마이그레이션과 동시 반영**.
- CompanyNode: graph/build.py가 CompanyRegistry를 읽도록 전환한 뒤 은퇴 (전환 완료까지 병존).

---

## 3. Universe 마스터 (registry · 시총 · 섹터)

```
universe/registry.py    DART corpCode 전량(기존 ingest/dart.py map_corp_codes() 재사용)
                        + KRX 상장 목록 교차 → CompanyRegistry 적재 · M1 루프 편승
universe/marketcap.py   pykrx 시총 스냅샷 → market_cap_krw / cap_asof (실패 시 yfinance 폴백)
universe/select.py      시장별 상위 200×2 → universe_tier / universe_rank (분기 재선정,
                        이탈·진입 diff를 PROGRESS.md 기록)
universe/sectors.py     DART 기업개황 induty_code 수집 + ksic_sector_map.csv 적용
                        → sector_id (미매핑 0 게이트) + 섹터별 기업 수 분포 리포트
                        (최대 섹터 = dots 렌더 예산의 기준)
universe/export.py      relation.db → 산출물 4종 (U-D9·U-D10)
```

CLI: `python -m modules.relation universe {sync|select|export}` (기존 `__main__.py` 서브커맨드 추가).

---

## 4. Export 계약 (integration과의 신규 계약 — 확정 시 integration/CLAUDE.md 계약 표 + docs/ARCHITECTURE.md §4 동시 갱신)

```jsonc
// universe.json
{ "meta": { "as_of": "...", "named_count": 400, "total": 2600 },
  "sectors": [ { "id": "semi", "ko": "반도체", "count": 210, "cap": 980,
                 "dots": [[x, y, capBucket], ...] } ],   // named 제외 잔여사 — 사전 배치 좌표
  "named": [ { "n": "삼성전자", "t": "005930", "s": "반도체", "sz": 1.0, "mc": "...",
               "group": "삼성", "rank": 1, "rl": ["대상명:type:detail", ...] } ] }
// named[].rl 은 400인 상호 간 엣지만 (adapter rl-string 파서 재사용 목적). 전체 엣지는 ego 파일에.
```

```jsonc
// ego/<ticker>.json — 레이어 통합 ego 계약 (U-D10, 작성자: universe/export.py 단독)
{ "t": "005930", "n": "삼성전자", "s": "반도체", "tier": "named400",
  "layers": {
    "governance":  [ { "t": "...", "n": "...", "type": "associate", "detail": "31.22%",
                       "dir": "out|in", "s": "바이오", "tier": "dot" } ],
    "valuechain":  { "up": [], "down": [] }    // valuechain V1 전까지 빈 값
  } }
```

- 크기 감각치: universe.json 200~400KB, ego 2,600본 합계 ~5MB(개별 1~5KB) — 정적 서빙
  (`python -m http.server 8000`) 문제 없음. dossier `galaxy_<ticker>.json` 지연 fetch로 검증된 패턴.
- `companies_index.json`: `[{t, n, s, tier}]` 2,600행 — 검색 타이프어헤드 전용 경량 인덱스.
- integration `extract_data.py`: universe.json·sectors.json·companies_index.json byte 복사 +
  `ego/` 디렉터리 동기화(매니페스트 해시 기반 — 변경분만 재작성, diff 노이즈 억제). **integration 측 작업.**

---

## 5. 시각화 계약 (integration에 넘길 렌더링 정책 명세)

> 구현은 integration 소유(§0.5). relation은 데이터 + 이 정책 명세만 공급.
> UI 착수 시 루트 DESIGN.md 선행 준수.

| 항목 | 정책 |
|---|---|
| LOD-0 Universe | 섹터 은하 + 섹터별 named 노드 대표 표시. 엣지 없음 |
| LOD-1 섹터 진입 | named 노드(라벨 포함) 현행 SectorMap 방식 + **배경 dots**(오프스크린 캔버스 1회 렌더 후 합성 — 프레임당 재도장 금지). dot hover 시 이름 툴팁, 클릭 시 ego 진입 |
| LOD-2 Ego | **EgoView 단일 컴포넌트** — valuechain §5 계약 그대로(앵커 중앙, 사이드당 Top-N 6, "외 n사" 묶음 노드, re-root + 브레드크럼) + 상단 `지배구조 / 밸류체인` 레이어 토글. 지배구조 레이어의 상/하 배치는 **출자(들어옴) 위 / 피출자(나감) 아래**로 방향 의미 재사용 |
| 레이어 문법 | U-D14 — 토글 전환 시 엣지 문법·범례 함께 교체 (혼합 범례 금지) |
| 엣지 예산 | 활성(클릭 선택) 노드의 엣지만 (U-D11 ★v1.1 정정). 상시 전체 엣지 금지. hover 엣지 표시는 U2 선택 과제 |
| 라벨 충돌 | 시총 우선 그리디 배치 — 기배치 라벨 bbox와 교차 시 생략, active/hover는 항상 표시 |
| 검색 | `companies_index.json` 타이프어헤드 → ego 직행 (dots 포함 전 기업 도달 보장) |
| 성능 게이트 | 최대 섹터(dots 최다)에서 pan/hover 60fps, ego 전환 <300ms (fetch 포함) |
| 팔레트 확장 | 신규 섹터 = integration이 `SECTOR_DEF`(adapter.js)와 `SECTOR_PALETTE`(bundle.jsx) **동시 추가** — ⚠️ adapter의 buildPalette(adapter.js:127-129)가 SECTOR_DEF 미등록 섹터를 **에러 없이 필터 탈락**시켜 섹터가 조용히 사라짐(실재 확인). ★v1.1 추가 실측: 현재도 SECTOR_DEF 12종 vs bundle.jsx fallback 팔레트 16종으로 **이중 소스 불일치** — U2에서 정합화. 소실 차단은 QA가 아니라 **하네스 V-2 assert(§5.5)로 기계화**. U2 태스크에 "루트 DESIGN.md에 섹터 색 추가 절차 조항 신설(현재 부재)" 포함 |
| 면책 | "공시 기반 참고 정보" 문구 — 투자 조언 표현 금지 |

### 단계별 화면 진행 시나리오

- **U2 (화면 v1)**: universe 첫 화면 구성은 현행 유지(named 노드 50→400 증가). 섹터 진입 시
  dots 추가. 기업 클릭 시 신설 EgoView — 지배구조 레이어만, 토글 UI는 자리만 두고 밸류체인 비활성.
  기존 graph_top50 경로 병행 유지(회귀 무손상 게이트).
- **U3**: EgoView 토글 활성 — 밸류체인 레이어(valuechain V1 T1 데이터) 표시, 범례 교체(U-D14).
- **U4**: universe 레벨 섹터 간 집계 흐름선(valuechain V4 합류) + graph_top50 은퇴.

---

## 5.5 시각화 엣지 검증 하네스 (하네스 V) ★v1.1 신설

> galaxy의 "체커 PASS + 감사 PASS" 패턴을 관계망 엣지에 이식 — 데이터→export→adapter→렌더
> 전 구간을 기계 검증한다. "엣지가 잘 그려졌는가"를 눈이 아니라 스크립트가 판정.

| 단 | 소유 | 내용 | 시점 |
|---|---|---|---|
| **V-1 계약 체커** | relation (pytest·CI) | export 산출물 정적 검증: JSON 스키마 · rl-string 3-분할 왕복 파싱 · ego 참조 무결성(이웃 티커 전원이 companies_index에 존재) · 엣지 sector_id가 sectors.json에 존재 · named=400 카운트 · 중복 엣지 0 · **export 2회 실행 diff 0(멱등)**. valuechain.json에도 동일 확장(valuechain V1) | U1/V1 export 구현과 **같은 브랜치에서 동시 작성** |
| **V-2 핸드오프 assert** | integration (extract_data 동기화 단계) | sectors.json의 모든 섹터가 `SECTOR_DEF`+`SECTOR_PALETTE` **양쪽에 등록**됐는지 동기화 시점 assert — 미등록 발견 시 **동기화 실패로 중단**. "섹터 조용한 소실"(§5 팔레트 행)을 QA 체크리스트가 아닌 기계적 차단으로 승격 | U2 |
| **V-3 렌더 하네스** | integration (/viewer-check 확장) | 시나리오 3종(대기업 계열·비계열 중견·코스닥 소형)에서 **기대값을 export JSON에서 자동 도출**(클릭 노드의 엣지 수·관계유형별 선 스타일·레이어 전환 시 범례 구성) → Playwright 실화면 대조 + 스크린샷 아카이브. 수기 fixture가 아닌 JSON 도출식 — 2,600사 확장에도 유지비 없음. U3에서 레이어 토글 범례 전환 검증 추가 | U2 (U3 확장) |

---

## 6. 실행 로드맵 U0~U4

> E2E 파이프라인: DART·공정위·pykrx 수집 → relation.db(RelationLocal) + CompanyRegistry
> → transform(필터·분류·dedupe) → universe/export.py 4종 산출 → integration extract_data 동기화
> → SectorMap LOD·EgoView 렌더 → /viewer-check QA. 각 단계 산출물이 다음 단계의 입력.

### 6.0 통합 실행 순서 — valuechain V-Phase 인터리빙 정본 ★v1.1

> 두 계획서의 Phase를 하나의 실행 대열로 확정. 이후 세션은 계획 재수립 없이 이 표 순서로 속행.

| 순서 | Phase | 핵심 내용 | 브랜치 | GPU | 게이트 |
|---|---|---|---|---|---|
| 0 | 보안 fix | llm.py IP·계정 제거(env 이동) | `fix/report-llm-secrets` → dev | ✗ | 저장소 grep 0건 |
| 1 | **V0+U0** | shared/data/ 신설·reports.db 승격(경로 10곳) · CompanyRegistry+universe 5컬럼 1회 마이그레이션 · corps.csv 2,600 확장 → 수집 배치 개시(3~5일, 병행) · 시총(pykrx)·KSIC 섹터·top-400 | `feat/relation-universe-v0` | ✗ | U0 게이트(§6 표) + galaxy 회귀 무손상 |
| 2 | **U1** | DART 2종 전수 + FTC 스타 전환 + filters Registry 교체 + 멱등 upsert + **V-1 계약 체커** — V0 수집 배치와 병행 | `feat/relation-universe-edges` | ✗ | U1 게이트 + V-1 통과 |
| 3 | **V1** | T1 정형 파서 3종 + valuechain.json(+V-1 확장) — 48사 코퍼스 선검증 → 수집 완료분 증분 | `feat/valuechain-t1` | ✗ | 반도체 앵커 3사 QA + V-1 |
| 4 | **U2** | export 4종 + extract_data 동기화(+**V-2 assert**) + dots + 셸 EgoView(governance) + SECTOR_DEF/PALETTE 정합화 + DESIGN.md 절차 신설 + **V-3 렌더 하네스** | `feat/relation-universe-viz` (리더) | ✗ | U2 게이트(V-3로 실행) |
| 5 | **U3** | 특수관계자 주석 파서(V1 공용 1벌) → dart_filing 확장 + EgoView 밸류체인 토글 활성 | V1 브랜치 편승 | ✗ | 스팟 30건 ≥0.85 |
| 6 | **V2** | B0 모델 후보군 조사·재선정(valuechain §3.4 ★v1.4) → 청킹 + 하네스 A·B → 봉인 평가 | `feat/valuechain-ml` | ✓(복구됨) | G-A·G-B·S1∧S2 |
| 7 | **V3** | 하네스 C 섹터 확산 + M2 별칭 루프 | 〃 | ✓ | G-C 섹터당 |
| 8 | **V4+U4** | ECOS 산업연관표 T3 백본 · 섹터 간 흐름선 · graph_top50 은퇴 | `feat/valuechain-t3` | ✓ | — |

### 6.1 실행 드라이버 절차 ★v1.1 — 모든 실행 세션의 공통 루프

1. PLAN.md(본 문서 + valuechain) 체크박스 스캔 → §6.0 순서상 다음 미완 항목 식별
2. 해당 항목 구현·실행 (장기 배치는 백그라운드 가동 후 다음 **병행 가능** 항목으로 이동)
3. 게이트는 **스크립트 산출값만**으로 판정 (pytest · 체커 · /viewer-check 리포트 — 주관 판정 금지)
4. PROGRESS.md에 결과 기록 + 체크박스 갱신
5. 사람 개입 지점은 **CPA 검수 4곳**(val 표본·test 봉인·C6 스팟·M2 별칭)과 게이트 연속
   실패 시 중단 결정뿐 — 그 외는 무인 속행. 세션 경계는 계획이 아니라 달력 대기
   (DART 일 한도 배치·GPU 야간 시분할·CPA 검수)에서만 생긴다.

| Phase | 내용 | 게이트 (정량) | 의존·브랜치 |
|---|---|---|---|
| **U0 기반** | valuechain V0와 **동시 실행**: CompanyRegistry에 universe 컬럼 포함해 1회 마이그레이션, registry 2,600 적재(KSIC 포함), 시총 스냅샷, `ksic_sector_map.csv`, top-400 선정, `sectors.json` handoff, pykrx requirements 등록 | **U0 하드 게이트(`universe/validate.py`, pytest 고정) — G1 registry ≥ 2,500 · G2 named400 == 400 · G3 오염 0(named400 전부 보통주: 종목코드 끝자리 0·우선주 명칭 없음) · G4 섹터 미매핑 0 · G5 named400 전부 시총 확보.** ★v1.1(2026-07-21) 재정의: 구 "KOSPI200 교집합 ≥90%"는 **잘못 지정된 프록시**였음 — 우리 선정=순수 시총 상위 200, KOSPI200=시총+유동성+섹터균형+리츠/펀드 제외라 순수 시총으론 교집합이 구조적으로 ~84%가 천장(실측 168/200, 불일치 64건 전부 실제 기업·펀드, 오염 0). 게이트의 **의도(오염 없는 건강한 대형주 유니버스)**를 G1~G5로 직접 검증. KOSPI200 교집합은 `validate.kospi200_crosscheck()`의 **정보용 참조**로만 유지(외부 원천·리밸런싱 stale, 게이트 아님) | `feat/relation-universe-v0` (V0와 한 브랜치 — 스키마 1회 마이그레이션) |
| **U1 엣지 전수** | DART 2종 전 상장사 수집(최신 연도 1일 + 5개년 백필 3일) + FTC 전 집단(스타) + **`transform/filters.py`의 top50 자연 필터 → CompanyRegistry 필터 교체**(미교체 시 2,600사를 수집해도 엣지는 top50 간만 생성 — E2E 단절 지점) + 멱등 upsert 전환. `dedupe.py`·`kifrs.py`는 그대로 스케일 | 지분 엣지 ≥ 3,000 · M4 멱등 pytest 통과 · 링킹 실패율 < 5% (초과분 LinkFailQueue) | `feat/relation-universe-edges` — GPU 불요 |
| **U2 export + 화면 v1** | 산출물 4종 + extract_data 동기화 등록 + SectorMap dots + EgoView(governance) + 팔레트 확장(SECTOR_DEF+SECTOR_PALETTE 동시) | 최대 섹터 60fps · 화면 QA 3시나리오(대기업 계열 / 비계열 중견 / 코스닥 소형)를 **/viewer-check**(정적+Playwright 동적 검증)로 실행 · graph_top50 경로 회귀 무손상 | `feat/relation-universe-viz` (integration 측 포함 — 리더 소유) |
| **U3 주석 엣지** | 특수관계자 주석 파서(valuechain V1 T1 공용) → dart_filing 확장 + EgoView 밸류체인 토글 wiring | 주석 엣지 스팟 30건 정밀도 ≥ 0.85 (G-C 준용) | valuechain V1 브랜치에 편승 (파서 1벌 원칙) |
| **U4 이연** | T2 서술 추출 지배구조 엣지(GPU) · 섹터 간 집계 흐름선 · 연도 스냅샷 타임머신 · graph_top50 은퇴 | — | **GPU 서버 복구 선행** (임차처 콘솔에서 허용 IP·가동 상태 확인) |

병행(전 Phase): PROGRESS.md에 phase별 엣지 수·게이트 결과 누적 기록. 완료 브랜치는 dev 머지 후 삭제.

---

## 7. 리스크 · 열린 결정

| 리스크 | 대응 |
|---|---|
| V0 스키마 조율 실패 → CompanyRegistry 마이그레이션 2회 | U0 게이트에 "V0 착수 전 스키마 합의" 명시 — 본 문서 U-D5와 valuechain §2.2를 한 마이그레이션으로 |
| adapter.js SECTOR_DEF 필터로 신규 섹터 조용한 소실 | U2 QA 체크리스트 항목화 (§5 팔레트 확장 행) |
| 2,600사 사명 링킹 오염 (동명·구사명) | CompanyAlias + LinkFailQueue (valuechain M2) 준용 |
| ego 2,600 파일 커밋 부피(~5MB)·diff 노이즈 | 매니페스트 해시 기반 변경분만 재작성 (§4) |
| pykrx 크롤 차단 | yfinance 폴백 + 실패 시 직전 스냅샷 유지 (cap_asof로 신선도 표기) |
| SQLite 쓰기 경합 (U1 배치 vs valuechain 배치) | WAL + 장기 배치 직렬 실행 원칙 (§2.1) |
| ftc_group 스타 전환으로 기존 top50 화면의 계열 파선 밀도 감소 | U2 QA에서 삼성·SK 화면 전후 비교 확인 |
| bundle.jsx 비대화 (2,911줄 + Babel-in-browser에 EgoView 추가) | EgoView 별도 소스 파일 분리는 integration(리더) 재량 — 리스크만 노트 |
| GPU 서버 접속 불안정 재발 | ★v1.1: 2026-07-21 IP 허용 후 접속 복구됨. U0~U3은 원래 무영향(CPU·API 경로). 재발 시에도 U4·valuechain V2+만 지연 — T1 전용으로 제품 성립(valuechain §7) |
