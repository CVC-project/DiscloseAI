# 하네스 A 결과 — CPA 검수 대기 (2026-07-29)

> 상태: **교사 라벨링 완주 · 사람 검수 지점 도달**. 다음 행동은 리더(CPA) 검수.
> 정본 절차: [PLAN.md](PLAN.md) §4.1(A1~A5)·§3.3(데이터셋)·§4.6(G-A 게이트).

## 산출물 (`modules/relation/data/vc_dataset/`)

| 파일 | 내용 |
|---|---|
| `split_snapshot.json` | 표본 정본(seed=7 층화, 재샘플링 금지 — 재개 시 이 파일 사용) |
| `val.jsonl` (400) · `test.jsonl` (500) | 청크 + pass1/pass2 라벨 + `agree` + `teacher`(합의분만) |
| `cpa_review_val.jsonl` (17) · `cpa_review_test.jsonl` (19) | **검수 큐** — 2회 불일치분, 불일치 폭 큰 순 정렬 |
| `batches/*.{input,pass1,pass2}.output.jsonl` | 원자료 62런(파일 존재=완료 규약) |

## 실측 결과

- **자기일치율: val 95.75%(383/400) · test 96.2%(481/500)** — G-A 기준 ≥85% **충족**.
- **스키마·evidence exact-match 오류 0건** (900청크 × 2패스 전량 검증).
- 하드 네거티브(관계 없음 합의): val 87.2% · test 87.7% — §3.3 목표 ≥30% 크게 상회.
  ⚠️ 역으로 **관계 보유 청크가 희소**(val 49 · test 59) → train 3,000청크 목표는
  이 비율대로면 관계 보유가 ~390청크뿐. **A6 표적 증강 필요**(관계 어휘 강한 층 과표집).
- 라벨 분포: val 118관계(customer 57·raw_material 27·competitor 21·supplier 13, 익명 45)
  / test 216관계(customer 140·supplier 46·competitor 21·raw_material 9, 익명 39).
  status는 active 압도(val 115/118 · test 198/216) — past·planned 희소(학습 난점 예상).

## 사람(CPA) 검수 지점 — 다음 행동

1. `cpa_review_val.jsonl` 17건 판정 → val 확정(운영점 τ 튜닝의 기준).
2. `cpa_review_test.jsonl` 19건 판정 + **test 500 전량 검수 후 봉인**(§3.3 — 봉인 후
   test 평가는 1회뿐, 재시도 금지).
3. 불일치 유형(실측): ① 표기 변이(`LG에너지솔루션L(폴란드법인)` vs `LG에너지솔루션L`)
   ② status 판정(past/planned/active 경계 — 연혁·계약종료 서술) ③ 익명 관계 추출 여부.
   → 판정 결과는 프롬프트 규칙 보강(A6)에 그대로 환류.

## 재개 절차 (라벨링이 중단됐을 때만)

`batches/*.input.jsonl` 대비 누락된 `.pass1/.pass2.output.jsonl`만 에이전트로 재실행
(교사 프롬프트는 PROGRESS.md 2026-07-29 기록 참조). 전부 모이면
`train/dataset.py collect_outputs()` → `assemble()` → 검수 큐 재생성.
