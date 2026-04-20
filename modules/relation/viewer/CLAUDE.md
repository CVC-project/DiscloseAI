# viewer/ — 단계 4: 우주맵 시각화

> 원본 프로토타입(`docs/prototype/corporate_universe_v5.html`)의 fork.
> Canvas 2D API + force-directed simulation. Three.js 미사용 (프로토타입 그대로 계승).
> 원본은 **수정 금지** (다른 팀원 참고용).

## 파일 1개

`index.html` — 프로토타입 fork + fetch 로더 + relation_type별 스타일 분기 + K-IFRS 교육 툴팁.

## 프로토타입 대비 변경점 3곳만

1. **데이터 로딩**: 하드코딩 제거 → fetch
   ```js
   // 기존: const raw=[...하드코딩 50개 객체];
   // 변경:
   let raw = [];
   fetch('../data/graph_top50.json')
     .then(r => r.json())
     .then(d => { raw = d; init(); requestAnimationFrame(tick); });
   ```

2. **엣지 파서**: `rl` 문자열 3-split (기존은 2-split `:`)
   ```js
   // 기존: const [tn, rt] = r.split(':');
   // 변경: const [tn, rt, detail] = r.split(':', 3);
   //       edges.push({ a: n, b: tgt, type: rt, detail });
   ```

3. **draw() 엣지 스타일**: `type`별 분기 추가 (아래 스타일 표)

## relation_type별 스타일 표 (draw 함수 분기)

**갱신 2026-04-20**: 기존 ftc_group·dart_filing·associate 세 종 구분이 약해 색·두께·대시 재조정.

| relation_type | 색상 | 선 스타일 | 두께 | K-IFRS·공정거래법 의미 |
|---|---|---|---|---|
| `subsidiary` | `#ef4444` 진한 빨강 | 실선 | **2.5px** | K-IFRS 1110 지배기업-종속기업 (> 50%) — 연결재무제표 작성 |
| `associate` | `#f97316` 주황 | 실선 | **2.0px** | K-IFRS 1028 관계기업 (20~50%) — 지분법 적용 |
| `investment` | `#94a3b8` 회색 | 점선 `[3,3]` | 1.2px | 자본시장법 §147 5% 대량보유 (5~20%) — K-IFRS 1109 공정가치측정 |
| `ftc_group` | `#fbbf24` 노랑 | 긴 대시 `[8,4]` | 1.5px | 공정거래법 §2 공시대상기업집단 소속회사 |
| `dart_filing` | **`#a78bfa`** 보라 | 대시 `[5,3]` | 1.2px | K-IFRS 1024 특수관계자 (공정위 미포함 기업 한정) |
| `manual` | **`#ec4899`** 핑크 | 점선 `[2,3]` | 1.0px | 공개 DB 미반영 수동 보정 |

**색 차별화 전략**:
- 실선 (K-IFRS 공식 지분): 빨강(지배) → 주황(관계)
- 점선: 회색(투자), 노랑(공정위), 보라(주석), 핑크(수동) — 4색으로 각각 구별

**코드 형태 (draw 엣지 루프 내)**:
```js
edges.forEach(e => {
  const style = EDGE_STYLES[e.type] || EDGE_STYLES.default;
  x.strokeStyle = style.color;
  x.lineWidth = style.width;
  x.setLineDash(style.dash);
  // ... 기존 선 그리기 로직
});
x.setLineDash([]);  // reset
```

## 평행 엣지 offset — 간격 밀착("Singularity" 케이블 UI) 및 수학적 버그 수정 (2026-04-20)

같은 기업 쌍에 여러 `relation_type` 엣지가 공존하는 경우(레이어 공존 원칙) Canvas에서 **나란히** 그린다. 이전에는 선 사이에 시각적 여백(PAD)을 두었으나, 가독성 향상을 위해 **이중선/삼중선이 여백 없이 딱 붙어서 '하나의 굵은 복합 케이블'처럼 보이도록 밀착(Zero Gap) 렌더링**으로 정책을 변경함.

**알고리즘 및 버그 수정 내역**
1. **식별자 오류 수정 (`init()`)**: 
   - 기존 `[e.a.t, e.b.t]`(티커 기준) 그룹핑은 티커가 없는 비상장사나 누락된 쌍을 동일 그룹으로 엉뚱하게 오판할 위험이 컸음. 불변 식별자인 `[e.a.n, e.b.n]`(이름 기준) 조합으로 고정 수정함.
2. **법선 벡터 방향 상쇄 버그 수정 (`draw()`)**:
   - `A→B` 엣지와 `B→A` 엣지의 기본 벡터 방향이 정반대이므로, 오프셋을 줘도 벡터 곱 과정에서 무효화되어 **정확히 제자리에 겹쳐버리는 수학적 오류(한화오션·한화시스템 사례)**가 있었음. `if(e.a.n > e.b.n) { px = -px; py = -py; }` 구문으로 법선 벡터 방향을 강제 통일하여 일관된 오프셋 밀어내기를 구현함.
   - ⚠️ **주의**: `init()`의 그룹핑 키(`e.a.n`, `e.b.n` 정렬)와 `draw()`의 법선 통일(`e.a.n > e.b.n`)은 묵시적으로 동일한 기준(이름)에 의존함. 만약 그룹핑 키를 티커(`t`) 기준으로 변경할 경우 겹침 버그가 재발할 수 있으므로 수정 시 주의 요망.
