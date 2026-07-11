# galaxy_&lt;ticker&gt;.json 스키마 (확정 — 해방판 전수 역산)

> **상태**: 2026-07-11. DOSSIER_TABS_PLAN Phase 0-A "해방판 실물 역산으로 확정" 산출물.
> `docs/prototype/현금은하수_해방판.html`(1,756줄) + `dc-runtime.js`를 전수 역산해 확정.
> **이 문서가 galaxy JSON의 SSOT.** 검증 계약은 `tests/report/check_golden_keys.py`, pydantic 승격은 Phase 4.
> DOSSIER_TABS_PLAN §5.1은 이 문서를 참조(리더가 §5.1 요약을 이 문서로 대체·링크 권장).

---

## 0. 역산 요지 — 부록 A2 재확인

해방판은 **삼성 하드코딩 단일 산출물**. 데이터가 여러 구조에 흩어져 있어 JSON은 이를 **역매핑**한 것:

| 해방판 위치 | JSON 필드 | 비고 |
|---|---|---|
| `:root` L26-35 | (JSON 아님 — theme-galaxy.css로 분리 완료) | 팔레트·폰트 |
| 상단바 L60·인트로 L67-69 | `corp` + `strings` | 히어로·헤더 |
| `KNOTS` L486-521 (17개) | `knots[]` | id/row/kind/name/amt/story |
| `SEGS` L523-530 | (코드 상수 유지 — JSON 아님) | 본류 구간 굵기(uniform이라 시각영향 적음) |
| `EQE` L532-540 / `EQSTORY` L550-558 | `panels.E` + 관련 dive | 자본변동 7행 |
| `ZONES` L542-548 | `strings.zones` | 존 질문·가이드 |
| 중앙 5패널 마크업 L98-432 | `panels.{A..E}` | ~90행, title=백만원 원값 |
| `S` L1063-1088 (24키×5) | `series` | **코드가 채움, LLM 금지** |
| `YEARS` L1062 | `years` | FY21~FY25 |
| `getDives()` L1290-1657 (41객체) | `dives` + `appendix` | 콘텐츠 27 + APPENDIX 14 |
| `ROW2DIVE`·`HL`·`GROUP_OF` L1089-1129 | (코드 상수 유지) | 행↔dive·하이라이트 매핑 |

---

## 1. 최상위 구조

```jsonc
{
  "schema_version": 2,                    // v6
  "corp":   { ... },                      // 회사 메타 (§2)
  "strings":{ ... },                      // 상단바·인트로·존 카피 (§3)
  "years":  ["FY21","FY22","FY23","FY24","FY25"],
  "series": { ...24키... },               // S 시계열 (§4) — 코드/DART, LLM 금지
  "anchor": { ... },                      // 앵커 이벤트 (§5) — story.py가 채움
  "knots":  [ ...17... ],                 // 매듭 (§6)
  "panels": { "A":[], "B":[], "C":[], "D":[], "E":[] },  // 중앙 패널 (§7)
  "dives":  { ...41 by key... },          // 딥다이브 (§8)
  "appendix":[ ...14... ],                // APPENDIX (§9)
  "meta":   { ... }                       // 생성 메타·routing (§10)
}
```

## 2. corp
```jsonc
"corp": {
  "ticker": "005930", "name": "삼성전자",
  "fiscal_year": 2025,
  "fiscal_label": "FY2025 (2025.1.1 ~ 12.31) · 연결 기준",
  "rcept_no": "20260310002820",           // 선택(LIG넥스원 결측 허용)
  "unit": "백만원",                        // raw_mn 단위
  "cash_begin": "53.7조", "cash_end": "57.9조",
  "equity_method_names": "삼성전기·삼성SDS"  // 관계기업명 (L293 보간용)
}
```

## 3. strings (상단바·인트로·존 카피 — 순수 표현 문자열)
```jsonc
"strings": {
  "header": "삼성전자 · FY2025 (2025.1.1 ~ 12.31) · 연결 기준",
  "hero": "작년 통장의 53.7조는, 어떻게 올해 57.9조가 됐을까요?",
  "intro_lines": ["이 이야기의 핵심은 …", "이 숫자들은 삼성전자 혼자가 …"],
  "zones": {   // ZONES L542-548
    "zoneA": { "q": "작년 통장엔 얼마가 있었을까요?", "g": "모든 이야기는 …" }
    // zoneA~zoneE
  }
}
```

