from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.entities import SearchRun
from backend.app.models.enums import SearchRunStatus


class SearchRunRepository:
    def create(
        self,
        session: Session,
        search_id: int,
        provider: str,
        *,
        pages_requested: int = 0,
    ) -> SearchRun:
        search_run = SearchRun(
            search_id=search_id,
            provider=provider,
            pages_requested=pages_requested,
        )
        session.add(search_run)
        session.flush()
        return search_run

    def update_progress(
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
        if status is not None:
            search_run.status = status
            if status is SearchRunStatus.RUNNING and search_run.started_at is None:
                search_run.started_at = datetime.now(timezone.utc)
            if status in {
                SearchRunStatus.COMPLETED,
                SearchRunStatus.PARTIAL,
                SearchRunStatus.FAILED,
                SearchRunStatus.CANCELLED,
            }:
                search_run.completed_at = datetime.now(timezone.utc)
        if pages_processed is not None:
            search_run.pages_processed = pages_processed
        if records_found is not None:
            search_run.records_found = records_found
        if records_saved is not None:
            search_run.records_saved = records_saved
        if error_message is not None:
            search_run.error_message = error_message
        session.flush()
        return search_run