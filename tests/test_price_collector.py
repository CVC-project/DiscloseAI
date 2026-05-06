"""주가 수집 모듈 (collector) 테스트"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.price.collector import (
    _ticker,
    fetch_prices,
    save_prices,
    collect_prices,
    collect_bulk,
)
from modules.price.models import Base, PriceLocal


@pytest.fixture
def local_session():
    """로컬 in-memory DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestTicker:
    """_ticker 함수 테스트"""

    def test_ticker_kospi(self):
        """KOSPI 종목 -> .KS suffix"""
        result = _ticker("005930", "KOSPI")
        assert result == "005930.KS"

    def test_ticker_kosdaq(self):
        """KOSDAQ 종목 -> .KQ suffix"""
        result = _ticker("247540", "KOSDAQ")
        assert result == "247540.KQ"

    def test_ticker_lowercase_market(self):
        """시장명 소문자 처리"""
        result = _ticker("005930", "kospi")
        assert result == "005930.KS"

    def test_ticker_unknown_market_defaults_to_ks(self):
        """unknown 시장 -> .KS 기본값"""
        result = _ticker("005930", "UNKNOWN")
        assert result == "005930.KS"


class TestFetchPrices:
    """fetch_prices 함수 테스트"""

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_success(self, mock_download):
        """정상 데이터 수집"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        # Mock yfinance 응답
        mock_df = pd.DataFrame(
            {
                "Close": [50000.0, 51000.0, 52000.0],
            },
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"]),
        )
        mock_download.return_value = mock_df

        result = fetch_prices("005930", "KOSPI", start_date, end_date)

        assert len(result) == 3
        assert result[0]["corp_code"] == "005930"
        assert result[0]["close_price"] == 50000.0
        assert result[1]["daily_return"] is not None  # 첫 NaN 제외

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_empty_data(self, mock_download):
        """빈 데이터 처리 (empty DataFrame)"""
        mock_download.return_value = pd.DataFrame()

        result = fetch_prices("999999", "KOSPI", date(2024, 1, 1), date(2024, 1, 10))

        assert result == []

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_none_data(self, mock_download):
        """None 데이터 처리"""
        mock_download.return_value = None

        result = fetch_prices("999998", "KOSPI", date(2024, 1, 1), date(2024, 1, 10))

        assert result == []

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_missing_close_column(self, mock_download):
        """종가 컬럼 누락"""
        mock_df = pd.DataFrame(
            {"Open": [50000.0, 51000.0]},
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"]),
        )
        mock_download.return_value = mock_df

        result = fetch_prices("999997", "KOSPI", date(2024, 1, 1), date(2024, 1, 10))

        assert result == []

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_caching(self, mock_download):
        """5분 캐시 검증"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)

        mock_df = pd.DataFrame(
            {"Close": [50000.0, 51000.0]},
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"]),
        )
        mock_download.return_value = mock_df

        # 첫 호출
        result1 = fetch_prices("111111", "KOSPI", start_date, end_date)
        call_count_1 = mock_download.call_count

        # 두 번째 호출 (캐시)
        result2 = fetch_prices("111111", "KOSPI", start_date, end_date)
        call_count_2 = mock_download.call_count

        assert result1 == result2
        assert call_count_2 == call_count_1  # yfinance 호출 없음

    @patch("modules.price.collector.yf.download")
    def test_fetch_prices_nan_daily_return(self, mock_download):
        """NaN daily_return -> None 변환"""
        mock_df = pd.DataFrame(
            {"Close": [50000.0, 51000.0, 52000.0]},
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"]),
        )
        mock_download.return_value = mock_df

        result = fetch_prices("222222", "KOSPI", date(2024, 1, 1), date(2024, 1, 10))

        assert len(result) == 3
        # 첫 번째 record의 daily_return은 None (pct_change 첫 값이 NaN)
        assert result[0]["daily_return"] is None
        # 이후는 float
        assert isinstance(result[1]["daily_return"], float)


