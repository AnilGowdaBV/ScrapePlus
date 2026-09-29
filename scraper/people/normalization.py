import re
from urllib.parse import urlsplit, urlunsplit


LINKEDIN_HOSTNAMES = frozenset({"linkedin.com", "www.linkedin.com"})


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized or None


def normalize_linkedin_profile_url(value: str | None) -> str | None:
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        if candidate.startswith("/"):
            candidate = "https://www.linkedin.com" + candidate
        else:
            candidate = "https://" + candidate

    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None

    if parsed.scheme.lower() != "https" or parsed.hostname not in LINKEDIN_HOSTNAMES:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0].lower() != "in" or not parts[1]:
        return None

    return urlunsplit(("https", "www.linkedin.com", f"/in/{parts[1]}", "", ""))