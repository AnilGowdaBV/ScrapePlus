from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base
from backend.app.database.types import UTCDateTime
from backend.app.models.enums import SearchRunStatus, SearchStatus, SearchType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Search(Base):
    __tablename__ = "searches"
    __table_args__ = (Index("ix_searches_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_url: Mapped[str] = mapped_column(Text, nullable=False)
    search_type: Mapped[SearchType] = mapped_column(
        Enum(SearchType, native_enum=False, length=20), nullable=False, default=SearchType.PEOPLE
    )
    status: Mapped[SearchStatus] = mapped_column(
        Enum(SearchStatus, native_enum=False, length=20),
        nullable=False,
        default=SearchStatus.QUEUED,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    total_results: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    search_runs: Mapped[list["SearchRun"]] = relationship(
        back_populates="search", cascade="all, delete-orphan", passive_deletes=True
    )
    leads: Mapped[list["Lead"]] = relationship(
        back_populates="search", cascade="all, delete-orphan", passive_deletes=True
    )


class SearchRun(Base):
    __tablename__ = "search_runs"
    __table_args__ = (Index("ix_search_runs_search_id", "search_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_id: Mapped[int] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    pages_requested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SearchRunStatus] = mapped_column(
        Enum(SearchRunStatus, native_enum=False, length=20),
        nullable=False,
        default=SearchRunStatus.QUEUED,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    search: Mapped[Search] = relationship(back_populates="search_runs")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("search_id", "linkedin_profile_url", name="uq_leads_search_profile_url"),
        UniqueConstraint("search_id", "external_id", name="uq_leads_search_external_id"),
        Index("ix_leads_search_id", "search_id"),
        Index("ix_leads_profile_url", "linkedin_profile_url"),
        Index("ix_leads_person_name", "person_name"),
        Index("ix_leads_company_name", "company_name"),
        Index("ix_leads_location", "location"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_id: Mapped[int] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    person_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_degree: Mapped[str | None] = mapped_column(String(50), nullable=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    search: Mapped[Search] = relationship(back_populates="leads")