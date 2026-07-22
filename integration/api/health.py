"""
integration/api/health.py — Vercel 배포 자체(및 DART_CHAT_ORIGIN 배선)가 살아있는지 확인하는
헬스체크. DartChatbot을 직접 호출하지 않는다 — 이 함수·환경변수 배선만 확인(api/PLAN.md M2).
"""

import json
import os
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(
            {
                "status": "ok",
                "origin_configured": bool(os.environ.get("DART_CHAT_ORIGIN")),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
