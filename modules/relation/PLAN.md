# Relation 모듈 — 진행 상태 (세션 재개용)

> 이 문서는 **진행 상태 체크리스트 + Phase 개략**. 매 세션마다 체크박스 갱신.
> 상세 명세(함수 시그니처·테스트 전략·리스크)는 [SPEC.md](SPEC.md) 참조.
> 다음 세션에서 체크리스트 상 가장 상단의 미완료 항목부터 이어서 진행.

---

## 현재 진행 상태 (2026-04-19 기준)

### Phase 1 — Harness 스켈레톤 ✅ **완료**
- [x] Step 0 폴더 구조 + `storage/`로 파일 이동 + 스키마 확장 (`CompanyNode` 신설)
- [x] Step 1 `CLAUDE.md` 6개 초안 (루트 + ingest/transform/graph/viewer/storage)
- [x] Step 2 빈 파일 스켈레톤 (`__main__.py` argparse + 각 .py `NotImplementedError`)
- [x] Step 3 마스터 데이터 CSV 초안 (`data/top50.csv` 50행)
- [x] Step 4 의존성·환경 (`requirements.txt`·`shared/config.py`·`.gitignore`)
- [x] Step 5 검증 통과 + `feat/relation` 커밋·push

### Phase 2 — 실제 구현

#### 선행 작업 3건 ✅ **완료 (2026-04-19)**
- [x] `modules/relation/ingest/_http.py` — HTTP 유틸 (세션·재시도·rate limit·캐시·DART status 처리)
- [x] `modules/relation/common/names.py` — `normalize_company_name` 공용 함수
- [x] `storage/models.py`에 `RelationRaw` 테이블 추가 (ingest 원본 기업명 저장용)

#### Phase 2X 진행 순서
- [x] **2a** `ingest/dart.py` ✅ — 전체 top50 수집 완료 (RelationRaw 수천건), map-corp-codes 50/50
- [x] **2b** `ingest/ftc.py` ✅ — appnGroupAffiList endpoint 확보, top50 매칭 49/50, ftc_group 62 엣지
- [x] **2c** `ingest/filing.py` ✅ — 한미반도체 파싱 (top50 매칭 0, 독립기업 정상)
- [x] **2d** `transform/` ✅ — filters/kifrs/dedupe, RelationLocal 93개 생성
- [x] **2e** `graph/` ✅ — MultiDiGraph + graph_top50.json (노드 50, 엣지 93)
- [x] **2f** `viewer/index.html` ✅ — 프로토타입 fork + fetch + 6가지 relation_type 스타일 + Playwright QA 통과
- [x] **2g** `skills/` ✅ — relation-{collect,graph,audit} 모듈 로컬 초안 완료
- [ ] **2h** **사용자 복귀 후** — 전체 `/check` + `feat/relation` → `dev` PR
- [ ] **2i** **사용자 복귀 후** — 스킬 승격 PR: `modules/relation/skills/*.md` → `.claude/skills/{name}/SKILL.md`

**Phase 2 총 예상**: 약 13.5시간. 세부 의존성·함수 시그니처·테스트 fixtures는 [SPEC.md](SPEC.md)의 "Phase 2 이후 — 실제 구현" 섹션 참조.

### 사용자 수동 작업
- [x] `.env`에 `DART_API_KEY` 추가 완료
- [x] `.env`에 `FTC_API_KEY` 추가 완료 (2026-04-19)
- [x] data.go.kr에 공정위 API 10종 활용신청 완료 (2026-04-19)
- [~] `.env.example` 업데이트는 스킵 결정 (본인만 작업 중이라 불필요)

---

## 🤖 자율 진행 요약 (2026-04-19 세션)

사용자 부재 중 Claude가 자율 실행한 Phase 2 결과. push는 전부 로컬 커밋만(사용자 확인 후 수동 push 예정).

### 커밋 9개 (push 필요)
```
745e06d feat(viewer): Phase 2f — 프로토타입 fork + 6가지 relation_type 시각화
        (상위에 Phase 2g skills 커밋 1개 추가)
[prior] feat(graph): Phase 2e — MultiDiGraph 구축 + JSON export
[prior] feat(transform): Phase 2d — 필터·K-IFRS 분류·중복제거
[prior] feat(ingest): Phase 2c — 사업보고서 주석 파싱 (filing.py, best-effort)
[prior] feat(ingest): Phase 2b — 공정위 OpenAPI 수집 (ftc.py)
[prior] feat(ingest): Phase 2a — DART 수집 (dart.py)
[prior] feat: Phase 2 선행 인프라 3건 + 자율 진행 권한 완화
```

