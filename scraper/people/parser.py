from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from scraper.people.models import PeopleSearchResult
from scraper.people.normalization import normalize_linkedin_profile_url, normalize_text
from scraper.people.page_state import PeoplePageState
from scraper.people.selectors import SELECTORS


class PeopleCardParseError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class ParseDiagnostic:
    card_index: int
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_index": self.card_index,
            "code": self.code,
            "message": self.message,
        }


@dataclass(slots=True)
class PeoplePageExtraction:
    state: PeoplePageState
    records: list[PeopleSearchResult] = field(default_factory=list)
    diagnostics: list[ParseDiagnostic] = field(default_factory=list)


def _text(element: Tag | None) -> str | None:
    if element is None:
        return None
    return normalize_text(element.get_text(" ", strip=True))


def _legacy_sibling_text(profile_link: Tag, sibling_index: int) -> str | None:
    parent = profile_link.parent
    if not isinstance(parent, Tag):
        return None
    siblings = list(parent.find_next_siblings("div"))
    if len(siblings) <= sibling_index:
        return None
    return _text(siblings[sibling_index].find("p"))


def _company_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or parsed.hostname not in {
        "linkedin.com",
        "www.linkedin.com",
    }:
        return None
    if not parsed.path.rstrip("/").startswith("/company/"):
        return None
    return f"https://www.linkedin.com{parsed.path.rstrip('/')}"


def extract_people_card(card: Tag, card_index: int = 0) -> PeopleSearchResult:
    # 1. Profile link resolution
    profile_link = card.select_one("span.entity-result__title-text a, a[data-view-name='search-result-lockup-title']")
    if profile_link is None:
        profile_link = card.select_one(SELECTORS.profile_link)

    # If still none or if profile_link points to jobs/company/badge, look for a valid profile link
    if profile_link is None or any(k in (profile_link.get("href") or "") for k in ["/jobs/", "/company/", "/school/"]):
        valid_links = [
            a for a in card.select('a[href*="/in/"]')
            if not any(k in (a.get("href") or "") for k in ["/jobs/", "/company/", "/school/"])
            and (a.get_text() or "").strip().lower() not in {"see open roles", "follow", "connect", "message", "view profile"}
        ]
        if valid_links:
            profile_link = valid_links[0]
        elif card.select_one('a[href*="/in/"]'):
            profile_link = card.select_one('a[href*="/in/"]')

    profile_href = profile_link.get("href") if profile_link else None
    profile_url = normalize_linkedin_profile_url(
        profile_href if isinstance(profile_href, str) else None
    )

    # If profile_url still None, check for snippet id like SearchResultssnippet_ACoAA...
    if profile_url is None:
        snip = card.select_one("[id^='SearchResultssnippet_']")
        if snip:
            urn = snip.get("id", "").replace("SearchResultssnippet_", "")
            if urn:
                profile_url = f"https://www.linkedin.com/in/{urn}"

    if profile_url is None and profile_link is None:
        raise PeopleCardParseError("PROFILE_LINK_MISSING", "Profile link is missing")

    company_link = card.select_one(SELECTORS.company_link)
    company_href = company_link.get("href") if company_link else None
    image = card.select_one(SELECTORS.profile_image)
    image_src = image.get("src") if image else None

    # Person Name
    name_el = None
    if profile_link is not None:
        name_el = profile_link.select_one('span[aria-hidden="true"]')
    if name_el is None:
        title_text_wrap = card.select_one("span.entity-result__title-text, .entity-result__title")
        if title_text_wrap:
            name_el = title_text_wrap.select_one('span[aria-hidden="true"]')

    if name_el is not None:
        person_name = _text(name_el)
    elif profile_link is not None:
        clone = Tag(name=profile_link.name, attrs=profile_link.attrs)
        clone.extend([child for child in profile_link.children])
        for vh in clone.select(".visually-hidden, span[aria-hidden='false']"):
            vh.decompose()
        person_name = _text(clone)
    else:
        person_name = None

    p_tags = card.find_all("p")
    if not person_name or person_name.lower() in {"see open roles", "view profile", "follow", "connect", "view"}:
        if p_tags:
            person_name = _text(p_tags[0])
        elif card.select_one(".entity-result__title-text, .app-aware-link"):
            person_name = _text(card.select_one(".entity-result__title-text, .app-aware-link"))

    # Headline
    headline = _text(card.select_one(SELECTORS.headline))
    if headline is None and len(p_tags) >= 2:
        headline = _text(p_tags[1])
    if headline is None:
        headline = _text(card.select_one(".entity-result__primary-subtitle"))
    if headline is None:
        headline = _legacy_sibling_text(profile_link, 0) if profile_link else None
    if headline is None:
        headline = _text(card.select_one(".entity-result__summary"))

    # Location
    location = _text(card.select_one(SELECTORS.location))
    if location is None and len(p_tags) >= 3:
        location = _text(p_tags[2])
    if location is None:
        location = _text(card.select_one(".entity-result__secondary-subtitle"))
    if location is None:
        location = _legacy_sibling_text(profile_link, 1) if profile_link else None

    # Company name
    company_name = _text(card.select_one(SELECTORS.company))
    if company_name is None and company_link is not None:
        company_name = _text(company_link)
    if company_name is None:
        snip = card.select_one("[id^='SearchResultssnippet_'], .entity-result__summary")
        if snip and " at " in snip.get_text():
            company_name = normalize_text(snip.get_text().split(" at ", 1)[1])
    if company_name is None and headline:
        if " at " in headline:
            cand = headline.split(" at ", 1)[1].strip()
            for sep in [" | ", " • ", " - ", ","]:
                if sep in cand:
                    cand = cand.split(sep, 1)[0].strip()
            if cand:
                company_name = cand
        elif " @ " in headline:
            cand = headline.split(" @ ", 1)[1].strip()
            for sep in [" | ", " • ", " - ", ","]:
                if sep in cand:
                    cand = cand.split(sep, 1)[0].strip()
            if cand:
                company_name = cand
        elif ", " in headline:
            cand = headline.split(", ", 1)[1].strip()
            for sep in [" | ", " • ", " - "]:
                if sep in cand:
                    cand = cand.split(sep, 1)[0].strip()
            if cand:
                company_name = cand

    person_title = _text(card.select_one(SELECTORS.person_title))
    if person_title is None and headline:
        if " at " in headline:
            person_title = headline.split(" at ", 1)[0].strip()
        elif " @ " in headline:
            person_title = headline.split(" @ ", 1)[0].strip()
        elif ", " in headline:
            person_title = headline.split(", ", 1)[0].strip()

    raw_data = {
        "card_attributes": dict(card.attrs),
        "person_name_text": person_name,
        "profile_href": profile_href,
        "title_text": person_title,
        "headline_text": headline,
        "location_text": location,
        "company_text": company_name,
        "connection_text": _text(card.select_one(SELECTORS.connection)),
        "profile_image_src": image_src,
        "education_text": _text(card.select_one(SELECTORS.education)),
    }

    return PeopleSearchResult(
        person_name=person_name,
        person_title=person_title,
        headline=headline,
        company_name=company_name,
        company_url=_company_url(company_href if isinstance(company_href, str) else None),
        location=location,
        linkedin_profile_url=profile_url,
        connection_degree=_text(card.select_one(SELECTORS.connection)),
        profile_image_url=normalize_text(image_src if isinstance(image_src, str) else None),
        education=_text(card.select_one(SELECTORS.education)),
        raw_data=raw_data,
    )


