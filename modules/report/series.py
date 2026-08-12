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
    # ⚠️ tax 파생 금지 규칙(V-105 ③ → 코드 승격 2026-08-04): `pretax − ni`로 역산하면
    #    IFRS5 중단영업 보유사에서 중단영업손익이 섞여 깨진다(CJ FY25 0.48 vs 실제 0.24조).
    #    tax는 반드시 계속영업 법인세비용 실계정에서만 회수한다 — 파생 폴백을 두지 않는다.
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
    # ⚠️ V-116 승격 — `rnd`는 주석 전용이 아니다. R&D 집약 업종은 **손익계산서 본표에
    #    `경상연구개발비` 실계정**을 둔다(원익IPS 240810: 총이익−판관비−R&D=영업이익 항등식이
    #    FY23·24·25 전부 0.00억 오차로 성립). 정답지 55사 중 **13사**가 IS/CIS 실계정 보유
    #    (8사는 5개년 전부) → 2회+ 규칙 충족. 없으면 종전대로 주석 추출(N) 소관.
    "rnd": {"src": "B|N", "acc": ["ifrs-full_ResearchAndDevelopmentExpense"],
            "note": "경상연구개발비 실계정 우선 · 없으면 연구개발활동/성격별비용 주석"},
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
    "rnd": ["IS", "CIS"],
}

YEARS_LEN = 5


def is_complete(vals) -> bool:
    """5점 완결: 길이 5 + 전부 수치."""
    return (
        isinstance(vals, list)
        and len(vals) == YEARS_LEN
        and all(isinstance(x, (int, float)) for x in vals)
    )


# ── 규모 적응형 반올림 (V-116, 2026-08-12 — KOSDAQ 첫 골든에서 승격) ──────────────
# 종전에는 조 단위 **1자리 고정**이었다. 대형 KOSPI(매출 100조대)에서는 문제가 없었으나,
# KOSDAQ 중형사에서는 서사가 통째로 뭉개진다 — 원익IPS 240810 실측:
#   revenue [1.2, 1.0, 0.7, 0.7, 0.9]  ← 실제 12,323 → 6,903 → 9,098억 (사이클 진폭 소실)
#   op      [0.2, 0.1, -0.0, 0.0, 0.1] ← 실제 1,641 → **-181(적자)** → 738억
# `-0.0`은 적자를 0으로 보이게 하고, tax·div·dep는 5개년이 전부 0.0이 된다.
# → 키마다 **최댓값 크기에 맞춰 유효숫자 ~3자리**를 유지한다. 대형주는 1자리 그대로라 무회귀.
# ⚠️ 기존 골든 JSON의 series는 정적이라 영향 없다(check_golden은 JSON만 읽는다).
#    `check_golden §18`은 series 마지막 값의 소수 자릿수를 그때그때 파생하므로 자릿수가 늘어도 정합.


# ── 표시 단위 (V-117, 리더 결정 2026-08-12 — "금액이 작으면 억으로 간다") ────────
# 조 단위는 대형 KOSPI 전용이다. 자산총계 1.16조인 원익IPS에서는 영업이익 738억이
# `0.074`가 돼 읽히지 않는다. → **자산총계 3조 미만이면 억 원**으로 적는다.
# 임계 3조 근거: 기존 골든 20본의 최소가 하이브 5.5조(다음이 크래프톤 9.4조)라
# 전 골든이 조를 유지한다(무회귀). 표시 단위는 `corp.unit_label`로 JSON에 실려
# 렌더러·`check_golden §18`이 함께 읽는다. `raw_mn`(백만원)은 단위와 무관하게 불변.
EOK = 100_000_000  # 원 → 억
UNIT_THRESHOLD_WON = 3_000_000_000_000  # 자산총계 3조 — 이 미만이면 억 표기


def pick_unit(assets_won: float | None) -> tuple[str, float]:
    """자산총계(원) → (unit_label, div). 판정 불가면 종전 조."""
    if assets_won is not None and abs(assets_won) < UNIT_THRESHOLD_WON:
        return "억 원", float(EOK)
    return "조 원", float(JO)


def _dec_for(vals, unit: str = "조 원") -> int:
    """표시 단위 배열에 적용할 소수 자릿수 — 유효숫자 ~3자리를 유지한다."""
    m = max((abs(v) for v in vals if v is not None), default=0.0)
    if unit == "억 원":
        # 억은 정수로 읽는 단위다. 1,000억 이상은 소수를 두지 않는다.
        return 0 if m >= 1000 else 1
    if m >= 10:
        return 1
    if m >= 1:
        return 2
    return 3


