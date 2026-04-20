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
    # test_smoke 모듈 객체를 sys.modules에서 찾아 name binding 복원
    # tests/__init__.py 없으면 'test_smoke', 있으면 'tests.test_smoke'
    smoke_mod = sys.modules.get("test_smoke") or sys.modules.get("tests.test_smoke")
    if smoke_mod is not None:
        for attr in ("FinancialData", "DisclosureData", "RelationData", "PriceData"):
            real_cls = getattr(_real_shared_models, attr, None)
            if real_cls is not None:
                monkeypatch.setattr(smoke_mod, attr, real_cls)
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
