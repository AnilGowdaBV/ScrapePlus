import pytest
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.base import Base
from backend.app.database.session import create_database_engine


@pytest.fixture
def db_session(tmp_path) -> Session:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()