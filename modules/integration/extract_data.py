"""Integration 데이터 통합 추출 스크립트.

각 모듈의 DB·Python 상수에서 데이터를 뽑아 ``modules/integration/data/`` 아래
통합 JSON을 생성한다. top50(modules/relation/data/top50.csv) 기준으로 필터링.

데이터 소스:
  - modules/financial/data/financial.db (financial_local 테이블)
  - modules/disclosure/data/disclosure.db (disclosure_local + financial_statement)
  - modules/price/quiz_data.py (QUIZ_LIST 상수)
  - modules/relation/data/graph_top50.json (dashboard가 직접 fetch, 여기선 미사용)

사용::

    python -m modules.integration.extract_data

출력::

    modules/integration/data/eqs_summary.json
    modules/integration/data/disclosures.json
    modules/integration/data/price_scenarios.json

자세한 규약은 ``modules/integration/CLAUDE.md`` 참조.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INTEGRATION_DATA = Path(__file__).parent / "data"
TOP50_CSV = ROOT / "modules" / "relation" / "data" / "top50.csv"
FINANCIAL_DB = ROOT / "modules" / "financial" / "data" / "financial.db"
DISCLOSURE_DB = ROOT / "modules" / "disclosure" / "data" / "disclosure.db"


# --------------------------------------------------------------------------- #
#  top50 로드
# --------------------------------------------------------------------------- #
def load_top50() -> list[dict]:
    """top50.csv를 읽어 dict list 반환.

    각 row는 rank·corp_name·ticker·market_cap·group_name·sector·corp_code 컬럼.
    """
    if not TOP50_CSV.exists():
        print(f"[WARN] top50.csv 없음: {TOP50_CSV}", file=sys.stderr)
        return []
    with TOP50_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
#  financial 추출
# --------------------------------------------------------------------------- #
def extract_financial(corp_codes: set[str]) -> list[dict]:
    """financial.db의 ``financial_local``에서 기업당 최신 레코드 1건 추출.

    연도·분기 DESC 정렬 후 corp_code별 첫 건.
    """
    if not FINANCIAL_DB.exists():
        print(f"[WARN] financial.db 없음: {FINANCIAL_DB}", file=sys.stderr)
        return []
    if not corp_codes:
        return []

    rows: list[dict] = []
    seen: set[str] = set()
    placeholders = ",".join("?" * len(corp_codes))
    query = f"""
        SELECT corp_code, corp_name, year, quarter,
               revenue, operating_income, net_income,
               total_assets, total_liabilities, total_equity,
               operating_cashflow, investing_cashflow, financing_cashflow,
               eqs_m1, eqs_m2, eqs_m3, eqs_m4, eqs_m5,
               eqs_total, eqs_grade
        FROM financial_local
        WHERE corp_code IN ({placeholders})
        ORDER BY corp_code, year DESC, COALESCE(quarter, 0) DESC
    """
    with sqlite3.connect(FINANCIAL_DB) as con:
        con.row_factory = sqlite3.Row
        for r in con.execute(query, tuple(corp_codes)):
            if r["corp_code"] in seen:
                continue
            seen.add(r["corp_code"])
            rows.append({k: r[k] for k in r.keys()})
    return rows


# --------------------------------------------------------------------------- #
#  disclosure 추출
# --------------------------------------------------------------------------- #
def extract_disclosures(
    corp_to_ticker: dict[str, str],
    per_corp: int = 5,
    statements_limit: int = 8,
) -> dict:
    """disclosure.db에서 기업당 최근 N건 + 분기 재무제표 최근 M분기 추출.

    ⚠️ 같은 DB 안에서도 **식별자 체계가 다름**:
      - ``disclosure_local.corp_code``  = DART 8자리 (예: '00126380')
      - ``financial_statement.corp_code`` = KRX 6자리 ticker (예: '005930')
    두 쿼리를 서로 다른 키로 실행한다.

    Args:
        corp_to_ticker: {DART corp_code 8자리: KRX ticker 6자리, ...}

    Returns:
        {
          "disclosures": [...],          # disclosure_local 기준 (corp_code 8자리)
          "statements": [...]            # financial_statement 기준 (ticker 6자리)
        }
    """
    if not DISCLOSURE_DB.exists():
        print(f"[WARN] disclosure.db 없음: {DISCLOSURE_DB}", file=sys.stderr)
        return {"disclosures": [], "statements": []}
    if not corp_to_ticker:
        return {"disclosures": [], "statements": []}

    disclosures: list[dict] = []
    statements: list[dict] = []
    disc_query = """
        SELECT disclosure_id, corp_code, corp_name, disclosure_date,
               disclosure_type, title, amount, summary,
               high_impact, dilution_ratio, stock_code
        FROM disclosure_local
        WHERE corp_code = ?
        ORDER BY disclosure_date DESC
        LIMIT ?
    """
    stmt_query = """
        SELECT corp_code, corp_name, year, quarter,
               revenue, operating_income, net_income,
               total_assets, total_debt, equity,
               operating_cashflow, roe, debt_ratio, operating_margin
        FROM financial_statement
        WHERE corp_code = ?
        ORDER BY year DESC, quarter DESC
        LIMIT ?
    """
    with sqlite3.connect(DISCLOSURE_DB) as con:
        con.row_factory = sqlite3.Row
        for cc, ticker in corp_to_ticker.items():
            # disclosure_local은 DART 8자리 corp_code 사용
            for r in con.execute(disc_query, (cc, per_corp)):
                disclosures.append({k: r[k] for k in r.keys()})
            # financial_statement는 KRX 6자리 ticker 사용 (컬럼명만 corp_code)
            if ticker:
                for r in con.execute(stmt_query, (ticker, statements_limit)):
                    statements.append({k: r[k] for k in r.keys()})
    return {"disclosures": disclosures, "statements": statements}


# --------------------------------------------------------------------------- #
#  price 시나리오 추출 (Python 상수)
# --------------------------------------------------------------------------- #
def extract_price_scenarios() -> list[dict]:
    """modules/price/quiz_data.QUIZ_LIST → 그대로 복사.

    price 모듈은 DB 없이 Python 상수로 데이터를 유지한다 (2026-04-22 기준 15건).
    """
    try:
        from modules.price.quiz_data import QUIZ_LIST
    except Exception as exc:  # pragma: no cover — 모듈 구조 변경 시 명시적 로그
        print(f"[WARN] quiz_data import 실패: {exc}", file=sys.stderr)
        return []
    return [dict(q) for q in QUIZ_LIST]


# --------------------------------------------------------------------------- #
#  JSON 직렬화 보조
# --------------------------------------------------------------------------- #
def _json_default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Unserializable: {type(obj).__name__}")


def _write_json(path: Path, payload: dict | list) -> int:
    """JSON 직렬화 후 파일에 쓰고 바이트 수 반환."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


