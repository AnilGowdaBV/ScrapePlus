import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright

from backend.app.core.config import get_settings
from backend.app.services.linkedin_auth import (
    login_with_credentials_sync,
    submit_2fa_code_sync,
)
from backend.app.services.settings import (
    delete_linkedin_cookie,
    get_linkedin_cookie,
    save_linkedin_cookie,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class LinkedInSessionPayload(BaseModel):
    li_at: str


class LinkedInSessionStatus(BaseModel):
    connected: bool
    masked_cookie: str | None = None


class CredentialsLoginPayload(BaseModel):
    email: str
    password: str


class TwoFactorPayload(BaseModel):
    session_id: str
    code: str


@router.post("/login-credentials")
async def login_with_credentials(payload: CredentialsLoginPayload) -> dict[str, Any]:
    """Logs into LinkedIn using user's email and password via backend automation."""
    if not payload.email.strip() or not payload.password.strip():
        raise HTTPException(status_code=400, detail="Email and password are required.")
    result = await asyncio.to_thread(login_with_credentials_sync, payload.email, payload.password)
    return result


@router.post("/submit-2fa")
async def submit_2fa(payload: TwoFactorPayload) -> dict[str, Any]:
    """Submits the 2FA code for a pending login session."""
    if not payload.session_id.strip() or not payload.code.strip():
        raise HTTPException(status_code=400, detail="Session ID and verification code are required.")
    result = await asyncio.to_thread(submit_2fa_code_sync, payload.session_id, payload.code)
    return result


async def _run_login_browser() -> None:
    """Launch a visible Chrome window to let user log into LinkedIn interactively."""
    settings = get_settings()
    profile_dir = Path(settings.browser_user_data_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

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
        try:
            await page.goto("https://www.linkedin.com/login")
            while not page.is_closed():
                await asyncio.sleep(1)
                # Auto-detect when user logs in and extract li_at
                try:
                    cookies = await context.cookies()
                    for c in cookies:
                        if c.get("name") == "li_at" and c.get("value"):
                            save_linkedin_cookie(c["value"])
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                await context.close()
            except Exception:
                pass


@router.get("/linkedin-session", response_model=LinkedInSessionStatus)
def get_session_status() -> LinkedInSessionStatus:
    cookie = get_linkedin_cookie()
    if not cookie:
        return LinkedInSessionStatus(connected=False, masked_cookie=None)

    masked = (
        f"{cookie[:6]}...{cookie[-4:]}" if len(cookie) > 10 else "******"
    )
    return LinkedInSessionStatus(connected=True, masked_cookie=masked)


@router.post("/linkedin-session", response_model=LinkedInSessionStatus)
def save_session(payload: LinkedInSessionPayload) -> LinkedInSessionStatus:
    cookie = payload.li_at.strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="LinkedIn session cookie cannot be empty.")
    save_linkedin_cookie(cookie)
    return get_session_status()


@router.delete("/linkedin-session", response_model=LinkedInSessionStatus)
def disconnect_session() -> LinkedInSessionStatus:
    delete_linkedin_cookie()
    return LinkedInSessionStatus(connected=False, masked_cookie=None)


import subprocess
import sys


@router.post("/open-login-browser")
async def open_login_browser() -> dict[str, str]:
    """Open a visible Chrome browser window for user to log into LinkedIn directly."""
    settings = get_settings()
    if settings.browser_headless:
        raise HTTPException(
            status_code=400,
            detail="Interactive browser requires running locally with a display (BROWSER_HEADLESS=false).",
        )
    script_path = str(Path("scripts/open_browser.py").resolve())
    subprocess.Popen([sys.executable, script_path])
    return {"message": "Chrome window opened! Log in with your ID and password."}
