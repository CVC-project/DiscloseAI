"""VKOSPI 수집 및 변동성 필터링 테스트"""

import pytest

# pykrx는 ad-hoc 의존(KRX 비공식 API 래퍼) — 미설치 환경에서는 collection skip.
pytest.importorskip("pykrx")

from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from modules.price.models import VkospiLocal, PriceLocal
from modules.price.vkospi_collector import (
    fetch_vkospi,
    save_vkospi,
    collect_vkospi,
    LOW_VOL_THRESHOLD,
)
from modules.price.volatility_filter import (
    classify_volatility,
    filter_low_volatility_disclosures,
    compute_label_purity,
    get_vkospi_on_date,
)


class TestFetchVkospi:
    """fetch_vkospi() 테스트"""

    @patch("modules.price.vkospi_collector.stock.get_index_ohlcv")
    def test_fetch_vkospi_normal(self, mock_get_index):
        """정상 데이터 수집 케이스"""
        # mock 데이터 준비
        mock_df = pd.DataFrame(
            {
                "종가": [15.5, 16.2, 14.8],
            },
            index=pd.to_datetime(["2026-04-15", "2026-04-16", "2026-04-17"]),
        )
        mock_get_index.return_value = mock_df

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = fetch_vkospi(start, end)

        assert len(result) == 3
        assert result[0]["date"] == date(2026, 4, 15)
        assert result[0]["vkospi"] == 15.5
        assert result[1]["vkospi"] == 16.2
        assert result[2]["vkospi"] == 14.8
        assert all("date" in r and "vkospi" in r for r in result)

    @patch("modules.price.vkospi_collector.stock.get_index_ohlcv")
    def test_fetch_vkospi_empty(self, mock_get_index):
        """빈 데이터 케이스"""
        mock_get_index.return_value = None

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = fetch_vkospi(start, end)

        assert result == []

    @patch("modules.price.vkospi_collector.stock.get_index_ohlcv")
    def test_fetch_vkospi_empty_dataframe(self, mock_get_index):
        """빈 DataFrame 케이스"""
        mock_get_index.return_value = pd.DataFrame()

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = fetch_vkospi(start, end)

        assert result == []

    @patch("modules.price.vkospi_collector.stock.get_index_ohlcv")
    def test_fetch_vkospi_missing_close(self, mock_get_index):
        """종가 컬럼 없는 경우"""
        mock_df = pd.DataFrame(
            {
                "고가": [16.0, 17.0],
                "저가": [15.0, 15.5],
            },
            index=pd.to_datetime(["2026-04-15", "2026-04-16"]),
        )
        mock_get_index.return_value = mock_df

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = fetch_vkospi(start, end)

        assert result == []

    @patch("modules.price.vkospi_collector.stock.get_index_ohlcv")
    def test_fetch_vkospi_close_column_variant(self, mock_get_index):
        """Close 컬럼(영문) 케이스"""
        mock_df = pd.DataFrame(
            {
                "Close": [15.5, 16.2],
            },
            index=pd.to_datetime(["2026-04-15", "2026-04-16"]),
        )
        mock_get_index.return_value = mock_df

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = fetch_vkospi(start, end)

        assert len(result) == 2
        assert result[0]["vkospi"] == 15.5


class TestSaveVkospi:
    """save_vkospi() 테스트"""

    def test_save_vkospi_normal(self, db_session):
        """신규 저장 케이스"""
        from modules.price.db import LocalSession
        from unittest.mock import patch

        records = [
            {"date": date(2026, 4, 15), "vkospi": 14.5},
            {"date": date(2026, 4, 16), "vkospi": 16.2},
        ]

        # get_local_session() mock
        with patch(
            "modules.price.vkospi_collector.get_local_session", return_value=db_session
        ):
            saved = save_vkospi(records)

        assert saved == 2
        rows = db_session.query(VkospiLocal).all()
        assert len(rows) == 2
        assert rows[0].vkospi == 14.5
        assert rows[0].is_low_vol is True  # 14.5 < 15.0
        assert rows[1].is_low_vol is False  # 16.2 >= 15.0

    def test_save_vkospi_empty_records(self, db_session):
        """빈 레코드 리스트 케이스"""
        from unittest.mock import patch

        with patch(
            "modules.price.vkospi_collector.get_local_session", return_value=db_session
        ):
            saved = save_vkospi([])

        assert saved == 0
        assert db_session.query(VkospiLocal).count() == 0

    def test_save_vkospi_duplicate_date_skip(self, db_session):
        """중복 날짜 건너뜀"""
        from unittest.mock import patch

        # 기존 데이터 삽입
        existing = VkospiLocal(date=date(2026, 4, 15), vkospi=15.0, is_low_vol=False)
        db_session.add(existing)
        db_session.commit()

        records = [
            {"date": date(2026, 4, 15), "vkospi": 14.0},  # 중복 (무시됨)
            {"date": date(2026, 4, 16), "vkospi": 16.0},  # 신규
        ]

        with patch(
            "modules.price.vkospi_collector.get_local_session", return_value=db_session
        ):
            saved = save_vkospi(records)

        assert saved == 1
        assert db_session.query(VkospiLocal).count() == 2
        # 기존 데이터는 변경 안 됨
        old_row = (
            db_session.query(VkospiLocal)
            .filter(VkospiLocal.date == date(2026, 4, 15))
            .first()
        )
        assert old_row.vkospi == 15.0

    def test_save_vkospi_is_low_vol_boundary(self, db_session):
        """저변동 임계값 경계값 테스트"""
        from unittest.mock import patch

        records = [
            {"date": date(2026, 4, 14), "vkospi": 14.99},  # < 15.0
            {"date": date(2026, 4, 15), "vkospi": 15.0},  # = 15.0 (not low_vol)
            {"date": date(2026, 4, 16), "vkospi": 15.01},  # > 15.0
        ]

        with patch(
            "modules.price.vkospi_collector.get_local_session", return_value=db_session
        ):
            saved = save_vkospi(records)

        assert saved == 3
        rows = db_session.query(VkospiLocal).order_by(VkospiLocal.date).all()
        assert rows[0].is_low_vol is True
        assert rows[1].is_low_vol is False
        assert rows[2].is_low_vol is False


