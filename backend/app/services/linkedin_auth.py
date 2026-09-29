import time
import uuid
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from backend.app.services.settings import save_linkedin_cookie

# In-memory storage for pending 2FA sessions (auto-expires after 5 minutes)
_PENDING_2FA: dict[str, dict[str, Any]] = {}


def _cleanup_old_sessions() -> None:
    now = time.time()
    expired = [sid for sid, data in _PENDING_2FA.items() if now - data["created_at"] > 300]
    for sid in expired:
        try:
            _PENDING_2FA[sid]["browser"].close()
        except Exception:
            pass
        _PENDING_2FA.pop(sid, None)


def login_with_credentials_sync(email: str, password: str) -> dict[str, Any]:
    """Logs into LinkedIn using Playwright, handling 2FA challenges and cookies."""
    _cleanup_old_sessions()

    p = sync_playwright().start()
    browser: Browser | None = None
    try:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context: BrowserContext = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page: Page = context.new_page()
        page.set_default_timeout(20000)

        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        page.wait_for_selector("#username, input[name='session_key']", timeout=10000)

        # Fill credentials
        page.fill("#username, input[name='session_key']", email.strip())
        page.fill("#password, input[name='session_password']", password.strip())
        page.click("button[type='submit']")

        # Wait for either feed navigation, checkpoint (2FA), error, or captcha
        time.sleep(3)

        # Check cookies for li_at (successful direct login)
        cookies = context.cookies()
        for c in cookies:
            if c.get("name") == "li_at" and c.get("value"):
                save_linkedin_cookie(c["value"])
                browser.close()
                p.stop()
                return {
                    "status": "SUCCESS",
                    "message": "Successfully authenticated with LinkedIn!",
                }

        current_url = page.url.lower()

        # Check for wrong password / email error
        error_elem = page.query_selector("#error-for-username, #error-for-password, .alert-content")
        if error_elem and error_elem.is_visible():
            err_text = error_elem.inner_text().strip()
            browser.close()
            p.stop()
            return {"status": "ERROR", "message": err_text or "Invalid email or password."}

        # Check for 2FA / Verification PIN challenge
        pin_input = page.query_selector(
            "#input__email_verification_pin, input[name='pin'], input[type='tel'], input.input_verification_pin"
        )
        if pin_input is not None or "checkpoint" in current_url or "challenge" in current_url:
            # If there's an actual pin input field:
            if pin_input is not None:
                session_id = str(uuid.uuid4())
                _PENDING_2FA[session_id] = {
                    "playwright": p,
                    "browser": browser,
                    "context": context,
                    "page": page,
                    "created_at": time.time(),
                }
                return {
                    "status": "REQUIRES_2FA",
                    "session_id": session_id,
                    "message": "LinkedIn sent a 6-digit verification code to your email/phone. Enter it below:",
                }

        # Check for visual captcha
        captcha = page.query_selector(".challenge-dialog, #captcha-internal, iframe[title*='challenge']")
        if captcha is not None:
            browser.close()
            p.stop()
            return {
                "status": "CAPTCHA",
                "message": "LinkedIn requested a security puzzle/CAPTCHA. Please log in once from your normal browser on this IP to clear security.",
            }

        # Final cookie check after extra wait
        time.sleep(3)
        cookies = context.cookies()
        for c in cookies:
            if c.get("name") == "li_at" and c.get("value"):
                save_linkedin_cookie(c["value"])
                browser.close()
                p.stop()
                return {
                    "status": "SUCCESS",
                    "message": "Successfully authenticated with LinkedIn!",
                }

        browser.close()
        p.stop()
        return {
            "status": "ERROR",
            "message": "Could not verify login. Please check your credentials or try again.",
        }

    except Exception as exc:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            p.stop()
        except Exception:
            pass
        return {"status": "ERROR", "message": f"Login attempt failed: {str(exc)}"}


def submit_2fa_code_sync(session_id: str, code: str) -> dict[str, Any]:
    """Submits the 2FA verification PIN for a pending LinkedIn session."""
    session_data = _PENDING_2FA.get(session_id)
    if not session_data:
        return {
            "status": "ERROR",
            "message": "Verification session expired. Please start login again.",
        }

    page: Page = session_data["page"]
    context: BrowserContext = session_data["context"]
    browser: Browser = session_data["browser"]
    p = session_data["playwright"]

    try:
        # Find pin input and fill
        page.fill(
            "#input__email_verification_pin, input[name='pin'], input[type='tel'], input.input_verification_pin",
            code.strip(),
        )
        page.click("#email-pin-submit-button, button[type='submit']")
        time.sleep(4)

        # Look for cookie
        cookies = context.cookies()
        for c in cookies:
            if c.get("name") == "li_at" and c.get("value"):
                save_linkedin_cookie(c["value"])
                _PENDING_2FA.pop(session_id, None)
                browser.close()
                p.stop()
                return {
                    "status": "SUCCESS",
                    "message": "Verification confirmed! LinkedIn is now connected.",
                }

        # Check for invalid code error
        error_elem = page.query_selector(".form__error, .alert-content, .error")
        if error_elem and error_elem.is_visible():
            err_text = error_elem.inner_text().strip()
            return {"status": "ERROR", "message": err_text or "Invalid verification code."}

        return {
            "status": "ERROR",
            "message": "Code verification failed. Please check the code and try again.",
        }

    except Exception as exc:
        return {"status": "ERROR", "message": f"Error submitting verification code: {str(exc)}"}
