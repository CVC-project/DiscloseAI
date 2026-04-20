"""batch.py — 배치 수집 + EQS 통합 테스트."""

from unittest.mock import MagicMock, patch
from modules.financial.batch import (
    build_sector_stats,
    FirmRecord,
    resolve_corp,
    ALIASES,
)
from modules.financial.collector import CorpInfo
from modules.financial.eqs.types import EQSResult, FirmPanel, ModuleScore
from tests._factories import healthy_panel, make_year


def test_build_sector_stats_empty_records():
    """빈 레코드 리스트 → 빈 결과."""
    result = build_sector_stats([])
    assert result["sectors_computed"] == 0
    assert result["total_companies"] == 0


def test_build_sector_stats_records_with_no_panel():
    """panel=None인 레코드는 제외."""
    record = FirmRecord(display_name="Test", corp=None, panel=None, error="매칭실패")
    result = build_sector_stats([record])
    assert result["sectors_computed"] == 0
    assert result["total_companies"] == 0


def test_build_sector_stats_records_with_error():
    """error가 set된 레코드는 제외."""
    corp = CorpInfo(
        corp_code="00000001",
        corp_name="Test",
        stock_code="000000",
        modify_date="20240101",
    )
    panel = healthy_panel()
    eqs = EQSResult(
        corp_code="00000001",
        corp_name="Test",
        industry_code="013",
        modules=[ModuleScore(name="M1", score=50.0)],
        total=50.0,
        grade="C",
    )
    record = FirmRecord(
        display_name="Test",
        corp=corp,
        panel=panel,
        eqs=eqs,
        error="API_ERROR",  # error 설정됨
    )
    result = build_sector_stats([record])
    # error가 있으면 skip
    assert result["sectors_computed"] == 0
    assert result["total_companies"] == 0


def test_build_sector_stats_record_with_none_latest():
    """panel이 있어도 latest()가 None이면 제외."""
    corp = CorpInfo(
        corp_code="00000001",
        corp_name="Test",
        stock_code="000000",
        modify_date="20240101",
    )
    empty_panel = FirmPanel(corp_code="test", years=[])  # 빈 panel
    record = FirmRecord(
        display_name="Test", corp=corp, panel=empty_panel, eqs=None, error=None
    )
    result = build_sector_stats([record])
    # latest()=None이므로 skip
    assert result["sectors_computed"] == 0
    assert result["total_companies"] == 0


@patch("modules.financial.industry_groups.compute_sector_stats")
@patch("modules.financial.industry_groups.save_sector_stats")
@patch("modules.financial.translator.ratios.compute_ratios")
def test_build_sector_stats_valid_records(
    mock_compute_ratios,
    mock_save_sector_stats,
    mock_compute_sector_stats,
):
    """정상 레코드 → sector_stats 계산 후 저장."""
    # Mock 설정
    mock_ratios = MagicMock()
    mock_ratios.as_dict.return_value = {"ROE": 0.15, "ROA": 0.10}
    mock_compute_ratios.return_value = mock_ratios

    mock_sector_stats = {
        "기술": MagicMock(n_companies=5),
        "금융": MagicMock(n_companies=3),
    }
    mock_compute_sector_stats.return_value = mock_sector_stats
    mock_save_sector_stats.return_value = "/cache/sector_stats.json"

    # 데이터 설정
    corp = CorpInfo(
        corp_code="00000001",
        corp_name="TestCo",
        stock_code="000001",
        modify_date="20240101",
    )
    panel = healthy_panel()
    eqs = EQSResult(
        corp_code="00000001",
        corp_name="TestCo",
        industry_code="013",
        modules=[ModuleScore(name="M1", score=75.0)],
        total=75.0,
        grade="A",
    )
    record = FirmRecord(
        display_name="TestCo", corp=corp, panel=panel, eqs=eqs, error=None
    )

    result = build_sector_stats([record])

    # Assertion
    assert result["cache_path"] == "/cache/sector_stats.json"
    assert result["sectors_computed"] == 2
    assert result["total_companies"] == 8
    mock_compute_ratios.assert_called_once()
    mock_compute_sector_stats.assert_called_once()
    mock_save_sector_stats.assert_called_once()