class TestSavePrices:
    """save_prices 함수 테스트"""

    @patch("modules.price.collector.get_local_session")
    def test_save_prices_new_records(self, mock_get_session, local_session):
        """신규 레코드 저장"""
        mock_get_session.return_value = local_session

        records = [
            {
                "corp_code": "005930",
                "date": date(2024, 1, 1),
                "close_price": 50000.0,
                "daily_return": None,
            },
            {
                "corp_code": "005930",
                "date": date(2024, 1, 2),
                "close_price": 51000.0,
                "daily_return": 2.0,
            },
        ]

        saved = save_prices(records)

        assert saved == 2
        rows = local_session.query(PriceLocal).all()
        assert len(rows) == 2

    @patch("modules.price.collector.get_local_session")
    def test_save_prices_duplicate_skip(self, mock_get_session, local_session):
        """중복 (corp_code+date) 건너뜀"""
        mock_get_session.return_value = local_session

        # 기존 데이터
        existing = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 1),
            close_price=50000.0,
        )
        local_session.add(existing)
        local_session.commit()

        records = [
            {
                "corp_code": "005930",
                "date": date(2024, 1, 1),
                "close_price": 52000.0,  # 다른 가격
                "daily_return": None,
            },
            {
                "corp_code": "005930",
                "date": date(2024, 1, 2),
                "close_price": 51000.0,
                "daily_return": 2.0,
            },
        ]

        saved = save_prices(records)

        assert saved == 1  # 1건만 저장
        rows = local_session.query(PriceLocal).all()
        assert len(rows) == 2
        # 기존 데이터 유지 확인
        first_row = (
            local_session.query(PriceLocal)
            .filter_by(corp_code="005930", date=date(2024, 1, 1))
            .first()
        )
        assert first_row.close_price == 50000.0

    @patch("modules.price.collector.get_local_session")
    def test_save_prices_empty_records(self, mock_get_session):
        """빈 레코드 리스트"""
        mock_get_session.return_value = MagicMock()

        saved = save_prices([])

        assert saved == 0
        mock_get_session.assert_not_called()

    @patch("modules.price.collector.get_local_session")
    def test_save_prices_multiple_corps(self, mock_get_session, local_session):
        """여러 기업 데이터 저장"""
        mock_get_session.return_value = local_session

        records = [
            {
                "corp_code": "005930",
                "date": date(2024, 1, 1),
                "close_price": 50000.0,
                "daily_return": None,
            },
            {
                "corp_code": "247540",
                "date": date(2024, 1, 1),
                "close_price": 30000.0,
                "daily_return": None,
            },
        ]

        saved = save_prices(records)

        assert saved == 2
        rows = local_session.query(PriceLocal).all()
        assert len(rows) == 2


class TestCollectPrices:
    """collect_prices 함수 테스트"""

    @patch("modules.price.collector.init_local_db")
    @patch("modules.price.collector.save_prices")
    @patch("modules.price.collector.fetch_prices")
    def test_collect_prices_integration(self, mock_fetch, mock_save, mock_init):
        """주가 수집 + 저장 통합"""
        mock_fetch.return_value = [
            {
                "corp_code": "005930",
                "date": date(2024, 1, 1),
                "close_price": 50000.0,
                "daily_return": None,
            }
        ]
        mock_save.return_value = 1

        result = collect_prices("005930", "KOSPI", date(2024, 1, 1), date(2024, 1, 10))

        assert result == 1
        mock_init.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()


class TestCollectBulk:
    """collect_bulk 함수 테스트"""

    @patch("modules.price.collector.init_local_db")
    @patch("modules.price.collector.collect_prices")
    def test_collect_bulk_multiple_targets(self, mock_collect, mock_init):
        """여러 종목 일괄 수집"""
        mock_collect.side_effect = [10, 15]

        targets = [
            {"corp_code": "005930", "market": "KOSPI"},
            {"corp_code": "247540", "market": "KOSDAQ"},
        ]

        result = collect_bulk(targets, date(2024, 1, 1), date(2024, 1, 10))

        assert result == {"005930": 10, "247540": 15}
        mock_init.assert_called_once()
        assert mock_collect.call_count == 2

    @patch("modules.price.collector.init_local_db")
    @patch("modules.price.collector.collect_prices")
    def test_collect_bulk_empty_targets(self, mock_collect, mock_init):
        """빈 종목 리스트"""
        result = collect_bulk([], date(2024, 1, 1), date(2024, 1, 10))

        assert result == {}
        mock_collect.assert_not_called()

    @patch("modules.price.collector.init_local_db")
    @patch("modules.price.collector.collect_prices")
    def test_collect_bulk_default_market(self, mock_collect, mock_init):
        """기본 시장값(KOSPI) 적용"""
        mock_collect.return_value = 10

        targets = [{"corp_code": "005930"}]  # market 미지정

        collect_bulk(targets, date(2024, 1, 1), date(2024, 1, 10))

        mock_collect.assert_called_once()
        call_args = mock_collect.call_args[0]
        assert call_args[1] == "KOSPI"  # 기본값 검증
