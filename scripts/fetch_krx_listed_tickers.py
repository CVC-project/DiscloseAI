"""Fetch the current KRX listed-company ticker universe from KIND.

The DART corporate-code file includes delisted companies, so it must not be
used as the collection universe by itself. This script stores the currently
listed six-digit tickers in a JSON cache for the EQS batch collector.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests


KIND_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "modules" / "financial" / "data" / "krx_listed_tickers.json"
_TICKER_PATTERN = re.compile(r"^\d{6}$")


class _KrxTableParser(HTMLParser):
    """Small dependency-free parser for KIND's spreadsheet-shaped HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell_parts).split()))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def parse_krx_tickers(html: str) -> list[str]:
    """Return current KRX six-digit tickers from the KIND corporate list."""
    parser = _KrxTableParser()
    parser.feed(html)
    parser.close()
    tickers = {
        row[2]
        for row in parser.rows
        if len(row) >= 3 and _TICKER_PATTERN.fullmatch(row[2])
    }
    if not tickers:
        raise ValueError("KIND corporate-list response did not contain any six-digit tickers")
    return sorted(tickers)


def decode_kind_response(content: bytes) -> str:
    for encoding in ("cp949", "euc-kr", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode KIND corporate-list response")


def fetch_tickers() -> list[str]:
    response = requests.get(KIND_LIST_URL, timeout=30, headers={"User-Agent": "DiscloseAI/0.1"})
    response.raise_for_status()
    return parse_krx_tickers(decode_kind_response(response.content))


def save_tickers(path: Path, tickers: list[str]) -> None:
    payload = {
        "schema_version": 1,
        "source": KIND_LIST_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ticker_count": len(tickers),
        "tickers": tickers,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    tickers = fetch_tickers()
    save_tickers(args.output, tickers)
    print(f"Saved {len(tickers)} listed KRX tickers: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
