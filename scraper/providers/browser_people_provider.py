from collections.abc import AsyncIterator
from typing import Protocol

from scraper.people.models import PeopleSearchResult
from scraper.people.page_state import PeoplePageState, PeopleSearchAccessError
from scraper.people.pagination import PeopleSearchPaginator
from scraper.people.parser import ParseDiagnostic, extract_people_results
from scraper.people.url import validate_people_search_url
from scraper.providers.base import PeopleSearchProvider


class PeoplePageLoader(Protocol):
    async def __call__(self, page_url: str) -> str:
        """Return already-authorized page HTML supplied by a browser boundary."""


class BrowserPeopleSearchProvider(PeopleSearchProvider):
    """Parse pages supplied by an external browser boundary.

    This phase deliberately does not implement browser startup, navigation,
    credentials, cookies, or access-control handling.
    """

    def __init__(self, page_loader: PeoplePageLoader) -> None:
        self.page_loader = page_loader
        self.last_page_state: PeoplePageState | None = None
        self.diagnostics: list[ParseDiagnostic] = []
        self.pages_processed = 0

    async def search(
        self,
        search_url: str,
        max_pages: int | None = None,
    ) -> AsyncIterator[PeopleSearchResult]:
        original_url = validate_people_search_url(search_url)
        paginator = PeopleSearchPaginator(original_url, max_pages=max_pages)
        current_page = paginator.current_page
        pages_requested = 0

        while max_pages is None or pages_requested < max_pages:
            page_url = original_url if pages_requested == 0 else paginator.page_url(current_page)
            try:
                html = await self.page_loader(page_url)
            except TimeoutError as error:
                self.last_page_state = PeoplePageState.TIMEOUT
                raise PeopleSearchAccessError(
                    PeoplePageState.TIMEOUT,
                    "People Search page loading timed out",
                ) from error
            extraction = extract_people_results(html)
            self.last_page_state = extraction.state
            self.diagnostics.extend(extraction.diagnostics)
            self.pages_processed += 1
            pages_requested += 1

            if extraction.state is PeoplePageState.NO_RESULTS or (extraction.state is PeoplePageState.READY and len(extraction.records) == 0):
                return
            if extraction.state is not PeoplePageState.READY:
                raise PeopleSearchAccessError(
                    extraction.state,
                    f"People Search stopped in state {extraction.state}",
                )

            for record in extraction.records:
                yield record

            current_page += 1