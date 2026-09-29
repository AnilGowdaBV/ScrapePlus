import pytest

from scraper.people.models import PeopleSearchResult
from scraper.people.normalization import (
    normalize_linkedin_profile_url,
    normalize_text,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://www.linkedin.com/in/synthetic-name", "https://www.linkedin.com/in/synthetic-name"),
        ("https://linkedin.com/in/synthetic-name/", "https://www.linkedin.com/in/synthetic-name"),
        ("linkedin.com/in/synthetic-name?trk=abc#top", "https://www.linkedin.com/in/synthetic-name"),
        ("https://www.linkedin.com/feed/", None),
        ("https://example.com/in/synthetic-name", None),
        (None, None),
    ],
)
def test_profile_url_normalization(source: str | None, expected: str | None) -> None:
    assert normalize_linkedin_profile_url(source) == expected


def test_text_normalization_and_nullable_contract() -> None:
    assert normalize_text("  Ada\n  Example ") == "Ada Example"
    assert normalize_text(" \t") is None

    record = PeopleSearchResult()
    assert record.person_name is None
    assert record.company_name is None
    assert record.to_dict()["raw_data"] == {}