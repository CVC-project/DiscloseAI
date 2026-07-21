# Relation 모듈 진행경과

> `/check` skill 실행 시 아래 형식으로 자동 기록됩니다.

## 2026-07-22 — V1 정확도 재검토 (related_party.py 커버리지 버그 발견·수정) + 공급계약 배치 착수
- **작업**: 이전 세션(2026-07-21)의 U1 PASS·V1 마무리·U2 착수 상태 확인 후 속행.
  단일판매·공급계약 실 코퍼스 실행 준비 중 DART `list.json` 조회기간 상한(문서화
  안 됨)을 실측으로 발견, 수정하는 과정에서 related_party.py의 1차 실행 결과(109
  노트→69엣지)가 비정상적으로 낮다는 의심이 들어 전수 재검증 → **심각한 커버리지
  버그 발견**(아래).
- **DART list.json 조회기간 상한 버그**: `bgn_de`~`end_de` 1년 범위 호출 시
  `status="100"`(파라미터 오류) 즉시 반환 — 3개월(분기) 단위는 정상(2024 Q1
  I001 19,434건/195페이지 확인). `discover_filings()`가 ≤89일 구간으로 내부
  자동 분할하도록 수정(`_split_date_windows()` 신설 + 순수함수 단위테스트 3건).
  기존 status 처리도 "013(데이터없음)"과 "그 외 오류"를 구분하지 않고 전부
  조용히 멈추던 것을, "013은 정상 종료·그 외는 예외 발생"으로 분리(할당량 소진
  등을 침묵 속에 놓치지 않도록).
- **related_party.py 커버리지 버그 발견·수정 (심각, 이미 배포된 데이터 오염)**:
  실측 재검증 결과 109개 특수관계자 노트 중 **겨우 13개만 파싱 성공**하고 있었음
  (1차 실행 69엣지는 사실상 이 13개에서만 나온 것). 원인: `_extract_period_blocks`가
  "당기/전기 마커 직후 빈 줄 하나"만 가정했으나(2026-07-21 삼성전자 표본 하나로
  확정한 가정), 실제로는 다수 회사가 마커와 표 사이에 **제목·기간·단위를 파이프 없이
  그대로 반복하는 평문 줄**을 끼워 넣어(sectioner가 `<P>` 문단과 `<TABLE>`을 각각
  렌더링해 중복 생김) 표가 통째로 0줄 파싱되고 있었음. 추가로 라벨 스킴 자체가
  회사군마다 다름을 발견 — "매출 등"/"매입 등"(삼성 계열) 외 "수익거래"/"비용거래"
  (현대차 계열 등)도 있어야 함. 두 버그를 함께 수정 → 41/109 노트 커버(3배 이상
  개선). 수정 중 **2단 rowspan 하위분류 행이 값 위치를 한 칸 밀어 엉뚱한 상대회사에
  금액을 귀속시킬 뻔한 위험**도 발견 — 헤더·데이터 셀 수가 정확히 일치하는 행만
  채택하는 가드 추가(총계 대신 세부내역만 잡히는 손실은 감수하되 오귀속은 원천 차단).
  현대로템 실제 공시 fixture 기반 회귀 테스트 4건 신설.
  - **정직하게 기록 — 남은 구조적 한계**: 나머지 ~65/109(하나금융지주 계열·
    LIG넥스원 등)는 표가 **전치(transposed)**돼 있음(행=상대회사명, 열=거래유형 —
    현재 파서가 가정하는 구조의 반대). 이번 세션엔 손대지 않음(억지 매칭 금지) —
    후속 과제로 valuechain/PLAN.md에 남김.
  - **재실행 결과**: 수정된 파서로 실 코퍼스 재실행 → **109노트 → 155엣지**(customer
    79·supply 76, 이전 69에서 +86). link_fail_queue는 164건(더 많은 노트를 정상
    파싱하게 되면서 링킹 시도 자체가 늘어난 자연스러운 결과).
