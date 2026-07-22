"""series.py — S 시계열 24키 × 5점 조립 (코드가 채움, LLM 금지 D7).

소스 3층: ⓐ firm_*.json(본표 14필드×5년, 확보) ⓑ fs_account(fnlttSinglAcntAll 미확보분)
ⓒ 파생(gross=revenue−cogs, tci=ni+oci). 주석 추출 의존 키(rnd·dsOp 등)는 Phase 4 extract 후 주입.
5점 완결성 판정 → 미완성 키는 galaxy_<t>.json의 해당 dive five=skip 플래그로.

⚠️ fs_account account_id 매핑은 backfill(실데이터)에서 검증·보정. 아래 매핑표가 초안(§CLAUDE.md 정본).
"""

from __future__ import annotations

# S 24키 → 소스 전략 (A=firm_json / B=fs_account / D=derived / N=note추출[Phase4])
SOURCE_MAP: dict[str, dict] = {
    # 손익 9
    "revenue": {"src": "A|B", "acc": ["ifrs-full_Revenue"]},
    "cogs": {"src": "B", "acc": ["ifrs-full_CostOfSales"]},
    "gross": {"src": "D", "formula": "revenue - cogs"},
    "sgna": {"src": "B", "acc": ["dart_TotalSellingGeneralAdministrativeExpenses"]},
    "op": {
        "src": "A|B",
        "acc": [
            "dart_OperatingIncomeLoss",
            "ifrs-full_ProfitLossFromOperatingActivities",
        ],
    },
    "pretax": {"src": "B", "acc": ["ifrs-full_ProfitLossBeforeTax"]},
    "tax": {"src": "B", "acc": ["ifrs-full_IncomeTaxExpenseContinuingOperations"]},
    "ni": {"src": "A|B", "acc": ["ifrs-full_ProfitLoss"]},
    "oci": {"src": "B", "acc": ["ifrs-full_OtherComprehensiveIncome"]},
    # 현금흐름 6
    "ocf": {"src": "A|B", "acc": ["ifrs-full_CashFlowsFromUsedInOperatingActivities"]},
    "icf": {"src": "B", "acc": ["ifrs-full_CashFlowsFromUsedInInvestingActivities"]},
    "capex": {
        "src": "B",
        "acc": [
            "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"
        ],
    },
    "fin": {"src": "B", "acc": ["ifrs-full_CashFlowsFromUsedInFinancingActivities"]},
    "div": {
        "src": "B",
        "acc": ["ifrs-full_DividendsPaidClassifiedAsFinancingActivities"],
    },
    "buyback": {
        "src": "B",
        "acc": ["ifrs-full_PaymentsToAcquireOrRedeemEntitysShares"],
    },
    # 성격별/판관 2 (주석 의존)
    "dep": {"src": "B|N", "acc": ["ifrs-full_DepreciationAndAmortisationExpense"]},
    "rnd": {"src": "N", "note": "연구개발활동 / 성격별비용"},
    # BS 4
    "cash": {"src": "A|B", "acc": ["ifrs-full_CashAndCashEquivalents"]},
    "assets": {"src": "A|B", "acc": ["ifrs-full_Assets"]},
    "debt": {"src": "A|B", "acc": ["ifrs-full_Liabilities"]},
    "equity": {"src": "A|B", "acc": ["ifrs-full_Equity"]},
    # 파생·부문 3
    "dsOp": {"src": "N", "note": "부문정보(주30) — DS 영업이익"},
    "eps": {"src": "B", "acc": ["ifrs-full_BasicEarningsLossPerShare"]},
    "tci": {"src": "D", "formula": "ni + oci"},
}

# 재무제표 구분(sj_div) 우선순위 — 같은 account_id가 여러 표에 나올 때 '총계'가 있는 표를 고른다.
# ⚠️ SCE(자본변동표)는 자본을 구성요소별로 쪼갠 값이라 총계 조회에서 제외 (ProfitLoss·Equity 오염 방지).
SJ_PRIORITY: dict[str, list[str]] = {
    "revenue": ["IS", "CIS"], "cogs": ["IS", "CIS"], "sgna": ["IS", "CIS"],
    "op": ["IS", "CIS"], "pretax": ["IS", "CIS"], "tax": ["IS", "CIS"],
    "ni": ["IS", "CIS"], "eps": ["IS", "CIS"], "oci": ["CIS", "IS"],
    "ocf": ["CF"], "icf": ["CF"], "capex": ["CF"], "fin": ["CF"],
    "div": ["CF"], "buyback": ["CF"], "dep": ["CF", "IS"],
    "cash": ["BS"], "assets": ["BS"], "debt": ["BS"], "equity": ["BS"],
}

