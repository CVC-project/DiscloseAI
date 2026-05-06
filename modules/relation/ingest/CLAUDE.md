# ingest/ — 단계 1: 원천 데이터 획득

> 순수 I/O 계층. API 호출·응답 파싱·RAW 저장까지. **가공·필터링·분류는 하지 않음** (transform/ 담당).
> 개인 주주·비상장 법인도 원본 그대로 저장 (감사 추적용).

## 모듈 3개

| 파일 | 역할 | 외부 의존 |
|---|---|---|
| `dart.py` | DART OpenAPI 2개 엔드포인트 호출 | `DART_API_KEY` |
| `ftc.py` | 공정위 OpenAPI 5개 호출 | `FTC_API_KEY` |
| `filing.py` | 공정위 미포함 기업의 사업보고서 주석 파싱 | `DART_API_KEY` + BeautifulSoup |

## DART API (`dart.py`)

베이스 URL: `https://opendart.fss.or.kr/api/{엔드포인트}.json`
인증: 쿼리스트링 `?crtfc_key={DART_API_KEY}`

| 엔드포인트 | 의미 | 필수 파라미터 |
|---|---|---|
| `hyslrSttus` | 최대주주 및 특수관계인 현황 | `corp_code`, `bsns_year`, `reprt_code` |
| `otrCprInvstmntSttus` | 타법인 출자현황 | `corp_code`, `bsns_year`, `reprt_code` |

**파라미터 값**
- `corp_code`: DART 8자리 (예: 삼성전자 `00126380`). 종목코드 6자리와 **다름**
- `bsns_year`: 사업연도 (예: `2024`)
- `reprt_code`: `11011`=사업보고서, `11012`=반기, `11013`=1분기, `11014`=3분기. MVP는 `11011`만

**응답 주요 필드 (hyslrSttus)**
- `nm`: 주주명 (예: "이재용", "삼성물산")
- `relate`: 관계 (예: "본인", "친인척", "계열회사")
- `stock_knd`: 주식 종류 (보통주/우선주)
- `bsis_posesn_stock_co`: 기초 보유 주식수
- `bsis_posesn_stock_qota_rt`: 기초 지분율 %
- `trmend_posesn_stock_co`: 기말 보유 주식수
- `trmend_posesn_stock_qota_rt`: 기말 지분율 %

**응답 주요 필드 (otrCprInvstmntSttus)**
- `inv_prm`: 법인명
- `frst_acqs_de`: 최초 취득일자
- `invstmnt_purps`: 출자목적
- `bsis_blce_qy`: 기초 잔액 주식수
- `bsis_blce_qota_rt`: 기초 지분율 %
- `trmend_blce_qy`: 기말 잔액 주식수
- `trmend_blce_qota_rt`: 기말 지분율 %

## 공정위 API (`ftc.py`)

베이스 URL: `https://apis.data.go.kr/1130000/{서비스명}/{오퍼레이션}`
인증: 쿼리스트링 `?serviceKey={FTC_API_KEY}` (URL encoded 주의)

**활용신청 완료 10종** (2026-04-19). 분류:

| 구분 | API | 용도 |
|---|---|---|
| **MVP 필수** | 지정된 대규모기업집단 조회 | 기업집단 코드·명 목록 (진입점) |
| **MVP 필수** | 지정된 대규모기업집단 소속회사 조회 | 기업집단코드 → 소속회사 (ftc_group 엣지 핵심) |
| **MVP 필수** | 사용 가능 공개년월 조회 | 최신 지정 YYYYMM 기준 시점 |
| **MVP 보조** | 지주회사 자회사 및 손자회사 현황 | SK·LG·한화 등 지주사 구조 보강 |
| **MVP 보조** | 특수관계인 내부지분 현황 | DART hyslrSttus와 크로스체크 |
| **MVP 보조** | 지정된 대규모기업집단 자산순위 | 노드 크기·정렬 메타데이터 보강 |
| v2 연기 | 소속회사 재무현황 | financial 모듈 영역 |
| v2 연기 | 소속회사 참여업종 | top50.csv sector 수동 매핑으로 대체 중 |
| v2 연기 | 계열 편입/제외/유예 변경내역 | 시계열 애니메이션용 |
| v2 연기 | 기업집단별 순환출자 현황 | 고급 분석 |

**응답 포맷**: XML(기본) 또는 JSON (`type=json` 파라미터). MVP는 JSON으로 통일.

**구현 우선순위 (Phase 2b)**: MVP 필수 3종 먼저 → 작동 확인 후 MVP 보조 3종 추가. v2 연기 4종은 스켈레톤만 유지.

## Rate Limit·재시도 정책

| 소스 | 일 한도 | 권장 간격 | 재시도 |
|---|---|---|---|
| DART | 10,000건 | 0.2초 | 3회 (exponential backoff 1·2·4초) |
| FTC | 10,000건 (데이터셋당) | 0.2초 | 3회 |
| DART document.json (주석용) | 한도 공유 | 0.5초 | 2회 |

**재시도하지 않을 에러**: 401/403(인증), 404(corp_code 잘못), 400(파라미터 오류). 즉시 로그 남기고 다음 기업으로.

## RAW 캐시

재실행 시 API 재호출 회피용. 저장 위치:
- `modules/relation/data/raw_cache/dart_{corp_code}_{bsns_year}_{endpoint}.json`
- `modules/relation/data/raw_cache/ftc_{api_name}_{yyyymm}.json`

캐시 TTL은 코드에 하드코딩하지 않음 — CLI 옵션 `--no-cache` 또는 `--refresh`로 제어.

## 주의

- DART 응답의 `status` 필드 확인: `"000"`=정상, `"013"`=데이터 없음, `"800"`=API 키 오류, `"900"`=원본 응답 없음
- `status="013"` (데이터 없음)은 에러가 아니라 정상 케이스로 처리 (예: 해당 연도 사업보고서 미제출)
- 공정위 API는 `지정일자` 기준으로 조회 — 매년 5월 공시대상기업집단 지정. `사용 가능 공개년월 조회`로 최신 `공개년월` 먼저 확인 필요
