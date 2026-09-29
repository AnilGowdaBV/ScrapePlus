from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PeopleSelectors:
    result_card: str = 'div[data-view-name="people-search-result"], li.reusable-search__result-container, div[data-view-name="search-entity-result-universal-template"], .entity-result__item, div[role="listitem"]'
    profile_link: str = 'span.entity-result__title-text a, a[data-view-name="search-result-lockup-title"], a.app-aware-link[href*="/in/"]'
    person_title: str = '[data-field="title"]'
    headline: str = '[data-field="headline"], .entity-result__primary-subtitle, .entity-result__summary'
    location: str = '[data-field="location"], .entity-result__secondary-subtitle'
    company: str = '[data-field="company"]'
    company_link: str = 'a[data-field="company-link"], a[href*="/company/"]'
    connection: str = '[data-field="connection-degree"], .entity-result__badge-text'
    profile_image: str = 'img[data-field="profile-image"], .presence-entity__image, .entity-result__universal-image img'
    education: str = '[data-field="education"]'


SELECTORS = PeopleSelectors()