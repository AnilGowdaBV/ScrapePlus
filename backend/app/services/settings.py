import json
import os
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings

SETTINGS_FILE = Path("./database/session_settings.json")


def get_linkedin_cookie() -> str | None:
    """Retrieve LinkedIn session cookie from env or persistent settings file."""
    # 1. Environment variable priority
    env_cookie = os.getenv("LINKEDIN_COOKIE_LI_AT")
    if env_cookie and env_cookie.strip():
        return env_cookie.strip().strip('"').strip("'")

    # 2. File storage in database directory
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            val = data.get("linkedin_li_at")
            if val and isinstance(val, str) and val.strip():
                return val.strip().strip('"').strip("'")
        except Exception:
            pass

    return None


def save_linkedin_cookie(cookie: str) -> None:
    """Save LinkedIn cookie to persistent JSON file."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean_cookie = cookie.strip().strip('"').strip("'")
    data: dict[str, Any] = {}
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["linkedin_li_at"] = clean_cookie
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def delete_linkedin_cookie() -> None:
    """Remove stored LinkedIn cookie."""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            data.pop("linkedin_li_at", None)
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


def parse_linkedin_cookies(cookie_input: str) -> list[dict[str, Any]]:
    """Parse cookie input into Playwright-compatible cookie dictionaries."""
    raw = cookie_input.strip()
    if not raw:
        return []

    # If raw value like 'AQED...' was provided
    if "=" not in raw:
        return [
            {
                "name": "li_at",
                "value": raw,
                "domain": ".linkedin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            }
        ]

    # If full cookie string like 'li_at=AQED...; JSESSIONID=...'
    results = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if "=" in chunk:
            name, val = chunk.split("=", 1)
            name = name.strip()
            val = val.strip().strip('"').strip("'")
            if name and val:
                results.append(
                    {
                        "name": name,
                        "value": val,
                        "domain": ".linkedin.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                    }
                )
    return results