def _scale(vals: list, div: float) -> list:
    """원 단위 → 조(eps는 원). **반올림하지 않는다** — 파생키가 원값에서 계산되도록."""
    return [v / div for v in vals]


def _round_scaled(vals: list, *, is_eps: bool = False, unit: str = "조 원") -> list:
    """이미 조(또는 eps는 원)로 환산된 배열을 규모 적응형으로 반올림. -0.0은 0.0으로 정규화.

    ⚠️ 분기는 **불리언 플래그**로 한다 — `div == 1`로 가르면 `1.0 == 1`이 True라
       전 키가 eps 취급돼 정수로 뭉개진다(2026-08-12 실측).
    """
    if is_eps:  # 원 단위 그대로
        return [round(v) for v in vals]
    dec = _dec_for(vals, unit)
    out = []
    for v in vals:
        r = round(v, dec)
        out.append(0.0 if r == 0 else r)  # -0.0 → 0.0 (적자를 0으로 보이게 하지 않는다)
    return out


import os
import re
import sqlite3

_HERE = os.path.dirname(os.path.abspath(__file__))
_DB = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "shared", "data", "reports.db")
JO = 1_000_000_000_000  # 원 → 조 환산
WINDOW = 5  # 최근 5개년


def _load_fs(ticker: str, db_path: str = _DB) -> tuple[dict, list[int]]:
    """reports.db fs_account → {account_id: {fy: amount_won}} + 대상 연도(최근 5).

    report 모듈 자체 데이터(reports.db)만 사용 — firm_json(integration 소유)은 읽지 않는다(경계 단방향).
    """
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT sj_div, account_id, fiscal_year, amount, account_nm FROM fs_account WHERE ticker=?",
        (ticker,),
    ).fetchall()
    con.close()
    by_acc: dict = {}
    years: set[int] = set()
    for sj, acc, fy, amt, nm in rows:
        if amt is None:
            continue
        by_acc.setdefault((sj, acc), {})[fy] = amt
        # V-061 폴백용 계정명 인덱스 — 같은 이름이 여러 행이면 절댓값이 큰 쪽(총계)을 남긴다.
        idx = by_acc.setdefault(("__NAME__", sj), {}).setdefault(nm or "", {})
        if fy not in idx or abs(amt) > abs(idx[fy]):
            idx[fy] = amt
        years.add(fy)
    fy_list = sorted(years)[-WINDOW:]
    return by_acc, fy_list


def _series_for(key: str, acc_ids: list[str], by_acc: dict, fy_list: list[int], *, div: float) -> list | None:
    """sj_div 우선순위 × account_id 후보 중 5개년 전부 채우는 첫 조합을 조(또는 원본÷div) 배열로.

    같은 account_id가 여러 표에 있을 때 SJ_PRIORITY로 총계 표를 골라 SCE 오염을 피한다.
    ⚠️ 한 account_id로 5개년이 안 채워지면 _merge_per_year(V-061 폴백)가 이어받는다.
    """
    sjs = SJ_PRIORITY.get(key, ["IS", "CIS", "CF", "BS"])
    for sj in sjs:
        for acc in acc_ids:
            yv = by_acc.get((sj, acc))
            if not yv:
                continue
            vals = [yv.get(fy) for fy in fy_list]
            if all(v is not None for v in vals):
                return _scale(vals, div)  # 반올림은 build_series가 파생 후 일괄
    return None