YEARS_LEN = 5


def is_complete(vals) -> bool:
    """5점 완결: 길이 5 + 전부 수치."""
    return (
        isinstance(vals, list)
        and len(vals) == YEARS_LEN
        and all(isinstance(x, (int, float)) for x in vals)
    )


import os
import sqlite3

_HERE = os.path.dirname(os.path.abspath(__file__))
_DB = os.path.join(_HERE, "data", "reports.db")
JO = 1_000_000_000_000  # 원 → 조 환산
WINDOW = 5  # 최근 5개년


def _load_fs(ticker: str, db_path: str = _DB) -> tuple[dict, list[int]]:
    """reports.db fs_account → {account_id: {fy: amount_won}} + 대상 연도(최근 5).

    report 모듈 자체 데이터(reports.db)만 사용 — firm_json(integration 소유)은 읽지 않는다(경계 단방향).
    """
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT sj_div, account_id, fiscal_year, amount FROM fs_account WHERE ticker=?",
        (ticker,),
    ).fetchall()
    con.close()
    by_acc: dict[tuple[str, str], dict[int, float]] = {}
    years: set[int] = set()
    for sj, acc, fy, amt in rows:
        if amt is None:
            continue
        by_acc.setdefault((sj, acc), {})[fy] = amt
        years.add(fy)
    fy_list = sorted(years)[-WINDOW:]
    return by_acc, fy_list


def _series_for(key: str, acc_ids: list[str], by_acc: dict, fy_list: list[int], *, div: float) -> list | None:
    """sj_div 우선순위 × account_id 후보 중 5개년 전부 채우는 첫 조합을 조(또는 원본÷div) 배열로.

    같은 account_id가 여러 표에 있을 때 SJ_PRIORITY로 총계 표를 골라 SCE 오염을 피한다.
    """
    sjs = SJ_PRIORITY.get(key, ["IS", "CIS", "CF", "BS"])
    for sj in sjs:
        for acc in acc_ids:
            yv = by_acc.get((sj, acc))
            if not yv:
                continue
            vals = [yv.get(fy) for fy in fy_list]
            if all(v is not None for v in vals):
                if div == 1:  # eps 등 원 단위 그대로
                    return [round(v) for v in vals]
                return [round(v / div, 1) for v in vals]
    return None


def build_series(ticker: str, db_path: str = _DB) -> dict:
    """fs_account(B) + 파생(D) → S 24키 × 5점(조 단위, eps만 원). N(rnd·dsOp)은 Phase4 extract 주입.

    반환: {"series": {key: [5점]}, "incomplete": [키...], "years": ["FY.."]}
    5점 완결 못한 키는 galaxy_<t>.json 해당 dive의 five=skip 대상.
    """
    by_acc, fy_list = _load_fs(ticker, db_path)
    series: dict[str, list] = {}

    # ⓑ B: fs_account 직접 매핑
    for key, spec in SOURCE_MAP.items():
        if spec["src"] == "D" or spec["src"] == "N":
            continue
        vals = _series_for(key, spec.get("acc", []), by_acc, fy_list, div=(1 if key == "eps" else JO))
        if vals is not None:
            series[key] = vals

    # ⓓ D: 파생 (양쪽 완결 시)
    if is_complete(series.get("revenue")) and is_complete(series.get("cogs")):
        series["gross"] = [round(r - c, 1) for r, c in zip(series["revenue"], series["cogs"])]
    if is_complete(series.get("ni")) and is_complete(series.get("oci")):
        series["tci"] = [round(n + o, 1) for n, o in zip(series["ni"], series["oci"])]

    # ⓝ N: rnd·dsOp 는 주석 추출(Phase4) 전까지 미완성
    incomplete = [k for k in SOURCE_MAP if not is_complete(series.get(k))]
    years = [f"FY{fy % 100:02d}" for fy in fy_list]
    return {"series": series, "incomplete": incomplete, "years": years}


if __name__ == "__main__":
    import sys

    t = sys.argv[1] if len(sys.argv) > 1 else "005930"
    r = build_series(t)
    done = 24 - len(r["incomplete"])
    print(f"[{t}] {r['years']}  완결 {done}/24, 미완성 {len(r['incomplete'])}: {r['incomplete']}")
