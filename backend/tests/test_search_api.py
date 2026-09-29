from collections.abc import AsyncIterator, Callable

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database.base import Base
from backend.app.main import create_app
from scraper.people.models import PeopleSearchResult
from scraper.providers.base import PeopleSearchProvider


SEARCH_URL = "https://www.linkedin.com/search/results/people/?keywords=synthetic&geoUrn=123"


class FakePeopleSearchProvider(PeopleSearchProvider):
    provider_name = "fake"

    def __init__(
        self,
        results: list[PeopleSearchResult] | None = None,
        error: Exception | None = None,
        diagnostics: list[object] | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.diagnostics = diagnostics or []
        self.pages_processed = 1

    async def search(
        self,
        search_url: str,
        max_pages: int | None = None,
    ) -> AsyncIterator[PeopleSearchResult]:
        if self.error is not None:
            raise self.error
        for result in self.results:
            yield result


def make_result(name: str, profile_url: str) -> PeopleSearchResult:
    return PeopleSearchResult(
        person_name=name,
        person_title="Builder",
        headline=f"{name} at Synthetic Systems",
        company_name="Synthetic Systems",
        location="Synthetic City",
        linkedin_profile_url=profile_url,
        raw_data={"source": "fake"},
    )


def client_for(factory: Callable[[], PeopleSearchProvider]) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TestClient(
        create_app(provider_factory=factory, session_factory=session_factory)
    )


def test_post_search_runs_fake_provider_and_persists_leads() -> None:
    fake = FakePeopleSearchProvider(
        [
            make_result("Alpha Example", "https://www.linkedin.com/in/alpha-example/"),
            make_result("Beta Example", "https://www.linkedin.com/in/beta-example/"),
        ]
    )
    with client_for(lambda: fake) as client:
        response = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 2})

        assert response.status_code == 202
        created = response.json()
        assert created["status"] == "QUEUED"

        detail = client.get(f"/api/searches/{created['search_id']}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "COMPLETED"
        assert detail.json()["latest_run"]["records_saved"] == 2

        results = client.get(f"/api/searches/{created['search_id']}/results?page=1&page_size=1")
        assert results.status_code == 200
        assert results.json()["total"] == 2
        assert results.json()["items"][0]["person_name"] == "Alpha Example"
        assert "raw_data" not in results.json()["items"][0]


def test_invalid_search_url_and_max_pages_are_rejected() -> None:
    with client_for(lambda: FakePeopleSearchProvider()) as client:
        invalid_url = client.post(
            "/api/searches",
            json={"search_url": "https://www.linkedin.com/jobs/search/", "max_pages": 1},
        )
        invalid_pages = client.post(
            "/api/searches",
            json={"search_url": SEARCH_URL, "max_pages": 0},
        )

    assert invalid_url.status_code == 422
    assert invalid_pages.status_code == 422


def test_provider_failure_is_persisted_as_failed() -> None:
    with client_for(lambda: FakePeopleSearchProvider(error=RuntimeError("synthetic provider failure"))) as client:
        response = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 1})
        search_id = response.json()["search_id"]
        detail = client.get(f"/api/searches/{search_id}").json()

    assert detail["status"] == "FAILED"
    assert detail["latest_run"]["status"] == "FAILED"
    assert detail["error_message"] == "synthetic provider failure"


def test_provider_diagnostics_produce_partial_status() -> None:
    fake = FakePeopleSearchProvider(
        [make_result("Partial Example", "https://www.linkedin.com/in/partial-example/")],
        diagnostics=[object()],
    )
    with client_for(lambda: fake) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL}).json()
        detail = client.get(f"/api/searches/{created['search_id']}").json()

    assert detail["status"] == "PARTIAL"
    assert detail["latest_run"]["status"] == "PARTIAL"