# ── V-061 per-year 병합 폴백 (5회+ 반복 패턴의 코드 승격, 2026-08-04) ────────────────
# 증상: 같은 계정이 연도마다 account_id·계정명이 갈려 단일 키로는 5점이 안 채워진다.
#   실측 변이 — 표준코드 도입 시점 변경('-표준계정코드 미사용-' → 'ifrs-full_…', 이마트 CF 3활동),
#   계정명 공백·표현 변경('영업활동 현금흐름'↔'영업활동현금흐름'·'배당금의 지급'↔'배당금지급'),
#   한글 가운뎃점 변이('자산ㆍ부채의변동'), 연도별 부호 반전(capex·div).
# 처방: account_id 후보 + 계정명 정규식 후보로 **연도별로 따로** 값을 회수해 병합한다.
#   (V-077 SKT·V-102 현대제철·V-104 S-Oil·V-105 CJ·V-107 이마트에서 수기로 하던 작업)
ALT_NAME: dict[str, str] = {
    "ocf": r"^영업활동(으로부터의|으로인한)?\s*(순)?현금(흐름|유입|유출)",
    "icf": r"^투자활동(으로부터의|으로인한)?\s*(순)?현금(흐름|유입|유출)",
    "fin": r"^재무활동(으로부터의|으로인한)?\s*(순)?현금(흐름|유입|유출)",
    "oci": r"^(당기\s*)?(세후\s*)?기타포괄손익$|^총\s*기타포괄손익$|^당기\s*세후\s*기타포괄손익$",
    # 대한항공 003490 — FY21~23은 유형자산과 투자부동산을 한 줄로(`유형자산 및 투자부동산의 취득`),
    # FY24~25는 `유형자산의 취득`으로 갈린다. 회사가 스스로 묶어 공시한 설비투자 라인이라 병합이 정당.
    "capex": r"유형자산(\s*및\s*투자부동산)?의?\s*취득",
    "div": r"^배당금(의)?\s*지급$",
    "sgna": r"^판매비와?\s*(일반)?관리비$",
    # ⚠️ `계속영업기본주당이익`은 **그 해에 중단영업 EPS가 없거나 0일 때만** 총 EPS와 같다.
    #    한화에어로 012450 실측: FY22 총 3,964 = 계속 3,223 + 중단 741 — 섞으면 기준 혼용이 된다
    #    (V-105 ③ `pretax−ni` 파생과 같은 사고 계열). 판정은 _eps_basis_ok()가 연도별로 한다.
    "eps": r"^(계속영업\s*)?기본주당(순)?이익",
    "dep": r"감가상각비",
    # 원익IPS 240810 — FY21~23은 `-표준계정코드 미사용-`, FY24~25는 `ifrs-full_ResearchAndDevelopmentExpense`로
    # account_id가 갈린다(V-061 변이의 전형). ⚠️ **앵커 고정 필수** — 앵커를 풀면
    # `정부보조금(연구개발비)`·`연구개발비환입` 같은 구성·조정 항목이 본계정을 밀어낸다.
    "rnd": r"^(경상)?연구개발비$|^연구개발비용$|^경상개발비$",
    # 크래프톤 259960 — 게임·플랫폼형은 최상단 계정명이 `매출액`이 아니라 `영업수익`이고,
    # FY21·22는 `-표준계정코드 미사용-`, FY23~25는 `ifrs-full_Revenue`로 account_id가 갈린다.
    # ⚠️ 앵커 고정(`^영업수익$`)이 필수 — `기타영업수익`·`보험영업수익`(금융·보험 스코프아웃사)에
    #    걸리면 최상단이 아닌 구성 항목이 매출로 둔갑한다. 전 티커 before/after 실측(55사):
    #    035720 카카오 None→[5.9,6.8,7.6,7.9,8.1] · 259960 None→[1.9,1.9,1.9,2.7,3.3], 나머지 53사 변화 0.
    "revenue": r"^영업수익$",
}
# 계속영업 EPS 채택 가드 — 중단영업 기본주당이익이 그 해에 실재하고 0이 아니면 거부(기준 혼용 차단).
_EPS_CONT = re.compile(r"^계속영업\s*기본주당")
_EPS_DISC = re.compile(r"^중단영업\s*기본주당")


def _eps_basis_ok(nm: str, fy: int, by_acc: dict, sjs: list[str]) -> bool:
    """계속영업 EPS 계정명이면, 그 해 중단영업 EPS가 없거나 0일 때만 총 EPS로 인정한다."""
    if not _EPS_CONT.search(nm):
        return True
    for sj in sjs:
        for other, yv in (by_acc.get(("__NAME__", sj)) or {}).items():
            if _EPS_DISC.search(other) and yv.get(fy):
                return False
    return True
# 부호가 연도마다 뒤집히는 키(유출을 양수/음수로 번갈아 적는 회사) — 절댓값으로 정규화.
ABS_KEYS = {"capex", "div", "buyback"}