## 4. series (S 24키 × 5점 — 조 원 단위, 코드가 채움)
24키 폐쇄 목록 (해방판 자구 그대로, 순서 무관):
```
revenue cogs gross sgna op pretax tax ni oci        (손익 9)
ocf icf capex fin div buyback                        (현금흐름 6)
dep rnd                                              (성격별/판관 2)
cash assets debt equity                              (BS 4)
dsOp eps tci                                         (파생·부문 3)
```
- 각 키 = 길이 5 배열(FY21→FY25). **5점 완결 필수**(미완성 키는 해당 dive `five.skip`).
- 파생: `tci = ni + oci`, `gross = revenue − cogs` (교육용 단순화 — residual 허용).
- 단위: **series/표시 = 조**(코드 생성 fmt1), **`raw_mn` = 백만원**. `eps`만 원 단위.
- 부호: 유출·차감은 음수 그대로(tax·icf·fin·dsOp 음수 정상 — vLine `zero:true`로 0선 표현).

## 5. anchor (앵커 이벤트 — story.py, 삼성=FY23 반도체 한파)
```jsonc
"anchor": { "label": "반도체 한파", "year": "FY23", "valley_index": 2,
            "cause_quote": "…원문 인용…", "confidence": 0.9 }
```
핵심 지표 3개+가 같은 trough 연도 공유 시 성립. vLine `valley` 파라미터가 이 인덱스 참조.

## 6. knots (17개 — row 기반 결정적 배치, 좌표는 코드)
```jsonc
"knots": [
  { "id":"k2", "num":"02", "row":"is-revenue", "kind":"source",
    "name":"매출", "amt":"333.6조", "raw_mn":333605938,
    "col":"mint", "src":"고객이 낸 돈", "dest":null,
    "story":"1초에 약 [1,000만 원] 꼴로 …" }
]
```
- id: k1,k2,k3,k4,k5,k6,k6b,k7,k8,k9,k10,k10b,k11,k12,k13,k14,k15 (**17개**).
- kind enum: `res|source|out|node|in|hub|back|bright`.
- `xf`(x위치)는 코드 상수(spineX=0.48 uniform) — JSON에 넣지 않음.
- `story`의 [브래킷]은 IBM Plex Mono 칩. 숫자는 payload 표시 문자열만.

## 7. panels (중앙 5패널 — 존 A~E, 마크업 데이터 구동화 대상 D4-층1)
```jsonc
"panels": {
  "B": [
    { "row":"is-revenue", "idx":"02", "name":"매출액", "v":"333.6",
      "raw_mn":333605938, "color":"mint", "sign":"pos",
      "children":[ /* is-sgna-rnd 등 펼침 소계 */ ] }
  ]
}
```
- 존: A(전기말 BS·현금), B(손익), C(현금흐름), D(기말 BS), E(자본변동).
- `raw_mn` = 마크업 `title`의 백만원 원값(예: "333,605,938 백만원" → 333605938).
- `color` enum: mint|cyan|gold|coral|steel|green. `sign`: pos|neg.
- 펼침 소계(sgna 8행·noncash·wc·inv·fin·bs 각 그룹)는 `children`.

## 8. dives (41객체 by key — getDives 역매핑)
```jsonc
"dives": {
  "k2": {
    "z":"B", "zc":"mint", "en":"REVENUE", "badge":null,
    "name":"매출액", "amt":"333.6조", "raw":"333,605,938", "raw_mn":333605938,
    "color_key":"mint", "row":"is-revenue",
    "what": ["…1~2문장…"],
    "links": [ { "t":"IS", "row":"is-revenue", "txt":"…", "a":"+333.6" } ],
    "lnote": "…선택…",
    "why": { "sub":"시각화 · 주30 부문정보", "body":["…"],
             "viz":"vBubbles", "viz_data": { /* §8.1 */ }, "cap":"…" },
    "five": { "key":"revenue", "cap":"…[칩]…", "so":"한 문장", "valley":2 }
  }
}
```
- dive 키: k1~k15,k6b,k10b + oci,totalcomp,ppe,assets,liab,eq-begin,eq-div,eq-buyback,eq-other,eq-end + n1..n34(14) = **41**.
- `t`(links 표종류) enum: IS|CF|BS|PBS|EQ|N (TBL L1061).
- `raw`=포맷 문자열(표시), `raw_mn`=백만원 정수(D7 — 중앙패널 title에서 회수).

