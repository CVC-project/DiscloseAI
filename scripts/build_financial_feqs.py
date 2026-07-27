"""Build financial-industry F-EQS and apply it to the top-company EQS export."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.eqs.financial_feqs import (  # noqa: E402
    F_MODULE_LABELS,
    CAGR,
    FinancialModuleScore,
    dps_continuity_score,
    grade,
    percentile_profile,
    percentile_score,
    weighted_average,
)


DEFAULT_PANELS = ROOT / "modules/financial/data/remote_eqs_cache/panels_2021_2025.json"
DEFAULT_CORP_XML = ROOT / "modules/financial/data/remote_eqs_cache/CORPCODE.xml"
DEFAULT_DIVIDENDS = ROOT / "modules/financial/data/financial_dividends_yfinance.json"
DEFAULT_FEQS = ROOT / "modules/financial/data/financial_feqs_scores.json"
DEFAULT_CALIBRATION = ROOT / "modules/financial/data/financial_feqs_calibration.json"
DEFAULT_INPUTS = ROOT / "modules/financial/data/financial_feqs_inputs.json"
DEFAULT_REPORT = ROOT / "modules/financial/data/financial_feqs_missing_report.json"
DEFAULT_EQS_DATA = ROOT / "modules/financial/data/eqs_data.json"
DEFAULT_DOSSIER_DATA = ROOT / "integration/dossier/data"

SCREEN_FINANCIAL_CORP_CODES = {
    "00688996",  # KB금융
    "00126256",  # 삼성생명
    "00382199",  # 신한지주
    "00111722",  # 미래에셋증권
    "00547583",  # 하나금융지주
    "01350869",  # 우리금융지주
    "00139214",  # 삼성화재
    "00860332",  # 메리츠금융지주
}

NAMED_FINANCIAL_HOLDINGS = {
    "KB금융",
    "신한지주",
    "하나금융지주",
    "우리금융지주",
    "메리츠금융지주",
    "한국금융지주",
    "JB금융지주",
    "iM금융지주",
    "BNK금융지주",
}


def _num(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ratio(numerator, denominator):
    numerator = _num(numerator)
    denominator = _num(denominator)
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def load_panels(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("panels", [])


def is_financial_panel(panel: dict) -> bool:
    code = str(panel.get("industry_code") or "")
    name = str(panel.get("corp_name") or "")
    if code.startswith(("641", "642", "65", "661", "662")):
        return True
    if code.startswith("649"):
        if name in NAMED_FINANCIAL_HOLDINGS:
            return True
        finance_keywords = (
            "금융",
            "은행",
            "증권",
            "보험",
            "카드",
            "캐피탈",
            "인베스트",
            "벤처",
            "투자",
            "스팩",
            "리츠",
        )
        return any(keyword in name for keyword in finance_keywords)
    return False


def peer_group(panel: dict) -> str:
    code = str(panel.get("industry_code") or "")
    name = str(panel.get("corp_name") or "")
    if "금융지주" in name or name in NAMED_FINANCIAL_HOLDINGS:
        return "bank_holding"
    if code.startswith("641") or code.startswith("642"):
        return "bank"
    if code.startswith("65"):
        return "insurance"
    if code.startswith("661") or "증권" in name:
        return "securities"
    if "카드" in name:
        return "card"
    if "캐피탈" in name or "투자" in name or "인베스트" in name or "벤처" in name:
        return "capital_investment"
    if "스팩" in name:
        return "spac"
    if "리츠" in name:
        return "reit"
    if code.startswith("66"):
        return "financial_service"
    return "other_financial"


def load_corp_stock_map(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    result: dict[str, str] = {}
    for item in root.iter("list"):
        corp_code = (item.findtext("corp_code") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        if corp_code and stock_code:
            result[corp_code] = stock_code.zfill(6)
    return result


def _fetch_one_dividend(ticker: str, start_year: int, end_year: int) -> dict:
    import yfinance as yf

    for suffix in (".KS", ".KQ"):
        symbol = f"{ticker}{suffix}"
        stock = yf.Ticker(symbol)
        history = stock.history(
            start=f"{start_year}-01-01",
            end=f"{end_year + 1}-01-10",
            auto_adjust=False,
            actions=True,
        )
        if history.empty:
            continue
        dividends = {year: 0.0 for year in range(start_year, end_year + 1)}
        if "Dividends" in history.columns:
            for date, value in history["Dividends"].items():
                year = int(date.year)
                if start_year <= year <= end_year:
                    dividends[year] = dividends.get(year, 0.0) + float(value or 0.0)
        yields: dict[int, float] = {}
        for year in range(start_year, end_year + 1):
            yearly = history[history.index.year == year]
            if yearly.empty:
                continue
            close = float(yearly["Close"].dropna().iloc[-1]) if not yearly["Close"].dropna().empty else 0.0
            dps = dividends.get(year, 0.0)
            yields[year] = dps / close if close > 0 else 0.0
        return {
            "ticker": ticker,
            "symbol": symbol,
            "dps_by_year": dividends,
            "dividend_yield_by_year": yields,
            "status": "ok",
        }
    return {
        "ticker": ticker,
        "symbol": None,
        "dps_by_year": {},
        "dividend_yield_by_year": {},
        "status": "no_price_history",
    }


def collect_dividends(
    financial_panels: list[dict],
    corp_stock: dict[str, str],
    path: Path,
    start_year: int,
    end_year: int,
) -> dict[str, dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    records: dict[str, dict] = {}
    for idx, panel in enumerate(financial_panels, 1):
        corp_code = panel["corp_code"]
        ticker = corp_stock.get(corp_code)
        if not ticker:
            records[corp_code] = {"status": "no_ticker", "ticker": None}
            continue
        try:
            records[corp_code] = _fetch_one_dividend(ticker, start_year, end_year)
        except Exception as exc:  # pragma: no cover - network quality depends on provider
            records[corp_code] = {"status": f"error:{type(exc).__name__}", "ticker": ticker}
        if idx % 25 == 0:
            print(f"dividend fetch {idx}/{len(financial_panels)}")
            path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def metric_inputs(panel: dict, dividends: dict | None) -> dict:
    years = sorted(panel.get("years", []), key=lambda item: item.get("year") or 0)
    last = years[-1] if years else {}
    roe_values = [(int(y["year"]), _ratio(y.get("net_income"), y.get("total_equity"))) for y in years]
    ni_to_oi_values = [(int(y["year"]), _ratio(y.get("net_income"), y.get("operating_income"))) for y in years]
    equity_values = [(int(y["year"]), _num(y.get("total_equity"))) for y in years if _num(y.get("total_equity")) is not None]
    div_yields = {}
    dps = {}
    if dividends:
        div_yields = {int(k): float(v) for k, v in (dividends.get("dividend_yield_by_year") or {}).items()}
        dps = {int(k): float(v) for k, v in (dividends.get("dps_by_year") or {}).items()}

    start_equity = equity_values[-3][1] if len(equity_values) >= 3 else (equity_values[0][1] if equity_values else None)
    end_equity = equity_values[-1][1] if equity_values else None
    cagr_years = equity_values[-1][0] - equity_values[-3][0] if len(equity_values) >= 3 else 0
    return {
        "corp_code": panel["corp_code"],
        "corp_name": panel.get("corp_name"),
        "industry_code": panel.get("industry_code"),
        "peer_group": peer_group(panel),
        "year_count": len(years),
        "f1_yield_raw": weighted_average(sorted(div_yields.items())),
        "f1_dps_score": dps_continuity_score(dps),
        "f2_roe_raw": weighted_average(roe_values),
        "f3_equity_ratio_raw": _ratio(last.get("total_equity"), last.get("total_assets")),
        "f4_ni_to_oi_raw": weighted_average(ni_to_oi_values),
        "f5_equity_cagr_raw": CAGR(start_equity, end_equity, cagr_years),
        "dividend_status": (dividends or {}).get("status"),
    }


def profile_for_metric(inputs: list[dict], key: str, group: str) -> dict | None:
    group_values = [row[key] for row in inputs if row["peer_group"] == group and row.get(key) is not None]
    if key == "f3_equity_ratio_raw" and group == "bank_holding":
        if len(group_values) >= 5:
            return percentile_profile(group_values)
        bank_values = [
            row[key]
            for row in inputs
            if row["peer_group"] in {"bank_holding", "bank"} and row.get(key) is not None
        ]
        return percentile_profile(bank_values)
    if len(group_values) >= 20:
        return percentile_profile(group_values)
    return percentile_profile([row[key] for row in inputs if row.get(key) is not None])


def build_scores(inputs: list[dict]) -> tuple[list[dict], dict]:
    metric_keys = {
        "F1_yield": "f1_yield_raw",
        "F2": "f2_roe_raw",
        "F3": "f3_equity_ratio_raw",
        "F4": "f4_ni_to_oi_raw",
        "F5": "f5_equity_cagr_raw",
    }
    groups = sorted({row["peer_group"] for row in inputs})
    calibration: dict[str, dict] = {}
    for group in groups:
        calibration[group] = {metric: profile_for_metric(inputs, key, group) for metric, key in metric_keys.items()}

    results = []
    for row in inputs:
        profiles = calibration[row["peer_group"]]
        yield_score = percentile_score(row.get("f1_yield_raw"), profiles["F1_yield"])
        dps_score = row.get("f1_dps_score")
        if yield_score is None and dps_score is None:
            f1 = None
        elif yield_score is None:
            f1 = round(float(dps_score), 1)
        elif dps_score is None:
            f1 = round(float(yield_score), 1)
        else:
            f1 = round(yield_score * 0.7 + float(dps_score) * 0.3, 1)
        modules = [
            FinancialModuleScore("F1", f1, row.get("f1_yield_raw"), f"3년 가중평균 배당수익률과 DPS 유지·성장 점수를 금융업 안에서 비교"),
            FinancialModuleScore("F2", percentile_score(row.get("f2_roe_raw"), profiles["F2"]), row.get("f2_roe_raw"), "3년 가중평균 ROE를 금융업 동료와 비교"),
            FinancialModuleScore("F3", percentile_score(row.get("f3_equity_ratio_raw"), profiles["F3"]), row.get("f3_equity_ratio_raw"), "최근 자본총계/자산총계로 손실 완충력을 비교"),
            FinancialModuleScore("F4", percentile_score(row.get("f4_ni_to_oi_raw"), profiles["F4"]), row.get("f4_ni_to_oi_raw"), "순이익/영업이익 비율로 영업이익이 최종 이익으로 남는 정도를 비교"),
            FinancialModuleScore("F5", percentile_score(row.get("f5_equity_cagr_raw"), profiles["F5"]), row.get("f5_equity_cagr_raw"), "최근 자본총계 CAGR로 주주의 몫 성장성을 비교"),
        ]
        scores = [module.score for module in modules if module.score is not None]
        total = round(sum(scores) / len(scores), 1) if scores else None
        results.append(
            {
                "corp_code": row["corp_code"],
                "corp_name": row.get("corp_name"),
                "industry_code": row.get("industry_code"),
                "peer_group": row["peer_group"],
                "year_count": row.get("year_count"),
                "total": total,
                "grade": grade(total),
                "modules": [module.__dict__ for module in modules],
                "method": "feqs_v1_financial_peer_percentile_2021_2025",
                "missing_modules": [module.name for module in modules if module.score is None],
            }
        )
    return results, calibration


def _module_payload(result: dict) -> dict[str, dict]:
    payload = {}
    for module in result["modules"]:
        payload[module["name"]] = {
            "label": F_MODULE_LABELS[module["name"]],
            "score": module["score"],
            "note": module["note"],
            "weight": 1.0,
        }
    return payload


def _module_list(result: dict) -> list[dict]:
    return [
        {
            "name": module["name"],
            "score": module["score"],
            "raw": module.get("raw"),
            "note": module["note"],
        }
        for module in result["modules"]
    ]


def apply_to_eqs_data(path: Path, results: list[dict]) -> list[str]:
    result_by_code = {row["corp_code"]: row for row in results}
    rows = json.loads(path.read_text(encoding="utf-8"))
    applied = []
    for row in rows:
        corp_code = row.get("corp_code")
        if corp_code not in SCREEN_FINANCIAL_CORP_CODES:
            continue
        result = result_by_code.get(corp_code)
        if not result:
            continue
        row["modules"] = _module_payload(result)
        row["total"] = result["total"]
        row["grade"] = result["grade"]
        row["eqs_method"] = result["method"]
        row["eqs_excluded"] = []
        row["eqs_profile_note"] = (
            "금융사는 일반기업과 재무제표 구조가 달라 별도 기준으로 평가합니다. "
            "배당, ROE, 자본 여력, 이익 전환, 자본 성장성을 금융업 안에서 비교합니다."
        )
        applied.append(f"{row.get('name')}({row.get('stock_code')}): {result['total']} {result['grade']}")
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return applied


def apply_to_dossier(path: Path, results: list[dict], corp_stock: dict[str, str]) -> list[str]:
    result_by_code = {row["corp_code"]: row for row in results}
    applied = []
    for corp_code in SCREEN_FINANCIAL_CORP_CODES:
        result = result_by_code.get(corp_code)
        ticker = corp_stock.get(corp_code)
        if not result or not ticker:
            continue
        for prefix in ("firm", "business"):
            file_path = path / f"{prefix}_{ticker}.json"
            if not file_path.exists():
                continue
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if prefix == "firm":
                payload["eqs"] = {
                    "total": result["total"],
                    "grade": result["grade"],
                    "excluded": [],
                    "modules": _module_list(result),
                    "method": result["method"],
                    "profile_note": (
                        "금융사는 일반기업과 재무제표 구조가 달라 별도 기준으로 평가합니다. "
                        "배당, ROE, 자본 여력, 이익 전환, 자본 성장성을 금융업 안에서 비교합니다."
                    ),
                }
            else:
                payload["total"] = result["total"]
                payload["grade"] = result["grade"]
                payload["modules"] = _module_payload(result)
                payload["eqs_method"] = result["method"]
                payload["eqs_profile_note"] = (
                    "금융사는 일반기업과 재무제표 구조가 달라 별도 기준으로 평가합니다. "
                    "배당, ROE, 자본 여력, 이익 전환, 자본 성장성을 금융업 안에서 비교합니다."
                )
            file_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        applied.append(ticker)
    return applied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panels", type=Path, default=DEFAULT_PANELS)
    parser.add_argument("--corp-xml", type=Path, default=DEFAULT_CORP_XML)
    parser.add_argument("--dividends", type=Path, default=DEFAULT_DIVIDENDS)
    parser.add_argument("--scores", type=Path, default=DEFAULT_FEQS)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--eqs-data", type=Path, default=DEFAULT_EQS_DATA)
    parser.add_argument("--dossier-data", type=Path, default=DEFAULT_DOSSIER_DATA)
    parser.add_argument("--skip-dividend-fetch", action="store_true")
    args = parser.parse_args()

    panels = load_panels(args.panels)
    financial_panels = [panel for panel in panels if is_financial_panel(panel)]
    corp_stock = load_corp_stock_map(args.corp_xml)
    if args.skip_dividend_fetch:
        dividends = json.loads(args.dividends.read_text(encoding="utf-8")) if args.dividends.exists() else {}
    else:
        dividends = collect_dividends(financial_panels, corp_stock, args.dividends, 2021, 2025)

    inputs = [metric_inputs(panel, dividends.get(panel["corp_code"])) for panel in financial_panels]
    results, calibration = build_scores(inputs)
    missing_report = {
        "financial_panel_count": len(financial_panels),
        "scored_count": sum(1 for row in results if row["total"] is not None),
        "dividend_status": {},
        "missing_modules": {},
    }
    for row in inputs:
        status = row.get("dividend_status") or "missing"
        missing_report["dividend_status"][status] = missing_report["dividend_status"].get(status, 0) + 1
    for row in results:
        for module in row.get("missing_modules", []):
            missing_report["missing_modules"][module] = missing_report["missing_modules"].get(module, 0) + 1

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "feqs_v1_financial_peer_percentile_2021_2025",
        "results": results,
    }
    args.scores.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.calibration.write_text(json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    args.inputs.write_text(json.dumps(inputs, ensure_ascii=False, indent=2), encoding="utf-8")
    args.report.write_text(json.dumps(missing_report, ensure_ascii=False, indent=2), encoding="utf-8")
    applied = apply_to_eqs_data(args.eqs_data, results)
    dossier_applied = apply_to_dossier(args.dossier_data, results, corp_stock)
    print(f"financial panels: {len(financial_panels)}")
    print(f"scored: {missing_report['scored_count']}")
    print(f"screen applied: {len(applied)}")
    print(f"dossier applied: {len(dossier_applied)}")
    for item in applied:
        print(f"  {item}")
    print(f"scores: {args.scores}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
