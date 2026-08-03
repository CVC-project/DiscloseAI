# 다음 세션 프롬프트 — Wave 2 신규 산업 T1 골든 8본 (브랜치 `feat/golden-wave2-industries`)

> 이 파일은 다음 세션에 붙여넣을 핸드오프다. 갱신: 2026-08-03.

## 현재 상태

- **골든 20본 목표 중 12본 완주**: 삼성 005930(T0) + T1 11사 — 전원 5게이트 + `--strict` §8~12(무핀 0) PASS, dev 병합(PR #51).
- **Wave 2 착수(2026-08-03, 리더 결정)**: 48사 밖 **새 산업 8클러스터**에 첫 T1을 세운다 — 철강 현대제철 004020 · 정유 S-Oil 010950 · 식품 CJ제일제당 097950 · 유통 이마트 139480 · 항공 대한항공 003490 · 게임 크래프톤 259960 · 엔터 하이브 352820 · 유틸리티 한국전력 015760. **T2 확장은 이 브랜치 범위 밖**(별도 트랙). **PR 없이 본당 1커밋 push만**(리더 지시).
- **하네스 정비 완료(V-099·V-100, 08-03)**: ① `check_golden --strict` **§13 CF 운전자본 분리** 게이트(본표 집계 라인 보유 시 cf-wc 강제 — 2회+ 패턴 코드 승격) ② `sectioning_health` **deep**(원문 재분할 대조로 stale 꼬리 절단 검출 — V-058 사각 폐쇄) ③ VARIATIONS **V-070~079 번호 이중 사용 박제**, 신규 채록은 V-099부터 단일 시퀀스 ④ 신규 pytest 9건(`test_cf_wc_split.py`·`test_sectioner_stale_tail.py`). 기존 12본 `--strict --all` 0 무회귀.

## ▶ 다음 작업

**[WAVE2_BATCH_PROMPT.md](WAVE2_BATCH_PROMPT.md)를 읽고 그대로 실행한다.** 진행 순서:

1. **Phase 2 (데이터 준비, 미완이면 먼저)** — `corps.csv`에 8클러스터·`tier=1c` 등재 확인, `fs_enrich`로 7본(한전 제외) fnlttSinglAcntAll 5개년 적재(DART 키), `series` 완결률, `sectioner --health` 8본(한전 주16 괴물블록 기보고 — 재섹션·별도FS 확인).
2. **Phase 3 (빌드)** — WAVE2_BATCH_PROMPT 순서대로 1본=1세션. `git log --oneline -5`와 `corps.csv` tier로 진행 위치 파악(tier=1 완주·1c 대기).
3. 본마다: 5게이트 + `--strict` §1~13 = 0 · VARIATIONS 채록(V-099 시퀀스) · 1커밋 push · **승인 대기 없이 다음 본으로**(V-101).

> **리더 검수 방식(2026-08-03 결정, V-101)**: DL 사전 시각승인 폐지 — 완주본은 리더가 직접
> `python -m http.server 8000` → `http://localhost:8000/integration/dossier/galaxy.html?ticker=<티커>` 로 사후 확인.
> (1차 T1 5본 승인 대기도 같은 방식으로 해소 — 별도 승인 절차 없음.)

## 잔여 리더 트랙 (이 브랜치 밖)

1. **T2 클러스터 확장** — 기존 12 + 신규 8클러스터의 나머지 기업(각 T1 견본 캐스케이드, §8.5). 별도 브랜치.
2. dead-click 2~3행 렌더러 버그(V-059, 전 골든 동형·콘텐츠 무관).

## 주의

- 인코딩 `PYTHONUTF8=1`. `reports.db`(shared/data/)·`facts/`·`raw_cache/`는 gitignore(로컬 전용) — `--strict` §7·§10·§13은 이 머신에서만 유효(CI skip).
- 라이브 검증 클릭 사이 **Esc** 필수(V-049). main 직접 push·force push 금지.