### 8.1 viz_data (viz 함수가 리터럴 대신 받을 데이터 — D4-층2 리팩터)
| viz | viz_data 형태 |
|---|---|
| `vLine` | five가 담당(key·valley·zero) — viz_data 불필요 |
| `vTwin` | `{ a:{name,key}, b:{name,key} }` |
| `vWater` | `{ steps:[{l,v,abs?,up?}] }` |
| `vHBar` | `{ items:[{l,v,hl?,color?,plus?}] }` |
| `vBubbles` | `{ segs:[{name,rev,op}] }` (4부문) |
| `vSteps` | `{ steps:[[label,color]] }` (RTSTEPS형) |
| `vPuddle` | `{ ar, inv }` (운전자본) |
| `vChips` | `{ chips:[{t,c}] }` |

viz enum = `vLine|vTwin|vWater|vHBar|vSteps|vBubbles|vPuddle|vChips`. **viz·색·스토리유형은 코드 결정, LLM 아님.**

### 8.2 five (5개년 카드 — 3형)
```jsonc
{ "key":"revenue", "cap":"…", "so":"…", "valley":2, "zero":false }   // 단일추세
{ "twin": { "a":{name,key}, "b":{name,key} }, "cap":"…", "so":"…" }  // 두지표
{ "skip": "사유 문장" }                                              // 5점 미완성·비추세
```
- `cap` 숫자 ≥ 1(payload). `so` 정확히 1문장. `skip` 17건(APPENDIX 14 + 콘텐츠 잔차 3).

## 9. appendix (14건 — five=skip, 탭③ 하단)
```jsonc
"appendix": [
  { "n":"n16", "z":"주16", "zc":"steel", "tag":"우발부채와 약정",
    "name":"우발부채와 약정", "amt":"약정 52.9조", "color_key":"steel",
    "what":["…"], "why":{...}, "five":{"skip":"…"} }
]
```
주번호: n1,n2,n3,n4,n5,n14,n15,n16,n18,n26,n28,n29,n31,n34 (**14**).
※ appendix 객체는 dives와 동일 스키마(badge:"APPENDIX") — 렌더 경로 공유. JSON에선 dives에 병합 저장 후 meta.routing으로 구분해도 되고, 별도 배열로 둬도 됨(check는 둘 다 허용).

## 10. meta
```jsonc
"meta": {
  "generated_by": "manual",     // 또는 pipeline@<model>@<bank_ver>@<detector_ver>@<lint_ver>
  "validated": true,
  "review_flags": [],
  "routing": { "dive": 27, "appendix": 14 }   // 합 41
}
```

---

## 11. §5.1(플랜 골격)과의 델타 — 리더 확인 요망

역산 결과 §5.1 예시와 다른 점(예시는 골격이라 정상, 실물 기준으로 확정):
1. **`knots` 개수 = 17** (k6b·k10b 포함). §5.1 예시엔 17로 명기됨 ✓.
2. **panels 키는 존 문자(A~E)**, 각 행에 `raw_mn`·`sign`·`children`(펼침 소계) 추가.
3. **dives에 `viz_data` 필드 필수** — viz 함수가 삼성 리터럴 대신 받을 데이터(D4-층2 핵심). §5.1엔 `viz_data:{…}`로 자리만 있음 → 위 §8.1로 형 확정.
4. **`strings.zones`** 신설 — ZONES 질문·가이드가 §5.1엔 누락(상단바·인트로만 있었음).
5. **appendix 객체 = dives와 동형** — 별도 축약 스키마 아님(badge로만 구분).
6. **`color` 표기** = color_key 문자열(mint|cyan|gold|coral|steel|green) 일관. green은 midOverlay 화살표 전용.
