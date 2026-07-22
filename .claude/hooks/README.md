# Hooks

이 폴더는 Claude Code의 자동 트리거 스크립트를 저장하는 곳입니다.

## 현재 상태

- **보호 기능**: `.claude/settings.json`의 Permissions deny rules로 처리 (`.env` 편집·force push·`git reset --hard`·main push 차단)
- **format_py.py**: PostToolUse 훅 스크립트 **작성·검증 완료**. 단, `settings.json` 연결은 **각자 개인 설정에서 opt-in** (아래).

## format_py.py — 편집한 Python 파일 자동 Black 포맷

Edit/Write 후 대상이 레포 안 `.py`면 Black을 실행해 **CI black 검사를 로컬에서 선반영**한다.
- **비차단**: 항상 exit 0 (도구는 이미 실행됨 — 훅은 뒷정리만). Black 미설치·타임아웃·레포 밖 파일은 조용히 skip.
- 실제로 포맷을 바꾼 경우에만 `[black] auto-formatted <file>` 한 줄 출력.
- `.venv/Scripts/black.exe`가 있으면 그걸, 없으면 `python -m black` 사용.

### 연결 방법 (opt-in)

`.claude/settings.json`(팀 공유) 또는 `settings.local.json`(개인)의 최상위에 아래를 추가:

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        { "type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/format_py.py\"" }
      ]
    }
  ]
}
```

> 연결 후 Windows에서 훅이 안 뜨면 `$CLAUDE_PROJECT_DIR` 확장 문제일 수 있음 →
> `python .claude/hooks/format_py.py`(상대경로, cwd=프로젝트 루트) 로 교체 시도.

### 독립 테스트

```bash
echo '{"tool_input":{"file_path":"경로/파일.py"}}' | .venv/Scripts/python.exe .claude/hooks/format_py.py
```

## 참고: Hooks 작성 시 주의사항 (Windows)

- `.sh` 파일은 Windows에서 동작하지 않음 → **Python 스크립트**(위 format_py.py 방식) 또는 `.bat` 사용
- 데이터는 `TOOL_INPUT` 환경변수가 아니라 **stdin JSON**으로 수신
- PostToolUse에서 Claude에게 피드백을 강제하려면 `exit 2`(stderr가 Claude로 전달, 도구는 이미 실행됨)
- 참조: https://docs.anthropic.com/en/docs/claude-code/hooks