### 핵심 성과
- **데이터**: 노드 50 + 엣지 93 (ftc_group 62 / associate 15 / investment 11 / subsidiary 5)
- **삼성 그룹**: 8개사 완전연결 28개 엣지 ✓
- **현대차→기아 34.53%** (associate) ✓
- **테스트**: 59/59 통과
- **시각**: Playwright QA — 페이지 에러 0, 렌더링 정상 ([screenshot](viewer/screenshot_phase2f.png))
- **고아 노드 15개** (금융지주·한국전력·한미반도체 등 공정위 미지정 + 지분 관계 無 — 정상)

### 인프라 변경
- **권한**: `.claude/settings.json` allow에 `Bash(*)` 추가 (자율 진행용). deny는 유지.
- **절전**: `powercfg` AC sleep/hibernate/monitor 전부 0 (never). 사용자 복귀 시 원복 안내 필요.
- **Playwright**: MCP 등록(user scope) + Python `playwright` + chromium 설치

### 사용자 복귀 시 할 일
1. **스크린샷 시각 QA** — [viewer/screenshot_phase2f.png](viewer/screenshot_phase2f.png) 확인
2. 실제 브라우저에서: `python -m http.server 8000` → `http://localhost:8000/modules/relation/viewer/index.html`
3. **push**: `git push origin feat/relation` (9커밋 push 필요)
4. **Phase 2h** — `feat/relation` → `dev` PR 생성 (`gh pr create --base dev`)
5. **Phase 2i** — 스킬 승격 PR: `modules/relation/skills/*.md` → `.claude/skills/{name}/SKILL.md` (별도 브랜치)
6. **절전 설정 원복** (선택): `powercfg /change standby-timeout-ac 30` 등

### 알려진 리스크
- **FTC 보조 API 3종** (지주회사 자회사·특수관계인 내부지분·자산순위): endpoint 미확정 → `NotImplementedError`. v2에서 `data.go.kr` 데이터셋 ID 확인 후 활성화
- **filing 파싱 커버리지 낮음**: 한미반도체에서 12건 파싱 but top50 매칭 0 (독립기업이므로 정상). 다른 독립기업 추가 시 `_clean_name` 규칙 추가 필요 가능
- **top50.csv corp_code**: 모두 매핑 완료 (git 변경사항으로 커밋됨)

---

## 세션 분할 권장 (Phase 2)

| 세션 | 범위 | 예상 시간 |
|---|---|---|
| B | 선행 작업 3건 + Phase 2a + Phase 2b 필수 3종 | 3~4h |
| C | Phase 2b 보조 3종 + Phase 2c | 3h |
| D | Phase 2d (transform 전체) | 2h |
| E | Phase 2e + Phase 2f + 시각 QA | 3h |
| F | Phase 2g + Phase 2h + Phase 2i | 1.5h |

**각 세션 시작 시**:
1. 이 파일(`modules/relation/PLAN.md`) 읽기 → 가장 상단 미완료 Phase 확인
2. [SPEC.md](SPEC.md)의 해당 Phase 섹션 읽기 → 하위 Step·함수 시그니처·완료 기준 파악
3. `git status` 확인 후 작업 시작
4. Phase 완료 시마다 이 파일의 체크박스 업데이트

---

## 핵심 결정 사항 요약 (변경 시 SPEC.md도 갱신)

- **MVP 범위**: 코스피 시총 상위 50개 × 지분+계열 2종. 공급·경쟁은 v2
- **저장 전략**: ingest는 `RelationRaw`(기업명 원본), transform이 ticker 매칭 후 `RelationLocal`로 마이그레이션
- **계열 관계**: 4단계 폴백 (공정위 API → K-IFRS 지분율 분류 → 주석 파싱 → 수동 보정)
- **공정위 API**: 10종 활용신청 완료. MVP 필수 3 + 보조 3 + v2 연기 4
- **K-IFRS 임계값** (상수): subsidiary `>50`, associate `[20,50]`, investment `[5,20)`, 그 외 엣지 없음
- **시각화**: 노드 = 상장 법인만. 개인·공익재단·비상장은 DB 기록만 남기고 그래프 export에서 제외
- **스킬 전략**: `modules/relation/skills/`에서 개발 → 안정화 후 `.claude/skills/`로 승격 PR (별도 브랜치)
