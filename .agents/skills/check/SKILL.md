---
name: check
description: 코드 리뷰 + 테스트 생성/실행 + PROGRESS.md 기록을 한번에 수행하는 최종 점검 skill
auto-invocable: false
---

# /check — 최종 점검

현재 세션에서 변경된 파일을 대상으로 아래 3가지를 순서대로 수행합니다.

## 1. 코드 리뷰 (code-reviewer agent)
- Agent 도구로 `code-reviewer` agent를 호출
- 변경된 파일의 코드 품질, 컨벤션 준수, 도메인 로직 이슈를 리뷰
- 이 agent는 읽기 전용 (코드 수정 안 함)

## 2. 테스트 생성 및 실행 (test-generator agent)
- Agent 도구로 `test-generator` agent를 호출 (1번과 **병렬 실행**)
- 변경된 함수에 대한 pytest 테스트를 자동 생성
- 생성된 테스트를 실행하여 통과 여부 확인

## 3. 결과 요약 및 PROGRESS.md 기록
- 1번과 2번 결과를 종합하여 팀원에게 요약 출력:
  - 리뷰 결과 (지적사항 있으면 표시)
  - 테스트 결과 (통과/실패 건수)
- 팀원이 확인 후, 해당 폴더의 PROGRESS.md에 아래 형식으로 기록:

```markdown
## YYYY-MM-DD
- **작업**: (변경 내용 요약)
- **파일**: (변경된 파일 목록)
- **테스트**: N/N 통과
- **리뷰**: (지적사항 요약 또는 "없음")
- **도메인 메모**: (팀원이 추가한 회계/도메인 관련 메모)
```
