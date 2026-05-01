"""
로컬 개발 환경 실행 스크립트.
스케줄러 + 챗서버를 한 번에 띄운다.

실행:
    python run_dev.py
"""

import subprocess
import sys
import os
import signal
from pathlib import Path

ROOT = Path(__file__).parent
# venv가 있으면 venv Python 사용, 없으면 현재 Python
_venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(_venv_python) if _venv_python.exists() else sys.executable

processes = []


def start():
    procs = [
        ("스케줄러", [PYTHON, "-m", "modules.disclosure.scheduler"]),
        ("챗서버",   [PYTHON, "-m", "modules.disclosure.chat_server"]),
    ]
    for name, cmd in procs:
        p = subprocess.Popen(cmd, cwd=ROOT)
        processes.append(p)
        print(f"[run_dev] {name} 시작 (pid={p.pid})")


def stop(sig=None, frame=None):
    print("\n[run_dev] 종료 중...")
    for p in processes:
        p.terminate()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    start()
    print("[run_dev] Ctrl+C 로 종료")
    for p in processes:
        p.wait()
