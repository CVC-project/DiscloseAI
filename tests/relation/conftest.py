"""tests/relation/ 공용 fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def dart_hyslr_005930() -> dict:
    return json.loads((FIXTURES_DIR / "dart_hyslrSttus_005930.json").read_text("utf-8"))


@pytest.fixture
def dart_invst_005930() -> dict:
    return json.loads(
        (FIXTURES_DIR / "dart_otrCprInvstmntSttus_005930.json").read_text("utf-8")
    )


@pytest.fixture
def in_memory_session():
    """각 테스트마다 fresh 메모리 SQLite + 스키마 생성."""
    from modules.relation.storage.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