@patch("modules.financial.industry_groups.compute_sector_stats")
@patch("modules.financial.industry_groups.save_sector_stats")
@patch("modules.financial.translator.ratios.compute_ratios")
def test_build_sector_stats_multiple_records(
    mock_compute_ratios,
    mock_save_sector_stats,
    mock_compute_sector_stats,
):
    """여러 레코드 중 일부만 유효."""
    # Mock
    mock_ratios = MagicMock()
    mock_ratios.as_dict.return_value = {"ROE": 0.15}
    mock_compute_ratios.return_value = mock_ratios

    mock_sector_stats = {"제조": MagicMock(n_companies=2)}
    mock_compute_sector_stats.return_value = mock_sector_stats
    mock_save_sector_stats.return_value = "/cache/stats.json"

    # 데이터
    corp1 = CorpInfo(
        corp_code="00000001",
        corp_name="Co1",
        stock_code="000001",
        modify_date="20240101",
    )
    panel1 = healthy_panel()
    record1 = FirmRecord(
        display_name="Co1", corp=corp1, panel=panel1, eqs=MagicMock(), error=None
    )

    # 에러 레코드
    record2 = FirmRecord(display_name="Co2", corp=None, panel=None, error="매칭실패")

    # 빈 panel 레코드
    record3 = FirmRecord(
        display_name="Co3",
        corp=corp1,
        panel=FirmPanel(corp_code="test", years=[]),
        error=None,
    )

    result = build_sector_stats([record1, record2, record3])

    # record1만 처리됨
    assert result["sectors_computed"] == 1
    assert result["total_companies"] == 2
    # 1개 레코드만 ratios 계산
    assert mock_compute_ratios.call_count == 1


def test_resolve_corp_alias_instrument_blacklist():
    """INSTRUMENT_BLACKLIST에 있는 이름은 None 반환."""
    result = resolve_corp("KODEX 200")
    assert result is None


def test_resolve_corp_aliases_mapping():
    """ALIASES 딕셔너리가 정상 구성되어 있는지 확인."""
    # 삼성전자우는 8자리 corp_code 매핑
    assert ALIASES["삼성전자우"] == "00126380"
    assert len(ALIASES["삼성전자우"]) == 8
    # 현대차는 6자리 종목코드 매핑
    assert ALIASES["현대차"] == "005380"
    assert len(ALIASES["현대차"]) == 6
    # ALIASES에 최소한 10개 이상의 엔트리
    assert len(ALIASES) >= 10


@patch("modules.financial.collector.fetch_corp_codes")
def test_resolve_corp_corp_code_lookup(mock_fetch_corp_codes):
    """8자리 corp_code는 fetch_corp_codes에서 lookup."""
    target_corp = CorpInfo(
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        modify_date="20240101",
    )
    other_corp = CorpInfo(
        corp_code="00000001",
        corp_name="Other",
        stock_code="000001",
        modify_date="20240101",
    )
    # Mock이 여러 기업을 반환하되, 목표 기업도 포함
    mock_fetch_corp_codes.return_value = [other_corp, target_corp]

    result = resolve_corp("삼성전자우")  # ALIASES: "00126380"
    assert result == target_corp


def test_build_sector_stats_return_structure():
    """build_sector_stats 반환값 구조 검증."""
    result = build_sector_stats([])
    # 필수 키 확인
    assert "cache_path" in result
    assert "sectors_computed" in result
    assert "total_companies" in result
    # 빈 입력시 값 확인
    assert isinstance(result["sectors_computed"], int)
    assert isinstance(result["total_companies"], int)
    assert result["sectors_computed"] == 0
    assert result["total_companies"] == 0


def test_resolve_corp_instrument_blacklist_exact_match():
    """INSTRUMENT_BLACKLIST는 정확히 "KODEX 200"만 거르고 비슷한 이름은 아님."""
    # KODEX 200은 제외
    assert resolve_corp("KODEX 200") is None
    # 유사하지만 다른 이름은 find_corp 시도 (mock 없으면 None)
    # 여기서는 단순히 정확한 match만 테스트
    from modules.financial.batch import INSTRUMENT_BLACKLIST

    assert "KODEX 200" in INSTRUMENT_BLACKLIST
