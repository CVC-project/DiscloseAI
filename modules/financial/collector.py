"""DART OpenAPI 수집기.

엔드포인트 (https://opendart.fss.or.kr/intro/main.do):
- corpCode.xml         — 전체 상장사 corp_code 매핑 (zip → CORPCODE.xml)
- fnlttSinglAcntAll    — 단일회사 전체 재무제표 (사업/반기/분기)
- fnlttCmpnyIndx       — 시장지표 (확장 여지)

Rate limit: 10,000건/일. 배치 호출 시 일별 사용량을 ``DART_DAILY_LIMIT``과
대조해 자동 sleep 처리(추후 추가 예정).

환경변수: ``DART_API_KEY`` (`.env`에서 로드, ``shared/config.py``).
"""

from __future__ import annotations

import io
import os
import time
import zipfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

import requests

from shared.config import DART_API_KEY

from .eqs.types import FirmPanel, FirmYear

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "https://opendart.fss.or.kr/api"
_TIMEOUT = 30
_USER_AGENT = "DiscloseAI/0.1 (financial collector)"

# 사업보고서(연간) — fnlttSinglAcntAll의 reprt_code
REPRT_ANNUAL = "11011"
REPRT_Q1 = "11013"
REPRT_HALF = "11012"
REPRT_Q3 = "11014"

# 연결재무제표 우선, 없으면 별도(개별)로 fallback
FS_DIV_CONSOLIDATED = "CFS"
FS_DIV_SEPARATE = "OFS"

# DART 계정ID(IFRS taxonomy) → FirmYear 필드 매핑.
# K-IFRS 표준 taxonomy 기준. DART 응답은 같은 항목이라도 (1) account_id 표준코드,
# (2) account_nm 한글명 둘 다 들고 있으므로 ID 우선 매칭 후 한글 fallback.
_ACCOUNT_ID_MAP: Dict[str, str] = {
    # 손익계산서
    "ifrs-full_Revenue": "revenue",
    "ifrs_Revenue": "revenue",
    # 금융업 수익 항목 — "매출액" 대신 이자/수수료/보험수익으로 기록됨.
    # collector가 첫 매칭만 사용하므로, revenue가 이미 잡혔으면 무시됨.
    "ifrs-full_RevenueFromInterest": "revenue",
    "ifrs-full_FeeAndCommissionIncome": "revenue",
    "ifrs-full_InsuranceRevenue": "revenue",
    "ifrs-full_CostOfSales": "cogs",
    "ifrs-full_GrossProfit": None,  # 직접 안 쓰지만 매칭표시용
    "dart_OperatingIncomeLoss": "operating_income",
    "ifrs-full_ProfitLoss": "net_income",
    "ifrs-full_DepreciationAndAmortisationExpense": "depreciation",
    # 재무상태표
    "ifrs-full_Assets": "total_assets",
    "ifrs-full_Liabilities": "total_liabilities",
    "ifrs-full_Equity": "total_equity",
    "ifrs-full_CurrentAssets": "current_assets",
    "ifrs-full_CurrentLiabilities": "current_liabilities",
    "ifrs-full_NoncurrentLiabilities": "long_term_debt",
    "ifrs-full_PropertyPlantAndEquipment": "ppe",
    "ifrs-full_TradeAndOtherCurrentReceivables": "accounts_receivable",
    # 현금흐름표
    "ifrs-full_CashFlowsFromUsedInOperatingActivities": "operating_cashflow",
    "ifrs-full_CashFlowsFromUsedInInvestingActivities": "investing_cashflow",
    "ifrs-full_CashFlowsFromUsedInFinancingActivities": "financing_cashflow",
}

# 한글명 fallback (account_nm). DART 표준 한글명 — 일부 기업이 영문 ID 누락 시 사용.
_ACCOUNT_NM_MAP: Dict[str, str] = {
    "수익(매출액)": "revenue",
    "매출액": "revenue",
    "영업수익": "revenue",
    "이자수익": "revenue",
    "수수료수익": "revenue",
    "보험수익": "revenue",
    "매출원가": "cogs",
    "영업이익": "operating_income",
    "영업이익(손실)": "operating_income",
    "당기순이익": "net_income",
    "당기순이익(손실)": "net_income",
    "감가상각비": "depreciation",
    "자산총계": "total_assets",
    "부채총계": "total_liabilities",
    "자본총계": "total_equity",
    "유동자산": "current_assets",
    "유동부채": "current_liabilities",
    "비유동부채": "long_term_debt",
    "유형자산": "ppe",
    "매출채권": "accounts_receivable",
    "영업활동현금흐름": "operating_cashflow",
    "영업활동으로 인한 현금흐름": "operating_cashflow",
    "투자활동현금흐름": "investing_cashflow",
    "투자활동으로 인한 현금흐름": "investing_cashflow",
    "재무활동현금흐름": "financing_cashflow",
    "재무활동으로 인한 현금흐름": "financing_cashflow",
}


class DartError(RuntimeError):
    """DART API 비정상 응답."""


# ---------------------------------------------------------------------------
# Low-level HTTP
# ---------------------------------------------------------------------------


def _require_key() -> str:
    if not DART_API_KEY:
        raise DartError("DART_API_KEY 미설정 — .env 또는 환경변수 확인")
    return DART_API_KEY


def _get(url: str, params: Optional[dict] = None) -> requests.Response:
    p = dict(params or {})
    p["crtfc_key"] = _require_key()
    r = requests.get(
        url, params=p, timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}
    )
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# corp_code 매핑 (캐시)
# ---------------------------------------------------------------------------


@dataclass
class CorpInfo:
    corp_code: str  # 8자리 DART 고유코드
    corp_name: str
    stock_code: Optional[str]  # 6자리 종목코드 (상장 안된 곳은 빈문자열)
    modify_date: str