3. **간격 여백 조율 (`init()`)**:
   - `PAD = 0.5`로 설정. Hover 대비용 `*1.5` 배수를 걷어내고 원래 선의 `width` 값만을 그대로 누적 더함. `0.0`으로 두면 Z-order상 뒤쪽 선이 앞 선을 덮어 색상 인식을 방해할 수 있으므로, 최소한의 안티앨리어싱 마진(`0.5px`)만 남겨두어 시각 처리 완성.

## 섹터 필터 + 노드 색 통합 (UI 개선 iteration 2026-04-20)

- 우측 하단 `.legend-sector` **제거**. 섹터-색 매핑은 중앙 하단 `.hud-sub` 필터 버튼에 **색띠(border-left 3px) + 활성 시 배경 투명 색상**으로 통합.
- setMode('analyze')에서 `sectors` 사전의 모든 키를 순회하여 12개 버튼을 자동 생성 (sectors에 신규 추가 시 자동 반영).
- "기타" 색상 `#78716c` → `#a3e635` 라임 변경 (중공업·방산 `#64748b` 블루그레이와 구분 선명).

## 엣지 범례 hover 툴팁

`.legend-edge .legend-item[data-tooltip]` + CSS `::after` pseudo-element로 호버 팝업. JS 불필요. 각 툴팁은 K-IFRS 기준서 번호(1024·1028·1109·1110)·공정거래법 제2조·자본시장법 제147조 등 공신력 있는 근거 포함.

## sectors 확장 (기존 8개 + 4개)

기존 sectors 사전([line 145](../../../docs/prototype/corporate_universe_v5.html#L145)) 그대로 계승하고 4개 추가:

```js
const sectors = {
  // 기존 8개
  '반도체':    { color: '#7c6cf0', cx: -0.25, cy: -0.2  },
  '디스플레이': { color: '#4da6ff', cx:  0.25, cy: -0.25 },
  '2차전지':   { color: '#22d3ee', cx:  0.30, cy:  0.1  },
  '바이오':    { color: '#34d399', cx: -0.30, cy:  0.2  },
  '자동차':    { color: '#f97316', cx:  0.00, cy:  0.3  },
  '금융':      { color: '#a78bfa', cx: -0.15, cy: -0.35 },
  '플랫폼':    { color: '#f472b6', cx:  0.20, cy: -0.1  },
  '에너지':    { color: '#facc15', cx: -0.35, cy:  0    },
  // 추가 4개
  '중공업·방산': { color: '#64748b', cx:  0.35, cy: -0.1 },  // 한화에어로·HD현대중공업·두산·한화시스템 등
  '건설':       { color: '#d97706', cx:  0.10, cy:  0.35 }, // 현대건설·HD한국조선해양
  '통신':       { color: '#06b6d4', cx: -0.20, cy:  0.35 }, // SK텔레콤
  '기타':       { color: '#a3e635', cx:  0.00, cy:  0    }, // KT&G·HMM·한미반도체 (라임, 2026-04-20 변경)
};
```

## K-IFRS 교육 툴팁 (호버 시)

엣지 호버 시 툴팁에 자동 생성되는 설명:

- `subsidiary` → "{source} → {target}: {ratio}% (종속기업). 50% 초과 지분은 K-IFRS상 지배관계가 성립합니다."
- `associate` → "{source} → {target}: {ratio}% (관계기업). 20% 넘으면 K-IFRS상 유의적 영향력이 인정됩니다."
- `investment` → "{source} → {target}: {ratio}% (유의적 투자). 5% 이상 지분은 공시 의무가 발생합니다."
- `ftc_group` → "{source}·{target}은 공정위 지정 [{group_name}] 그룹 소속 계열사입니다."
- `dart_filing` → "{source} → {target}: 사업보고서 주석에 명시된 특수관계자입니다."

## 원본 프로토타입 활용 함수 (수정 없이 재사용)

- `init()` ([line 231](../../../docs/prototype/corporate_universe_v5.html#L231)) — 노드 좌표 초기화 + 엣지 파싱
- `physics()` ([line 232](../../../docs/prototype/corporate_universe_v5.html#L232)) — Force-directed 시뮬레이션
- `draw()` ([line 233](../../../docs/prototype/corporate_universe_v5.html#L233)) — Canvas 렌더링 (엣지 스타일 부분만 교체)

## 로컬 확인 방법

```bash
python -m http.server 8000
# → http://localhost:8000/modules/relation/viewer/index.html
```

data/graph_top50.json이 먼저 생성돼 있어야 함 (Phase 2e 완료 후).