# --------------------------------------------------------------------------- #
#  메인
# --------------------------------------------------------------------------- #
def main() -> int:
    INTEGRATION_DATA.mkdir(exist_ok=True)
    top50 = load_top50()
    corp_to_ticker = {
        row["corp_code"]: row.get("ticker", "") for row in top50 if row.get("corp_code")
    }
    corp_codes = set(corp_to_ticker.keys())
    tickers = {t for t in corp_to_ticker.values() if t}

    print(f"[INFO] top50 로드: {len(corp_codes)} 기업")

    eqs_rows = extract_financial(corp_codes)
    disc_payload = extract_disclosures(corp_to_ticker)
    scenarios = extract_price_scenarios()

    # 각 record에 ticker 필드 주입 (dashboard가 ticker 기준으로 join하기 위함)
    # financial·disclosure는 내부적으로 다른 식별자를 쓰므로, 공통 키로 통일
    eqs_rows = [
        {**r, "ticker": corp_to_ticker.get(r.get("corp_code"), "")} for r in eqs_rows
    ]
    disc_payload["disclosures"] = [
        {**d, "ticker": corp_to_ticker.get(d.get("corp_code"), "")}
        for d in disc_payload["disclosures"]
    ]
    # statements는 corp_code 컬럼이 이미 ticker (6자리)임 → 그대로 ticker 필드로 복제
    disc_payload["statements"] = [
        {**s, "ticker": s.get("corp_code", "")} for s in disc_payload["statements"]
    ]

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "top50_count": len(corp_codes),
        "coverage": {
            "financial": len(eqs_rows),
            "disclosure_companies": len(
                {d["corp_code"] for d in disc_payload["disclosures"]}
            ),
            "disclosure_rows": len(disc_payload["disclosures"]),
            "statement_companies": len(
                {s["corp_code"] for s in disc_payload["statements"]}
            ),
            "statement_rows": len(disc_payload["statements"]),
            "price_scenarios": len(scenarios),
            "price_scenarios_matching_top50": sum(
                1 for s in scenarios if s.get("ticker") in tickers
            ),
        },
    }

    size_eqs = _write_json(
        INTEGRATION_DATA / "eqs_summary.json",
        {"meta": meta, "data": eqs_rows},
    )
    size_disc = _write_json(
        INTEGRATION_DATA / "disclosures.json",
        {"meta": meta, **disc_payload},
    )
    size_price = _write_json(
        INTEGRATION_DATA / "price_scenarios.json",
        {"meta": meta, "data": scenarios},
    )

    print("[INFO] 추출 완료")
    print(
        f"  eqs_summary.json      : {size_eqs:>8,} bytes  ({meta['coverage']['financial']} rows)"
    )
    print(
        f"  disclosures.json      : {size_disc:>8,} bytes  ({meta['coverage']['disclosure_rows']} disc, {meta['coverage']['statement_rows']} stmt)"
    )
    print(
        f"  price_scenarios.json  : {size_price:>8,} bytes  ({meta['coverage']['price_scenarios']} scenarios, {meta['coverage']['price_scenarios_matching_top50']} matched)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
