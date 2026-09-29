from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import Search
from backend.app.models.enums import SearchStatus, SearchType
from scraper.people.url import validate_people_search_url


class SearchRepository:
    def create(
        self,
        session: Session,
        search_url: str,
        *,
        search_type: SearchType = SearchType.PEOPLE,
    ) -> Search:
        exact_url = validate_people_search_url(search_url)
        search = Search(search_url=exact_url, search_type=search_type)
        session.add(search)
        session.flush()
        return search

    def get(self, session: Session, search_id: int) -> Search | None:
        return session.get(Search, search_id)

    def list_page(
        self,
        session: Session,
        *,
        limit: int,
        offset: int,
    ) -> list[Search]:
        statement = select(Search).order_by(Search.created_at.desc(), Search.id.desc()).limit(limit).offset(offset)
        return list(session.scalars(statement))

    def count(self, session: Session) -> int:
        return int(session.scalar(select(func.count(Search.id))) or 0)

    def update_status(
        self,
        session: Session,
        search: Search,
        status: SearchStatus,
        *,
        error_message: str | None = None,
    ) -> Search:
        now = datetime.now(timezone.utc)
        search.status = status
        search.error_message = error_message
        if status is SearchStatus.RUNNING and search.started_at is None:
            search.started_at = now
        if status in {
            SearchStatus.COMPLETED,
            SearchStatus.PARTIAL,
            SearchStatus.FAILED,
            SearchStatus.CANCELLED,
        }:
            search.completed_at = now
        session.flush()
        return search

    def delete(self, session: Session, search: Search) -> None:
        session.delete(search)
        session.flush()