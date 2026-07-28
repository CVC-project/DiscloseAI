"""KIND(kind.krx.co.kr) 상장회사 목록 다운로드 → 시장구분·업종설명 보강 원재료 생성.

기존 GPU 디스크의 fetch_krx_listed_tickers.py(scripts/)는 종목코드만 남기고 나머지
컬럼(시장구분·업종)을 버렸다. 이 스크립트는 같은 소스를 다시 받아 그 컬럼들까지 보존해
company_master.json의 market(코스피/코스닥)·industry_name 갭을 메운다.

주의:
  - "업종"은 KIND가 붙인 자유서술 텍스트라 DART KSIC 숫자코드(company_ksic.json)와
    1:1 대응은 아니다. 사람이 읽기 좋은 보조 라벨로만 쓴다.
  - market은 KIND 원문 그대로("유가증권"=코스피, "코스닥", "코넥스")를 표준 라벨로 정규화.

실행 (repo 루트에서)::
    python integration/dossier/fetch_krx_market_industry.py
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_OUT_PATH = os.path.join(
    _ROOT, "modules", "financial", "data", "universe", "krx_market_industry.json"
)

_KIND_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"
_TICKER_RE = re.compile(r"^\d{6}$")

def _normalize_market(raw: str) -> str | None:
    """KIND 원문 라벨 → 표준 코드.

    "유가증권"이 파싱 과정에서 "유가"로 잘리는 사례가 있어(원인 미상 — KIND HTML 셀
    안의 중첩 마크업 추정) 부분 일치로 판정한다.
    """
    if not raw:
        return None
    if raw.startswith("유가"):
        return "KOSPI"
    if "코스닥" in raw:
        return "KOSDAQ"
    if "코넥스" in raw:
        return "KONEX"
    return raw


class _KrxTableParser(HTMLParser):
    """의존성 없는 KIND 스프레드시트형 HTML 파서 (GPU측 fetch_krx_listed_tickers.py와 동일 방식)."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
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


def _decode(content: bytes) -> str:
    for enc in ("cp949", "euc-kr", "utf-8"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("KIND 응답 디코딩 실패")


def fetch_rows() -> list[dict]:
    resp = requests.get(_KIND_URL, timeout=30, headers={"User-Agent": "DiscloseAI/0.1"})
    resp.raise_for_status()
    parser = _KrxTableParser()
    parser.feed(_decode(resp.content))
    parser.close()

    out = []
    for row in parser.rows:
        if len(row) < 4:
            continue
        stock_code = row[2].strip()
        if not _TICKER_RE.fullmatch(stock_code):
            continue
        market_raw = row[1].strip()
        out.append(
            {
                "ticker": stock_code,
                "company_name": row[0].strip(),
                "market": _normalize_market(market_raw),
                "market_raw": market_raw,
                "industry_desc": row[3].strip() or None,
            }
        )
    if not out:
        raise ValueError("KIND 응답에서 유효한 종목코드를 찾지 못함")

    # 동일 ticker 중복 행 제거 (KIND 응답에 드물게 중복 행 존재 확인됨) — 첫 항목 채택
    seen: set[str] = set()
    deduped = []
    for row in out:
        if row["ticker"] in seen:
            continue
        seen.add(row["ticker"])
        deduped.append(row)
    return deduped


def main() -> int:
    rows = fetch_rows()
    payload = {
        "schema_version": 1,
        "source": _KIND_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "row_count": len(rows),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(_OUT_PATH), exist_ok=True)
    with open(_OUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

    from collections import Counter

    market_counts = Counter(r["market"] for r in rows)
    print(f"[done] {_OUT_PATH} ({len(rows)}행)")
    print(f"  시장 분포: {dict(market_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
