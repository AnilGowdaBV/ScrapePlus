from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
