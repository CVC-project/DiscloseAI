# 하네스 A 실행 상태 — 세션 재개용 (2026-07-29)

> 목표: val 400 + test 500 교사 라벨 2회수 → 자기일치 집계 → **CPA 검수 큐 산출(사람 지점)**.
> 이 파일은 실행 상태 원장 — 완료 시 삭제하고 결과는 PROGRESS.md로.

## 확정 사항
- 교사 = Claude Code 서브에이전트 (계획상 Claude API였으나 키 부재 — galaxy 선례 준용,
  학생 채점 비관여 원칙 §0.5 불변). 패스1·2는 동일 프롬프트의 독립 에이전트.
- 표본: seed=7 층화(시장×섹터×패턴 3종), 파일럿 100청크 제외(봉인 순수성).
  스냅샷 = `modules/relation/data/vc_dataset/split_snapshot.json` (재개 시 재샘플링 금지 — 이 파일 사용).
- 배치: `modules/relation/data/vc_dataset/batches/{val|test}_{NNN}.input.jsonl`
  (val 14개 · test 17개, 30청크/배치).
- 산출 규약: 같은 폴더 `{stem}.pass{1|2}.output.jsonl` — **파일 존재 = 완료** (멱등 재개 키).

## 재개 절차
1. `batches/*.input.jsonl` 대비 누락된 `.pass1/.pass2.output.jsonl`만 에이전트로 재실행
   (웨이브 ~8개 병렬, 프롬프트는 아래 §교사 프롬프트 그대로).
2. 전부 모이면: `train/dataset.py collect_outputs()` → 검증(스키마·evidence exact-match)
   + 자기일치율 → `assemble()` → `{val,test}.jsonl`.
3. CPA 검수 큐 산출(불일치·오류 우선 정렬) → 리더 보고 후 정지. G-A 참고치(자기일치 ≥85%).

## 교사 프롬프트 (패스 공통 — 변경 금지)
입력 파일의 각 JSONL 행(chunk_id, anchor, text)에 대해 §3.2 스키마로 관계 추출,
출력 파일에 `{"chunk_id": ..., "relations": [...]}` 한 행씩(관계 없으면 빈 배열).
규칙: counterparty=원문 표기 그대로 / evidence=원문에서 한 글자도 바꾸지 말고 복사
(표 행이면 그 행 텍스트 그대로) / 익명 상대는 counterparty=null+anonymous=true /
일반명사·산업동향 속 타사명 언급·자사 계열 나열은 관계 아님 / status: active|past|planned.
