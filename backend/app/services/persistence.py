from sqlalchemy.orm import Session

from backend.app.models.entities import Lead, Search, SearchRun
from backend.app.models.enums import SearchRunStatus, SearchStatus, SearchType
from backend.app.repositories.leads import LeadRepository
from backend.app.repositories.search_runs import SearchRunRepository
from backend.app.repositories.searches import SearchRepository
from scraper.people.models import PeopleSearchResult


class PersistenceService:
    def __init__(self) -> None:
        self.searches = SearchRepository()
        self.search_runs = SearchRunRepository()
        self.leads = LeadRepository()

    def create_search(self, session: Session, search_url: str) -> Search:
        return self.searches.create(session, search_url, search_type=SearchType.PEOPLE)

    def update_search_status(
        self,
        session: Session,
        search: Search,
        status: SearchStatus,
        *,
        error_message: str | None = None,
    ) -> Search:
        return self.searches.update_status(
            session, search, status, error_message=error_message
        )

    def create_search_run(
        self,
        session: Session,
        search: Search,
        provider: str,
        *,
        pages_requested: int = 0,
    ) -> SearchRun:
        return self.search_runs.create(
            session, search.id, provider, pages_requested=pages_requested
        )

    def update_search_run(
        self,
        session: Session,
        search_run: SearchRun,
        *,
        status: SearchRunStatus | None = None,
        pages_processed: int | None = None,
        records_found: int | None = None,
        records_saved: int | None = None,
        error_message: str | None = None,
    ) -> SearchRun:
        return self.search_runs.update_progress(
            session,
            search_run,
            status=status,
            pages_processed=pages_processed,
            records_found=records_found,
            records_saved=records_saved,
            error_message=error_message,
        )

    def save_lead(
        self,
        session: Session,
        search: Search,
        result: PeopleSearchResult,
        *,
        source: str = "people_search",
        external_id: str | None = None,
    ) -> tuple[Lead, bool]:
        return self.leads.save_result(
            session,
            search.id,
            result,
            source=source,
            external_id=external_id,
        )

    def list_leads(
        self,
        session: Session,
        search_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        return self.leads.list_for_search(
            session, search_id, limit=limit, offset=offset
        )

    def list_all_leads(self, session: Session, search_id: int) -> list[Lead]:
        return self.leads.list_all_for_search(session, search_id)

    def delete_search(self, session: Session, search: Search) -> None:
        self.searches.delete(session, search)