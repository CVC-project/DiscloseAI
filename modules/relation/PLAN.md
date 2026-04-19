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

### Phase 2 — 실제 구현 (미착수)

#### 선행 작업 3건 (Phase 2a 시작 전)
- [ ] `modules/relation/ingest/_http.py` — HTTP 유틸 (세션·재시도·rate limit·캐시·DART status 처리)
- [ ] `modules/relation/common/names.py` — `normalize_company_name` 공용 함수
- [ ] `storage/models.py`에 `RelationRaw` 테이블 추가 (ingest 원본 기업명 저장용)

#### Phase 2X 진행 순서
- [ ] **2a** (2.5h) `ingest/dart.py` — hyslrSttus + otrCprInvstmntSttus + `top50.csv`의 corp_code 채우기 + 삼성전자 스모크
- [ ] **2b** (4h) `ingest/ftc.py` — 필수 3 + 보조 3 API (교육용 정확도 우선)
- [ ] **2c** (2.5h) `ingest/filing.py` — 공정위 미포함 기업 주석 HTML 파싱 (best-effort)
- [ ] **2d** (2h) `transform/` — `RelationRaw → RelationLocal` 마이그레이션 + filters/kifrs/dedupe
- [ ] **2e** (1h) `graph/` — MultiDiGraph 구축 + 프로토타입 호환 JSON export
- [ ] **2f** (2h) `viewer/index.html` — 프로토타입 fork + 6가지 relation_type 스타일 + K-IFRS 툴팁
- [ ] **2g** (30m) `modules/relation/skills/` 도메인 스킬 초안 3개
- [ ] **2h** (1h) 전체 `/check` + `feat/relation` → `dev` PR (Phase 단위 5커밋 권장)
- [ ] **2i** (15m, 별도 브랜치) 스킬 승격 PR: `modules/relation/skills/*.md` → `.claude/skills/{name}/SKILL.md`

**Phase 2 총 예상**: 약 13.5시간. 세부 의존성·함수 시그니처·테스트 fixtures는 [SPEC.md](SPEC.md)의 "Phase 2 이후 — 실제 구현" 섹션 참조.

### 사용자 수동 작업
- [x] `.env`에 `DART_API_KEY` 추가 완료
- [x] `.env`에 `FTC_API_KEY` 추가 완료 (2026-04-19)
- [x] data.go.kr에 공정위 API 10종 활용신청 완료 (2026-04-19)
- [~] `.env.example` 업데이트는 스킵 결정 (본인만 작업 중이라 불필요)

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