def test_search_list_and_delete() -> None:
    with client_for(lambda: FakePeopleSearchProvider()) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL}).json()
        listing = client.get("/api/searches?page=1&page_size=20")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        deleted = client.delete(f"/api/searches/{created['search_id']}")
        assert deleted.status_code == 204
        assert client.get(f"/api/searches/{created['search_id']}").status_code == 404
        assert client.delete("/api/searches/9999").status_code == 404


def test_empty_results_search() -> None:
    fake = FakePeopleSearchProvider([])
    with client_for(lambda: fake) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 1}).json()
        search_id = created["search_id"]

        detail = client.get(f"/api/searches/{search_id}").json()
        assert detail["status"] == "COMPLETED"
        assert detail["total_leads"] == 0
        assert detail["latest_run"]["records_saved"] == 0

        results = client.get(f"/api/searches/{search_id}/results?page=1&page_size=25")
        assert results.status_code == 200
        data = results.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 25


def test_results_backend_pagination() -> None:
    leads = [
        make_result(f"Person {i}", f"https://www.linkedin.com/in/person-{i}/")
        for i in range(1, 6)
    ]
    fake = FakePeopleSearchProvider(leads)
    with client_for(lambda: fake) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 1}).json()
        search_id = created["search_id"]

        # Page 1 (2 items)
        p1 = client.get(f"/api/searches/{search_id}/results?page=1&page_size=2").json()
        assert p1["total"] == 5
        assert p1["page"] == 1
        assert len(p1["items"]) == 2
        assert p1["items"][0]["person_name"] == "Person 1"
        assert p1["items"][1]["person_name"] == "Person 2"

        # Page 2 (2 items)
        p2 = client.get(f"/api/searches/{search_id}/results?page=2&page_size=2").json()
        assert p2["total"] == 5
        assert p2["page"] == 2
        assert len(p2["items"]) == 2
        assert p2["items"][0]["person_name"] == "Person 3"
        assert p2["items"][1]["person_name"] == "Person 4"

        # Page 3 (1 item)
        p3 = client.get(f"/api/searches/{search_id}/results?page=3&page_size=2").json()
        assert p3["total"] == 5
        assert p3["page"] == 3
        assert len(p3["items"]) == 1
        assert p3["items"][0]["person_name"] == "Person 5"

        # Page 4 (empty, beyond total)
        p4 = client.get(f"/api/searches/{search_id}/results?page=4&page_size=2").json()
        assert p4["total"] == 5
        assert p4["items"] == []


def test_access_error_stops_polling_and_sets_failed() -> None:
    from scraper.people.page_state import PeoplePageState, PeopleSearchAccessError

    error = PeopleSearchAccessError(PeoplePageState.LOGIN_REQUIRED, "User login required")
    fake = FakePeopleSearchProvider(error=error)
    with client_for(lambda: fake) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 1}).json()
        search_id = created["search_id"]

        detail = client.get(f"/api/searches/{search_id}").json()
        assert detail["status"] == "FAILED"
        assert "LOGIN_REQUIRED" in detail["error_message"]
        assert detail["latest_run"]["status"] == "FAILED"


def test_results_strict_fields() -> None:
    fake = FakePeopleSearchProvider([
        make_result("Strict Example", "https://www.linkedin.com/in/strict-example/")
    ])
    with client_for(lambda: fake) as client:
        created = client.post("/api/searches", json={"search_url": SEARCH_URL, "max_pages": 1}).json()
        search_id = created["search_id"]

        results = client.get(f"/api/searches/{search_id}/results").json()
        lead = results["items"][0]
        # Only allowed display fields
        assert "person_name" in lead
        assert "person_title" in lead
        assert "headline" in lead
        assert "company_name" in lead
        assert "location" in lead
        assert "linkedin_profile_url" in lead
        # Never infer or expose prohibited / internal data
        assert "raw_data" not in lead
        assert "email" not in lead
        assert "phone" not in lead
        assert "recruiter" not in lead
        assert "founder" not in lead