def _merge_per_year(key: str, acc_ids: list[str], by_acc: dict, fy_list: list[int], *, div: float):
    """연도별로 account_id 후보 → 계정명 정규식 후보 순으로 값을 회수해 5점을 병합(V-061)."""
    import re as _re

    sjs = SJ_PRIORITY.get(key, ["IS", "CIS", "CF", "BS"])
    pat = _re.compile(ALT_NAME[key]) if key in ALT_NAME else None
    out: list = []
    for fy in fy_list:
        got = None
        for sj in sjs:
            for acc in acc_ids:
                v = (by_acc.get((sj, acc)) or {}).get(fy)
                if v is not None:
                    got = v
                    break
            if got is not None:
                break
        if got is None and pat is not None:
            # 계정명 폴백 — _load_fs가 넣어 둔 이름 인덱스에서 회수(공백 제거본으로도 매칭)
            cands = []
            for sj in sjs:
                for nm, yv in (by_acc.get(("__NAME__", sj)) or {}).items():
                    if pat.search(nm) or pat.search(nm.replace(" ", "")):
                        if key == "eps" and not _eps_basis_ok(nm, fy, by_acc, sjs):
                            continue  # 계속영업 EPS인데 그 해 중단영업 EPS가 실재 — 기준 혼용 차단
                        v = yv.get(fy)
                        if v is not None:
                            cands.append(v)
            if cands:
                got = max(cands, key=abs)
        if got is None:
            return None
        out.append(got)
    if key in ABS_KEYS:
        out = [abs(v) for v in out]
    return _scale(out, div)  # 반올림은 build_series가 파생 후 일괄


def build_series(ticker: str, db_path: str = _DB, unit: str | None = None) -> dict:
    """fs_account(B) + 파생(D) → S 24키 × 5점(조 단위, eps만 원). N(rnd·dsOp)은 Phase4 extract 주입.

    반환: {"series": {key: [5점]}, "incomplete": [키...], "years": ["FY.."]}
    5점 완결 못한 키는 galaxy_<t>.json 해당 dive의 five=skip 대상.
    """
    by_acc, fy_list = _load_fs(ticker, db_path)
    # V-117 — 표시 단위 결정(자산총계 기준). 호출자가 unit을 주면 그것을 따른다.
    _assets = None
    for _sj in ("BS",):
        _yv = by_acc.get((_sj, "ifrs-full_Assets")) or {}
        if fy_list and fy_list[-1] in _yv:
            _assets = _yv[fy_list[-1]]
    if unit is None:
        unit, div_unit = pick_unit(_assets)
    else:
        div_unit = float(EOK) if unit == "억 원" else float(JO)
    series: dict[str, list] = {}

    # ⓑ B: fs_account 직접 매핑
    for key, spec in SOURCE_MAP.items():
        if spec["src"] == "D" or spec["src"] == "N":
            continue
        _div = 1 if key == "eps" else div_unit
        vals = _series_for(key, spec.get("acc", []), by_acc, fy_list, div=_div)
        if vals is None:  # V-061 폴백 — 연도별 account_id·계정명 변이를 병합
            vals = _merge_per_year(key, spec.get("acc", []), by_acc, fy_list, div=_div)
        if vals is not None:
            series[key] = vals

    # ⓓ D: 파생 (양쪽 완결 시) — ⚠️ **반올림 전 원값**에서 계산한다(V-116).
    #    이미 반올림된 배열끼리 빼면 오차가 누적돼 실계정과 어긋난다(전 골든 11본 부채, §18 주석).
    if is_complete(series.get("revenue")) and is_complete(series.get("cogs")):
        series["gross"] = [r - c for r, c in zip(series["revenue"], series["cogs"])]
    if is_complete(series.get("ni")) and is_complete(series.get("oci")):
        series["tci"] = [n + o for n, o in zip(series["ni"], series["oci"])]

    # ⓡ 반올림 일괄 적용 — 키마다 규모에 맞춘 자릿수(V-116)
    for key, vals in list(series.items()):
        series[key] = _round_scaled(vals, is_eps=(key == "eps"), unit=unit)

    # ⓝ N: rnd·dsOp 는 주석 추출(Phase4) 전까지 미완성
    incomplete = [k for k in SOURCE_MAP if not is_complete(series.get(k))]
    years = [f"FY{fy % 100:02d}" for fy in fy_list]
    return {"series": series, "incomplete": incomplete, "years": years,
            "unit_label": unit, "unit_div": div_unit}


if __name__ == "__main__":
    import sys

    t = sys.argv[1] if len(sys.argv) > 1 else "005930"
    r = build_series(t)
    done = 24 - len(r["incomplete"])
    print(f"[{t}] {r['years']}  단위 {r['unit_label']}  완결 {done}/24, "
          f"미완성 {len(r['incomplete'])}: {r['incomplete']}")
