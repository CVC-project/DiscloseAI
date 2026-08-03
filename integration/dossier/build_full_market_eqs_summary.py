"""Build integration/data/eqs_summary.json from full-market firm_<ticker>.json.

The v2 loader enriches universe nodes from this compact file. firm_<ticker>.json
remains the detailed source for the EQS iframe; this script only creates the
small index used by the main galaxy UI.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIRM_DIR = ROOT / "integration" / "dossier" / "data"
OUT_PATH = ROOT / "integration" / "data" / "eqs_summary.json"
BUSINESS_DIR = ROOT / "integration" / "dossier" / "data"
UNIVERSE_PATH = ROOT / "integration" / "data" / "universe.json"
MARKET_CAP_PATH = ROOT / "integration" / "data" / "market_caps_naver.json"

NAVER_MARKET_SUM_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
NAVER_HEADERS = {"User-Agent": "Mozilla/5.0"}
NAVER_MARKETS = {"KOSPI": 0, "KOSDAQ": 1}
NAVER_MAX_PAGES = 80
NAVER_SLEEP_SEC = 0.15


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def module_map(eqs: dict[str, Any]) -> dict[str, Any]:
    return {m.get("name"): m for m in (eqs.get("modules") or []) if m.get("name")}


def latest_year(years: list[dict[str, Any]]) -> dict[str, Any]:
    if not years:
        return {}
    return sorted(years, key=lambda y: y.get("year") or 0)[-1]


def to_eok(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) / 100_000_000, 1)
    except (TypeError, ValueError):
        return None


def parse_market_cap_label(value: Any) -> float | None:
    """Parse labels like '1210.2조' or '5000억' into KRW."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        if text.endswith("조"):
            return float(text[:-1]) * 1_000_000_000_000
        if text.endswith("억"):
            return float(text[:-1]) * 100_000_000
        return float(text)
    except ValueError:
        return None


def _merge_cap(
    caps: dict[str, float],
    prices: dict[str, float],
    sources: dict[str, str],
    asofs: dict[str, str],
    ticker: str,
    cap: Any,
    *,
    price: Any = None,
    source: str,
    asof: str | None = None,
    overwrite: bool = False,
) -> None:
    parsed = parse_market_cap_label(cap)
    if parsed is None:
        return
    if ticker in caps and not overwrite:
        return
    caps[ticker] = parsed
    sources[ticker] = source
    if asof:
        asofs[ticker] = asof
    try:
        if price is not None:
            prices[ticker] = float(price)
    except (TypeError, ValueError):
        pass


def load_business_market_caps() -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
    caps: dict[str, float] = {}
    prices: dict[str, float] = {}
    sources: dict[str, str] = {}
    asofs: dict[str, str] = {}
    for path in BUSINESS_DIR.glob("business_*.json"):
        ticker = path.stem.replace("business_", "")
        try:
            data = load_json(path)
        except Exception:
            continue
        _merge_cap(
            caps,
            prices,
            sources,
            asofs,
            ticker,
            data.get("market_cap"),
            price=data.get("last_price"),
            source=data.get("market_cap_source") or "business_json",
            asof=data.get("market_cap_asof"),
        )
    return caps, prices, sources, asofs


def load_universe_market_caps() -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
    caps: dict[str, float] = {}
    prices: dict[str, float] = {}
    sources: dict[str, str] = {}
    asofs: dict[str, str] = {}
    if not UNIVERSE_PATH.exists():
        return caps, prices, sources, asofs
    data = load_json(UNIVERSE_PATH)
    asof = (data.get("meta") or {}).get("as_of")
    for node in data.get("named") or []:
        ticker = node.get("t")
        if not ticker:
            continue
        _merge_cap(
            caps,
            prices,
            sources,
            asofs,
            ticker,
            node.get("mc"),
            source="universe_json",
            asof=asof,
        )
    return caps, prices, sources, asofs


def fetch_naver_market_caps() -> dict[str, Any]:
    """Fetch a full KOSPI/KOSDAQ market-cap snapshot from Naver Finance.

    Naver's market-sum table exposes market cap in units of 억원. We persist the
    snapshot so repeated EQS summary builds do not depend on live HTTP calls.
    """
    import requests
    from bs4 import BeautifulSoup

    rows: list[dict[str, Any]] = []
    asof = datetime.now(timezone.utc).date().isoformat()
    for market, sosok in NAVER_MARKETS.items():
        for page in range(1, NAVER_MAX_PAGES + 1):
            response = requests.get(
                NAVER_MARKET_SUM_URL,
                params={"sosok": sosok, "page": page},
                headers=NAVER_HEADERS,
                timeout=20,
            )
            response.raise_for_status()
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")
            page_rows: list[dict[str, Any]] = []
            for tr in soup.select("table.type_2 tr"):
                anchor = tr.select_one("a.tltle")
                if anchor is None:
                    continue
                href = anchor.get("href", "")
                ticker = href.rsplit("code=", 1)[-1].strip() if "code=" in href else ""
                cells = [td.text.strip() for td in tr.select("td")]
                if not ticker or len(cells) <= 6:
                    continue
                try:
                    rank = int(cells[0].replace(",", ""))
                    last_price = float(cells[2].replace(",", ""))
                    market_cap = float(cells[6].replace(",", "")) * 100_000_000
                except ValueError:
                    continue
                page_rows.append(
                    {
                        "ticker": ticker,
                        "name": anchor.text.strip(),
                        "market": market,
                        "rank": rank,
                        "last_price": last_price,
                        "market_cap": market_cap,
                    }
                )
            if not page_rows:
                break
            rows.extend(page_rows)
            time.sleep(NAVER_SLEEP_SEC)
    return {
        "meta": {
            "source": "naver_finance_market_sum",
            "as_of": asof,
            "count": len(rows),
        },
        "data": rows,
    }


