"""pytest 공용 fixture.

tests/ 하위 모든 테스트 파일이 import 없이 여기의 fixture를 사용합니다.
"""

import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.db import Base as SharedBase
import shared.models as _real_shared_models  # 진짜 모듈 참조 보존 (test_linker가 오염 전에 저장)

from modules.price.models import Base as PriceBase


@pytest.fixture(autouse=True)
def _restore_shared_models(monkeypatch):
    """test_linker.py가 sys.modules['shared.models']를 MagicMock으로 교체한 뒤
    test_smoke.py의 module-level binding이 오염되는 것을 방지한다."""
    # sys.modules 복원
    monkeypatch.setitem(sys.modules, "shared.models", _real_shared_models)
    # test_smoke의 top-level name binding도 실제 클래스로 복원
    try:
        import tests.test_smoke as smoke_mod

        monkeypatch.setattr(
            smoke_mod, "FinancialData", _real_shared_models.FinancialData
        )
        monkeypatch.setattr(
            smoke_mod, "DisclosureData", _real_shared_models.DisclosureData
        )
        monkeypatch.setattr(
            smoke_mod, "RelationData", _real_shared_models.RelationData
        )
        monkeypatch.setattr(smoke_mod, "PriceData", _real_shared_models.PriceData)
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture
def in_memory_session():
    """in-memory SQLite DB 세션. 테스트마다 깨끗한 상태로 초기화."""
    engine = create_engine("sqlite:///:memory:")
    SharedBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def db_session():
    """price 모듈용 in-memory SQLite DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    PriceBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
