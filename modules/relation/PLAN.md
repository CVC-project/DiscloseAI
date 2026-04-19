# Relation 모듈 — 실행 계획 요약

> **세션 재개용 요약.** 전체 계획 원본은 `C:\Users\yangw\.claude\plans\v2-twinkly-kurzweil.md`.
> 다음 세션에서는 이 파일부터 읽고 체크리스트 상 미완료 항목부터 이어서 진행하면 됨.

---

## 현재 진행 상태 (2026-04-19)

### Phase 1 — Harness 스켈레톤 ✅ **완료 (2026-04-19)**

- [x] **Step 0** 폴더 구조 생성 + `models.py`·`db.py`를 `storage/`로 이동 + 스키마 확장 (`CompanyNode` 신설, `RelationLocal` 컬럼 확장)
- [x] **Step 1** `CLAUDE.md` 6개 작성 (루트 + ingest/transform/graph/viewer/storage)
- [x] **Step 2** 빈 파일 스켈레톤 (`__main__.py` argparse + 각 .py 함수 시그니처 with `NotImplementedError`)
- [x] **Step 3** 마스터 데이터 CSV 초안 (`data/top50.csv` 50행 + `data/manual_overrides.csv` 헤더)
- [x] **Step 4** 의존성·환경 갱신 (`requirements.txt`에 requests·networkx·pandas·bs4·lxml 추가, `shared/config.py`에 `FTC_API_KEY` 추가, `.gitignore`에 graph export·raw_cache 추가)
- [x] **Step 5** 검증 통과: `python -m modules.relation --help` ✓ / init DB 생성 ✓ / imports OK ✓ / `pytest tests/test_smoke.py` 2 passed ✓ / black 포매팅 통과

### 사용자 수동 작업
- [x] `.env` 실파일에 `FTC_API_KEY=...` 한 줄 추가 완료 (2026-04-19)
- [x] data.go.kr에 공정위 API 10종 활용신청 완료 (2026-04-19)
- [~] `.env.example` 업데이트는 스킵 결정 (본인만 작업 중이라 불필요)

### Phase 2 — 실제 구현 (미착수, 다음 세션 이후)

- [ ] 2a `ingest/dart.py` — DART 2개 엔드포인트 (hyslrSttus, otrCprInvstmntSttus)
- [ ] 2b `ingest/ftc.py` — 공정위 OpenAPI 5개 호출
- [ ] 2c `ingest/filing.py` — 공정위 미포함 기업 주석 HTML 파싱
- [ ] 2d `transform/` — filters / kifrs / dedupe
- [ ] 2e `graph/` — build / export
- [ ] 2f `viewer/index.html` — 프로토타입 fork
- [ ] 2g `modules/relation/skills/` 도메인 스킬 초안 3개
- [ ] 2h `feat/relation` PR
- [ ] 2i **별도 PR** `modules/relation/skills/` → `.claude/skills/`로 승격

---

## 범위·결정 사항 (잊지 말 것)

### MVP 범위
- **대상**: 코스피 시총 상위 50개 기업 (삼성전자우·KODEX200 제외)
- **관계**: 지분 + 계열 2종만. 공급·경쟁은 v2로 연기
- **시각화 원칙**: 노드는 상장 법인만. 개인 주주(이재용 등)·공익재단·비상장은 DB에 audit 기록만 남기고 그래프 export에서 제외

### 데이터 소스
- **지분**: DART OpenAPI
  - `hyslrSttus.json` (들어오는 지분 — 최대주주·특수관계인)
  - `otrCprInvstmntSttus.json` (나가는 지분 — 타법인 출자)
- **계열 (4단계 폴백)**:
  1. `ftc_group` — 공정위 OpenAPI (data.go.kr, 공식 계열, ~47~49개 커버)
  2. `subsidiary`/`associate`/`investment` — K-IFRS 지분율 자동분류 (공정위 계열과 공존 레이어)
  3. `dart_filing` — 공정위 미포함 기업만 사업보고서 주석 HTML 파싱 (1~3개 예상)
  4. `manual` — `data/manual_overrides.csv` CPA 보정 (0~2건 예상)

