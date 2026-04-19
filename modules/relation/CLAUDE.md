# relation/ 모듈 — 루트 지도

> 이 파일은 `modules/relation/` 아래 파일 작업 시 자동 로드됨.
> 상세 도메인 규칙은 서브폴더 각 CLAUDE.md를 **해당 폴더 작업 시에만** 참조 (Progressive Disclosure).
> 전체 계획 원본: `C:\Users\yangw\.claude\plans\v2-twinkly-kurzweil.md`
> 세션 재개용 진행 상태: [PLAN.md](PLAN.md)

## 담당 범위
코스피 시총 상위 50개 기업의 **지분·계열 관계** 수집·분류·시각화. 공급·경쟁은 v2.

## 데이터 흐름 (파이프라인 = 폴더)

```
ingest/     → DART + 공정위 OpenAPI + 사업보고서 주석 원천 획득 (순수 I/O)
transform/  → K-IFRS 지분율 자동분류, 개인·비상장 필터, 중복 제거
graph/      → NetworkX MultiDiGraph 구축 → JSON export
viewer/     → 프로토타입 fork + fetch 로더로 Canvas 렌더
storage/    → SQLite 로컬 DB (CompanyNode, RelationLocal)
```

## 서브폴더별 한 줄 요약

| 폴더 | 담당 | 상세 규칙 |
|---|---|---|
| [ingest/](ingest/CLAUDE.md) | DART·FTC·주석 API 호출 | 파라미터 표, rate limit, 재시도 |
| [transform/](transform/CLAUDE.md) | 정제·분류 | K-IFRS 임계값, 필터 규칙, 기업명 정규화 |
| [graph/](graph/CLAUDE.md) | NetworkX 그래프 | MultiDiGraph 스키마, 레이어 공존 규칙 |
| [viewer/](viewer/CLAUDE.md) | Canvas 시각화 | sectors 색상, relation_type별 스타일 표 |
| [storage/](storage/CLAUDE.md) | SQLite 스키마 | 테이블 정의, Supabase 이전 계획 |

## CLI 진입점

```bash
python -m modules.relation init                          # DB 생성
python -m modules.relation collect {dart|ftc|filing|all}
python -m modules.relation transform
python -m modules.relation graph
python -m modules.relation export
python -m modules.relation run                           # 전체 파이프라인
python -m modules.relation audit                         # 무결성 체크
```

## 외부 의존 (환경변수)

- `DART_API_KEY` — opendart.fss.or.kr (일 10,000건 한도)
- `FTC_API_KEY` — data.go.kr (공정위 OpenAPI 5개 활용신청 후 공통 사용)

환경변수는 `shared/config.py`에서 로드. `.env`는 settings.json `Edit(.env.*)` deny로 Claude 직접 편집 차단 → 사용자가 IDE에서 수동 추가.

## 핵심 원칙 (잊지 말 것)

1. **노드는 상장 법인만** — 개인 주주·공익재단·비상장은 DB 기록만, 그래프 export에서 제외
2. **모듈 간 import 금지** — 다른 팀원 모듈(financial/disclosure/price)과 데이터 공유는 DB 테이블로만
3. **`shared/` 수정은 리더 역할** — MVP는 `storage/` 로컬 스키마로만, 검증 완료 후 별도 PR로 `shared/models.py` 동기화
4. **확정 규칙 = 코드 상수** — K-IFRS 임계값 같은 법정 기준은 `transform/kifrs.py` 상수로. 휴리스틱만 이 CLAUDE.md들에.

## 자주 하는 실수

- ❌ DART `corp_code` (8자리) ↔ 종목코드 `ticker` (6자리) 혼동 — 반드시 구분해서 저장
- ❌ `hyslrSttus` 응답에서 개인 주주를 노드로 생성 — target 필터링 필수
- ❌ 양방향 지분 엣지 중복 생성 (A→B 수집 + B→A 수집 시) — dedupe에서 higher ratio 채택
- ❌ 공정위 계열과 K-IFRS 지분 분류를 같은 엣지로 합침 — 레이어 공존이 원칙
