"""pytest 공용 fixture.

tests/ 하위 모든 테스트 파일이 import 없이 여기의 fixture를 사용합니다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.db import Base
import shared.models  # SQLAlchemy 모델 등록 (side effect)  # noqa: F401


@pytest.fixture
def in_memory_session():
    """in-memory SQLite DB 세션. 테스트마다 깨끗한 상태로 초기화."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