- **단일판매·공급계약 T1 파서 실 코퍼스(2020~2026) 배치 착수**: 전 상장사 5개년
  범위는 1년(2024)만 시험 조회해도 discover 610초·매칭 1,648건 — 5~7개년 전체는
  list.json 페이지네이션만 수천 건, 매칭 공시 document.xml 개별 fetch까지 합치면
  DART 일 할당량(10,000건) 초과 가능성이 높아 **DART 5개년 백필과 동일하게 연도별
  체크포인트 배치**로 설계(연도마다 discover→fetch→apply 커밋, 할당량 소진 시
  RuntimeError로 즉시 감지해 그 자리에서 정상 중단·로그 기록 — 침묵 실패 방지).
  백그라운드 실행 중(로그: scratchpad/supply_contract_backfill.log) — 다음 세션에서
  진행 상황 확인 필요.
- **회귀**: 전체 153/153 PASS(기존 140 + 신규 date-window 3건 + Hyundai Rotem 4건 +
  기존 테스트 조정 후 재검증 6건 순증분 반영).
- **다음 세션**: (1) 공급계약 배치 진행/완료 확인 → 미완료면 이어서(연도별 재개
  가능) → export.py 재실행해 valuechain.json 갱신 (2) U3 착수 재검토 — 특수관계자
  노트 안에 거버넌스용 "구분/특수관계자명"(지배기업·관계기업·대규모기업집단 등)
  리스팅 표가 거래금액 표와 별도로 존재함을 확인(삼성바이오로직스·현대로템 표본).
  이 표 역시 회사마다 구조가 다르므로(2-컬럼 구분/명칭 나열형 vs 와이드 카테고리별
  1행형) U-D2 "파서 1벌, 소비자 2곳" 원칙대로 재사용하되 신규 investigate 필요 —
  서두르지 말 것. 레거시 `ingest/filing.py`(CompanyNode 기반, U1 이전 스캐폴드)는
  이 신규 경로로 대체 대상 — 대체 완료 전까지는 유지, U-D2 원칙 위반(이중 구현)
  상태임을 인지하고 있을 것.

## 2026-07-21 (7) — U2 착수: universe/export.py + filters.py prune 버그 발견·수정
- **작업**: V0 마무리(CompanyAlias 시드 재시도 성공, 21건) → V1 T1 파서(특수관계자 주석)
  실 코퍼스 전량 실행(109 노트 → 69 ValueChainEdge, 123 LinkFailQueue) → U2 착수:
  `universe/export.py` 신규 구현.
- **실측 버그 발견·수정 (3번째)**: `universe/export.py`로 삼성전자 ego 파일을 만들어
  교차검증하던 중, `ftc_group` 엣지가 dir=in/out 뒤섞여 28쌍(C(8,2) 클리크) + 8개
  신규 스타가 **공존**하는 것을 발견 — U1에서 FTC를 클리크→스타로 바꿨는데도 2026-04
  MVP 시절 클리크 엣지가 그대로 남아있었음. 원인: `filters.apply()`가 upsert만 하고,
  RelationRaw에서 이미 사라진 관계에 대응하는 RelationLocal 행을 지우는 로직이
  없었음(ftc.py의 collect()는 RelationRaw를 지우고 다시 채우지만 RelationLocal은
  손대지 않는 설계라 상류 변경이 하류에 전파 안 됨). 수정: 이 함수가 관리하는 4개
  source_type 전체에 대해 이번 실행에서 touch된 자연키를 추적, 끝에 미touch 행을
  prune. 재실행 결과 48건 정리 → relation_local 3,508→**3,460행**(U1 게이트
  ≥3,000 여전히 충족). 회귀 테스트 추가(클리크→스타 전환 재현). 전체 189/189 PASS.
- **universe/export.py 구현 + 실행**: universe.json(400 named/2,651 total, 섹터
  25종 집계+dots 좌표) · ego/`<ticker>`.json ×2,651(governance+valuechain 레이어
  통합, U-D10) · sectors.json · companies_index.json — 4종 전부 실제 생성(8.1MB,
  계획 추정 ~5MB와 같은 자릿수). 삼성전자 ego로 정합성 확인(지분·FTC 스타 정상).
- **다음 세션**: DART 할당량 리셋 후 단일판매공급계약 파서 실 코퍼스 실행 →
  U2 계속(SectorMap dots·셸 EgoView·SECTOR_DEF/PALETTE 정합화는 integration
  프론트엔드 작업, 리더 담당) → U3(주석 파서 governance 소비) → V2(GPU 모델
  재선정) 순.

