from urllib.parse import parse_qs, urlsplit

from scraper.people.pagination import PeopleSearchPaginator


def test_page_url_preserves_all_search_parameters() -> None:
    original = (
        "https://www.linkedin.com/search/results/people/?keywords=founder"
        "&geoUrn=123&origin=FACETED_SEARCH"
    )
    paginator = PeopleSearchPaginator(original)

    generated = paginator.page_url(2)
    query = parse_qs(urlsplit(generated).query)

    assert query["keywords"] == ["founder"]
    assert query["geoUrn"] == ["123"]
    assert query["origin"] == ["FACETED_SEARCH"]
    assert query["page"] == ["2"]


def test_current_page_and_relative_max_pages() -> None:
    original = "https://www.linkedin.com/search/results/people/?page=3&keywords=test"
    paginator = PeopleSearchPaginator(original, max_pages=2)

    assert paginator.current_page == 3
    assert paginator.next_page_url() is not None
    assert "page=4" in paginator.next_page_url()
    assert paginator.next_page_url(4) is None