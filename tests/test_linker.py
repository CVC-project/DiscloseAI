"""공시 ↔ 주가 연결 모듈 (linker) 테스트"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, Column, String, Integer, Float, Date
from sqlalchemy.orm import sessionmaker, declarative_base

# Shared models를 테스트용으로 정의
SharedBase = declarative_base()


class DisclosureData(SharedBase):
    """Test용 DisclosureData"""
    __tablename__ = "disclosure_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    disclosure_id = Column(String, unique=True, index=True)
    corp_code = Column(String, nullable=False, index=True)
    corp_name = Column(String)
    disclosure_date = Column(Date)
    disclosure_type = Column(String)
    title = Column(String)
    amount = Column(Float)
    summary = Column(String)


class PriceData(SharedBase):
    """Test용 PriceData"""
    __tablename__ = "price_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    close_price = Column(Float)
    daily_return = Column(Float)
    post_disclosure_5d = Column(Float)
    label = Column(String)
    disclosure_id = Column(String)


# shared.models을 테스트 모델로 대체
import sys
shared_models_module = MagicMock()
shared_models_module.DisclosureData = DisclosureData
shared_models_module.PriceData = PriceData
shared_models_module.Base = SharedBase
sys.modules['shared.models'] = shared_models_module

# shared.db도 mock
shared_db_module = MagicMock()
sys.modules['shared.db'] = shared_db_module


from modules.price.linker import (
    _detect_market,
    fetch_unlinked_disclosures,
    push_to_shared,
    link_single,
    run_pipeline,
)


@pytest.fixture
def shared_session():
    """shared DB in-memory 세션"""
    engine = create_engine("sqlite:///:memory:")
    SharedBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDetectMarket:
    """_detect_market 함수 테스트"""

    def test_detect_market_kospi_default(self):
        """현재 구현: 항상 KOSPI 반환"""
        result = _detect_market("005930")
        assert result == "KOSPI"

    def test_detect_market_kosdaq_code(self):
        """0으로 시작하지 않는 코드 → KOSDAQ 추정"""
        result = _detect_market("247540")
        assert result == "KOSDAQ"

    def test_detect_market_various_codes(self):
        """다양한 코드 -> KOSPI 기본값"""
        for code in ["000080", "035420", "051910"]:
            assert _detect_market(code) == "KOSPI"


class TestFetchUnlinkedDisclosures:
    """fetch_unlinked_disclosures 함수 테스트"""

    @patch("modules.price.linker.get_session")
    def test_fetch_unlinked_disclosures_success(self, mock_get_session, shared_session):
        """미연결 공시 조회"""
        mock_get_session.return_value = shared_session

        # 미연결 공시
        disclosure1 = DisclosureData(
            disclosure_id="acc_001",
            corp_code="005930",
            disclosure_date=date(2024, 1, 1),
        )
        # 이미 연결된 공시
        disclosure2 = DisclosureData(
            disclosure_id="acc_002",
            corp_code="005930",
            disclosure_date=date(2024, 1, 2),
        )
        price_data = PriceData(
            corp_code="005930",
            date=date(2024, 1, 2),
            disclosure_id="acc_002",
        )

        shared_session.add_all([disclosure1, disclosure2, price_data])
        shared_session.commit()

        result = fetch_unlinked_disclosures(limit=10)

        assert len(result) == 1
        assert result[0].disclosure_id == "acc_001"

    @patch("modules.price.linker.get_session")
    def test_fetch_unlinked_disclosures_limit(self, mock_get_session, shared_session):
        """limit 파라미터 검증"""
        mock_get_session.return_value = shared_session

        # 5개 공시 생성
        for i in range(5):
            d = DisclosureData(
                disclosure_id=f"acc_{i:03d}",
                corp_code="005930",
                disclosure_date=date(2024, 1, 1) + timedelta(days=i),
            )
            shared_session.add(d)
        shared_session.commit()

        result = fetch_unlinked_disclosures(limit=3)

        assert len(result) == 3

    @patch("modules.price.linker.get_session")
    def test_fetch_unlinked_disclosures_empty(self, mock_get_session, shared_session):
        """미연결 공시 없음"""
        mock_get_session.return_value = shared_session

        result = fetch_unlinked_disclosures(limit=10)

        assert result == []

    @patch("modules.price.linker.get_session")
    def test_fetch_unlinked_disclosures_no_date(
        self, mock_get_session, shared_session
    ):
        """disclosure_date 없는 행은 제외"""
        mock_get_session.return_value = shared_session

        # 유효한 공시
        valid = DisclosureData(
            disclosure_id="acc_001",
            corp_code="005930",
            disclosure_date=date(2024, 1, 1),
        )
        # 날짜 없음
        no_date = DisclosureData(
            disclosure_id="acc_002",
            corp_code="005930",
            disclosure_date=None,
        )

        shared_session.add_all([valid, no_date])
        shared_session.commit()

        result = fetch_unlinked_disclosures(limit=10)

        assert len(result) == 1
        assert result[0].disclosure_id == "acc_001"


class TestPushToShared:
    """push_to_shared 함수 테스트"""

    @patch("modules.price.linker.get_session")
    def test_push_to_shared_success(self, mock_get_session, shared_session):
        """주가 데이터 저장"""
        mock_get_session.return_value = shared_session

        label_result = {
            "disclosure_id": "acc_001",
            "base_date": date(2024, 1, 2),
            "label": "수혜",
            "change_pct": 2.5,
        }
        prices = [
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
            {
                "corp_code": "005930",
                "date": date(2024, 1, 3),
                "close_price": 52000.0,
                "daily_return": 1.96,
            },
        ]

        saved = push_to_shared("005930", label_result, prices)

        assert saved == 3
        rows = shared_session.query(PriceData).all()
        assert len(rows) == 3
        # base_date에만 라벨 기록
        base_row = next(r for r in rows if r.date == date(2024, 1, 2))
        assert base_row.label == "수혜"
        assert base_row.disclosure_id == "acc_001"
        # 다른 날짜는 라벨 없음
        other_row = next(r for r in rows if r.date == date(2024, 1, 1))
        assert other_row.label is None
        assert other_row.disclosure_id is None

    @patch("modules.price.linker.get_session")
    def test_push_to_shared_duplicate_skip(self, mock_get_session, shared_session):
        """중복 (corp_code+date) 건너뜀"""
        mock_get_session.return_value = shared_session

        # 기존 데이터
        existing = PriceData(
            corp_code="005930",
            date=date(2024, 1, 1),
            close_price=50000.0,
        )
        shared_session.add(existing)
        shared_session.commit()

        label_result = {
            "disclosure_id": "acc_001",
            "base_date": date(2024, 1, 2),
            "label": "수혜",
            "change_pct": 2.5,
        }
        prices = [
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

        saved = push_to_shared("005930", label_result, prices)

        assert saved == 1  # 1건만 저장
        rows = shared_session.query(PriceData).all()
        assert len(rows) == 2
        # 기존 데이터 유지
        first_row = next(r for r in rows if r.date == date(2024, 1, 1))
        assert first_row.close_price == 50000.0

    @patch("modules.price.linker.get_session")
    def test_push_to_shared_empty_prices(self, mock_get_session, shared_session):
        """빈 주가 리스트"""
        mock_get_session.return_value = shared_session

        label_result = {
            "disclosure_id": "acc_001",
            "base_date": date(2024, 1, 2),
            "label": "수혜",
            "change_pct": 2.5,
        }

        saved = push_to_shared("005930", label_result, [])

        assert saved == 0

    @patch("modules.price.linker.get_session")
    def test_push_to_shared_multiple_corps(self, mock_get_session, shared_session):
        """여러 기업 데이터 저장"""
        mock_get_session.return_value = shared_session

        # 005930 처리
        label_result_1 = {
            "disclosure_id": "acc_001",
            "base_date": date(2024, 1, 2),
            "label": "수혜",
            "change_pct": 2.5,
        }
        prices_1 = [
            {
                "corp_code": "005930",
                "date": date(2024, 1, 1),
                "close_price": 50000.0,
                "daily_return": None,
            },
        ]

        saved_1 = push_to_shared("005930", label_result_1, prices_1)

        # 247540 처리
        label_result_2 = {
            "disclosure_id": "acc_002",
            "base_date": date(2024, 1, 2),
            "label": "악재",
            "change_pct": -2.5,
        }
        prices_2 = [
            {
                "corp_code": "247540",
                "date": date(2024, 1, 1),
                "close_price": 30000.0,
                "daily_return": None,
            },
        ]

        saved_2 = push_to_shared("247540", label_result_2, prices_2)

        assert saved_1 == 1
        assert saved_2 == 1
        rows = shared_session.query(PriceData).all()
        assert len(rows) == 2


class TestLinkSingle:
    """link_single 함수 테스트"""

    @patch("modules.price.linker.push_to_shared")
    @patch("modules.price.linker.label_disclosure")
    @patch("modules.price.linker.collect_prices")
    def test_link_single_success(
        self, mock_collect, mock_label, mock_push
    ):
        """단일 공시 처리 성공"""
        disclosure = MagicMock()
        disclosure.corp_code = "005930"
        disclosure.disclosure_date = date(2024, 1, 1)
        disclosure.disclosure_id = "acc_001"

        mock_label.return_value = {
            "disclosure_id": "acc_001",
            "label": "수혜",
            "change_pct": 2.5,
        }
        mock_push.return_value = 10

        result = link_single(disclosure, market="KOSPI")

        assert result is True
        mock_collect.assert_called_once()
        mock_label.assert_called_once()
        mock_push.assert_called_once()

    @patch("modules.price.linker.push_to_shared")
    @patch("modules.price.linker.label_disclosure")
    @patch("modules.price.linker.collect_prices")
    def test_link_single_labeling_fails(
        self, mock_collect, mock_label, mock_push
    ):
        """라벨링 실패"""
        disclosure = MagicMock()
        disclosure.corp_code = "005930"
        disclosure.disclosure_date = date(2024, 1, 1)
        disclosure.disclosure_id = "acc_001"

        mock_label.return_value = None

        result = link_single(disclosure)

        assert result is False
        mock_push.assert_not_called()

    @patch("modules.price.linker.push_to_shared")
    @patch("modules.price.linker.label_disclosure")
    @patch("modules.price.linker.collect_prices")
    def test_link_single_auto_detect_market(
        self, mock_collect, mock_label, mock_push
    ):
        """시장 자동 감지"""
        disclosure = MagicMock()
        disclosure.corp_code = "005930"
        disclosure.disclosure_date = date(2024, 1, 1)
        disclosure.disclosure_id = "acc_001"

        mock_label.return_value = {
            "disclosure_id": "acc_001",
            "label": "수혜",
            "change_pct": 2.5,
        }
        mock_push.return_value = 10

        link_single(disclosure)  # market 미지정

        call_args = mock_collect.call_args[0]
        assert call_args[1] == "KOSPI"  # 자동 감지된 기본값


class TestRunPipeline:
    """run_pipeline 함수 테스트"""

    @patch("modules.price.linker.link_single")
    @patch("modules.price.linker.fetch_unlinked_disclosures")
    def test_run_pipeline_all_success(
        self, mock_fetch, mock_link
    ):
        """파이프라인 모든 공시 성공"""
        disclosures = [
            MagicMock(disclosure_id="acc_001"),
            MagicMock(disclosure_id="acc_002"),
        ]
        mock_fetch.return_value = disclosures
        mock_link.side_effect = [True, True]

        result = run_pipeline(limit=10)

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0

    @patch("modules.price.linker.link_single")
    @patch("modules.price.linker.fetch_unlinked_disclosures")
    def test_run_pipeline_partial_failure(
        self, mock_fetch, mock_link
    ):
        """일부 공시 실패"""
        disclosures = [
            MagicMock(disclosure_id="acc_001"),
            MagicMock(disclosure_id="acc_002"),
            MagicMock(disclosure_id="acc_003"),
        ]
        mock_fetch.return_value = disclosures
        mock_link.side_effect = [True, False, True]

        result = run_pipeline(limit=10)

        assert result["total"] == 3
        assert result["success"] == 2
        assert result["failed"] == 1

    @patch("modules.price.linker.link_single")
    @patch("modules.price.linker.fetch_unlinked_disclosures")
    def test_run_pipeline_exception_handling(
        self, mock_fetch, mock_link
    ):
        """예외 발생하면 계속 진행"""
        disclosures = [
            MagicMock(disclosure_id="acc_001"),
            MagicMock(disclosure_id="acc_002"),
        ]
        mock_fetch.return_value = disclosures
        mock_link.side_effect = [Exception("Network error"), True]

        result = run_pipeline(limit=10)

        assert result["total"] == 2
        assert result["success"] == 1
        assert result["failed"] == 1

    @patch("modules.price.linker.link_single")
    @patch("modules.price.linker.fetch_unlinked_disclosures")
    def test_run_pipeline_empty(self, mock_fetch, mock_link):
        """미연결 공시 없음"""
        mock_fetch.return_value = []

        result = run_pipeline(limit=10)

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0
        mock_link.assert_not_called()

    @patch("modules.price.linker.link_single")
    @patch("modules.price.linker.fetch_unlinked_disclosures")
    def test_run_pipeline_limit_parameter(
        self, mock_fetch, mock_link
    ):
        """limit 파라미터 전달"""
        mock_fetch.return_value = []

        run_pipeline(limit=100)

        mock_fetch.assert_called_once_with(limit=100)
