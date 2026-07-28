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

## ③ 배포·환경 층

- **FN-007** (07-22, 환경) — **로컬 검증 서버는 브랜치 상태에 종속**: `integration/data/*.json`은 커밋 대상 파생물이라 **브랜치를 바꾸면 서빙 데이터도 바뀐다** — universe 데이터가 없는 브랜치에서 404가 나 "구현이 사라졌다"로 오진 가능(실제 발생: fix/vercel-* 브랜치에서 universe.json 404). **재발 방지**: localhost 검증 전 `git branch --show-current` 확인 + 대상 브랜치 체크아웃. 검증 흐름: `python -m http.server 8777` → `http://localhost:8777/integration/v2/index.html` → 하드 리로드(Ctrl+Shift+R).