class TestCollectVkospi:
    """collect_vkospi() 통합 테스트"""

    @patch("modules.price.vkospi_collector.init_local_db")
    @patch("modules.price.vkospi_collector.fetch_vkospi")
    @patch("modules.price.vkospi_collector.save_vkospi")
    def test_collect_vkospi_integration(self, mock_save, mock_fetch, mock_init):
        """통합 수집 실행"""
        mock_fetch.return_value = [
            {"date": date(2026, 4, 15), "vkospi": 14.5},
        ]
        mock_save.return_value = 1

        start = date(2026, 4, 15)
        end = date(2026, 4, 17)
        result = collect_vkospi(start, end)

        assert result == 1
        mock_init.assert_called_once()
        mock_fetch.assert_called_once_with(start, end)
        mock_save.assert_called_once()


class TestClassifyVolatility:
    """classify_volatility() 테스트"""

    def test_classify_volatility_low(self):
        """저변동 케이스"""
        assert classify_volatility(10.0) == "low"
        assert classify_volatility(14.99) == "low"

    def test_classify_volatility_low_boundary(self):
        """저변동 경계값"""
        assert classify_volatility(15.0) == "medium"
        assert classify_volatility(14.999) == "low"

    def test_classify_volatility_medium(self):
        """중변동 케이스"""
        assert classify_volatility(15.0) == "medium"
        assert classify_volatility(20.0) == "medium"
        assert classify_volatility(24.99) == "medium"

    def test_classify_volatility_medium_boundary(self):
        """중변동 경계값"""
        assert classify_volatility(25.0) == "high"
        assert classify_volatility(24.999) == "medium"

    def test_classify_volatility_high(self):
        """고변동 케이스"""
        assert classify_volatility(25.0) == "high"
        assert classify_volatility(30.0) == "high"
        assert classify_volatility(100.0) == "high"


class TestGetVkospiOnDate:
    """get_vkospi_on_date() 테스트"""

    def test_get_vkospi_on_date_exists(self, db_session):
        """존재하는 날짜"""
        vkospi_row = VkospiLocal(date=date(2026, 4, 15), vkospi=15.5, is_low_vol=False)
        db_session.add(vkospi_row)
        db_session.commit()

        result = get_vkospi_on_date(db_session, date(2026, 4, 15))
        assert result == 15.5

    def test_get_vkospi_on_date_not_exists(self, db_session):
        """존재하지 않는 날짜"""
        result = get_vkospi_on_date(db_session, date(2026, 4, 15))
        assert result is None


