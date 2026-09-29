from collections.abc import Callable

from fastapi import FastAPI

from backend.app.api.routes.searches import router as searches_router
from backend.app.api.routes.health import router as health_router
from backend.app.core.config import get_settings
from backend.app.database.session import SessionLocal
from backend.app.providers.factory import ProviderFactory, default_provider_factory
from backend.app.services.orchestration import SearchOrchestrator


def create_app(
    *,
    provider_factory: ProviderFactory | None = None,
    session_factory: Callable = SessionLocal,
) -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(searches_router, prefix=settings.api_prefix)
    application.state.session_factory = session_factory
    application.state.orchestrator = SearchOrchestrator(
        session_factory,
        provider_factory or default_provider_factory,
    )
    return application


app = create_app()