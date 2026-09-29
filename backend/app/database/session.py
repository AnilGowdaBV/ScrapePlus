from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
	cursor = dbapi_connection.cursor()
	cursor.execute("PRAGMA foreign_keys=ON")
	cursor.close()


def create_database_engine(database_url: str) -> Engine:
	connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
	database_engine = create_engine(database_url, connect_args=connect_args)
	if database_url.startswith("sqlite"):
		event.listen(database_engine, "connect", _enable_sqlite_foreign_keys)
	return database_engine


settings = get_settings()
engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()