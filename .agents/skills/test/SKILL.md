---
name: test
description: 변경된 함수에 대한 pytest 테스트를 자동 생성하고 실행합니다.
auto-invocable: true
---

# /test — 테스트 생성 및 실행

Agent 도구로 `test-generator` agent를 호출하여 테스트를 생성하고 실행합니다.

## 수행 내용
1. 현재 세션에서 변경된 함수/클래스를 식별
2. 해당 함수에 대한 pytest 테스트 파일을 `tests/` 폴더에 생성
3. `python -m pytest` 실행하여 결과 확인

## 테스트 작성 규칙
- 파일명: `tests/test_{모듈명}.py`
- 정상 케이스 + 엣지 케이스 포함
- 외부 API(DART, yfinance 등)는 mock 처리
- shared/models.py의 DB 스키마에 맞는 fixture 사용

## 출력
- 생성된 테스트 파일 경로
- 실행 결과 (통과/실패 건수)
- 실패 시 원인 요약
