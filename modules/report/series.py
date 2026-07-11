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

YEARS_LEN = 5


def is_complete(vals) -> bool:
    """5점 완결: 길이 5 + 전부 수치."""
    return (
        isinstance(vals, list)
        and len(vals) == YEARS_LEN
        and all(isinstance(x, (int, float)) for x in vals)
    )


def build_series(ticker: str) -> dict:
    """firm_json + fs_account + (Phase4)주석추출 → {series, incomplete_keys}.

    ⚠️ 현재는 스켈레톤: fs_account 적재(backfill) 후 실제 조립. 조립 규칙은 SOURCE_MAP.
    반환: {"series": {key: [5점]}, "incomplete": [키...], "years": [FY..]}
    """
    series: dict[str, list] = {}
    incomplete: list[str] = []

    # TODO(Phase 3 backfill): fs_account/firm_json 로드 후 SOURCE_MAP 따라 채움.
    #   1) A: firm_<ticker>.json 5개년 본표 → revenue·op·ni·cash·assets·debt·equity·ocf 등
    #   2) B: fs_account(ticker) account_id 매칭 → tax·oci·icf·capex·fin·div·buyback·dep·pretax·cogs·sgna·eps
    #   3) D: gross=revenue−cogs, tci=ni+oci (양쪽 완결 시)
    #   4) N: rnd·dsOp 는 Phase4 extract 결과 주입 (없으면 incomplete)
    for key in SOURCE_MAP:
        if not is_complete(series.get(key)):
            incomplete.append(key)

    return {"series": series, "incomplete": incomplete, "years": []}


if __name__ == "__main__":
    import sys

    t = sys.argv[1] if len(sys.argv) > 1 else "005930"
    r = build_series(t)
    print(
        f"[{t}] series 키 {len(r['series'])}/24, 미완성 {len(r['incomplete'])}: {r['incomplete']}"
    )
