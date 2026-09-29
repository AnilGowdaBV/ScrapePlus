import asyncio
from pathlib import Path
import sys

# Ensure repository root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.app.core.config import get_settings


async def main() -> None:
    settings = get_settings()
    profile_dir = Path(settings.browser_user_data_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(f"Opening browser profile at: {profile_dir}")
    print("Please log into LinkedIn in the browser window that opens.")
    print("Once logged in, your session will be saved automatically.")
    print("=" * 60)

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                str(profile_dir),
                channel="chrome",
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )
        except Exception:
            context = await p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("\n--> When you have finished logging in, you can close the browser window or press Ctrl+C here.\n")
        try:
            while not page.is_closed():
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            try:
                await context.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
