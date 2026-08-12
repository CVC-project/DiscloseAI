"""Server-side OpenDART feed for the integration disclosure panel.

The browser never receives the OpenDART certification key. Configure
``DART_API_KEY`` only as a local environment variable or a Vercel server
environment variable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from http.server import BaseHTTPRequestHandler


_KST = timezone(timedelta(hours=9))
_DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
_DART_DOCUMENT_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}"
_DEFAULT_LIMIT = 30
_MAX_LIMIT = 100


def _today_kst(now: Optional[datetime] = None) -> str:
    """Return the current calendar day in Korea as YYYYMMDD."""
    current = now.astimezone(_KST) if now else datetime.now(_KST)
    return current.strftime("%Y%m%d")


def _display_date(value: Any) -> str:
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_items(
    items: Iterable[Dict[str, Any]], limit: int
) -> List[Dict[str, str]]:
    """Keep only listed-company disclosures and expose safe public fields."""
    normalized: List[Dict[str, str]] = []
    for item in items:
        receipt_no = _clean_text(item.get("rcept_no"))
        stock_code = _clean_text(item.get("stock_code"))
        if not receipt_no or not stock_code:
            continue
        normalized.append(
            {
                "rceptNo": receipt_no,
                "dartUrl": _DART_DOCUMENT_URL.format(receipt_no),
                "company": _clean_text(item.get("corp_name")),
                "stockCode": stock_code,
                "title": _clean_text(item.get("report_nm")),
                "filer": _clean_text(item.get("flr_nm")),
                "receiptDate": _display_date(item.get("rcept_dt")),
            }
        )
        if len(normalized) >= limit:
            break
    return normalized


def _read_limit(path: str) -> int:
    try:
        requested = int(
            parse_qs(urlparse(path).query).get("limit", [_DEFAULT_LIMIT])[0]
        )
    except (TypeError, ValueError):
        requested = _DEFAULT_LIMIT
    return max(1, min(requested, _MAX_LIMIT))


def _read_corp_code(path: str) -> str:
    raw = parse_qs(urlparse(path).query).get("corp_code", [""])[0]
    raw = _clean_text(raw)
    return raw if raw.isdigit() and len(raw) == 8 else ""


_COMPANY_LOOKBACK_DAYS = 90


class handler(BaseHTTPRequestHandler):
    """Vercel Python handler. Uses only the standard library by design."""

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header(
            "Cache-Control", "public, s-maxage=120, stale-while-revalidate=300"
        )
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name
        api_key = os.environ.get("DART_API_KEY", "").strip()
        if not api_key:
            self._send_json(503, {"detail": "DART API is not configured"})
            return

        day = _today_kst()
        corp_code = _read_corp_code(self.path)
        params = {
            "crtfc_key": api_key,
            "bgn_de": day,
            "end_de": day,
            "sort": "date",
            "sort_mth": "desc",
            "page_no": "1",
            "page_count": str(_MAX_LIMIT),
        }
        if corp_code:
            # 아카이브(top50만 사전 수집)에 없는 기업을 조회할 때, 저장 없이 그 자리에서
            # DART에 직접 물어본다 — corp_code가 있으면 오늘 하루가 아니라 최근 N일을 본다.
            now = datetime.now(_KST)
            params["bgn_de"] = (now - timedelta(days=_COMPANY_LOOKBACK_DAYS)).strftime(
                "%Y%m%d"
            )
            params["corp_code"] = corp_code
        request = Request(
            f"{_DART_LIST_URL}?{urlencode(params)}",
            headers={"User-Agent": "DiscloseAI/1.0 (server disclosure feed)"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            self._send_json(
                502, {"detail": "DART disclosure feed is temporarily unavailable"}
            )
            return

        status = str(payload.get("status", ""))
        if status == "013":  # OpenDART: no data found for the requested day.
            raw_items: List[Dict[str, Any]] = []
        elif status == "000":
            raw_items = payload.get("list") or []
        else:
            self._send_json(
                502, {"detail": "DART disclosure feed request failed", "status": status}
            )
            return

        items = _normalize_items(raw_items, _read_limit(self.path))
        self._send_json(
            200,
            {
                "source": "OpenDART",
                "date": _display_date(day),
                "asOfKst": datetime.now(_KST).isoformat(timespec="seconds"),
                "count": len(items),
                "items": items,
            },
        )
