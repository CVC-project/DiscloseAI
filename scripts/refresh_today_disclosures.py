"""Refresh the public, key-free DART disclosure feed used by GitHub Pages."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


KST = timezone(timedelta(hours=9))
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
OUTPUT_PATH = (
    Path(__file__).parents[1]
    / "integration"
    / "data"
    / "today_disclosures.json"
)


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def display_date(value: object) -> str:
    raw = clean(value)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}" if len(raw) == 8 and raw.isdigit() else raw


def main() -> int:
    api_key = os.environ.get("DART_API_KEY", "").strip()
    if not api_key:
        print("DART_API_KEY is not configured", file=sys.stderr)
        return 2

    today = datetime.now(KST).strftime("%Y%m%d")
    params = {
        "crtfc_key": api_key,
        "bgn_de": today,
        "end_de": today,
        "sort": "date",
        "sort_mth": "desc",
        "page_no": "1",
        "page_count": "100",
    }
    request = Request(
        f"{DART_LIST_URL}?{urlencode(params)}",
        headers={"User-Agent": "DiscloseAI/1.0 (scheduled disclosure feed)"},
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    status = str(payload.get("status", ""))
    if status == "013":
        rows = []
    elif status == "000":
        rows = payload.get("list") or []
    else:
        print(f"OpenDART request failed with status {status}", file=sys.stderr)
        return 1

    items = []
    for row in rows:
        receipt_no = clean(row.get("rcept_no"))
        stock_code = clean(row.get("stock_code"))
        if not receipt_no or not stock_code:
            continue
        items.append(
            {
                "rceptNo": receipt_no,
                "dartUrl": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_no}",
                "company": clean(row.get("corp_name")),
                "stockCode": stock_code,
                "title": clean(row.get("report_nm")),
                "filer": clean(row.get("flr_nm")),
                "receiptDate": display_date(row.get("rcept_dt")),
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "source": "OpenDART",
                "date": display_date(today),
                "asOfKst": datetime.now(KST).isoformat(timespec="seconds"),
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
