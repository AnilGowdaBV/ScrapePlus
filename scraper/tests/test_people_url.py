import pytest

from scraper.people.url import InvalidPeopleSearchUrl, validate_people_search_url


def test_valid_url_is_returned_exactly() -> None:
    url = (
        "https://www.linkedin.com/search/results/people/?keywords=founder%20hiring"
        "&geoUrn=%5B%22123%22%5D&origin=FACETED_SEARCH"
    )

    assert validate_people_search_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/jobs/search/?keywords=engineer",
        "https://www.linkedin.com/feed/",
        "https://example.com/search/results/people/",
        "not a url",
        "https://www.linkedin.com/",
        "http://www.linkedin.com/search/results/people/",
    ],
)
def test_invalid_people_urls_are_rejected(url: str) -> None:
    with pytest.raises(InvalidPeopleSearchUrl):
        validate_people_search_url(url)