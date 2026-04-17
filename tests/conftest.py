"""테스트용 공유 fixtures — pytest"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.price.models import Base


@pytest.fixture
def db_session():
    """in-memory SQLite DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
