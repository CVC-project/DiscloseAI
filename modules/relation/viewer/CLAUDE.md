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

| relation_type | 색상 | 선 스타일 | 두께 | K-IFRS 의미 |
|---|---|---|---|---|
| `subsidiary` | `#ef4444` 진한 빨강 | 실선 | 2px | 지배기업-종속기업 (> 50%) |
| `associate` | `#f97316` 주황 | 실선 | 1.5px | 관계기업 (20~50%) |
| `investment` | `#94a3b8` 회색 | 점선 `[2,3]` | 0.8px | 유의적 투자 (5~20%) |
| `ftc_group` | `#fbbf24` 노랑 | 점선 `[4,2]` | 1px | 공정위 공식 계열 |
| `dart_filing` | `#facc15` 밝은 노랑 | 점선 `[6,2]` | 1px | 사업보고서 주석 (공정위 미포함) |
| `manual` | `#a78bfa` 보라 | 점선 `[2,2]` | 0.8px | 수동 보정 |

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
  '기타':       { color: '#78716c', cx:  0.00, cy:  0    }, // KT&G·HMM·한미반도체
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
