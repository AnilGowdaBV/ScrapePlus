import asyncio
import os
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from scraper.people.models import PeopleSearchResult
from scraper.people.selectors import SELECTORS
from scraper.providers.browser_people_provider import BrowserPeopleSearchProvider


class PlaywrightPageLoader:
    """Authorized local browser adapter using Playwright.

    Executes in a visible, user-controlled browser context without credential extraction,
    cookie stealing, CAPTCHA bypass, or stealth emulation.
    """

    def __init__(
        self,
        *,
        user_data_dir: str | Path = "./database/browser_profile",
        headless: bool = False,
        cdp_url: str | None = None,
        timeout_ms: int = 30000,
        cookies: list[dict[str, Any]] | None = None,
    ) -> None:
        self.user_data_dir = Path(user_data_dir)
        self.headless = headless
        self.cdp_url = cdp_url
        self.timeout_ms = timeout_ms
        self.cookies = cookies or []
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def _ensure_browser(self) -> Page:
        if self._page is not None and not self._page.is_closed():
            return self._page

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        if self.cdp_url:
            browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
            contexts = browser.contexts
            self._context = contexts[0] if contexts else await browser.new_context()
        else:
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    str(self.user_data_dir),
                    channel="chrome",
                    headless=self.headless,
                    viewport=None,
                    args=["--start-maximized"],
                )
            except Exception:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    str(self.user_data_dir),
                    headless=self.headless,
                    viewport=None,
                    args=["--start-maximized"],
                )

        if self.cookies and self._context:
            try:
                await self._context.add_cookies(self.cookies)
            except Exception:
                pass

        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        try:
            await self._page.bring_to_front()
        except Exception:
            pass
        return self._page

    async def __call__(self, page_url: str) -> str:
        """Navigate to page_url in the authorized browser and return rendered HTML."""
        page = await self._ensure_browser()
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except Exception as error:
            if "timeout" in str(error).lower():
                raise TimeoutError(f"Navigation timed out for {page_url}") from error
            raise

        # Wait for dynamic result cards, empty state, or page state signals to hydrate
        detection_selectors = [
            "li.reusable-search__result-container",
            "div[data-view-name='search-entity-result-universal-template']",
            ".entity-result__item",
            ".entity-result",
            "div.search-results-container",
            SELECTORS.result_card,
            "[data-page-state]",
            "input#username",
            "input#session_key",
            ".challenge-dialog",
            ".captcha",
            ".artdeco-empty-state",
        ]
        combined_selector = ", ".join(detection_selectors)

        try:
            await page.wait_for_selector(combined_selector, timeout=12000)
        except Exception:
            pass

        # Check if redirected to a login, authwall, or sign-in screen
        current_url = page.url
        login_input = None
        try:
            login_input = await page.query_selector(
                "input#username, input#session_key, input[name='session_key'], form.login__form, .sign-in-form, .join-form"
            )
        except Exception:
            pass

        is_auth_page = (
            login_input is not None
            or any(
                k in current_url
                for k in ["/login", "/checkpoint", "/authwall", "/uas/login", "signup"]
            )
        )

        if not self.headless and is_auth_page:
            try:
                # Wait up to 180 seconds for the user to complete login in the visible browser window
                await page.wait_for_selector(
                    "li.reusable-search__result-container, .global-nav__me, .feed-identity-module, .artdeco-empty-state",
                    timeout=180000,
                )
                # Re-navigate to the exact search URL once authenticated
                await page.goto(
                    page_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                try:
                    await page.wait_for_selector(
                        combined_selector,
                        timeout=12000,
                    )
                except Exception:
                    pass
            except Exception:
                pass

        # Progressive scroll down to allow lazy-loaded search result cards on the current page to hydrate
        try:
            for step in [0.25, 0.5, 0.75, 1.0]:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {step})")
                await asyncio.sleep(0.3)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.2)
        except Exception:
            pass

        return await page.content()

    async def close(self) -> None:
        """Cleanly close browser context and playwright."""
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
            self._page = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


class PlaywrightPeopleSearchProvider(BrowserPeopleSearchProvider):
    """People Search Provider powered by the authorized Playwright browser adapter.

    Delegates completely to the existing Phase 3 BrowserPeopleSearchProvider,
    reusing its parser, pagination, normalization, and page-state classification.
    """

    provider_name = "playwright_authorized_browser"

    def __init__(self, loader: PlaywrightPageLoader | None = None, **loader_kwargs: Any) -> None:
        self.loader = loader or PlaywrightPageLoader(**loader_kwargs)
        super().__init__(page_loader=self.loader)

    async def search(self, search_url: str, max_pages: int | None = None):
        try:
            async for record in super().search(search_url, max_pages=max_pages):
                yield record
        finally:
            await self.loader.close()
