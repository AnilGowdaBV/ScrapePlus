from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PeopleSearchResult:
    person_name: str | None = None
    person_title: str | None = None
    headline: str | None = None
    company_name: str | None = None
    company_url: str | None = None
    location: str | None = None
    linkedin_profile_url: str | None = None
    connection_degree: str | None = None
    profile_image_url: str | None = None
    education: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)