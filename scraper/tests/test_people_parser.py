from pathlib import Path

from scraper.people.page_state import PeoplePageState
from scraper.people.parser import extract_people_results


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_normal_card_extracts_explicit_fields() -> None:
    extraction = extract_people_results(fixture("normal_card.html"))

    assert extraction.state is PeoplePageState.READY
    assert len(extraction.records) == 1
    record = extraction.records[0]
    assert record.person_name == "Ada Example"
    assert record.person_title == "Founder"
    assert record.headline == "Founder at Example Systems"
    assert record.company_name == "Example Systems"
    assert record.company_url == "https://www.linkedin.com/company/example-systems"
    assert record.location == "Synthetic City"
    assert record.connection_degree == "2nd"
    assert record.profile_image_url.endswith("ada.jpg")
    assert record.education == "Example University"
    assert record.linkedin_profile_url == "https://www.linkedin.com/in/ada-example"
    assert record.raw_data["profile_href"].endswith("trk=synthetic")


def test_missing_company_is_null() -> None:
    record = extract_people_results(fixture("missing_company.html")).records[0]

    assert record.company_name is None
    assert record.headline == "Independent builder"


def test_missing_location_is_null() -> None:
    record = extract_people_results(fixture("missing_location.html")).records[0]

    assert record.location is None
    assert record.person_title == "Engineer"


def test_multiple_cards_and_malformed_card_are_isolated() -> None:
    multiple = extract_people_results(fixture("multiple_cards.html"))
    malformed = extract_people_results(fixture("malformed_card.html"))

    assert len(multiple.records) == 2
    assert multiple.records[1].company_name is None
    assert len(malformed.records) == 0
    assert malformed.diagnostics[0].code == "PROFILE_LINK_MISSING"


def test_access_and_page_states_are_classified() -> None:
    assert extract_people_results(fixture("no_results.html")).state is PeoplePageState.NO_RESULTS
    assert extract_people_results(fixture("login_required.html")).state is PeoplePageState.LOGIN_REQUIRED
    assert extract_people_results(fixture("access_restricted.html")).state is PeoplePageState.ACCESS_RESTRICTED
    assert extract_people_results(fixture("captcha.html")).state is PeoplePageState.CAPTCHA
    assert (
        extract_people_results(fixture("unexpected_page.html"), expected_people_page=False).state
        is PeoplePageState.UNEXPECTED_PAGE
    )