"""Create search, search run, and lead persistence tables.

Revision ID: 0001_initial_persistence
Revises:
Create Date: 2026-09-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_persistence"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_url", sa.Text(), nullable=False),
        sa.Column("search_type", sa.String(length=20), nullable=False, server_default="PEOPLE"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.String(length=32), nullable=True),
        sa.Column("total_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_searches_status", "searches", ["status"])
    op.create_index("ix_searches_created_at", "searches", ["created_at"])

    op.create_table(
        "search_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "search_id",
            sa.Integer(),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.String(length=32), nullable=True),
        sa.Column("pages_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_search_runs_search_id", "search_runs", ["search_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "search_id",
            sa.Integer(),
            sa.ForeignKey("searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("person_name", sa.String(length=500), nullable=True),
        sa.Column("person_title", sa.String(length=500), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("company_name", sa.String(length=500), nullable=True),
        sa.Column("company_url", sa.Text(), nullable=True),
        sa.Column("linkedin_profile_url", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("profile_image_url", sa.Text(), nullable=True),
        sa.Column("connection_degree", sa.String(length=50), nullable=True),
        sa.Column("education", sa.Text(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("search_id", "linkedin_profile_url", name="uq_leads_search_profile_url"),
        sa.UniqueConstraint("search_id", "external_id", name="uq_leads_search_external_id"),
    )
    op.create_index("ix_leads_search_id", "leads", ["search_id"])
    op.create_index("ix_leads_profile_url", "leads", ["linkedin_profile_url"])
    op.create_index("ix_leads_person_name", "leads", ["person_name"])
    op.create_index("ix_leads_company_name", "leads", ["company_name"])
    op.create_index("ix_leads_location", "leads", ["location"])


def downgrade() -> None:
    op.drop_index("ix_leads_location", table_name="leads")
    op.drop_index("ix_leads_company_name", table_name="leads")
    op.drop_index("ix_leads_person_name", table_name="leads")
    op.drop_index("ix_leads_profile_url", table_name="leads")
    op.drop_index("ix_leads_search_id", table_name="leads")
    op.drop_table("leads")
    op.drop_index("ix_search_runs_search_id", table_name="search_runs")
    op.drop_table("search_runs")
    op.drop_index("ix_searches_created_at", table_name="searches")
    op.drop_index("ix_searches_status", table_name="searches")
    op.drop_table("searches")
