from collections.abc import Callable

from backend.app.core.config import get_settings
from backend.app.services.settings import get_linkedin_cookie, parse_linkedin_cookies
from scraper.providers.base import PeopleSearchProvider
from scraper.providers.playwright_adapter import PlaywrightPageLoader, PlaywrightPeopleSearchProvider

ProviderFactory = Callable[[], PeopleSearchProvider]


def default_provider_factory() -> PeopleSearchProvider:
    settings = get_settings()
    raw_cookie = get_linkedin_cookie()
    cookies = parse_linkedin_cookies(raw_cookie) if raw_cookie else None

    loader = PlaywrightPageLoader(
        user_data_dir=settings.browser_user_data_dir,
        headless=settings.browser_headless,
        cdp_url=settings.browser_cdp_url,
        timeout_ms=settings.browser_timeout_ms,
        cookies=cookies,
    )
    return PlaywrightPeopleSearchProvider(loader=loader)


default_provider_factory.provider_name = "playwright_authorized_browser"  # type: ignore[attr-defined]