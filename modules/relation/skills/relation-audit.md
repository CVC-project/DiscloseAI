---
name: relation-audit
description: relation 모듈 데이터 무결성 체크. 삼성 그룹 완전연결·기아↔현대차 상호지분·고아 노드·relation_type 분포 등을 확인합니다.
auto-invocable: true
---

# /relation-audit

수집·변환 완료된 RelationLocal 데이터의 도메인 무결성 검증.

## 체크 항목

### 1. 삼성 그룹 완전연결 (ftc_group 28개)
```sql
SELECT COUNT(*) FROM relation_local
WHERE relation_type='ftc_group'
  AND source_corp IN ('005930','028260','032830','207940','009150','006400','010140','000810')
  AND target_corp IN ('005930','028260','032830','207940','009150','006400','010140','000810');
-- 기대: 28
```

### 2. 기아 ↔ 현대차 상호 지분 (양방향)
- 현대차(005380) → 기아(000270): ~33% (associate)
- 기아(000270) → 현대차(005380): ~4~5% (investment)

### 3. 고아 노드 (in+out degree=0)
공정위 미지정 + 지분 관계 없음 = 고아. 예상:
- KB금융·신한지주·하나금융지주·우리금융지주·메리츠금융지주 (금융지주)
- 한국전력 (공기업)
- HMM·KT&G·한미반도체·LIG디펜스·한국항공우주 (독립/최근 상장)
- NAVER·카카오·셀트리온·미래에셋증권·고려아연 (공정위 지정이지만 top50 내 다른 계열 없음)

18개 내외가 정상.

### 4. relation_type 분포
- ftc_group: ~60 (공정위 계열, 완전연결 기준)
- investment/associate/subsidiary: ~5~10 (K-IFRS 지분)
- dart_filing: 0~2 (공정위 미포함 기업 주석)
- manual: 0~2 (수동 보정)

## 실행 방법

```bash
cd DiscloseAI
source .venv/Scripts/activate
python -c "
from modules.relation.storage.db import get_local_session
from modules.relation.storage.models import RelationLocal, CompanyNode
from collections import Counter
s = get_local_session()
# 1. 삼성 완전연결
samsung = {'005930','028260','032830','207940','009150','006400','010140','000810'}
cnt = s.query(RelationLocal).filter(
    RelationLocal.relation_type=='ftc_group',
    RelationLocal.source_corp.in_(samsung),
    RelationLocal.target_corp.in_(samsung),
).count()
print(f'삼성 ftc_group: {cnt} (기대 28)')
# 2. 기아↔현대차
for a,b in [('005380','000270'), ('000270','005380')]:
    r = s.query(RelationLocal).filter_by(source_corp=a, target_corp=b).filter(RelationLocal.ratio.isnot(None)).all()
    for e in r: print(f'  {a}->{b}: {e.ratio}% [{e.relation_type}]')
# 3. 분포
print('relation_type:', Counter(r.relation_type for r in s.query(RelationLocal).all()))
# 4. 고아
nodes = {n.ticker: n.corp_name for n in s.query(CompanyNode).all()}
connected = set()
for e in s.query(RelationLocal).all():
    connected.add(e.source_corp); connected.add(e.target_corp)
orphans = [f'{t} {nodes[t]}' for t in nodes if t not in connected]
print(f'고아 {len(orphans)}개:', orphans[:5], '...')
s.close()
"
```

## 이상 감지 시 조치
- 삼성 엣지 ≠ 28 → `common/names.py`의 NAME_ALIASES 확인
- 기아↔현대차 없음 → DART 수집 실패. `collect dart --corp 000270 --year 2024` 재시도
- 고아 > 20 → 많은 기업이 공정위 미포함 → FTC 응답 포맷 변경 가능성
- relation_type에 'ownership' 있음 → kifrs.apply() 미실행 상태. `transform` 재실행
