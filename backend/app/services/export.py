import csv
import io
from collections.abc import Sequence

import openpyxl

from backend.app.models.entities import Lead

EXPORT_COLUMNS = [
    "Company",
    "Person Name",
    "Title / Headline",
    "Location",
    "LinkedIn Profile URL",
]


def format_title_headline(title: str | None, headline: str | None) -> str:
    """Combine title and headline cleanly without duplicating or inventing data."""
    t = (title or "").strip()
    h = (headline or "").strip()
    if not t and not h:
        return ""
    if t and not h:
        return t
    if h and not t:
        return h
    if t == h or t in h:
        return h
    return f"{t} - {h}"


def export_leads_csv(leads: Sequence[Lead]) -> bytes:
    """Generate RFC 4180 CSV with UTF-8 BOM encoding for complete Unicode support."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(EXPORT_COLUMNS)

    for lead in leads:
        writer.writerow(
            [
                lead.company_name or "",
                lead.person_name or "",
                format_title_headline(lead.person_title, lead.headline),
                lead.location or "",
                lead.linkedin_profile_url or "",
            ]
        )

    return output.getvalue().encode("utf-8-sig")


def export_leads_xlsx(leads: Sequence[Lead]) -> bytes:
    """Generate an Excel workbook using openpyxl with correct headers and null safety."""
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Leads"

    worksheet.append(EXPORT_COLUMNS)

    for lead in leads:
        worksheet.append(
            [
                lead.company_name or "",
                lead.person_name or "",
                format_title_headline(lead.person_title, lead.headline),
                lead.location or "",
                lead.linkedin_profile_url or "",
            ]
        )

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
