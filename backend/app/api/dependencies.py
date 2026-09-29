from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.services.orchestration import SearchOrchestrator


def get_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_orchestrator(request: Request) -> SearchOrchestrator:
    return request.app.state.orchestrator