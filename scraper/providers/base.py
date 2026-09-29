from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from scraper.people.models import PeopleSearchResult


class PeopleSearchProvider(ABC):
    """Boundary for replaceable People Search providers.

    Provider implementations belong in a later phase. This interface intentionally
    contains no browser, authentication, or LinkedIn automation behavior yet.
    """

    @abstractmethod
    async def search(
        self,
        search_url: str,
        max_pages: int | None = None,
    ) -> AsyncIterator[PeopleSearchResult]:
        """Yield normalized People Search records."""
        raise NotImplementedError