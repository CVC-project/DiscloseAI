"""Vercel serverless endpoint for live index/stock quotes.

Generalizes the original kospi.py (hardcoded to ^KS11) to accept any Yahoo
Finance chart symbol via ?symbol=, so one endpoint serves the KOSPI/KOSDAQ
index cards and the per-company current-price display:

  /api/quote?symbol=%5EKS11   → KOSPI
  /api/quote?symbol=%5EKQ11   → KOSDAQ
  /api/quote?symbol=005930.KS → 삼성전자 현재가

The v2 landing page is static, but browser-side finance APIs are often blocked
by CORS. This endpoint fetches the Yahoo Finance chart server-side and returns
the small normalized payload the UI needs.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
)

# 지수(^KS11)·개별 종목(005930.KS) 심볼만 허용 — 임의 경로 프록시로 악용되는 것을 방지.
_SYMBOL_RE = re.compile(r"^\^?[A-Za-z0-9]{1,10}(\.[A-Za-z]{1,4})?$")


def _is_valid_symbol(symbol: str) -> bool:
    return bool(symbol) and bool(_SYMBOL_RE.match(symbol))


def _last_finite(values: list[Any]) -> tuple[int | None, float | None]:
    for index in range(len(values) - 1, -1, -1):
        value = values[index]
        if isinstance(value, (int, float)):
            return index, float(value)
    return None, None


def _normalize_yahoo(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise ValueError("empty chart result")

    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    last_index, last_close = _last_finite(closes)

    value = meta.get("regularMarketPrice")
    if not isinstance(value, (int, float)):
        value = last_close
    if not isinstance(value, (int, float)):
        raise ValueError("missing price")

    previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    if not isinstance(previous_close, (int, float)) or previous_close == 0:
        raise ValueError("missing previous close")

    updated_at = meta.get("regularMarketTime")
    if (
        not isinstance(updated_at, (int, float))
        and last_index is not None
        and last_index < len(timestamps)
    ):
        updated_at = timestamps[last_index]
    if not isinstance(updated_at, (int, float)):
        updated_at = int(time.time())

    change_pct = ((float(value) - float(previous_close)) / float(previous_close)) * 100
    return {
        "symbol": symbol,
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
        query = urllib.parse.urlparse(self.path).query
        symbol = (urllib.parse.parse_qs(query).get("symbol") or [""])[0].strip()
        if not _is_valid_symbol(symbol):
            self._send_json(400, {"detail": "missing or invalid symbol"})
            return
        try:
            url = YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol, safe=""))
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self._send_json(200, _normalize_yahoo(payload, symbol))
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self._send_json(502, {"detail": "quote fetch failed", "error": str(exc)})
