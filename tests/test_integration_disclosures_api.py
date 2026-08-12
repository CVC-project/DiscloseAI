from datetime import datetime, timezone

from integration.api.disclosures import _normalize_items, _read_limit, _today_kst


def test_today_kst_converts_utc_day_boundary():
    utc = datetime(2026, 8, 6, 16, 30, tzinfo=timezone.utc)
    assert _today_kst(utc) == "20260807"


def test_normalize_items_keeps_only_listed_disclosures():
    items = [
        {
            "rcept_no": "20260807000123",
            "stock_code": "005930",
            "corp_name": "삼성전자",
            "report_nm": "반기보고서",
            "flr_nm": "삼성전자",
            "rcept_dt": "20260807",
        },
        {"rcept_no": "20260807000456", "corp_name": "비상장사", "report_nm": "기타"},
    ]

    assert _normalize_items(items, 30) == [
        {
            "rceptNo": "20260807000123",
            "dartUrl": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260807000123",
            "company": "삼성전자",
            "stockCode": "005930",
            "title": "반기보고서",
            "filer": "삼성전자",
            "receiptDate": "2026-08-07",
        }
    ]


def test_limit_is_bounded():
    assert _read_limit("/api/disclosures?limit=500") == 100
    assert _read_limit("/api/disclosures?limit=invalid") == 30
    assert _read_limit("/api/disclosures?limit=0") == 1
