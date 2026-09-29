from urllib.parse import urlsplit


PEOPLE_SEARCH_PATH = "/search/results/people"
LINKEDIN_HOSTNAMES = frozenset({"linkedin.com", "www.linkedin.com"})


class InvalidPeopleSearchUrl(ValueError):
    """Raised when a URL is not an HTTPS LinkedIn People Search URL."""


def validate_people_search_url(search_url: str) -> str:
    """Validate and return the exact supplied URL without rebuilding it."""
    if not isinstance(search_url, str) or not search_url:
        raise InvalidPeopleSearchUrl("A People Search URL is required")

    try:
        parsed = urlsplit(search_url)
    except ValueError as error:
        raise InvalidPeopleSearchUrl("The URL is malformed") from error

    if parsed.scheme.lower() != "https":
        raise InvalidPeopleSearchUrl("The URL must use HTTPS")
    if parsed.hostname not in LINKEDIN_HOSTNAMES:
        raise InvalidPeopleSearchUrl("The URL must use a LinkedIn hostname")
    if parsed.path.rstrip("/") != PEOPLE_SEARCH_PATH:
        raise InvalidPeopleSearchUrl("The URL must point to LinkedIn People Search")

    return search_url