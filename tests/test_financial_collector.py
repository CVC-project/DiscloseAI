"""DART collector — HTTP는 unittest.mock으로 차단.

실제 DART 호출은 rate limit(10,000/일)과 키 노출 위험이 있어 CI에서 부적절.
계정과목 매핑/파싱/fallback 로직만 검증.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.financial import collector
from modules.financial.collector import (
    CorpInfo,
    DartError,
    fetch_annual_financial,
    _map_account,
    _to_float,
    REPRT_ANNUAL,
    FS_DIV_CONSOLIDATED,
    FS_DIV_SEPARATE,
)

# ---------- _to_float ----------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,234,567", 1234567.0),
        ("-500", -500.0),
        ("0", 0.0),
        ("", None),
        ("-", None),
        (None, None),
    ],
)
def test_to_float_parses_dart_amount_strings(raw, expected):
    assert _to_float(raw) == expected


# ---------- _map_account ----------


def test_map_account_prefers_account_id():
    row = {"account_id": "ifrs-full_Revenue", "account_nm": "다른이름"}
    assert _map_account(row) == "revenue"


def test_map_account_falls_back_to_korean_name():
    row = {"account_id": "ifrs-full_Unknown", "account_nm": "영업이익"}
    assert _map_account(row) == "operating_income"


def test_map_account_returns_none_for_unknown():
    assert _map_account({"account_id": "X", "account_nm": "처음보는항목"}) is None


# ---------- fetch_annual_financial (HTTP mocked) ----------


def _mock_resp(payload: dict) -> MagicMock:
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_fetch_annual_financial_maps_into_firm_year():
    payload = {
        "status": "000",
        "list": [
            {"account_id": "ifrs-full_Revenue", "thstrm_amount": "1,000,000"},
            {"account_id": "dart_OperatingIncomeLoss", "thstrm_amount": "120,000"},
            {"account_id": "ifrs-full_ProfitLoss", "thstrm_amount": "80,000"},
            {"account_id": "ifrs-full_Assets", "thstrm_amount": "5,000,000"},
            {
                "account_id": "ifrs-full_CashFlowsFromUsedInOperatingActivities",
                "thstrm_amount": "150,000",
            },
            {
                "account_id": "ifrs-full_TradeAndOtherCurrentReceivables",
                "thstrm_amount": "300,000",
            },
        ],
    }
    with patch.object(collector, "_get", return_value=_mock_resp(payload)) as m:
        fy = fetch_annual_financial("00126380", 2024)
    assert fy is not None
    assert fy.year == 2024
    assert fy.revenue == 1_000_000
    assert fy.operating_income == 120_000
    assert fy.net_income == 80_000
    assert fy.total_assets == 5_000_000
    assert fy.operating_cashflow == 150_000
    assert fy.accounts_receivable == 300_000
    # 호출된 파라미터에 reprt_code/fs_div가 들어갔는지
    args, kwargs = m.call_args
    params = args[1] if len(args) > 1 else kwargs.get("params")
    assert params["reprt_code"] == REPRT_ANNUAL
    assert params["fs_div"] == FS_DIV_CONSOLIDATED


def test_fetch_annual_financial_falls_back_to_separate_when_consolidated_missing():
    """status=013(데이터 없음)이면 OFS(별도)로 자동 재시도."""
    cfs_payload = {"status": "013", "message": "조회된 데이터가 없습니다."}
    ofs_payload = {
        "status": "000",
        "list": [{"account_id": "ifrs-full_Revenue", "thstrm_amount": "999"}],
    }
    responses = [_mock_resp(cfs_payload), _mock_resp(ofs_payload)]
    with patch.object(collector, "_get", side_effect=responses):
        fy = fetch_annual_financial("123", 2024)
    assert fy is not None
    assert fy.revenue == 999


def test_fetch_annual_financial_returns_none_when_both_missing():
    miss = {"status": "013"}
    with patch.object(
        collector, "_get", side_effect=[_mock_resp(miss), _mock_resp(miss)]
    ):
        fy = fetch_annual_financial("123", 2024)
    assert fy is None


def test_fetch_annual_financial_raises_on_bad_status():
    with patch.object(
        collector,
        "_get",
        return_value=_mock_resp({"status": "020", "message": "한도 초과"}),
    ):
        with pytest.raises(DartError):
            fetch_annual_financial("123", 2024)


def test_fetch_annual_financial_skips_unknown_accounts():
    payload = {
        "status": "000",
        "list": [
            {"account_id": "ifrs-full_Revenue", "thstrm_amount": "1000"},
            {"account_id": "unknown_account", "thstrm_amount": "9999"},
            {
                "account_id": "ifrs-full_GrossProfit",
                "thstrm_amount": "300",
            },  # 매핑 None
        ],
    }
    with patch.object(collector, "_get", return_value=_mock_resp(payload)):
        fy = fetch_annual_financial("123", 2024)
    assert fy.revenue == 1000
    # 알 수 없는 계정은 무시되고 다른 필드 손상 없음
    assert fy.operating_income is None


def test_fetch_annual_financial_first_match_wins():
    """같은 필드가 중복 매칭되면 첫 값 우선 (CFS·OFS 혼합 응답 보호)."""
    payload = {
        "status": "000",
        "list": [
            {"account_id": "ifrs-full_Revenue", "thstrm_amount": "1000"},
            {"account_id": "ifrs_Revenue", "thstrm_amount": "9999"},  # 두 번째
        ],
    }
    with patch.object(collector, "_get", return_value=_mock_resp(payload)):
        fy = fetch_annual_financial("123", 2024)
    assert fy.revenue == 1000


# ---------- corp_code 매핑 ----------


def test_find_corp_exact_match(monkeypatch):
    fake = [
        CorpInfo("00111111", "삼성중공업", "010140", "20240101"),
        CorpInfo("00126380", "삼성전자", "005930", "20240101"),
    ]
    monkeypatch.setattr(collector, "fetch_corp_codes", lambda **_: fake)
    c = collector.find_corp("삼성전자")
    assert c.corp_code == "00126380"


def test_find_corp_by_stock_code(monkeypatch):
    fake = [CorpInfo("00126380", "삼성전자", "005930", "20240101")]
    monkeypatch.setattr(collector, "fetch_corp_codes", lambda **_: fake)
    c = collector.find_corp("005930")
    assert c.corp_name == "삼성전자"


def test_find_corp_partial_match_listed_only(monkeypatch):
    fake = [
        CorpInfo("00000001", "삼성그룹비상장", None, "20240101"),  # 비상장
        CorpInfo("00126380", "삼성전자우", "005935", "20240101"),  # 상장
    ]
    monkeypatch.setattr(collector, "fetch_corp_codes", lambda **_: fake)
    c = collector.find_corp("삼성")
    assert c.stock_code == "005935"  # 상장사 우선


def test_require_key_raises_when_missing(monkeypatch):
    monkeypatch.setattr(collector, "DART_API_KEY", "")
    with pytest.raises(DartError, match="DART_API_KEY"):
        collector._require_key()