def classify_people_page(
    html: str,
    expected_people_page: bool = True,
) -> PeoplePageState:
    if not expected_people_page:
        return PeoplePageState.UNEXPECTED_PAGE

    soup = BeautifulSoup(html, "html.parser")
    declared_state = soup.select_one("[data-page-state]")
    declared_value = declared_state.get("data-page-state", "") if declared_state else ""
    state_map = {
        "login-required": PeoplePageState.LOGIN_REQUIRED,
        "captcha": PeoplePageState.CAPTCHA,
        "access-restricted": PeoplePageState.ACCESS_RESTRICTED,
        "no-results": PeoplePageState.NO_RESULTS,
    }
    if declared_value in state_map:
        return state_map[declared_value]

    page_text = normalize_text(soup.get_text(" ", strip=True)) or ""
    lowered = page_text.lower()
    if "captcha" in lowered or "security verification" in lowered:
        return PeoplePageState.CAPTCHA
    if "sign in to linkedin" in lowered or "join linkedin" in lowered or "authwall" in lowered:
        return PeoplePageState.LOGIN_REQUIRED
    if "access restricted" in lowered or "unusual activity" in lowered:
        return PeoplePageState.ACCESS_RESTRICTED

    card_selectors = [
        "div[data-view-name='people-search-result']",
        "li.reusable-search__result-container",
        "div[data-view-name='search-entity-result-universal-template']",
        ".entity-result__item",
        "div[role='listitem']",
        ".entity-result",
    ]
    for sel in card_selectors:
        if soup.select(sel):
            return PeoplePageState.READY

    if (
        "no results" in lowered
        or "no people found" in lowered
        or "no matching people" in lowered
        or "unlimited search" in lowered
        or "benefit from unlimited search" in lowered
        or soup.select_one(".artdeco-empty-state")
        or soup.select_one("[data-view-name*='search']")
        or soup.select_one("[data-view-name*='search-filter-top-bar']")
        or soup.select_one("div.scaffold-layout__main")
        or soup.select_one("main")
    ):
        return PeoplePageState.NO_RESULTS

    return PeoplePageState.SELECTOR_MISMATCH


def extract_people_results(
    html: str,
    expected_people_page: bool = True,
) -> PeoplePageExtraction:
    state = classify_people_page(html, expected_people_page)
    if state is not PeoplePageState.READY:
        return PeoplePageExtraction(state=state)

    soup = BeautifulSoup(html, "html.parser")
    records: list[PeopleSearchResult] = []
    diagnostics: list[ParseDiagnostic] = []

    # Select top-level cards
    cards = []
    if soup.select("div[data-view-name='people-search-result']"):
        cards = soup.select("div[data-view-name='people-search-result']")
    elif soup.select("li.reusable-search__result-container"):
        cards = soup.select("li.reusable-search__result-container")
    elif soup.select("div[data-view-name='search-entity-result-universal-template']"):
        cards = soup.select("div[data-view-name='search-entity-result-universal-template']")
    elif soup.select(".entity-result__item"):
        cards = soup.select(".entity-result__item")
    elif soup.select(SELECTORS.result_card):
        cards = soup.select(SELECTORS.result_card)

    for index, card in enumerate(cards):
        try:
            record = extract_people_card(card, index)
            # Ignore false-positive non-people cards
            if record.person_name and record.person_name.lower() not in {"see open roles", "view profile", "view"}:
                records.append(record)
        except PeopleCardParseError as error:
            diagnostics.append(ParseDiagnostic(index, error.code, str(error)))
        except Exception as error:
            diagnostics.append(ParseDiagnostic(index, "UNEXPECTED_PARSE_ERROR", str(error)))

    return PeoplePageExtraction(state=state, records=records, diagnostics=diagnostics)