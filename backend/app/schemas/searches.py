from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.enums import SearchRunStatus, SearchStatus, SearchType
from scraper.people.url import InvalidPeopleSearchUrl, validate_people_search_url


class CreateSearchRequest(BaseModel):
    search_url: str
    max_pages: int = Field(default=1, ge=1, le=1000)
    session_cookie: str | None = None

    @field_validator("search_url")
    @classmethod
    def validate_search_url(cls, value: str) -> str:
        try:
            return validate_people_search_url(value)
        except InvalidPeopleSearchUrl as error:
            raise ValueError(str(error)) from error


class CreateSearchResponse(BaseModel):
    search_id: int
    run_id: int
    status: SearchStatus


class SearchRunStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    status: SearchRunStatus
    started_at: datetime | None
    completed_at: datetime | None
    pages_requested: int
    pages_processed: int
    records_found: int
    records_saved: int
    error_message: str | None


class SearchSummary(BaseModel):
    id: int
    search_url: str
    search_type: SearchType
    status: SearchStatus
    created_at: datetime
    total_leads: int
    latest_run: SearchRunStatusResponse | None


class SearchDetail(SearchSummary):
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    total_results: int
    error_message: str | None


class LeadResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None
    person_name: str | None
    person_title: str | None
    headline: str | None
    company_name: str | None
    company_url: str | None
    linkedin_profile_url: str | None
    location: str | None
    profile_image_url: str | None
    connection_degree: str | None
    education: str | None


class PaginatedLeadResults(BaseModel):
    items: list[LeadResult]
    page: int
    page_size: int
    total: int


class PaginatedSearches(BaseModel):
    items: list[SearchSummary]
    page: int
    page_size: int
    total: int


class ErrorResponse(BaseModel):
    detail: str


class ProviderConfiguration(BaseModel):
    provider_name: str = "unconfigured"
    metadata: dict[str, Any] = Field(default_factory=dict)