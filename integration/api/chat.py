"""
integration/api/chat.py — Vercel 서버리스 함수: DartChatbot(OpenDART RAG · Amazon Bedrock) 프록시.

Vercel Root Directory=integration이라 함수도 이 폴더 밑에 있어야 인식된다
(2026-07-22 배포 실측 — 루트 api/는 Root Directory 밖이라 404). api/PLAN.md M2.
브라우저(same-origin `/api/chat`) -> 이 함수 -> DartChatbot(GPU 서버) 순서로 중계한다.
DartChatbot의 실제 주소(DART_CHAT_ORIGIN)는 Vercel 환경변수에만 존재 — 저장소·프론트
소스 어디에도 하드코딩하지 않는다(보안 규칙, api/PLAN.md M2).

계약(C1, api/PLAN.md): POST /api/chat {"messages":[{"role","content"}]}
-> {"answer", "disclaimer", "sources"?}
"""

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

DART_CHAT_ORIGIN = os.environ.get("DART_CHAT_ORIGIN", "").rstrip("/")
DISCLAIMER = "과거 통계·공시 기반 참고 정보이며, 투자 조언이 아닙니다."  # C5

# 서버리스 인스턴스가 재사용되는 동안만 유효한 최소 방어(콜드스타트마다 리셋).
# 진짜 rate limit(다중 인스턴스 공유 카운터)은 M4에서 외부 저장소로 대체 예정 —
# 그 전까지 없는 것보다는 나은 1차 방어선.
_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_IP = 20
_hits: dict[str, list[float]] = {}


def _rate_limited(ip: str) -> bool:
    now = time.time()
    bucket = _hits.setdefault(ip, [])
    bucket[:] = [t for t in bucket if now - t < _WINDOW_SECONDS]
    if len(bucket) >= _MAX_REQUESTS_PER_IP:
        return True
    bucket.append(now)
    return False


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._send_json(
            200, {"status": "ok", "origin_configured": bool(DART_CHAT_ORIGIN)}
        )

    def do_POST(self) -> None:
        if not DART_CHAT_ORIGIN:
            self._send_json(
                500, {"detail": "DART_CHAT_ORIGIN 환경변수가 설정되지 않았습니다."}
            )
            return

        client_ip = (
            self.headers.get("x-forwarded-for", self.client_address[0])
            .split(",")[0]
            .strip()
        )
        if _rate_limited(client_ip):
            self._send_json(
                429, {"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}
            )
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > 20_000:
            self._send_json(413, {"detail": "요청이 너무 큽니다."})
            return
        raw = self.rfile.read(length) if length else b"{}"

        try:
            upstream_req = urllib.request.Request(
                f"{DART_CHAT_ORIGIN}/api/chat",
                data=raw,
                headers={
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true",
                },
                method="POST",
            )
            with urllib.request.urlopen(upstream_req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace") if e.fp else e.reason
            self._send_json(e.code, {"detail": f"DartChatbot 오류: {detail}"[:300]})
            return
        except (
            Exception
        ) as e:  # noqa: BLE001 — 업스트림 장애는 그대로 우아한 저하로 전달(C1)
            self._send_json(502, {"detail": f"챗봇 서버 연결 실패: {e}"})
            return

        data["disclaimer"] = DISCLAIMER
        self._send_json(200, data)
