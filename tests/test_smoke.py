"""프로젝트 초기 상태 smoke test. CI의 첫 초록불을 보장합니다."""

from shared.models import FinancialData, DisclosureData, RelationData, PriceData


def test_shared_models_importable():
    """Fix 1 regression 방지: shared.models import가 항상 성공해야 함."""
    assert FinancialData.__tablename__ == "financial_data"
    assert DisclosureData.__tablename__ == "disclosure_data"
    assert RelationData.__tablename__ == "relation_data"
    assert PriceData.__tablename__ == "price_data"


def test_in_memory_session_fixture(in_memory_session):
    """conftest fixture 동작 확인."""
    row = FinancialData(corp_code="005930", corp_name="삼성전자", year=2024)
    in_memory_session.add(row)
    in_memory_session.commit()
    result = in_memory_session.query(FinancialData).first()
    assert result.corp_code == "005930"
    assert result.corp_name == "삼성전자"
