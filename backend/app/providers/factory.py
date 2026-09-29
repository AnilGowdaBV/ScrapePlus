from collections.abc import Callable

from backend.app.core.config import get_settings
from scraper.providers.base import PeopleSearchProvider
from scraper.providers.playwright_adapter import PlaywrightPageLoader, PlaywrightPeopleSearchProvider

ProviderFactory = Callable[[], PeopleSearchProvider]


def default_provider_factory() -> PeopleSearchProvider:
    settings = get_settings()
    loader = PlaywrightPageLoader(
        user_data_dir=settings.browser_user_data_dir,
        headless=settings.browser_headless,
        cdp_url=settings.browser_cdp_url,
        timeout_ms=settings.browser_timeout_ms,
    )
    return PlaywrightPeopleSearchProvider(loader=loader)


default_provider_factory.provider_name = "playwright_authorized_browser"  # type: ignore[attr-defined]