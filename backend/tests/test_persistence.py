from datetime import datetime, timezone

from sqlalchemy import func, inspect, select

from backend.app.database.session import create_database_engine
from backend.app.models.entities import Lead, Search, SearchRun
from backend.app.models.enums import SearchRunStatus, SearchStatus, SearchType
from backend.app.services.persistence import PersistenceService
from scraper.people.models import PeopleSearchResult


SEARCH_URL = "https://www.linkedin.com/search/results/people/?keywords=synthetic%20founder&geoUrn=123"


def make_result(
    profile_url: str | None = "https://www.linkedin.com/in/synthetic-person/",
    *,
    name: str | None = "Synthetic Person",
    location: str | None = "Synthetic City",
    company: str | None = "Synthetic Systems",
) -> PeopleSearchResult:
    return PeopleSearchResult(
        person_name=name,
        person_title="Founder",
        headline="Founder at Synthetic Systems",
        company_name=company,
        location=location,
        linkedin_profile_url=profile_url,
        raw_data={"fixture": True},
    )


def test_create_search_run_lead_and_relationships(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)
    run = service.create_search_run(db_session, search, "fixture-provider", pages_requested=3)
    lead, created = service.save_lead(db_session, search, make_result())
    db_session.commit()

    assert created is True
    assert search.search_url == SEARCH_URL
    assert search.search_type is SearchType.PEOPLE
    assert search.status is SearchStatus.QUEUED
    assert run.search is search
    assert lead.search is search
    assert search.search_runs == [run]
    assert search.leads == [lead]
    assert lead.raw_data == {"fixture": True}
    assert lead.created_at.tzinfo is not None
    assert lead.created_at.utcoffset() == timezone.utc.utcoffset(lead.created_at)


def test_nullable_fields_remain_null(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)
    result = PeopleSearchResult()

    lead, _ = service.save_lead(db_session, search, result)
    db_session.commit()

    assert lead.person_name is None
    assert lead.company_name is None
    assert lead.linkedin_profile_url is None
    assert lead.raw_data == {}


def test_status_and_run_progress_are_persisted(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)
    run = service.create_search_run(db_session, search, "fixture-provider")

    service.update_search_status(db_session, search, SearchStatus.RUNNING)
    service.update_search_run(
        db_session,
        run,
        status=SearchRunStatus.RUNNING,
        pages_processed=2,
        records_found=20,
        records_saved=18,
    )
    db_session.commit()

    assert search.started_at is not None
    assert run.started_at is not None
    assert run.pages_processed == 2
    assert run.records_found == 20
    assert run.records_saved == 18


def test_deduplicates_profile_within_search(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)

    first, first_created = service.save_lead(db_session, search, make_result())
    second, second_created = service.save_lead(
        db_session,
        search,
        make_result("https://linkedin.com/in/synthetic-person/?trk=duplicate"),
    )
    db_session.commit()

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert db_session.scalar(select(func.count(Lead.id))) == 1


def test_same_profile_is_allowed_in_different_searches(db_session) -> None:
    service = PersistenceService()
    first_search = service.create_search(db_session, SEARCH_URL)
    second_search = service.create_search(
        db_session,
        "https://www.linkedin.com/search/results/people/?keywords=another",
    )

    _, first_created = service.save_lead(db_session, first_search, make_result())
    _, second_created = service.save_lead(db_session, second_search, make_result())
    db_session.commit()

    assert first_created is True
    assert second_created is True
    assert db_session.scalar(select(func.count(Lead.id))) == 2


def test_fallback_deduplication_requires_all_identity_fields(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)
    first = make_result(None)
    second = make_result(None, name="Different Person")

    _, first_created = service.save_lead(db_session, search, first)
    _, second_created = service.save_lead(db_session, search, second)
    db_session.commit()

    assert first_created is True
    assert second_created is True
    assert db_session.scalar(select(func.count(Lead.id))) == 2


def test_delete_search_removes_runs_and_leads(db_session) -> None:
    service = PersistenceService()
    search = service.create_search(db_session, SEARCH_URL)
    service.create_search_run(db_session, search, "fixture-provider")
    service.save_lead(db_session, search, make_result())
    db_session.commit()

    service.delete_search(db_session, search)
    db_session.commit()

    assert db_session.scalar(select(func.count(Search.id))) == 0
    assert db_session.scalar(select(func.count(SearchRun.id))) == 0
    assert db_session.scalar(select(func.count(Lead.id))) == 0


def test_transaction_rolls_back_search_and_lead(db_session) -> None:
    service = PersistenceService()

    try:
        with db_session.begin():
            search = service.create_search(db_session, SEARCH_URL)
            service.save_lead(db_session, search, make_result())
            raise RuntimeError("synthetic failure")
    except RuntimeError:
        pass

    assert db_session.scalar(select(func.count(Search.id))) == 0
    assert db_session.scalar(select(func.count(Lead.id))) == 0


def test_migration_creates_all_tables_on_fresh_database(tmp_path, monkeypatch) -> None:
    from alembic import command
    from alembic.config import Config
    from backend.app.core.config import get_settings

    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        engine = create_database_engine(database_url)
        table_names = set(inspect(engine).get_table_names())
        assert {"searches", "search_runs", "leads", "alembic_version"} <= table_names
        engine.dispose()
    finally:
        get_settings.cache_clear()