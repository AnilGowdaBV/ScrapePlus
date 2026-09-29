import asyncio
from pathlib import Path

import pytest

from scraper.people.page_state import PeoplePageState, PeopleSearchAccessError
from scraper.providers.browser_people_provider import BrowserPeopleSearchProvider


FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_provider_yields_records_and_stops_at_no_results() -> None:
    requested_urls: list[str] = []

    async def load_page(page_url: str) -> str:
        requested_urls.append(page_url)
        return read_fixture("normal_card.html" if len(requested_urls) == 1 else "no_results.html")

    provider = BrowserPeopleSearchProvider(load_page)

    async def collect() -> list[object]:
        return [record async for record in provider.search(
            "https://www.linkedin.com/search/results/people/?keywords=synthetic&geoUrn=123",
            max_pages=3,
        )]

    records = asyncio.run(collect())

    assert len(records) == 1
    assert provider.last_page_state is PeoplePageState.NO_RESULTS
    assert len(requested_urls) == 2
    assert "keywords=synthetic" in requested_urls[1]
    assert "geoUrn=123" in requested_urls[1]
    assert "page=2" in requested_urls[1]


def test_provider_stops_on_access_state() -> None:
    async def load_page(_: str) -> str:
        return read_fixture("login_required.html")

    provider = BrowserPeopleSearchProvider(load_page)

    async def consume() -> None:
        async for _ in provider.search(
            "https://www.linkedin.com/search/results/people/?keywords=synthetic"
        ):
            pass

    with pytest.raises(PeopleSearchAccessError) as error:
        asyncio.run(consume())

    assert error.value.state is PeoplePageState.LOGIN_REQUIRED


def test_provider_classifies_loader_timeout() -> None:
    async def load_page(_: str) -> str:
        raise TimeoutError("synthetic timeout")

    provider = BrowserPeopleSearchProvider(load_page)

    async def consume() -> None:
        async for _ in provider.search(
            "https://www.linkedin.com/search/results/people/?keywords=synthetic"
        ):
            pass

    with pytest.raises(PeopleSearchAccessError) as error:
        asyncio.run(consume())

    assert error.value.state is PeoplePageState.TIMEOUT
    assert provider.last_page_state is PeoplePageState.TIMEOUT