from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from scraper.people.url import validate_people_search_url


class PeopleSearchPaginator:
    """Create page URLs without discarding the original search filters."""

    def __init__(self, search_url: str, max_pages: int | None = None) -> None:
        self.search_url = validate_people_search_url(search_url)
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be greater than zero")
        self.max_pages = max_pages

    @property
    def current_page(self) -> int:
        query = parse_qs(urlsplit(self.search_url).query, keep_blank_values=True)
        raw_page = query.get("page", ["1"])[0]
        try:
            page = int(raw_page)
        except ValueError:
            return 1
        return page if page > 0 else 1

    def page_url(self, page: int) -> str:
        if page < 1:
            raise ValueError("page must be greater than zero")

        parsed = urlsplit(self.search_url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query["page"] = [str(page)]
        return urlunsplit(parsed._replace(query=urlencode(query, doseq=True)))

    def next_page_url(self, page: int | None = None) -> str | None:
        current_page = page or self.current_page
        next_page = current_page + 1
        pages_from_start = next_page - self.current_page + 1
        if self.max_pages is not None and pages_from_start > self.max_pages:
            return None
        return self.page_url(next_page)