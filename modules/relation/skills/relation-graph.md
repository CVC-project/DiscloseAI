---
name: relation-graph
description: 수집된 RelationRaw를 필터·K-IFRS 분류·중복제거 후 MultiDiGraph로 구축하고 graph_top50.json으로 export합니다.
auto-invocable: false
---

# /relation-graph

수집(`/relation-collect`) 이후 실행하는 변환·그래프 구축 파이프라인.

## 실행 절차

```bash
cd DiscloseAI
source .venv/Scripts/activate

# transform (filters → kifrs → dedupe)
python -m modules.relation transform

# MultiDiGraph 구축 + JSON export
python -m modules.relation graph
python -m modules.relation export
# 또는 한 번에: python -m modules.relation run
```

## 기대 출력

```
filters.apply 결과: {'kept_ownership': 8, 'kept_ftc': 62, 'kept_filing': 0,
                     'dropped_personal': 15, 'dropped_foundation': 3, 'dropped_unmatched': 138}
K-IFRS 분류: 6개 (dropped<5%: 2개)
dedupe 결과: kept 6쌍, removed 0건

MultiDiGraph 구축: 노드 50, 엣지 68
export: 노드 50개, 엣지 68개, 고아(연결0) 18개 → data/graph_top50.json
  고아 노드: ['KB금융', '신한지주', ...]  # 금융지주·독립기업
```

## 기대 분포
- 노드 ≥ 48 (top50 기준)
- 엣지 ≥ 30
- relation_type 분포:
  - ftc_group 60~70개 (삼성 28 + SK 10 + 현대 10 + HD현대 6 + 기타)
  - associate 2~3개 (삼성전자↔삼성바이오로직스 등)
  - investment 3~5개 (삼성전자↔삼성SDI 등)
  - subsidiary 0~3개 (50% 초과 지분)

## 시각 확인

```bash
python -m http.server 8000
# 브라우저: http://localhost:8000/modules/relation/viewer/index.html
```

## 다음 단계
시각 QA 완료 후 → `/relation-audit` 호출 (무결성 체크)
