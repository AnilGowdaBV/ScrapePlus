import asyncio
from pathlib import Path
import sys

# Ensure Windows uses ProactorEventLoop for Playwright subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Ensure repository root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from backend.app.core.config import get_settings
from backend.app.services.settings import save_linkedin_cookie


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
        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            viewport=None,
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        print("\n--> Log into LinkedIn with your ID and password.")
        print("--> As soon as you log in, your session cookie will be saved automatically!\n")
        try:
            saved = False
            while not page.is_closed():
                await asyncio.sleep(1)
                if not saved:
                    try:
                        cookies = await context.cookies()
                        for c in cookies:
                            if c.get("name") == "li_at" and c.get("value"):
                                save_linkedin_cookie(c["value"])
                                print(f"\n[+] Successfully saved LinkedIn session cookie (li_at)!")
                                saved = True
                                break
                    except Exception:
                        pass
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            try:
                await context.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