## 2026-07-21 (6) — U1 게이트 최종 PASS (dedupe.py 연도 오삭제 버그 발견·수정)
- **작업**: DART 5개년 백필 완주(2020 부분 5,657행 + 2021~2024 전량, 백필 전체
  68,021+86,988행 신규) 확인 후 relation.db 커밋 → filters→kifrs→dedupe 재실행 →
  U1 게이트 재평가.
- **실측 버그 발견·수정 (중요)**: 재실행 결과 엣지가 1,088→1,353(24%만 증가 —
  raw 데이터는 5배 늘었는데 이상하게 적음)로 나와 원인 추적 → **`dedupe.py`의
  그룹핑 키 `(pair, relation_type)`에 `bsns_year`가 빠져 있어, 같은 기업쌍의
  "다른 연도" 기록까지 "양방향 중복"(A→B vs B→A)으로 오인해 지워버리고 있었음**
  (kifrs 분류 4,766건 중 71.6%가 dedupe에서 사라짐 — 정상적인 양방향 중복 비율이
  아님). top50 단일연도 MVP 때는 잠복해 있던 버그(그때는 애초에 "다른 연도"가
  존재하지 않았음), 전 상장사 5개년 도입으로 처음 표면화. 그룹핑 키에 bsns_year
  추가로 수정 — RelationLocal의 UNIQUE 키(U-D13)와도 이제 정합. 회귀 테스트
  추가(같은 쌍·다른 연도 2건이 dedupe 후에도 유지되는지, 커밋 `ab17ae0`).
- **U1 게이트 최종 판정 — 4개 전부 PASS**:
  - ✅ 지분 엣지 ≥ 3,000 → 수정 후 재실행 결과 **3,508행**(subsidiary 517·
    associate 1,631·investment 1,134·ftc_group 226). 연도별 분포도 상식적
    (2020 부분 86 · 2021 737 · 2022 783 · 2023 814 · 2024 862 · 2025(ftc) 226)
  - ✅ M4 멱등 pytest 통과 (188/188 전체 회귀, dedupe 회귀 1건 포함)
  - ✅ 링킹 실패율 < 5% → 5개년 확장 데이터로 무작위 40건 재표본(seed=7) 전수
    분류 결과 **진짜 링킹 실패 0건**(1개년 때의 50건 표본과 동일 결론 재확인) —
    전부 개인(relate 미포함 유형: 임원·특관자·자·미등기임원 등)·해외 자회사·
    사모펀드·비상장 소형사였음
  - ✅ galaxy 회귀 무손상
  - **U1 = 완료.**
- **다음 세션**: V0 마무리(CompanyAlias 시드 재시도, 이제 relation.db 락 없음) →
  T1 파서 2종(특수관계자 주석·단일판매공급계약) 실 코퍼스 전량 실행(현재 fixture
  검증만) → U2(export 4종·SectorMap dots·셸 EgoView) 착수. universe/valuechain
  PLAN.md §6.0 순서 그대로, 계획 재수립 불필요.

