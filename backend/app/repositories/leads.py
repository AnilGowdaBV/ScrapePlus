from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import Lead
from scraper.people.models import PeopleSearchResult
from scraper.people.normalization import normalize_linkedin_profile_url


class LeadRepository:
    def find_duplicate(
        self,
        session: Session,
        search_id: int,
        result: PeopleSearchResult,
        *,
        external_id: str | None = None,
    ) -> Lead | None:
        profile_url = normalize_linkedin_profile_url(result.linkedin_profile_url)
        if profile_url is not None:
            duplicate = session.scalar(
                select(Lead).where(
                    Lead.search_id == search_id,
                    Lead.linkedin_profile_url == profile_url,
                )
            )
            if duplicate is not None:
                return duplicate

        if external_id:
            duplicate = session.scalar(
                select(Lead).where(
                    Lead.search_id == search_id,
                    Lead.external_id == external_id,
                )
            )
            if duplicate is not None:
                return duplicate

        if result.person_name and result.location and result.company_name:
            return session.scalar(
                select(Lead).where(
                    and_(
                        Lead.search_id == search_id,
                        Lead.person_name == result.person_name,
                        Lead.location == result.location,
                        Lead.company_name == result.company_name,
                    )
                )
            )
        return None

    def save_result(
        self,
        session: Session,
        search_id: int,
        result: PeopleSearchResult,
        *,
        source: str = "people_search",
        external_id: str | None = None,
    ) -> tuple[Lead, bool]:
        duplicate = self.find_duplicate(
            session,
            search_id,
            result,
            external_id=external_id,
        )
        if duplicate is not None:
            return duplicate, False

        lead = Lead(
            search_id=search_id,
            source=source,
            external_id=external_id,
            person_name=result.person_name,
            person_title=result.person_title,
            headline=result.headline,
            company_name=result.company_name,
            company_url=result.company_url,
            linkedin_profile_url=normalize_linkedin_profile_url(result.linkedin_profile_url),
            location=result.location,
            profile_image_url=result.profile_image_url,
            connection_degree=result.connection_degree,
            education=result.education,
            raw_data=dict(result.raw_data),
        )
        session.add(lead)
        session.flush()
        return lead, True

    def list_for_search(
        self,
        session: Session,
        search_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        statement = (
            select(Lead)
            .where(Lead.search_id == search_id)
            .order_by(Lead.id)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(statement))

    def list_all_for_search(self, session: Session, search_id: int) -> list[Lead]:
        statement = select(Lead).where(Lead.search_id == search_id).order_by(Lead.id)
        return list(session.scalars(statement))

    def count_for_search(self, session: Session, search_id: int) -> int:
        statement = select(func.count(Lead.id)).where(Lead.search_id == search_id)
        return int(session.scalar(statement) or 0)