_CORP_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
_CORP_CACHE_XML = os.path.join(_CORP_CACHE_DIR, "CORPCODE.xml")


def fetch_corp_codes(force_refresh: bool = False) -> List[CorpInfo]:
    """전체 상장사 corp_code 매핑 (CORPCODE.xml). 첫 호출 시 다운로드 후 캐시."""
    os.makedirs(_CORP_CACHE_DIR, exist_ok=True)
    if force_refresh or not os.path.exists(_CORP_CACHE_XML):
        r = _get(f"{_BASE}/corpCode.xml")
        # zip 응답
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            with zf.open("CORPCODE.xml") as fp:
                xml_bytes = fp.read()
        with open(_CORP_CACHE_XML, "wb") as fp:
            fp.write(xml_bytes)
    else:
        with open(_CORP_CACHE_XML, "rb") as fp:
            xml_bytes = fp.read()

    root = ET.fromstring(xml_bytes)
    out: List[CorpInfo] = []
    for el in root.findall("list"):
        out.append(
            CorpInfo(
                corp_code=(el.findtext("corp_code") or "").strip(),
                corp_name=(el.findtext("corp_name") or "").strip(),
                stock_code=(el.findtext("stock_code") or "").strip() or None,
                modify_date=(el.findtext("modify_date") or "").strip(),
            )
        )
    return out


def find_corp(name_or_stock: str) -> Optional[CorpInfo]:
    """기업명 또는 종목코드로 CorpInfo 1건 조회 (정확 일치 우선)."""
    needle = name_or_stock.strip()
    corps = fetch_corp_codes()
    # 종목코드 6자리 우선 매칭
    if needle.isdigit() and len(needle) == 6:
        for c in corps:
            if c.stock_code == needle:
                return c
    # 정확 일치
    for c in corps:
        if c.corp_name == needle:
            return c
    # 부분 일치 (상장사 한정)
    matches = [c for c in corps if c.stock_code and needle in c.corp_name]
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# 재무제표 수집 → FirmYear 변환
# ---------------------------------------------------------------------------


def _to_float(s: Optional[str]) -> Optional[float]:
    if not s or s in ("-", ""):
        return None
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _map_account(row: dict) -> Optional[str]:
    """API 응답 1행 → FirmYear 필드명. 매칭 안 되면 None."""
    aid = (row.get("account_id") or "").strip()
    if aid in _ACCOUNT_ID_MAP and _ACCOUNT_ID_MAP[aid]:
        return _ACCOUNT_ID_MAP[aid]
    nm = (row.get("account_nm") or "").strip()
    return _ACCOUNT_NM_MAP.get(nm)


def fetch_annual_financial(
    corp_code: str, year: int, fs_div: str = FS_DIV_CONSOLIDATED
) -> Optional[FirmYear]:
    """단일회사 단일연도 사업보고서(연간) → FirmYear.

    연결재무제표가 없으면 별도(OFS)로 자동 fallback.
    응답 status: '000' 정상 / '013' 데이터 없음 / 그 외 오류.
    """
    params = {
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": REPRT_ANNUAL,
        "fs_div": fs_div,
    }
    r = _get(f"{_BASE}/fnlttSinglAcntAll.json", params)
    data = r.json()
    status = data.get("status")
    if status == "013":  # 데이터 없음 → fallback 한 번
        if fs_div == FS_DIV_CONSOLIDATED:
            return fetch_annual_financial(corp_code, year, FS_DIV_SEPARATE)
        return None
    if status != "000":
        raise DartError(f"DART status={status} msg={data.get('message')}")

    fy = FirmYear(year=year)
    setattr(fy, "_fs_div", fs_div)  # 디버깅용 메타
    for row in data.get("list", []):
        field = _map_account(row)
        if not field:
            continue
        # thstrm_amount: 당기, frmtrm_amount: 전기, bfefrmtrm_amount: 전전기
        # 사업보고서니까 '당기' 사용
        v = _to_float(row.get("thstrm_amount"))
        if v is None:
            continue
        # 같은 필드가 여러 번 매칭되면 (CFS·OFS 혼합 등) 첫 값 우선
        if getattr(fy, field) is None:
            setattr(fy, field, v)
    return fy


def fetch_panel(
    corp_code: str,
    years: Iterable[int],
    *,
    corp_name: Optional[str] = None,
    industry_code: Optional[str] = None,
    sleep_sec: float = 0.1,
) -> FirmPanel:
    """다년도 재무 패널 수집.

    DART rate limit(10,000/일) 보호용 ``sleep_sec`` 기본 0.1초 = 초당 10건.
    """
    fys: List[FirmYear] = []
    for y in years:
        fy = fetch_annual_financial(corp_code, y)
        if fy is not None:
            fys.append(fy)
        time.sleep(sleep_sec)
    return FirmPanel(
        corp_code=corp_code,
        corp_name=corp_name,
        industry_code=industry_code,
        years=fys,
    )


def fetch_latest_report_url(corp_code: str) -> Optional[str]:
    """DART 최신 사업보고서 조회 URL 반환. 없으면 None."""
    try:
        from datetime import datetime

        bgn = f"{datetime.now().year - 2}0101"
        r = _get(
            f"{_BASE}/list.json",
            {
                "corp_code": corp_code,
                "bgn_de": bgn,
                "pblntf_ty": "A",
                "last_reprt_at": "Y",
                "page_count": 1,
            },
        )
        data = r.json()
        if data.get("status") == "000" and data.get("list"):
            rcept_no = data["list"][0]["rcept_no"]
            return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
    except Exception:  # noqa: BLE001
        pass
    return None
