# 다음 세션 핸드오프 — 골든 캐스케이드(원문+V-062~069 패리티)

> 시작점 브랜치 `feat/report-phase5`. 인프라(Phase A/B/C) 완료·커밋·푸시. **다음 = 골든 1본당 1세션 캐스케이드.**

## 먼저 읽기 (순서)
1. `modules/report/MILKYWAY_GENERATOR.md` **§8.6**(캐스케이드 레시피 D1~D5) + §6(R6.6a~d 계약).
2. `modules/report/VARIATIONS.md` **V-062~069**(S0 필수) — 특히 V-068(원문 오라벨)·V-069(렌더러 일반화).
3. 이 파일 + `git log --oneline -8`.

## 지금 상태 (2026-07-17)
- **삼성 005930 (T0)**: V-062~067 전부 반영 = 완주 정본. 원문 3-way·amt 6칙·값색·라우팅 완비.
- **인프라 전 티커 일반화 완료(커밋 d6809a1)**:
  - **V-068** 원문 생성기 명칭 매칭 — 단일 CIS 4사(SK·NAVER·고려아연·현대건설) cf 결손·오라벨 복구. 8본 `report_*.json` 재생성됨.
  - **V-069** 렌더러 `_diveKey`(.row 우선)·`_hlRows`(dive.hl 우선) 일반화 — 신규 티커는 승격 dive에 `.row`/`.hl` 선언만. 삼성 무회귀.
  - **check_golden `--strict`** 게이트(§8: 원문 정합·amt·승격 구조) — dormant, 캐스케이드 수렴 판정용. 기본 `--all`은 green 유지.
  - **SK 매출채권 주8 승격 end-to-end 검증**(되돌림 — SK JSON은 승격 전 상태). 렌더러가 SK 자기 주번호로 정확 라우팅 확인.

## 다음 작업 — T1 골든 5본 캐스케이드 (삼성 패리티까지)
현재 T1 5본은 **V-048(APPENDIX)까지만** 반영, V-062~067(주석 승격·note_dive·amt·값색)은 **미반영**. 순서(갭 큰 순, 감사 실측):
1. **000660 SK하이닉스** (레시피 검증 겸 첫 타자) — 승격 대상 ~11주석(매출채권8·재고9·관계기업11·무형14·차입금16·충당부채18·종업원급여19·자본22·이익잉여금23·금융손익27·기타손익28), note_dive ~7, appendix 재키잉, 값색(서브행 전부 steel→dim).
2. 051910 LG화학 (갭 최다) → 3. 005380 현대차 → 4. 068270 셀트리온 → 5. 035420 NAVER.

각 티커 = `/galaxy-golden <ticker>` 또는 MILKYWAY §8.6 D1~D5 수동. **1본 = 1세션**(D2~D4 컨텍스트 큼).

## 그 다음 — T1 후보 6본 (미착수, 원문+신계약 처음부터 포함)
한화에어로 012450(원문 결함 보류·[[t1-batch-data-state]])·고려아연 010130·현대건설 000720·SKT 017670·HMM 011200·KT&G 033780. `T1_BATCH_PROMPT.md` 참조하되 **원문(S8)+§8.6 신계약을 완주 게이트에 포함**.

## 검증(완주 게이트, 티커마다)
- `check_golden <t> --strict` 0 · `check_golden --all` 0(무회귀) · `GALAXY_TICKER=<t> pytest tests/report/test_galaxy_interaction.py`
- 라이브: `python -m http.server 8000` → `http://localhost:8000/integration/dossier/galaxy.html?ticker=<t>` — 승격 행 클릭→그 회사 주N 카드·원문 동기·파선·콘솔 0. **클릭 사이 Esc**(V-049).
- 인코딩: `PYTHONUTF8=1`. `reports.db`는 로컬 전용(--strict §8·§7 원장은 이 머신만 유효).
