"""Vercel serverless endpoint for the live KOSPI status card.

The v2 landing page is static, but browser-side finance APIs are often blocked
by CORS. This endpoint fetches the Yahoo Finance KOSPI chart server-side and
returns the small normalized payload the UI needs.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any


YAHOO_KOSPI_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=1d&interval=1m"
)


def _last_finite(values: list[Any]) -> tuple[int | None, float | None]:
    for index in range(len(values) - 1, -1, -1):
        value = values[index]
        if isinstance(value, (int, float)):
            return index, float(value)
    return None, None


def _normalize_yahoo(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise ValueError("empty KOSPI chart result")

    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    last_index, last_close = _last_finite(closes)

    value = meta.get("regularMarketPrice")
    if not isinstance(value, (int, float)):
        value = last_close
    if not isinstance(value, (int, float)):
        raise ValueError("missing KOSPI price")

    previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    if not isinstance(previous_close, (int, float)) or previous_close == 0:
        raise ValueError("missing KOSPI previous close")

    updated_at = meta.get("regularMarketTime")
    if not isinstance(updated_at, (int, float)) and last_index is not None and last_index < len(timestamps):
        updated_at = timestamps[last_index]
    if not isinstance(updated_at, (int, float)):
        updated_at = int(time.time())

    change_pct = ((float(value) - float(previous_close)) / float(previous_close)) * 100
    return {
        "symbol": "KOSPI",
        "value": round(float(value), 2),
        "previousClose": round(float(previous_close), 2),
        "changePct": round(change_pct, 4),
        "updatedAt": int(updated_at) * 1000,
        "source": "Yahoo Finance",
    }


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "s-maxage=60, stale-while-revalidate=120")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            request = urllib.request.Request(
                YAHOO_KOSPI_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._send_json(200, _normalize_yahoo(payload))
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(502, {"detail": "KOSPI quote fetch failed", "error": str(exc)})