class TestFilterLowVolatilityDisclosures:
    """filter_low_volatility_disclosures() 테스트"""

    def test_filter_low_volatility_disclosures_normal(self, db_session):
        """저변동 공시 필터링"""
        # VKOSPI 데이터 삽입
        vkospi1 = VkospiLocal(date=date(2026, 4, 15), vkospi=14.0, is_low_vol=True)
        vkospi2 = VkospiLocal(date=date(2026, 4, 16), vkospi=16.0, is_low_vol=False)
        vkospi3 = VkospiLocal(date=date(2026, 4, 17), vkospi=13.0, is_low_vol=True)
        db_session.add_all([vkospi1, vkospi2, vkospi3])

        # PriceLocal 데이터 삽입
        price1 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 15),
            close_price=50000.0,
            label="수혜",
            disclosure_id="disc_001",
        )
        price2 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 16),
            close_price=49500.0,
            label="악재",
            disclosure_id="disc_002",
        )
        price3 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 17),
            close_price=50200.0,
            label="수혜",
            disclosure_id="disc_003",
        )
        db_session.add_all([price1, price2, price3])
        db_session.commit()

        result = filter_low_volatility_disclosures(db_session)

        assert len(result) == 2
        assert result[0].date == date(2026, 4, 15)
        assert result[1].date == date(2026, 4, 17)

    def test_filter_low_volatility_disclosures_empty(self, db_session):
        """저변동 날짜 없는 경우"""
        result = filter_low_volatility_disclosures(db_session)
        assert result == []

    def test_filter_low_volatility_disclosures_filter_by_ids(self, db_session):
        """특정 공시 ID로 필터링"""
        vkospi = VkospiLocal(date=date(2026, 4, 15), vkospi=14.0, is_low_vol=True)
        db_session.add(vkospi)

        price1 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 15),
            close_price=50000.0,
            disclosure_id="disc_001",
        )
        price2 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 15),
            close_price=50100.0,
            disclosure_id="disc_002",
        )
        db_session.add_all([price1, price2])
        db_session.commit()

        result = filter_low_volatility_disclosures(
            db_session, disclosure_ids=["disc_001"]
        )

        assert len(result) == 1
        assert result[0].disclosure_id == "disc_001"

    def test_filter_low_volatility_disclosures_exclude_none_disclosure_id(
        self, db_session
    ):
        """disclosure_id가 None인 행 제외"""
        vkospi = VkospiLocal(date=date(2026, 4, 15), vkospi=14.0, is_low_vol=True)
        db_session.add(vkospi)

        price1 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 15),
            close_price=50000.0,
            disclosure_id="disc_001",
        )
        price2 = PriceLocal(
            corp_code="005930",
            date=date(2026, 4, 15),
            close_price=50100.0,
            disclosure_id=None,
        )
        db_session.add_all([price1, price2])
        db_session.commit()

        result = filter_low_volatility_disclosures(db_session)

        assert len(result) == 1
        assert result[0].disclosure_id == "disc_001"


class TestComputeLabelPurity:
    """compute_label_purity() 테스트"""

    def test_compute_label_purity_normal(self, db_session):
        """라벨 분포 계산"""
        all_records = [
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 15),
                close_price=50000.0,
                label="수혜",
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 16),
                close_price=49500.0,
                label="악재",
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 17),
                close_price=50200.0,
                label="중립",
            ),
        ]

        low_vol_records = [all_records[0], all_records[1]]

        result = compute_label_purity(all_records, low_vol_records)

        assert result["total"]["수혜"] == 1
        assert result["total"]["악재"] == 1
        assert result["total"]["중립"] == 1
        assert result["total"]["total"] == 3

        assert result["low_vol"]["수혜"] == 1
        assert result["low_vol"]["악재"] == 1
        assert result["low_vol"]["중립"] == 0
        assert result["low_vol"]["total"] == 2

    def test_compute_label_purity_empty_records(self, db_session):
        """빈 레코드 케이스"""
        result = compute_label_purity([], [])

        assert result["total"]["total"] == 0
        assert result["low_vol"]["total"] == 0
        assert result["non_neutral_ratio"]["total"] == 0.0
        assert result["non_neutral_ratio"]["low_vol"] == 0.0

    def test_compute_label_purity_none_label_as_neutral(self, db_session):
        """None 라벨을 중립으로 처리"""
        all_records = [
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 15),
                close_price=50000.0,
                label=None,
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 16),
                close_price=49500.0,
                label="수혜",
            ),
        ]

        result = compute_label_purity(all_records, all_records)

        assert result["total"]["중립"] == 1
        assert result["total"]["수혜"] == 1

    def test_compute_label_purity_non_neutral_ratio(self, db_session):
        """라벨 순도 비율 계산"""
        all_records = [
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 15),
                close_price=50000.0,
                label="수혜",
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 16),
                close_price=49500.0,
                label="수혜",
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 17),
                close_price=50200.0,
                label="중립",
            ),
            PriceLocal(
                corp_code="005930",
                date=date(2026, 4, 18),
                close_price=50300.0,
                label="중립",
            ),
        ]

        low_vol_records = [all_records[0], all_records[1]]

        result = compute_label_purity(all_records, low_vol_records)

        # 전체: (2 + 0) / 4 = 0.5
        assert result["non_neutral_ratio"]["total"] == 0.5
        # 저변동: (2 + 0) / 2 = 1.0
        assert result["non_neutral_ratio"]["low_vol"] == 1.0
