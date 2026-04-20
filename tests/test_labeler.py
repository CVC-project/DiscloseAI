"""공시 후 주가변동 라벨링 모듈 (labeler) 테스트"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.price.labeler import (
    compute_label,
    _next_trading_day,
    _nth_trading_day,
    label_disclosure,
    label_bulk,
    label_summary,
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


class TestComputeLabel:
    """compute_label 함수 테스트"""

    def test_positive_threshold_exact(self):
        """정확히 +2% -> 수혜"""
        assert compute_label(2.0) == "수혜"

    def test_positive_above_threshold(self):
        """+3% -> 수혜"""
        assert compute_label(3.0) == "수혜"

    def test_negative_threshold_exact(self):
        """정확히 -2% -> 악재"""
        assert compute_label(-2.0) == "악재"

    def test_negative_below_threshold(self):
        """-3% -> 악재"""
        assert compute_label(-3.0) == "악재"

    def test_neutral_within_range(self):
        """0% -> 중립"""
        assert compute_label(0.0) == "중립"

    def test_neutral_between_thresholds(self):
        """1.5% (2.0 미만) -> 중립"""
        assert compute_label(1.5) == "중립"

    def test_neutral_between_negative_thresholds(self):
        """-1.5% (-2.0 초과) -> 중립"""
        assert compute_label(-1.5) == "중립"

    def test_large_positive(self):
        """+10% -> 수혜"""
        assert compute_label(10.0) == "수혜"

    def test_large_negative(self):
        """-10% -> 악재"""
        assert compute_label(-10.0) == "악재"


class TestNextTradingDay:
    """_next_trading_day 함수 테스트"""

    def test_next_trading_day_same_day(self, local_session):
        """공시일 당일은 제외하고 다음 날부터 탐색 — 공시 당일 종가는 발표 전 가격일 수 있음"""
        row = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),  # 공시일(1/1) 다음 거래일
            close_price=50000.0,
        )
        local_session.add(row)
        local_session.commit()

        result = _next_trading_day(local_session, "005930", date(2024, 1, 1))

        assert result is not None
        assert result.date == date(2024, 1, 2)

    def test_next_trading_day_after_date(self, local_session):
        """공시 후 첫 거래일 탐색"""
        # 1월 2일 거래일
        row = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=50000.0,
        )
        local_session.add(row)
        local_session.commit()

        result = _next_trading_day(local_session, "005930", date(2024, 1, 1))

        assert result is not None
        assert result.date == date(2024, 1, 2)

    def test_next_trading_day_no_data(self, local_session):
        """데이터 없으면 None 반환"""
        result = _next_trading_day(local_session, "005930", date(2024, 1, 1))

        assert result is None

    def test_next_trading_day_max_days_limit(self, local_session):
        """max_days 초과하면 None 반환"""
        row = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 10),
            close_price=50000.0,
        )
        local_session.add(row)
        local_session.commit()

        result = _next_trading_day(
            local_session, "005930", date(2024, 1, 1), max_days=5
        )

        assert result is None

    def test_next_trading_day_no_close_price(self, local_session):
        """close_price가 None이면 건너뜀"""
        row1 = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 1),
            close_price=None,  # NaN
        )
        row2 = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=50000.0,
        )
        local_session.add_all([row1, row2])
        local_session.commit()

        result = _next_trading_day(local_session, "005930", date(2024, 1, 1))

        assert result.date == date(2024, 1, 2)


class TestNthTradingDay:
    """_nth_trading_day 함수 테스트"""

    def test_nth_trading_day_exact(self, local_session):
        """정확히 n번째 거래일 반환"""
        dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        for d in dates:
            row = PriceLocal(
                corp_code="005930",
                date=d,
                close_price=50000.0 + (d - dates[0]).days * 100,
            )
            local_session.add(row)
        local_session.commit()

        result = _nth_trading_day(local_session, "005930", date(2024, 1, 1), n=2)

        assert result is not None
        assert result.date == date(2024, 1, 3)

    def test_nth_trading_day_insufficient_data(self, local_session):
        """n번째 데이터가 없으면 None 반환"""
        row = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=50000.0,
        )
        local_session.add(row)
        local_session.commit()

        result = _nth_trading_day(local_session, "005930", date(2024, 1, 1), n=5)

        assert result is None

    def test_nth_trading_day_n_equals_1(self, local_session):
        """n=1이면 from_date 이후 첫 거래일"""
        dates = [date(2024, 1, 1), date(2024, 1, 2)]
        for d in dates:
            row = PriceLocal(
                corp_code="005930",
                date=d,
                close_price=50000.0,
            )
            local_session.add(row)
        local_session.commit()

        result = _nth_trading_day(local_session, "005930", date(2024, 1, 1), n=1)

        assert result.date == date(2024, 1, 2)

    def test_nth_trading_day_skips_missing_close_price(self, local_session):
        """close_price 없는 날은 건너뜀"""
        rows = [
            PriceLocal(corp_code="005930", date=date(2024, 1, 2), close_price=None),
            PriceLocal(corp_code="005930", date=date(2024, 1, 3), close_price=50000.0),
            PriceLocal(corp_code="005930", date=date(2024, 1, 4), close_price=51000.0),
        ]
        local_session.add_all(rows)
        local_session.commit()

        result = _nth_trading_day(local_session, "005930", date(2024, 1, 1), n=2)

        assert result.date == date(2024, 1, 4)


class TestLabelDisclosure:
    """label_disclosure 함수 테스트"""

    @patch("modules.price.labeler.get_local_session")
    def test_label_disclosure_success(self, mock_get_session, local_session):
        """정상 라벨링 (+2.0% 변동)"""
        mock_get_session.return_value = local_session

        # 기준일 (공시일 다음 거래일: 2024-01-02)
        # _next_trading_day(2024-01-01) = 2024-01-02
        # _nth_trading_day(2024-01-02, n=5) = 2024-01-07
        base_price = 50000.0
        base = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=base_price,
        )

        # 5거래일 후 종가: 51000 = 50000 * 1.02
        for i in range(3, 10):
            if i == 7:  # 5거래일 후가 2024-01-07
                price = 51000.0
            else:
                price = 50000.0 + (i - 2) * 100
            row = PriceLocal(
                corp_code="005930",
                date=date(2024, 1, i),
                close_price=price,
            )
            local_session.add(row)

        local_session.add(base)
        local_session.commit()

        result = label_disclosure(
            "005930",
            date(2024, 1, 1),
            "acc_no_001",
            trading_days=5,
        )

        assert result is not None
        assert result["label"] == "수혜"
        assert result["change_pct"] >= 2.0
        assert result["disclosure_id"] == "acc_no_001"

    @patch("modules.price.labeler.get_local_session")
    def test_label_disclosure_no_base_price(self, mock_get_session, local_session):
        """기준 종가 없으면 None 반환"""
        mock_get_session.return_value = local_session

        result = label_disclosure(
            "005930",
            date(2024, 1, 1),
            "acc_no_001",
        )

        assert result is None

    @patch("modules.price.labeler.get_local_session")
    def test_label_disclosure_insufficient_future_data(
        self, mock_get_session, local_session
    ):
        """5거래일 데이터 부족"""
        mock_get_session.return_value = local_session

        base = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=50000.0,
        )
        # 2거래일만 존재
        end = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 3),
            close_price=51000.0,
        )
        local_session.add_all([base, end])
        local_session.commit()

        result = label_disclosure(
            "005930",
            date(2024, 1, 1),
            "acc_no_001",
            trading_days=5,
        )

        assert result is None

    @patch("modules.price.labeler.get_local_session")
    def test_label_disclosure_negative_label(self, mock_get_session, local_session):
        """악재 라벨링 (-2.0% 변동)"""
        mock_get_session.return_value = local_session

        base_price = 50000.0
        base = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=base_price,
        )
        # 5거래일 후 종가: 49000 = 50000 * 0.98
        for i in range(3, 10):
            if i == 7:  # 5거래일 후가 2024-01-07
                price = 49000.0
            else:
                price = 50000.0 - (i - 2) * 100
            row = PriceLocal(
                corp_code="005930",
                date=date(2024, 1, i),
                close_price=price,
            )
            local_session.add(row)

        local_session.add(base)
        local_session.commit()

        result = label_disclosure(
            "005930",
            date(2024, 1, 1),
            "acc_no_001",
        )

        assert result is not None
        assert result["label"] == "악재"
        assert result["change_pct"] <= -2.0

    @patch("modules.price.labeler.get_local_session")
    def test_label_disclosure_neutral_label(self, mock_get_session, local_session):
        """중립 라벨링 (+1% 변동)"""
        mock_get_session.return_value = local_session

        base_price = 50000.0
        base = PriceLocal(
            corp_code="005930",
            date=date(2024, 1, 2),
            close_price=base_price,
        )
        # 5거래일 후 종가: 50500 = 50000 * 1.01
        for i in range(3, 10):
            if i == 7:  # 5거래일 후가 2024-01-07
                price = 50500.0
            else:
                price = 50000.0 + (i - 2) * 50
            row = PriceLocal(
                corp_code="005930",
                date=date(2024, 1, i),
                close_price=price,
            )
            local_session.add(row)

        local_session.add(base)
        local_session.commit()

        result = label_disclosure(
            "005930",
            date(2024, 1, 1),
            "acc_no_001",
        )

        assert result is not None
        assert result["label"] == "중립"


class TestLabelBulk:
    """label_bulk 함수 테스트"""

    @patch("modules.price.labeler.label_disclosure")
    def test_label_bulk_multiple_disclosures(self, mock_label):
        """여러 공시 일괄 라벨링"""
        mock_label.side_effect = [
            {
                "disclosure_id": "acc_001",
                "label": "수혜",
                "change_pct": 2.5,
            },
            None,  # 실패
            {
                "disclosure_id": "acc_003",
                "label": "악재",
                "change_pct": -2.5,
            },
        ]

        disclosures = [
            {"corp_code": "005930", "disclosure_date": date(2024, 1, 1), "disclosure_id": "acc_001"},
            {"corp_code": "005930", "disclosure_date": date(2024, 1, 2), "disclosure_id": "acc_002"},
            {"corp_code": "005930", "disclosure_date": date(2024, 1, 3), "disclosure_id": "acc_003"},
        ]

        result = label_bulk(disclosures)

        assert len(result) == 2
        assert result[0]["label"] == "수혜"
        assert result[1]["label"] == "악재"

    @patch("modules.price.labeler.label_disclosure")
    def test_label_bulk_empty_list(self, mock_label):
        """빈 리스트"""
        result = label_bulk([])

        assert result == []
        mock_label.assert_not_called()


class TestLabelSummary:
    """label_summary 함수 테스트"""

    @patch("modules.price.labeler.get_local_session")
    def test_label_summary_all_labels(self, mock_get_session, local_session):
        """모든 라벨 분포 조회"""
        mock_get_session.return_value = local_session

        rows = [
            PriceLocal(corp_code="005930", date=date(2024, 1, 1), label="수혜"),
            PriceLocal(corp_code="005930", date=date(2024, 1, 2), label="수혜"),
            PriceLocal(corp_code="005930", date=date(2024, 1, 3), label="악재"),
            PriceLocal(corp_code="005930", date=date(2024, 1, 4), label="중립"),
            PriceLocal(corp_code="005930", date=date(2024, 1, 5), label=None),
        ]
        local_session.add_all(rows)
        local_session.commit()

        result = label_summary()

        assert result["수혜"] == 2
        assert result["악재"] == 1
        assert result["중립"] == 1
        assert result["미라벨"] == 1
        assert result["total"] == 5

    @patch("modules.price.labeler.get_local_session")
    def test_label_summary_by_corp_code(self, mock_get_session, local_session):
        """특정 기업 라벨 분포"""
        mock_get_session.return_value = local_session

        rows = [
            PriceLocal(corp_code="005930", date=date(2024, 1, 1), label="수혜"),
            PriceLocal(corp_code="005930", date=date(2024, 1, 2), label="악재"),
            PriceLocal(corp_code="247540", date=date(2024, 1, 1), label="수혜"),
        ]
        local_session.add_all(rows)
        local_session.commit()

        result = label_summary("005930")

        assert result["수혜"] == 1
        assert result["악재"] == 1
        assert result["total"] == 2

    @patch("modules.price.labeler.get_local_session")
    def test_label_summary_empty_db(self, mock_get_session, local_session):
        """빈 DB"""
        mock_get_session.return_value = local_session

        result = label_summary()

        assert result["수혜"] == 0
        assert result["악재"] == 0
        assert result["중립"] == 0
        assert result["미라벨"] == 0
        assert result["total"] == 0
