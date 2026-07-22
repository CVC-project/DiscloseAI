# graph/ — 단계 3: NetworkX 그래프 구축 + JSON export

> `RelationLocal` 테이블을 읽어 `nx.MultiDiGraph`로 구축한 뒤, 프로토타입 호환 JSON으로 export.
> MultiDiGraph 선택 이유: 같은 (source, target) 쌍에 relation_type이 다른 엣지가 **공존**해야 함.

## 모듈 2개

| 파일 | 역할 |
|---|---|
| `build.py` | SQLite → `nx.MultiDiGraph` 로드. 노드 속성·엣지 속성 부여 |
| `export.py` | `nx.node_link_data(G)` + 프로토타입 호환 스키마 변환 → `data/graph_top50.json` |

## 노드 속성 (CompanyNode 기반)

```python
G.add_node(
    ticker,                     # 6자리 종목코드 (노드 id)
    n=corp_name,                # 기업명 (프로토타입 호환)
    t=ticker,                   # 프로토타입 호환 (노드 id와 동일)
    s=sector,                   # sectors 키 (viewer/CLAUDE.md 참조)
    sz=market_cap / 10_000,     # 프로토타입용 크기 (조 원 단위)
    mc=f"{market_cap // 10_000}조",  # 표시용 ("12조")
    group=group_name,           # 공정위 집단명 (null 가능)
)
```

## 엣지 속성 (RelationLocal 기반)

```python
G.add_edge(
    source_ticker,
    target_ticker,
    relation_type=...,  # ftc_group / subsidiary / associate / investment / dart_filing / manual
    ratio=...,          # Float, 지분율 %. ftc_group·manual은 None
    detail=...,         # "삼성물산 5.01% (최대주주)"
    source_type=...,    # hyslrSttus / otrCprInvstmntSttus / ftc / dart_filing / manual
    bsns_year=...,      # 사업연도
)
```

## 레이어 공존 규칙

같은 (A, B) 쌍에 여러 엣지가 있을 수 있음. **삭제하지 않음**.

예: 삼성전자 → 삼성SDI
- 엣지 1: `relation_type="ftc_group"` (공정위 집단)
- 엣지 2: `relation_type="investment"` + `ratio=19.58` (K-IFRS 유의적 투자)

`MultiDiGraph`는 같은 쌍의 엣지를 key로 구분해서 저장함.

## JSON export 스키마 (프로토타입 호환)

목표: 프로토타입 원본(corporate_universe_v5.html, #28 제거)의 `raw=[]` 형식과 드롭인 호환. 현재 정본은 viewer/index.html.

```js
// graph_top50.json 출력 예시
[
  {
    "n": "삼성전자", "t": "005930", "s": "반도체",
    "sz": 51.2, "mc": "512조", "group": "삼성",
    "rl": [
      "삼성SDI:investment:19.58%",
      "삼성바이오로직스:associate:43.44%",
      "삼성SDI:ftc_group:",
      "삼성물산:subsidiary:",
    ]
  },
  ...
]
```

**핵심**: `rl` 배열은 `"대상명:relation_type:detail"` 3-필드 문자열. `viewer/index.html`의 `init()` 파서가 `split(':', 2)`로 처리.

## export.py 구현 가이드

1. `build.py`로 MultiDiGraph 로드
2. 각 노드를 dict로 변환 (위 스키마)
3. 해당 노드에서 나가는 모든 엣지(`G.out_edges(n, data=True, keys=True)`)를 `rl` 배열로 수집
4. `json.dump()` → `data/graph_top50.json`
5. 파일명 버전: 기본 `graph_top50.json`, 날짜 추가 옵션 `graph_top50_{YYYYMMDD}.json`

## 검증 규칙

export 후 자체 검증:
- [ ] 모든 노드 id가 6자리 숫자 ticker 형식
- [ ] 모든 엣지의 source·target이 노드 집합에 존재
- [ ] 노드 수 ≥ 48 (top50 기준 최소 48개는 있어야)
- [ ] 엣지 수 ≥ 30
- [ ] 고아 노드(in+out degree=0) 목록 출력 → 한미반도체 같은 독립기업은 정상

## 주의

- `nx.node_link_data()`의 기본 출력은 `{"nodes": [...], "links": [...]}` 형태이지만, **프로토타입 호환을 위해 변환**해서 `[{...노드+rl...}, ...]` 단일 배열로 저장
- ratio가 None인 엣지(ftc_group, manual)의 detail에 ratio 문자열 넣지 말 것 — 빈 문자열로
- 엣지 정렬: ratio 내림차순(큰 지분이 먼저), 같으면 relation_type 알파벳순
