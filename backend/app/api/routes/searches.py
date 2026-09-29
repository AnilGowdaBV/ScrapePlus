from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_orchestrator, get_session
from backend.app.models.entities import Search
from backend.app.schemas.searches import (
    CreateSearchRequest,
    CreateSearchResponse,
    LeadResult,
    PaginatedLeadResults,
    PaginatedSearches,
    SearchDetail,
    SearchRunStatusResponse,
    SearchSummary,
)
from backend.app.services.export import export_leads_csv, export_leads_xlsx
from backend.app.services.orchestration import SearchOrchestrator



router = APIRouter(prefix="/searches", tags=["searches"])


def _latest_run(orchestrator: SearchOrchestrator, session: Session, search_id: int):
    return orchestrator.latest_run(session, search_id)


def _summary(
    search: Search,
    orchestrator: SearchOrchestrator,
    session: Session,
) -> SearchSummary:
    persistence = orchestrator.persistence
    latest = _latest_run(orchestrator, session, search.id)
    return SearchSummary(
        id=search.id,
        search_url=search.search_url,
        search_type=search.search_type,
        status=search.status,
        created_at=search.created_at,
        total_leads=persistence.leads.count_for_search(session, search.id),
        latest_run=SearchRunStatusResponse.model_validate(latest) if latest else None,
    )


@router.post("", response_model=CreateSearchResponse, status_code=status.HTTP_202_ACCEPTED)
def create_search(
    payload: CreateSearchRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> CreateSearchResponse:
    persistence = orchestrator.persistence
    try:
        search = persistence.create_search(session, payload.search_url)
        run = persistence.create_search_run(
            session,
            search,
            orchestrator.provider_name,
            pages_requested=payload.max_pages,
        )
        session.commit()
    except Exception as error:
        session.rollback()
        raise HTTPException(status_code=500, detail="Could not create search") from error

    cookie = payload.session_cookie or request.headers.get("X-LinkedIn-Cookie")
    background_tasks.add_task(orchestrator.run, search.id, run.id, payload.max_pages, cookie)
    return CreateSearchResponse(search_id=search.id, run_id=run.id, status=search.status)


@router.get("", response_model=PaginatedSearches)
def list_searches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> PaginatedSearches:
    search_repository = orchestrator.persistence.searches
    searches = search_repository.list_page(session, limit=page_size, offset=(page - 1) * page_size)
    return PaginatedSearches(
        items=[_summary(search, orchestrator, session) for search in searches],
        page=page,
        page_size=page_size,
        total=search_repository.count(session),
    )


@router.get("/{search_id}", response_model=SearchDetail)
def get_search(
    search_id: int,
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> SearchDetail:
    search = orchestrator.persistence.searches.get(session, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    summary = _summary(search, orchestrator, session)
    return SearchDetail(
        **summary.model_dump(),
        updated_at=search.updated_at,
        started_at=search.started_at,
        completed_at=search.completed_at,
        total_results=search.total_results,
        error_message=search.error_message,
    )


@router.get("/{search_id}/results", response_model=PaginatedLeadResults)
def get_results(
    search_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> PaginatedLeadResults:
    if orchestrator.persistence.searches.get(session, search_id) is None:
        raise HTTPException(status_code=404, detail="Search not found")
    leads = orchestrator.persistence.list_leads(
        session, search_id, limit=page_size, offset=(page - 1) * page_size
    )
    return PaginatedLeadResults(
        items=[LeadResult.model_validate(lead) for lead in leads],
        page=page,
        page_size=page_size,
        total=orchestrator.persistence.leads.count_for_search(session, search_id),
    )


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search(
    search_id: int,
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> Response:
    search = orchestrator.persistence.searches.get(session, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    orchestrator.persistence.delete_search(session, search)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{search_id}/export/csv")
def export_csv(
    search_id: int,
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> Response:
    search = orchestrator.persistence.searches.get(session, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    leads = orchestrator.persistence.list_all_leads(session, search_id)
    csv_bytes = export_leads_csv(leads)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="leads_search_{search_id}.csv"'},
    )


@router.get("/{search_id}/export/xlsx")
def export_xlsx(
    search_id: int,
    session: Session = Depends(get_session),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> Response:
    search = orchestrator.persistence.searches.get(session, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    leads = orchestrator.persistence.list_all_leads(session, search_id)
    xlsx_bytes = export_leads_xlsx(leads)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="leads_search_{search_id}.xlsx"'},
    )