## 2026-07-21 (5) — V1 마무리 (리더 결정 2건 + V-1 계약 체커 완성)
- **작업**: 별도 세션(동일 저장소, 사용자가 이 세션을 열어둔 채 다른 터미널에서 이어
  실행한 것으로 추정)이 만든 V1 T1 파서 2종(related_party.py·supply_contract.py)이
  다음 세션으로 넘긴 두 열린 질문("타법인출자현황 파서 여부", "익명 엣지 스키마 확장
  여부")을 리더로서 처리.
- **리더 결정 A**: 타법인출자현황은 3번째 T1 파서로 만들지 않음 — U1의 RelationLocal
  (거버넌스)에 이미 완전히 표현돼 있고, ValueChainEdge.edge_type(supply/customer/
  raw_material/competition)에 자연히 대응하지 않음. 억지 구현 시 U-D14의 거버넌스/
  밸류체인 문법 분리를 파서 레벨에서 재차 위반. → **valuechain T1 = 정형 파서 2종
  확정**(특수관계자 주석·단일판매공급계약).
- **리더 결정 B**: 익명 엣지 스키마 확장(`dst_corp` nullable)은 지금 안 하고 T2로
  이연 — T1의 존재 이유는 정밀·고신뢰인데 익명 항목은 정반대. §7 "카운트 기여" 취지는
  LinkFailQueue 누적 + apply() 카운터(`link_failed`/`no_counterparty`)로 이미 약하게
  충족. T2가 confidence·운영점(τ) 스키마를 새로 설계할 시점에 함께 다뤄 마이그레이션
  중복 회피.
- **하네스 V-1 계약 체커 완성**: `test_v1_contract_checker.py` 4건(전부 in_memory_session,
  실 DB 미접촉) — 참조 무결성(엣지 endpoint 전원 Registry 실존) · 자연키 중복 0(3회
  재실행) · 멱등 export(연속 호출 + 파서 재실행 후 재호출 모두 바이트 단위 diff 0) ·
  근거 노출(provenance·rcept_no 필수). universe/PLAN.md §5.5 밸류체인 확장분 완료.
- **회귀**: relation+report 전체 187/187 PASS.
- **관찰(개입 안 함)**: DART 5개년 백필의 2020년치가 이 시점 DART 일일 할당량 소진
  (status=020)으로 전량 실패 스핀 중(1시간 반+ 경과) — 강제 종료 시 그 회차 전체
  트랜잭션(부분 성공분 포함)이 롤백되므로 자연 완주 대기. report 5개년 수집은
  2,590/2,651(97.7%)로 사실상 완료.
- **다음 세션**: 백필 완주 확인(2020년치는 할당량 소진으로 거의 빈 상태 예상 —
  정상, 다음날 재실행으로 보강 가능) → filters→kifrs→dedupe 재실행 → U1 게이트
  최종 재판정(엣지≥3,000) → 커밋. relation.db 락 해제 후: CompanyAlias 시드
  재시도, T1 파서 2종 실 코퍼스 전량 실행(현재 fixture 검증만).

## 2026-07-21 (4) — V1 속행 (T1 파서 2/3: 단일판매·공급계약 수시공시)
- **DART 엔드포인트 조사 결과**(신규 investigate 완료): 전용 구조화 API(fnlttSinglAcntAll류)
  없음 — KRX 수시공시 문서(`document.xml`)뿐. `list.json`을 corp_code 생략(전 상장사 대상)
  + `pblntf_detail_ty="I001"`(거래소 공시)로 검색 → `report_nm`에 "단일판매" 포함 건만
  클라이언트 필터(정확 표기 "단일판매ㆍ공급계약체결"의 가운뎃점은 일반 middle dot이
  아니라 한글 아래아 U+318D — "단일판매" 부분 매칭이 표기 변형에 안전). 실측: 2026년 6월
  한 달 I001 공시 3,602건 중 실제 원본(정정 제외) 6건 확인.
- **document.xml 인코딩 함정 발견**: 응답의 meta 태그가 `charset=euc-kr`이라 명시하지만
  실제 바이트는 UTF-8(euc-kr/cp949로 디코드 시 즉시 "illegal multibyte sequence" 에러) —
  meta 태그를 신뢰하지 않고 UTF-8 우선 시도로 처리.
  문서는 고정 라벨 HTML 표이나 **행 번호·rowspan 그룹 구성이 회사·연도별로 다름**(실측:
  샘플 간 항목 수 7~10개 편차) — 위치 기반이 아니라 라벨 문자열 포함 매칭으로 파싱.
- **실측 발견 — 상대방 비공개 다수**: 계약상대방 필드가 ① 실제 상장사명 ② 업종 설명
  등 비고유명사(영업기밀 보호 사유로 비공개, 실 사례: "방산 솔루션 공급 업체") ③ "-"
  세 갈래로 나뉨. valuechain/PLAN.md §7 리스크("공급계약 공시 상대방 '비공개' 다수 —
  익명 엣지로만 카운트 기여")가 실측으로 그대로 적중.
- **설계 판단 보류(의도적, 리더 검토 필요)**: §7이 말하는 "익명 엣지"를 만들려면
  `ValueChainEdge.dst_corp`가 NOT NULL인 현 스키마로는 표현 불가 — nullable 전환 또는
  별도 익명 카운터 테이블이 필요한 **구조적 결정**이라 이 세션에서 단독으로 스키마를
  바꾸지 않았다. 현재는 링킹 성공분만 엣지화, 실패분(익명 포함)은 카운트만 반환하고
  엣지를 만들지 않는다 — 과소집계이지만 안전한 기본값(다음 세션 리더 판단 대상).
  같은 이유로 **타법인출자현황(RelationRaw 재사용) 파서도 보류** — edge_type이
  supply/customer/raw_material/competition인데 지분투자가 이 중 무엇에도 자연히
  대응하지 않고, RelationLocal(governance investment)과의 중복 표현 위험도 있어
  edge_type 의미론 자체를 리더가 정하기 전엔 구현하지 않기로 함(추측 구현 금지).
  M3 정정공시 처리("[기재정정]" 건)도 원본 rcept_no 참조 파싱이 필요해 이번엔 스킵
  (원본만 처리, 정정 건은 후속 과제로 정직하게 기록).
- **구현**: `extract/supply_contract.py` — `discover_filings()`(list.json 페이지네이션
  검색) / `fetch_filing_html()`(document.xml ZIP → UTF-8) / `parse_filing_html()`(bs4로
  라벨 매칭 파싱) / `apply()`(entity linking + 멱등 upsert, related_party.py와 동일
  linking.py 재사용). CLI: `python -m modules.relation valuechain parse-supply-contracts
  --bgn --end`.
- **테스트**: 실제 DART 공시 문서 2건(그린광학·아티스트스튜디오, 2026-06-30 수집)을
  fixture로 저장 — `tests/relation/test_valuechain/test_supply_contract.py` 5건
  (파싱 단위 2 + apply 통합 3: 링킹 성공/실패·멱등) 전부 PASS. 전체 회귀 140/140 PASS.
- **다음 세션**: (1) 리더에게 익명 엣지 스키마 확장 여부·타법인출자현황 edge_type 의미론
  질문 후 처리 (2) DART 백필 완료 확인 후 U1 재처리 + 특수관계자 주석·단일판매공급계약
  실 코퍼스 실행(현재 둘 다 fixture/샘플 검증만, 전량 실행은 relation.db 쓰기 락 회피로
  보류 중).

## 2026-07-21 (3) — V1 착수 (valuechain 패키지 스켈레톤 + T1 파서 1/3: 특수관계자 주석)
- **작업**: universe/valuechain PLAN.md §6.0 순서 속행. DART 5개년 백필(bfv901a08)·report
  5개년 수집(boocv2xax) 둘 다 백그라운드 실행 중임을 확인(프로세스 alive, 2021년치 수집 중 /
  2,259·2,651 tickers) — 계획서 지시대로 두 배치는 그대로 두고 병행 가능한 다음 항목(V1)으로 이동.
- **정리**: `relation.db.pre-v0-backup` 삭제 — V0 마이그레이션 실측 검증 끝난 지 오래됐고
  git 이력에 원본 보존(복구 가능 확인 후 삭제).
- **신규 패키지**: `modules/relation/valuechain/`
  - `__init__.py`·`chunker/__init__.py`·`train/__init__.py`·`evaluate.py` — Phase V2(GPU 착수) 전까지의
    스켈레톤(docstring만, 착수 시점·의존관계 명시)
  - `extract/reports_source.py` — shared/data/reports.db 읽기 전용 접근. **`modules.report` 패키지를
    import하지 않고 sqlite3 read-only URI로 직결** — "데이터 모듈끼리 import 금지" 원칙과 D11
    reports.db read-only 예외를 동시에 만족시키는 설계(문서화된 전례 없어 신규 결정)
  - `extract/linking.py` — CompanyRegistry+CompanyAlias 기반 엔티티 링킹 공용 유틸(정규화는
    common/names.py 재사용), 실패분 LinkFailQueue 빈도 누적(M2 루프 입력)
  - `extract/related_party.py` — **T1 파서 1/3: 특수관계자 주석**. 실측 확인 10종 제목으로
    report_section 필터 → 마크다운 표 파싱(당기만) → 매출="customer"/매입="supply" 엣지 →
    `ValueChainEdge` 멱등 upsert(UNIQUE src/dst/type/as_of/rcept_no)
  - `export.py` — `ValueChainEdge`(status=active) → `data/valuechain.json`(§2.3 계약. edge별
    as_of 포함 — 최상위 단일 as_of로는 연도 스냅샷 다중 active를 표현 못 하는 실측 보정)
  - `python -m modules.relation valuechain {parse-related-party|export}` CLI 서브커맨드 추가
- **표 구조 실측(삼성전자 5개년 샘플)**: DART XBRL→마크다운 변환이 계층형 컬럼 헤더의 콜스팬
  정보를 소실시켜, 상위 그룹 헤더 행(예: "관계기업 및 공동기업")이 리프 헤더보다 셀 수가 적다 —
  "이 표 블록에서 첫 칸이 빈 마지막 행"을 리프(개별 상대회사명) 헤더로 식별하는 규칙으로 해결.
  "...공시, 합계" 표는 리프 헤더 자체가 카테고리명이라(개별 법인명 아님) 제목으로 통째 스킵.
  "기타 OO" 컬럼은 미상 다수의 집계라 상대회사로 취급하지 않음. "비유동자산 매입"처럼 "매입"을
  포함하되 상거래가 아닌 라벨은 `startswith` 판정으로 오분류 방지(포함 매치 금지).
- **실제 발견한 버그·수정**: 최초 구현은 당기/전기 마커 행 바로 다음에 표 행이 온다고 가정했으나
  실제로는 마커 행과 헤더 행 사이에 빈 줄이 하나 끼어 있어(실측 고정 패턴) 모든 블록이 0줄로
  파싱되는 버그 발생 — pytest 8건 중 3건이 결과 0건으로 실패해 발견, 마커 직후 빈 줄 스킵 로직
  추가로 수정. 회귀 방지용 pytest가 이미 이 케이스를 커버(모든 assertion이 실제 값 대조).
- **테스트**: `tests/relation/test_valuechain/` 신설 — 파서 단위 8건(실제 삼성전자 공시 샘플
  fixture) + apply/export 통합 5건(in_memory_session, 엔티티 링킹·LinkFailQueue·멱등·export
  계약 형태·superseded 제외) = 13건 전부 PASS. 전체 회귀 135/135(기존 122 + 신규 13) PASS.
- **보류(의도적)**: 실 코퍼스 전량 `parse-related-party` 실행은 이번 세션에 하지 않음 — DART
  5개년 백필이 relation.db에 장기 트랜잭션 쓰기 중이라 §2.1 "장기 배치 직렬 실행 원칙" 위반
  회피(SQLite 단일 쓰기 락 재현 이력 있음, U1 세션 기록 참조). 백필 완료 후 실행.
- **미완료(정직하게 기록)**: T1 파서 나머지 2종(단일판매·공급계약 수시공시는 DART 엔드포인트
  미조사, 타법인출자현황은 미착수) — 다음 세션 계속. V-1 계약 체커는 스키마 형태 테스트만
  있고 참조 무결성·멱등 export diff 0 검증은 파서 3종 완료 후 정식화 예정.
- **다음 세션**: DART 백필 완료 확인(2020년치까지) → U1 재처리(filters→kifrs→dedupe) +
  게이트 재판정 + 특수관계자 주석 실 코퍼스 실행. 병행 가능: T1 파서 2/3(단일판매·공급계약
  수시공시 DART 엔드포인트 조사) 또는 3/3(타법인출자현황, RelationRaw 재사용 설계).

## 2026-07-21 (2) — U1 착수 (전 상장사 확장 · 스타 토폴로지 · 멱등 upsert)
- **작업**: universe/PLAN.md §6.0 순서대로 U0 다음 U1 연속 실행 (드라이버 절차, 계획
  재수립 없음).
- **파일**: `common/names.py`(Registry 기반 ticker map) · `transform/filters.py`(Registry
  전환·manual_overrides 구현·전량삭제→upsert) · `ingest/dart.py`(collect() 전 상장사
  확장) · `ingest/ftc.py`(클리크→스타 토폴로지, 시총 최댓값 허브) · `storage/models.py`
  (UNIQUE 키) · `storage/db.py`(busy_timeout) · pytest 4개 신설/개정.
- **실측 버그 발견·수정**: RelationLocal UNIQUE 키에 `relation_type`을 포함시켰던
  최초 설계(V0 커밋)가 kifrs.apply()의 사후 재분류(ownership→subsidiary 등) UPDATE와
  충돌해 즉시 깨짐 — 재현 확인 후 `source_type`(kifrs가 안 건드리는 안정 필드)으로
  키 교체(스키마 주석 + 실 DB 인덱스 마이그레이션, 데이터 93행 바이트 단위 동일 확인).
- **사고·복구**: 버그 조사용 임시 스크립트의 monkeypatch가 이미 임포트된 이름이라
  적용 안 되고 실제 relation.db를 오염(93→275행)시킨 것을 발견 → `git restore`로
  즉시 복구(미커밋 상태였어서 데이터 완전 보존). 이후 filters/kifrs/dedupe에
  `session=` 주입 파라미터를 추가해(validate.py와 동일 패턴) monkeypatch 없이
  in_memory_session으로 안전하게 격리 테스트하도록 전환.
- **SQLite 동시접근**: DART 장기배치(2,651사, 커밋 1회로 묶인 트랜잭션)와 FTC를
  동시 실행하다 "database is locked" 재현 → `busy_timeout=30` 추가. WAL 모드는
  장기 트랜잭션의 배타 락과 충돌해 전환 자체가 실패함을 확인, 보류 — 당장은
  직렬 실행 원칙 유지(근본 해결=증분 커밋 전환은 후속 과제).
- **실제 수집 결과**:
  - DART 2종(2024년, 전 상장사): 주주현황 23,084행 + 타법인출자 31,876행, 오류 0
  - FTC(전 집단): 3,301건 중 247사 매칭, 69개 집단, **스타 178엣지**(클리크였다면
    수천 엣지 폭발 — 예: 최대 집단이 20개사면 C(20,2)=190 vs 스타 19)
  - filters→kifrs→dedupe: kept_ownership 2,706 → K-IFRS 분류 1,298(<5% 1,348건 정당
    제외) → dedupe 862쌍 → **RelationLocal 최종 1,088행**(subsidiary 142·associate
    428·investment 292·ftc_group 226)
- **U1 게이트 판정 (진행 중 — 완료 아님, 정직하게 기록)**:
  - ⏳ 지분 엣지 ≥ 3,000 → **1,088건, 미달**. 원인 규명: 계획서 자체가 U1을
    "최신 연도 1일 + 5개년 백필 3일"의 **다일간 작업**으로 설계했는데 이번 세션은
    최신연도(2024) 1개년만 수집 — **계획된 범위의 1/5만 완료한 정상적 중간 상태**이지
    게이트가 잘못 설정된 게 아님(KOSPI200 케이스와 다름 — 재정의 불필요). 2020~2023
    4개년 백필을 백그라운드 개시(idempotent, 여러 세션에 걸쳐 자동 이어감).
  - ✅ M4 멱등 pytest 통과 (test_idempotency.py 3건 + 전체 회귀 122/122)
  - ✅ 링킹 실패율 < 5% → **실질적으로 충족 추정**: 원본 dropped_unmatched=48,327은
    개인주주·비상장 자회사·해외법인·사모펀드가 압도적이라 그대로는 잘못된 지표
    (KOSPI200 프록시와 같은 함정). 무작위 50건 표본 전수 수동 분류 결과 **진짜
    링킹 실패(실제 상장사인데 이름 불일치로 놓침) 0건** — 전부 정당한 제외였음.
    다만 `is_personal_shareholder`의 relate 커버리지가 좁아(사외이사·등기임원·
    특수관계인 단독·자매 등 미포함) 일부 개인이 "개인 제외"가 아니라 "미매칭"으로
    잘못 집계됨(최종 결과엔 무영향, 카운터 라벨만 부정확 — 후속 정리 대상).
  - ✅ galaxy 회귀 무손상 — report/relation 배치 병행 진행 중에도 165/165(report 43 +
    relation 122) 통과 확인
- **다음 세션**: DART 5개년 백필 진행 확인(ID bfv901a08) → 엣지 3,000 도달 시 U1
  게이트 최종 PASS 선언 + 커밋. 병행: report 5개년 원문 수집도 계속 진행 중
  (1,767/2,651, 66.7%). U1 게이트 완료 여부와 무관하게 V1(밸류체인 T1 정형 파서)은
  report_section 텍스트 기반이라 독립적으로 착수 가능.

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
