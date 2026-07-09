#!/usr/bin/env python
"""PostToolUse 훅 — 편집한 Python 파일을 Black으로 자동 포맷.

Claude Code가 Edit/Write 후 stdin으로 넘기는 PostToolUse JSON을 읽어,
대상이 이 레포 안의 .py 파일이면 Black을 실행한다.
- **비차단**: 어떤 경우에도 exit 0 (도구는 이미 실행됨 — 훅은 뒷정리만).
- Black 미설치·타임아웃·레포 밖 파일 등은 조용히 skip.
- 실제로 포맷을 바꾼 경우에만 stdout 한 줄로 알린다 (CI black 루프를 로컬에서 선반영).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # .claude/hooks/ -> repo root


def _black_cmd():
    venv_black = ROOT / ".venv" / "Scripts" / "black.exe"
    if venv_black.exists():
        return [str(venv_black)]
    return [sys.executable, "-m", "black"]


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    fp = tool_input.get("file_path") or tool_input.get("path")
    if not fp:
        return 0

    p = Path(fp)
    if p.suffix != ".py" or not p.exists():
        return 0
    try:
        p.resolve().relative_to(ROOT)  # 레포 밖 파일은 건드리지 않음
    except ValueError:
        return 0

    cmd = _black_cmd()
    try:
        would_change = subprocess.run(
            cmd + ["--check", "--quiet", str(p)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return 0

    if would_change.returncode != 1:  # 0=이미 정렬됨, 123=에러 → skip
        return 0

    try:
        subprocess.run(
            cmd + ["--quiet", str(p)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        print(f"[black] auto-formatted {p.name}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