def load_naver_market_caps() -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str], dict[str, Any] | None]:
    if not MARKET_CAP_PATH.exists():
        MARKET_CAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        snapshot = fetch_naver_market_caps()
        if snapshot.get("data"):
            MARKET_CAP_PATH.write_text(
                json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
    if not MARKET_CAP_PATH.exists():
        return {}, {}, {}, {}, None

    snapshot = load_json(MARKET_CAP_PATH)
    meta = snapshot.get("meta") or {}
    asof = meta.get("as_of")
    caps: dict[str, float] = {}
    prices: dict[str, float] = {}
    sources: dict[str, str] = {}
    asofs: dict[str, str] = {}
    for row in snapshot.get("data") or []:
        ticker = row.get("ticker")
        if not ticker:
            continue
        _merge_cap(
            caps,
            prices,
            sources,
            asofs,
            ticker,
            row.get("market_cap"),
            price=row.get("last_price"),
            source=meta.get("source") or "naver_finance_market_sum",
            asof=asof,
        )
    return caps, prices, sources, asofs, meta


def load_market_cap_context() -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str], dict[str, Any]]:
    caps: dict[str, float] = {}
    prices: dict[str, float] = {}
    sources: dict[str, str] = {}
    asofs: dict[str, str] = {}
    for loader in (load_business_market_caps, load_universe_market_caps):
        loaded_caps, loaded_prices, loaded_sources, loaded_asofs = loader()
        for ticker, cap in loaded_caps.items():
            _merge_cap(
                caps,
                prices,
                sources,
                asofs,
                ticker,
                cap,
                price=loaded_prices.get(ticker),
                source=loaded_sources.get(ticker) or loader.__name__,
                asof=loaded_asofs.get(ticker),
            )

    naver_caps, naver_prices, naver_sources, naver_asofs, naver_meta = load_naver_market_caps()
    for ticker, cap in naver_caps.items():
        _merge_cap(
            caps,
            prices,
            sources,
            asofs,
            ticker,
            cap,
            price=naver_prices.get(ticker),
            source=naver_sources.get(ticker) or "naver_finance_market_sum",
            asof=naver_asofs.get(ticker),
            overwrite=True,
        )

    meta = {
        "market_cap_snapshot": naver_meta,
    }
    return caps, prices, sources, asofs, meta


def build_row(
    path: Path,
    market_caps: dict[str, float],
    market_prices: dict[str, float],
    market_sources: dict[str, str],
    market_asofs: dict[str, str],
) -> dict[str, Any] | None:
    ticker = path.stem.replace("firm_", "")
    data = load_json(path)
    corp = data.get("corp") or {}
    eqs = data.get("eqs") or {}
    years = data.get("years") or []
    latest = latest_year(years)
    modules = module_map(eqs)

    if eqs.get("total") is None:
        return None

    row = {
        "ticker": ticker,
        "corp_code": corp.get("code"),
        "corp_name": corp.get("name"),
        "year": latest.get("year"),
        "quarter": None,
        "revenue": to_eok(latest.get("revenue")),
        "operating_income": to_eok(latest.get("operating_income")),
        "net_income": to_eok(latest.get("net_income")),
        "total_assets": to_eok(latest.get("total_assets")),
        "total_liabilities": to_eok(latest.get("total_liabilities")),
        "total_equity": to_eok(latest.get("total_equity")),
        "operating_cashflow": to_eok(latest.get("operating_cashflow")),
        "market_cap": market_caps.get(ticker),
        "last_price": market_prices.get(ticker),
        "market_cap_source": market_sources.get(ticker),
        "market_cap_asof": market_asofs.get(ticker),
        "dart_url": None,
        "industry_code": corp.get("industry"),
        "is_financial": str(eqs.get("method") or "").startswith("feqs_"),
        "eqs_total": eqs.get("total"),
        "eqs_grade": eqs.get("grade"),
        "eqs_method": eqs.get("method"),
        "eqs_excluded": eqs.get("excluded") or [],
        "eqs_modules": modules,
        "eqs_module_notes": {
            k: v.get("note") for k, v in modules.items() if isinstance(v, dict)
        },
    }
    for key in ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]:
        row[f"eqs_{key.lower()}"] = (modules.get(key) or {}).get("score")
    return row


def main() -> int:
    market_caps, market_prices, market_sources, market_asofs, market_meta = (
        load_market_cap_context()
    )
    rows = []
    financial = 0
    for path in sorted(FIRM_DIR.glob("firm_*.json")):
        row = build_row(path, market_caps, market_prices, market_sources, market_asofs)
        if row is None:
            continue
        if row["is_financial"]:
            financial += 1
        rows.append(row)

    row_source_counts: dict[str, int] = {}
    for row in rows:
        source = row.get("market_cap_source")
        if source:
            row_source_counts[source] = row_source_counts.get(source, 0) + 1

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "integration/dossier/data/firm_<ticker>.json",
            "count": len(rows),
            "financial_feqs_count": financial,
            "non_financial_eqs_count": len(rows) - financial,
            "market_cap_count": sum(row.get("market_cap") is not None for row in rows),
            "market_cap_missing_count": sum(row.get("market_cap") is None for row in rows),
            "market_cap_sources": row_source_counts,
            **market_meta,
        },
        "data": rows,
    }
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
