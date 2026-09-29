from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import Search, SearchRun
from backend.app.models.enums import SearchRunStatus, SearchStatus
from backend.app.providers.factory import ProviderFactory
from backend.app.services.persistence import PersistenceService
from scraper.people.page_state import PeopleSearchAccessError


SessionFactory = Callable[[], Session]


class SearchOrchestrator:
    def __init__(
        self,
        session_factory: SessionFactory,
        provider_factory: ProviderFactory,
        persistence: PersistenceService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.provider_factory = provider_factory
        self.persistence = persistence or PersistenceService()

    @property
    def provider_name(self) -> str:
        return getattr(self.provider_factory, "provider_name", "people_provider")

    async def run(
        self,
        search_id: int,
        run_id: int,
        max_pages: int,
        cookie: str | None = None,
    ) -> None:
        session = self.session_factory()
        try:
            search = session.get(Search, search_id)
            search_run = session.get(SearchRun, run_id)
            if search is None or search_run is None:
                return

            self.persistence.update_search_status(session, search, SearchStatus.RUNNING)
            self.persistence.update_search_run(
                session,
                search_run,
                status=SearchRunStatus.RUNNING,
            )
            session.commit()

            records_found = 0
            records_saved = 0
            try:
                provider = self.provider_factory(cookie=cookie)
            except TypeError:
                provider = self.provider_factory()
            try:
                async for result in provider.search(search.search_url, max_pages=max_pages):
                    records_found += 1
                    _, created = self.persistence.save_lead(session, search, result)
                    if created:
                        records_saved += 1
                    self.persistence.update_search_run(
                        session,
                        search_run,
                        records_found=records_found,
                        records_saved=records_saved,
                    )
                    session.commit()

                diagnostics = getattr(provider, "diagnostics", [])
                pages_processed = getattr(provider, "pages_processed", 0)
                final_status = (
                    SearchRunStatus.PARTIAL if diagnostics else SearchRunStatus.COMPLETED
                )
                search_status = (
                    SearchStatus.PARTIAL if diagnostics else SearchStatus.COMPLETED
                )
                self.persistence.update_search_run(
                    session,
                    search_run,
                    status=final_status,
                    pages_processed=pages_processed,
                    records_found=records_found,
                    records_saved=records_saved,
                    error_message=(
                        f"{len(diagnostics)} record diagnostics" if diagnostics else None
                    ),
                )
                search.total_results = records_saved
                self.persistence.update_search_status(session, search, search_status)
                session.commit()
            except PeopleSearchAccessError as error:
                final_status = SearchRunStatus.PARTIAL if records_saved else SearchRunStatus.FAILED
                search_status = SearchStatus.PARTIAL if records_saved else SearchStatus.FAILED
                self.persistence.update_search_run(
                    session,
                    search_run,
                    status=final_status,
                    pages_processed=getattr(provider, "pages_processed", 0),
                    records_found=records_found,
                    records_saved=records_saved,
                    error_message=f"{error.state}: {error}",
                )
                search.total_results = records_saved
                self.persistence.update_search_status(
                    session,
                    search,
                    search_status,
                    error_message=f"{error.state}: {error}",
                )
                session.commit()
            except Exception as error:
                session.rollback()
                search = session.get(Search, search_id)
                search_run = session.get(SearchRun, run_id)
                if search is not None and search_run is not None:
                    self.persistence.update_search_run(
                        session,
                        search_run,
                        status=SearchRunStatus.FAILED,
                        records_found=records_found,
                        records_saved=records_saved,
                        error_message=str(error),
                    )
                    search.total_results = records_saved
                    self.persistence.update_search_status(
                        session,
                        search,
                        SearchStatus.FAILED,
                        error_message=str(error),
                    )
                    session.commit()
        finally:
            session.close()

    def latest_run(self, session: Session, search_id: int) -> SearchRun | None:
        statement = (
            select(SearchRun)
            .where(SearchRun.search_id == search_id)
            .order_by(SearchRun.id.desc())
            .limit(1)
        )
        return session.scalar(statement)