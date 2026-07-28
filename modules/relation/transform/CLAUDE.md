# transform/ — 단계 2: 정제·분류

> 도메인 규칙 집약. ingest/가 저장한 RAW 데이터를 읽어 필터·분류·중복제거 후 `RelationLocal` 테이블에 저장.
> 임계값은 모두 **코드 상수**(확정 규칙), 휴리스틱은 이 CLAUDE.md에(권장 규칙).

## 모듈 3개

| 파일 | 역할 |
|---|---|
| `filters.py` | 개인·공익재단·비상장 제외, top50 target 매칭 |
| `kifrs.py` | 지분율 → K-IFRS 관계 유형 분류 (subsidiary/associate/investment) |
| `dedupe.py` | 양방향 중복 엣지 제거 (higher ratio 채택) |

## K-IFRS 1024호 임계값 (`kifrs.py` 상수)

```python
SUBSIDIARY_THRESHOLD = 50.0   # > 50% → 지배기업-종속기업 (control)
ASSOCIATE_THRESHOLD = 20.0    # 20~50% → 관계기업 (significant influence)
INVESTMENT_THRESHOLD = 5.0    # 5~20% → 유의적 투자 (엣지 유지)
                              # < 5% → 엣지 제외
```

**분류 함수 시그니처**
```python
def classify_ownership(ratio: float) -> str | None:
    """지분율(%) → 'subsidiary' / 'associate' / 'investment' / None"""
```

## 필터 규칙 (`filters.py`)

### 개인 주주 판별
다음 중 하나라도 해당하면 노드 제외:
- `relate` 필드가 `"본인"`, `"친인척"`, `"친족"`, `"인척"` 중 하나
- 주주명에 주민번호 패턴(XXXXXX-XXXXXXX) 포함
- 주주명이 2~4자 한글이고 `relate`가 비어있음 (휴리스틱 — 드물지만 발생)

### 비상장 법인 판별
- `top50.csv`의 ticker 컬럼에 없는 기업명은 일단 보류
- 기업명 정규화 후에도 매칭 안 되면 비상장으로 처리 (노드 제외)

### 공익재단 판별
- 기업명에 `"재단"`, `"공익"`, `"장학회"` 포함
- 예: "삼성생명공익재단", "삼성문화재단" → 제외

## 엔티티 링킹 방어 5층 (2026-07-28 조문화 — FN-013, 교육 서비스의 Key 요건)

> **배경 사고**: 현대차 사업보고서 타법인출자의 "HMM"(해외 생산법인 약칭)이 상장 해운사
> HMM(011200)에 이름 정확 일치로 오링킹 → "현대차가 HMM 99.99% 종속" 허위 관계가
> 4개년 노출(리더 발견). 잘못된 지배구조는 교육 서비스의 신뢰를 직접 훼손한다 —
> **이름 정확 일치는 신원 증명이 아니다.** 아래 5층은 회귀 테스트
> (`tests/relation/test_transform/test_linking_guards.py`)로 박제 — 삭제·완화 금지.
> 다음 확장(재수집·T2·신규 원천 추가) 때도 이 5층을 통과해야 한다.

| 층 | 방어 | 구현 | 잡는 것 |
|---|---|---|---|
| L1 | **모호 약칭 게이트** — 대상명이 영문 2~5자 단독이면 자동 링킹 금지 → LinkFailQueue. 단 **실존 상장사 정식명**(NAVER·KT 등 — ticker_map에 정확 존재)은 통과 | `filters.is_ambiguous_abbrev()` | HMA·HMI·GMC류 해외법인 약칭 |
| L2 | **쌍 블록리스트** — CPA 검수로 확정된 오링킹 (source,target) 차단. 사유 병기 필수 | `data/link_blocklist.csv` + `load_link_blocklist()` | 화이트리스트 통과분(현대차→HMM)·한글 동명 비상장(DS단석 '하이브')·구사명 충돌 |
| L3 | **ratio sanity** — 지분율 >100%는 오파싱(주식수 혼입) drop. 정확히 100%는 유효(상장 前) | `filters.apply()` otrCpr 분기 | 영풍→시그네틱스 710651% |
| L4 | **50%+ 교차검증** — otrCpr 50%+인데 상대 hyslrSttus에 출자사 부재=모순 → CPA 검수 리스트 산출(자동 삭제 금지 — 오탐 다수) | 스캔 스크립트 → `data/review_*.csv` | "상장사 100% 보유"류 모순 |
| L5 | **LinkFailQueue → M2 수동 루프** — 큐 상위 표기를 CPA가 별칭(구사명 포함) 또는 블록으로 확정 | `NAME_ALIASES`·blocklist 갱신 후 transform 재실행 | 잔여 전부 |

- **구사명 시차**: registry `name_current`는 현재 사명만 보유 — 과거 연도 공시의 구사명은
  `NAME_ALIASES`에 "구사명→현재사명"으로 흡수(예: 에스씨엠생명과학→풍전약품).
  근본 해법(사명 이력 테이블)은 V2+ 과제.
- transform 재실행만으로 오염이 정리된다(prune) — RelationLocal 수동 DELETE 금지.

## 기업명 정규화 (`filters.py` 또는 공통 유틸)

매칭 실패를 줄이기 위한 전처리:

```
입력 → 정규화 결과
"(주)삼성전자"    → "삼성전자"
"삼성전자(주)"    → "삼성전자"
"주식회사 삼성전자" → "삼성전자"
"삼성전자 Ltd."   → "삼성전자"
"삼 성 전 자"     → "삼성전자"   (공백 제거)
"HD한국조선해양"  → "HD한국조선해양" (영문+한글 혼용 유지)
```

**예외 수동 매핑** (필요 시 `data/name_aliases.csv`에 추가):
- "현대자동차" ↔ "현대차" (DART 표기 vs KRX 약칭)
- "SK" ↔ "에스케이" (드물지만 DART에 있을 수 있음)

## 중복 제거 (`dedupe.py`)

### 양방향 지분 중복
같은 엣지가 A→B와 B→A 양쪽에서 수집될 수 있음 (DART는 양방향 모두 허용):
- 예: A의 hyslrSttus에서 "B 5% 보유" + B의 otrCprInvstmntSttus에서 "A 지분 5%"
- 동일 사실의 두 기록 — higher ratio 채택 후 하나만 남김

### relation_type 레이어 공존은 유지
같은 (source, target) 쌍이라도 relation_type이 다르면 별도 엣지로 유지:
- `ftc_group`(공정위) + `subsidiary`(K-IFRS) 둘 다 존재 가능 — 교육용 대조를 위해 **삭제하지 않음**

## 데이터 흐름

```
ingest/ 결과 (RAW JSON)
  ↓
filters.apply() → 개인·공익재단·비상장 제외 + top50 target 매칭
  ↓
kifrs.classify_ownership() → 지분율별 relation_type 부여
  ↓
dedupe.merge_bidirectional() → 양방향 중복 제거
  ↓
storage/RelationLocal 에 upsert
```

## 주의

- 경계값은 **초과(>)** 또는 **이상(≥)** 중 무엇인지 주의: SUBSIDIARY는 `> 50%` (50% 정확히는 관계기업)
- 테스트에서 경계값 반드시 포함: 49.99, 50.0, 50.01, 19.99, 20.0 등
- 공정위 계열 엣지는 이 단계를 통과하지 않음 — `ingest/ftc.py`에서 직접 생성 후 `storage/`로 바로 저장 (필터 대상 아님)