### K-IFRS 1024호 임계값 (코드 상수로)
- `> 50%` → `subsidiary` (지배기업-종속기업)
- `20% ~ 50%` → `associate` (관계기업, 유의적 영향력)
- `5% ~ 20%` → `investment` (유의적 투자)
- `< 5%` → 엣지 없음

### 공정위 API 10개 (활용신청 완료 2026-04-19, 인증키 1개로 공통)
**MVP 필수 3**: 지정된 대규모기업집단 조회 / 지정된 대규모기업집단 소속회사 조회 / 사용 가능 공개년월 조회
**MVP 보조 3** (Phase 2b에서 여건 시): 지주회사 자회사 및 손자회사 현황 / 특수관계인 내부지분 현황 / 지정된 대규모기업집단 자산순위
**v2 연기 4**: 소속회사 재무현황 / 소속회사 참여업종 / 계열 편입/제외/유예 변경내역 / 기업집단별 순환출자 현황
(MVP에서 제외: 소속회사 주주현황·개요 — 활용신청하지 않음)

### 환경변수 (`.env`)
- `DART_API_KEY` — 발급 완료
- `FTC_API_KEY` — **사용자가 IDE에서 직접 추가 필요** (settings.json `Edit(.env.*)` deny로 Claude 편집 차단)

### 도메인 스킬 — 2단계 승격
- 개발: `modules/relation/skills/relation-{collect,graph,audit}.md` (모듈 로컬)
- 승격: 안정화 후 별도 리더 PR로 `.claude/skills/{name}/SKILL.md` 이동 → 전역 `/relation-*` 호출 가능

---

## 폴더 구조 (확정)

```
modules/relation/
├── CLAUDE.md              ← 루트 지도 (Step 1에서 작성)
├── CLAUDE.local.md        ← 기존, 개인 설정
├── PLAN.md                ← 이 파일 (세션 재개용 요약)
├── PROGRESS.md            ← /check가 기록
├── __init__.py            ← 기존
├── __main__.py            ← Step 2에서 작성 (argparse CLI)
│
├── ingest/                ← 단계 1: 원천 수집
│   ├── CLAUDE.md, __init__.py, dart.py, ftc.py, filing.py
├── transform/             ← 단계 2: 정제·분류
│   ├── CLAUDE.md, __init__.py, filters.py, kifrs.py, dedupe.py
├── graph/                 ← 단계 3: MultiDiGraph
│   ├── CLAUDE.md, __init__.py, build.py, export.py
├── viewer/                ← 단계 4: 시각화
│   ├── CLAUDE.md, index.html
├── storage/               ← 저장 계층 (이미 이동 완료)
│   ├── __init__.py, models.py, db.py (CLAUDE.md는 Step 1에서)
├── skills/                ← 도메인 스킬 초안 (Phase 2g에서 작성)
└── data/                  ← 마스터·산출물
    ├── top50.csv (Step 3), manual_overrides.csv (Step 3)
    ├── relation.db (gitignored)
    └── graph_top50.json (gitignored, Phase 2e 결과물)
```

---

## CLI 진입점 (Step 2에서 구현)

```bash
python -m modules.relation init                    # DB 생성
python -m modules.relation collect {dart|ftc|filing|all}
python -m modules.relation transform
python -m modules.relation graph
python -m modules.relation export
python -m modules.relation run                     # 전체 파이프라인
python -m modules.relation audit                   # 무결성 체크
```

---

## 재개 체크리스트

다음 세션에서 이어갈 때:

1. 이 파일(`modules/relation/PLAN.md`) 읽기
2. 현재 브랜치 확인 → `git status` (feat/relation이어야 함)
3. 위 Phase 1 체크리스트에서 가장 상단의 미완료 항목부터 진행
4. 애매하면 원본 계획(`~/.claude/plans/v2-twinkly-kurzweil.md`) 참조
5. 각 Step 완료 시 이 파일의 체크박스 업데이트
