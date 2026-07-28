# 기능 결정 원장 — 서빙 계층 기능·파이프라인 채록 (FN_DECISIONS)

> **목적**: integration 서빙 계층(extract_data·build_data·loader·adapter·배포)의 **기능적 결정·버그 패턴·재발 방지 규칙**을
> `FN-###` 번호로 채록한다. UI/UX는 [v2/UX_DECISIONS.md](v2/UX_DECISIONS.md)(UX-###), galaxy 파이프라인은
> [../modules/report/VARIATIONS.md](../modules/report/VARIATIONS.md)(V-###) — 이 파일은 그 사이의 **기능 층**을 담당한다.
> 데이터 모듈은 각자 PLAN.md 결정번호(예: relation U-D#)·PROGRESS.md가 같은 역할.
>
> **운영 규칙** (UX 원장과 동일):
> 1. **착수 전 필독(S0)**: 서빙 계층 기능 작업 전 이 원장을 읽는다 — 같은 버그를 다시 밟지 않기 위해.
> 2. **작업 후 기록(S7)**: 기능적 버그·설계 번복·재발 위험 패턴을 발견하면 그 자리에서 FN-### 추가.
> 3. **2회 반복 = 승격**: 같은 패턴 2회 이상이면 원장에 머물지 말고 코드 게이트(assert·테스트)나
>    CLAUDE.md 조문으로 승격, 항목에 `→ 코드화`/`→ 조문화` 표기.
>
> **기록 형식**: `FN-###` | 일자 | 층위(파이프라인/프론트 와이어링/배포/환경) | 증상 → 원인 → 처리 | 재발 방지

---

## ① 파이프라인 층 (extract_data·build_data·export 동기화)

- **FN-001** (07-22, 환경) — **Windows cp949 콘솔에서 print문 em-dash(—) 크래시**: extract_data.py의 한국어 print에 `—`를 쓰자 `UnicodeEncodeError: 'cp949' codec can't encode`로 exit 1 — 동기화는 다 끝났는데 출력만 죽어 실패로 오인. **원인**: Windows 콘솔 기본 인코딩 cp949는 em-dash·불릿(·는 OK) 일부 유니코드를 못 쓴다. **처리**: print문 한정 `—`→`-` 교체(주석·docstring은 무관). **재발 방지**: 파이썬 print에 em-dash·특수 대시 금지 — 하이픈만. 같은 계열(relation CLI도 동일 환경)이니 전 파이프라인 공통 주의.
- **FN-002** (07-22, 파이프라인) — **V-2 핸드오프 assert = 섹터 조용한 소실 차단 게이트** `→ 코드화`: sectors.json의 섹터가 adapter.js SECTOR_DEF에 미등록이면 buildPalette가 필터링해 **화면에서 조용히 사라진다**(에러 없음). **처리**: extract_data.py가 동기화 시 정규식으로 SECTOR_DEF 등록 여부를 검사, 미등록 발견 시 exit 1(빌드 실패). 섹터 추가 절차는 루트 DESIGN.md §2.5. **재발 방지**: relation이 섹터 taxonomy를 바꾸면 이 게이트가 자동으로 잡는다 — 게이트를 우회(주석 처리)하지 말 것.
- **FN-003** (07-22, 파이프라인) — **동기화 산출물은 diff 노이즈 억제**: ego/<ticker>.json 2,651건을 매 실행마다 전량 재작성하면 git diff가 폭발. **처리**: SHA-256 해시 비교로 변경분만 쓰고, 소스에서 사라진 티커 파일은 삭제(상장폐지 대응). **재발 방지**: 대량 파일 동기화 단계를 새로 만들 땐 같은 해시-diff 패턴을 쓸 것.

## ② 프론트 와이어링 층 (loader·adapter·bundle)

- **FN-004** (07-22, 와이어링) — **캐시버스트 버전 규율**: loader.js·adapter.js·bundle.jsx는 쿼리 버전(`?v=k5b`)으로 로드된다 — **파일을 수정해도 버전을 안 올리면 브라우저가 구버전을 실행**해 "고쳤는데 안 고쳐짐"으로 오진(실제 발생: 새 loader가 디스크에 있는데 캐시된 구버전이 돌았음). **처리**: 수정 시 반드시 버전 문자열 올리기 — index.html(mock/valuation/narration/loader/adapter)과 adapter.js 내부(bundle.jsx URL) 두 곳. **재발 방지 후보**: 빌드 도구 도입 전까지는 수동 규율 — 검증 전 체크리스트 1번.
- **FN-005** (07-22, 와이어링) — **데이터 소스 전환은 graceful fallback 사다리로**: universe.json 도입 시 기존 graph_top50 경로를 제거하지 않고 `usingUniverse` 분기(universe → top50 → mock 순 폴백)로 공존시킴 — 소스 파일이 없거나 브랜치가 달라도 화면이 죽지 않는다(실측: universe 없는 브랜치에서 top50으로 자동 폴백). **재발 방지**: 새 데이터 소스로 갈아탈 때 구 경로를 즉시 삭제하지 말고 폴백 사다리에 편입, 은퇴는 안정화 후 별도 커밋으로.
- **FN-006** (07-22, 와이어링) — **캔버스 레이아웃 노드는 x/y·gx/gy 쌍 필수**: SectorMap 애니메이션이 `c.x/c.y`(초기 위치)와 `c.gx/c.gy`(목표 위치)를 모두 읽는다 — 새 레이아웃 빌더가 gx/gy만 넣으면 animPos 초기화가 NaN → `createRadialGradient non-finite` 크래시(실제 발생, 드릴인 구현 중). **재발 방지**: layout 배열에 노드를 만드는 코드는 네 필드 전부 채울 것.

- **FN-008** (07-28, 와이어링) — **드릴인 상태 리셋이 기업 진입을 붕괴시킴** `→ 코드화`: ghost 관계 노드로 타 섹터 기업에 진입(SK하이닉스→SK류)하면 `selectGhost`→`enterSector()`가 `activeMarket`을 null로 리셋 → SectorMap이 성운 개요 모드(시장 프록시 노드 2개)로 렌더되는데 활성 기업은 layout에 없어(ai=-1) **중앙에 안 나타나고 배경은 개요 dots로 남음**(전 기업 공통, 리더 보고). **처리 2중**: ① App — selectCompany/selectGhost가 `indexByCode[code].mkt`로 그 기업의 시장을 즉시 설정 ② SectorMap — `effectiveMarket = activeMarket || 활성기업의 mkt` 방어(상태 불일치여도 개요 모드로 안 떨어짐). **재발 방지**: LOD 상태(activeSectorId·activeMarket·activeCompanyCode)를 바꾸는 새 진입 경로(딥링크·검색·목록 클릭 등)를 추가할 땐 **세 상태가 정합인지**(기업이 있으면 그 기업의 섹터·시장) 반드시 확인 — 하위 상태만 세팅하고 상위를 리셋하면 같은 붕괴 재발.

- **FN-009** (07-28, 와이어링) — **CSS는 캐시버스트 대상에서 누락돼 있었다 → 레이아웃 붕괴** `→ 조문화`: EgoView 신설 시 `.ego-stage`/`.ego-canvas` 규칙을 styles.css에 넣었으나 **index.html의 `<link href="./styles.css">`에 버전 쿼리가 없어** 브라우저가 구버전 스타일시트를 계속 사용 → 규칙 부재 → 캔버스가 CSS 사이즈를 못 받고 **기본 300×150으로 붕괴**, 그림이 화면 좌상단에 박힘(리더 보고). **원인 2중**: ① FN-004는 JS 3종(loader/adapter/bundle)만 규율했고 **CSS 2종(styles.css·tokens.css)은 버전이 아예 없었다** ② 신규 컴포넌트의 필수 레이아웃(캔버스 크기)을 스타일시트에만 의존시켰다. **오진 위험**: 개발자의 Playwright 검증은 캐시 빈 새 컨텍스트라 정상으로 보이고 리더 브라우저만 깨진다 — 실제로 그렇게 지나갔다. **처리 2중**: ① index.html의 styles.css·tokens.css에 `?v=` 부여(이후 FN-004와 동일하게 함께 상향) ② EgoView 캔버스의 `position/inset·width/height 100%`를 **JSX 인라인 스타일로 고정** — 레이아웃은 스타일시트 캐시에 의존하지 않게. **재발 방지**: 캐시버스트 규율(FN-004)의 대상은 **JS 3종 + CSS 2종 = 5개 전부**. 그리고 **캔버스류 컴포넌트의 크기 결정 CSS는 인라인으로** — 스타일시트가 한 세대 밀려도 화면이 붕괴하지 않게. 검증 시 캐시된 브라우저(하드 리로드 전) 상태도 한 번 볼 것.

- **FN-010** (07-28, 파이프라인) — **export가 파싱된 주석 카테고리를 통째로 흘렸다**: EgoView가 특수관계자 노드에 구분(지배기업/관계기업/대규모기업집단)을 못 띄우길래 원인을 보니 ego JSON의 `detail`이 dart_filing 124건 전부 빈 문자열. **원인**: `universe/export.py`가 `detail = ratio% if ratio else (group_name or "")`로만 만들어 **`RelationLocal.detail` 컬럼을 아예 안 읽었다** — DB에는 `사업보고서 주석: 지배기업` 등이 멀쩡히 있었다(파싱 실패가 아니라 export 누락). 리더가 "사업보고서에 있어서 추출이 된 거 아냐?"로 짚어 발견. **처리**: `_edge_detail()` 헬퍼 신설(지분율 > 계열 그룹명 > 주석 구분 순 폴백) + `_normalize_filing_category()`로 원문 변형 정규화(`사업보고서 주석: ` 접두 제거, `(주1)`·`(*1)` 주석기호 제거, `기  타`→`기타`, `유의한 영향력을행사하는 회사`→`유의적 영향력`) → 6종 카테고리로 수렴(대규모기업집단 50·관계기업 36·기타 20·지배기업 12·유의적 영향력 4·최상위 지배기업 2). **⚠️ 같이 잡은 지뢰**: rl-string은 `이름:타입:detail` 3분할 계약이라 원문의 콜론이 그대로 나갔으면 adapter 파싱이 깨졌다 — 정규화가 접두어와 함께 제거하고 방어적으로 콜론을 한 번 더 지운다. **재발 방지**: export가 DB 컬럼을 화면 필드로 접을 때 **폴백 사다리의 마지막 칸을 비워두지 말 것**(빈 문자열은 에러가 아니라 조용한 소실). 값이 항상 비는 필드는 V-1 계약 체커에 "필드별 non-empty 비율" 점검을 넣는 게 다음 단계.

## ③ 배포·환경 층

- **FN-012** (07-28, 와이어링) — **집계의 first-wins는 순서 종속 버그의 온상**: EgoView `mergeEgoNeighbors`가 이웃의 `dir`을 "처음 만난 엣지" 기준으로 고정 → 삼성물산처럼 investment(in)+ftc_group(out) 혼재 이웃은 **ego JSON의 엣지 나열 순서에 따라 위/아래가 뒤바뀔** 수 있었다(화면 증상 없이 잠복 — V-3 하네스 오라클을 스펙에서 독립 재구현하다 발견). **처리**: `dirByType`으로 타입별 dir을 보존하고 `isIncoming = primary(최우선) 타입의 dir` — hasEquity면 primary는 항상 지분 타입이라 UX-011 "지분 엣지의 출자 방향" 계약과 정확히 일치. **재발 방지 2중**: ① 여러 레코드를 하나로 접는 코드에서 "첫 값 채택"은 입력 순서가 계약인지 먼저 물을 것 — 아니면 우선순위 규칙으로 결정적이게 ② 이런 계열은 눈으로 안 보인다 — **V-3 하네스가 오라클(스펙 재구현) 대조로 상시 검출**(qa/v3_harness.py, 뮤테이션 캘리브레이션 완료: SIDE_N 변조 시 정확히 해당 체크만 FAIL 확인).

- **FN-013** (07-28, 파이프라인/relation) — **이름-only 엔티티 링킹의 동명 충돌 → 허위 지배 엣지**: HMM 화면에 "현대자동차 종속기업 99.99%"(리더 발견 — HMM 대주주는 산업은행·해양진흥공사). **계보**: 현대차 사업보고서 타법인출자현황(otrCpr)의 출자 대상 원문 "HMM"은 해외 생산법인 약칭(LinkFailQueue 물증: 같은 보고서에서 HMA·HMI·HMD·GMC·GMI가 무리로 검출)인데, otrCpr 응답엔 corp_code가 없어 **정규화 이름 정확 일치만으로 상장 해운사 HMM(011200)에 오링킹** → 4개년 허위 subsidiary 엣지. universe/PLAN.md §2.2가 경고한 "동명·구사명 충돌"의 실물. **처리 3중**: ① `filters.py`에 **모호 약칭 게이트** — otrCpr 대상명이 영문 2~5자 단독(`^[A-Za-z&.\- ]{2,5}$`)이면 자동 링킹 금지, LinkFailQueue 적재(M2 수동 별칭 루프 입력). 정밀도 우선 트레이드오프: KT·NAVER·POSCO 등 진짜였을 소액 지분 엣지도 큐로 빠짐(active 3,508→3,448) — M2에서 별칭 확정 시 복구 ② transform 재실행의 기존 **prune 로직**이 오염 4행 자동 정리(수동 DELETE 불요 — 재수집에도 재발 안 함) ③ **50%+ 교차검증 스캔**(otrCpr 50%+인데 상대의 hyslrSttus에 출자사 부재 = 모순) → 54건 CPA 검수 리스트 `modules/relation/data/review_otrcpr_50plus_crosscheck.csv`. ⚠️ 이 54건은 자동 삭제 금지 — 표본 확인 결과 하림지주→팬오션·신한지주→제주은행 등 **사실인 엣지 다수**(hyslrSttus 수집 갭이 원인) — §6.1 CPA 검수 지점. **재발 방지**: corp_code 없는 원천의 이름 링킹에는 항상 "모호성 게이트 + 큐" 층을 둘 것 — 정확 일치는 신원 증명이 아니다.
  - **M2 1차 검수 반영 (07-28 후속)**: CPA 검수 54건 판정 = TRUE 39 / FALSE 15. FALSE 유형 3종 — ① **한글 동명 비상장**(12건: DS단석의 '하이브 주식회사', 유진기업의 '동화기업(주)' 등 — 약칭 게이트가 못 막는 한글판. "상장사 100% 보유 = 유통주식 없음 = 모순" 정황이 8건에서 결정타) ② **수치 오파싱**(영풍→시그네틱스 710651%, SKT→하나금융지주 62.5%) ③ **구사명 충돌**(금호에이치티의 '풍전약품(주)'=비상장 자회사인데, 이를 인수한 에스씨엠생명과학(298060)이 '풍전약품'으로 개명해 현재 사명과 정확 일치 — 외부 검수표의 사유 검증 중 웹 확인으로 확정). **처리**: `data/link_blocklist.csv`(쌍 단위 차단, 사유 병기) + filters 적용 → transform 재실행 → prune 자동 정리(active 3,448→3,415). 교훈 2가지: 검수표(외부 AI 산출 포함)도 사유가 틀릴 수 있다 — 수용 전 registry·웹 재검증 필수 / **registry의 name_current는 "현재" 사명** — 과거 연도 공시의 이름 링킹은 그 시점 사명과 어긋날 수 있다(구사명 이력 테이블이 근본 해법, V2+ 과제).

- **FN-011** (07-28, 환경) — **DB가 100MB를 넘으면 push가 통째로 막힌다 → 대용량 DB는 추적 제외가 원칙**: relation.db가 U1~U3 전 상장사 수집으로 156MB가 되어 `git push`가 GitHub 100MB 한도에 거부됨(미푸시 60커밋 중 25개가 이 파일 포함 — 커밋 시점엔 아무 경고 없음). **처리**: reports.db 선례(2026-07-21 gitignore 승격)와 동일 취급 — ① `.gitignore` 등록 + `git rm --cached` ② 미푸시 구간(origin/dev..HEAD) `filter-branch --index-filter`로 이력에서 blob 제거(빈 커밋은 보존 — 메시지가 작업 원장 역할). 재작성 전 `backup/pre-filter-relation-db-20260728` 태그. 조상 브랜치 feat/relation-universe-v0도 동일 체인이라 재작성본으로 재지정. **팀 공유 경로**: DB가 아니라 export 산출물(universe.json·ego/ 등 커밋 유지) — DB는 파이프라인 재실행으로 재현 가능. **재발 방지**: 수집 DB가 커지는 모듈은 50MB 넘기 전에 gitignore 여부를 결정할 것 — 100MB는 커밋이 아니라 **push에서 터지므로** 발견이 항상 늦다.

- **FN-007** (07-22, 환경) — **로컬 검증 서버는 브랜치 상태에 종속**: `integration/data/*.json`은 커밋 대상 파생물이라 **브랜치를 바꾸면 서빙 데이터도 바뀐다** — universe 데이터가 없는 브랜치에서 404가 나 "구현이 사라졌다"로 오진 가능(실제 발생: fix/vercel-* 브랜치에서 universe.json 404). **재발 방지**: localhost 검증 전 `git branch --show-current` 확인 + 대상 브랜치 체크아웃. 검증 흐름: `python -m http.server 8777` → `http://localhost:8777/integration/v2/index.html` → 하드 리로드(Ctrl+Shift+R).
