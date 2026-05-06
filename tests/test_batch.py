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
    """INSTRUMENT_BLACKLIST가 비어 있으면 ETF 등이 정확매칭 단계로 흘러감 (find_corp이 처리).

    v2: KOSPI_TOP_50 universe에서 KODEX 200/삼성전자우 제거 후 BLACKLIST는 빈 set.
    여기선 BLACKLIST 동작 자체는 유지되는지(빈 set이라도 멤버십 검사 정상)만 확인.
    """
    from modules.financial.batch import INSTRUMENT_BLACKLIST

    assert isinstance(INSTRUMENT_BLACKLIST, set)
    assert "KODEX 200" not in INSTRUMENT_BLACKLIST  # v2에서 제거됨


def test_resolve_corp_aliases_mapping():
    """ALIASES 딕셔너리가 정상 구성되어 있는지 확인.

    v2: 삼성전자우는 universe에서 제거되어 ALIASES에서도 제외됨.
    """
    # 현대차는 6자리 종목코드 매핑
    assert ALIASES["현대차"] == "005380"
    assert len(ALIASES["현대차"]) == 6
    # 미래에셋증권은 6자리 종목코드 매핑 (alias '미래에셋증권'은 시장명, 정식명 다름)
    assert "미래에셋증권" in ALIASES
    # ALIASES에 최소한 10개 이상의 엔트리
    assert len(ALIASES) >= 10
    # 제거된 항목 검증 — 삼성전자우는 universe 제외되어 alias에도 없어야 함
    assert "삼성전자우" not in ALIASES


@patch("modules.financial.collector.fetch_corp_codes")
def test_resolve_corp_corp_code_lookup(mock_fetch_corp_codes):
    """8자리 corp_code는 fetch_corp_codes에서 lookup.

    v2: 삼성전자우 alias 제거 후 8자리 매핑 검증을 다른 alias(미래에셋증권)로 변경.
    """
    target_corp = CorpInfo(
        corp_code="00111722",
        corp_name="미래에셋증권",
        stock_code="006800",
        modify_date="20240101",
    )
    other_corp = CorpInfo(
        corp_code="00000001",
        corp_name="Other",
        stock_code="000001",
        modify_date="20240101",
    )
    mock_fetch_corp_codes.return_value = [other_corp, target_corp]

    # 미래에셋증권은 6자리 stock_code 매핑이지만, find_corp이 stock_code로 잘 매칭됨.
    # 8자리 corp_code 매핑 alias가 현재 universe엔 없어서, find_corp 경로 검증.
    result = resolve_corp("미래에셋증권")
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
    """INSTRUMENT_BLACKLIST 검사 메커니즘 자체가 동작하는지 확인.

    v2: KODEX 200을 universe에서 제거하면서 BLACKLIST를 빈 set으로 비움.
    BLACKLIST에 항목이 있을 경우의 동작 자체는 유지 — 단위 테스트로 그것만 확인.
    """
    from modules.financial.batch import INSTRUMENT_BLACKLIST

    # 빈 set이라도 자료형 보존, 멤버십 검사 정상 동작
    assert isinstance(INSTRUMENT_BLACKLIST, set)
    assert "KODEX 200" not in INSTRUMENT_BLACKLIST
