"""terms acceptance records for S1137.

Revision ID: bq_terms_acceptance_s1137
Revises: 9f4888486c2d
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "bq_terms_acceptance_s1137"
down_revision = "9f4888486c2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "terms_acceptance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("accepted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("terms_version", sa.Text(), nullable=False),
        sa.Column("terms_hash_sha256", sa.Text(), nullable=False),
        sa.Column("terms_url", sa.Text(), nullable=False),
        sa.Column("terms_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkbox_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("signer_full_name", sa.Text(), nullable=False),
        sa.Column("signer_title", sa.Text(), nullable=False),
        sa.Column("business_legal_name", sa.Text(), nullable=False),
        sa.Column("authority_ack", sa.Boolean(), nullable=False),
        sa.Column("ack_box1", sa.Boolean(), nullable=False),
        sa.Column("ack_box2", sa.Boolean(), nullable=False),
        sa.Column("ack_box3", sa.Boolean(), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("auth_session_id", sa.Text(), nullable=True),
        sa.Column("admin_initiated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("scope IN ('individual','organization')", name="ck_terms_acceptance_scope"),
        sa.CheckConstraint(
            "ack_box1 IS TRUE AND ack_box2 IS TRUE AND ack_box3 IS TRUE",
            name="ck_terms_acceptance_ack_boxes_true",
        ),
        sa.CheckConstraint(
            "btrim(signer_full_name) <> '' AND btrim(signer_title) <> '' AND btrim(business_legal_name) <> ''",
            name="ck_terms_acceptance_signature_nonempty",
        ),
        sa.CheckConstraint(
            "scope <> 'organization' OR authority_ack IS TRUE",
            name="ck_terms_acceptance_org_authority_ack",
        ),
        sa.CheckConstraint(
            "terms_published_at <= accepted_at",
            name="ck_terms_acceptance_published_before_accepted",
        ),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["party_id"], ["party.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_terms_acceptance_user_version", "terms_acceptance", ["accepted_by_user_id", "terms_version"])
    op.create_index("ix_terms_acceptance_party_version", "terms_acceptance", ["party_id", "terms_version"])
    op.create_index("ix_terms_acceptance_org_version", "terms_acceptance", ["org_id", "terms_version"])
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_terms_acceptance_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'terms_acceptance is append-only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_terms_acceptance_append_only
        BEFORE UPDATE OR DELETE ON terms_acceptance
        FOR EACH ROW
        EXECUTE FUNCTION prevent_terms_acceptance_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_terms_acceptance_append_only ON terms_acceptance")
    op.execute("DROP FUNCTION IF EXISTS prevent_terms_acceptance_mutation()")
    op.drop_index("ix_terms_acceptance_org_version", table_name="terms_acceptance")
    op.drop_index("ix_terms_acceptance_party_version", table_name="terms_acceptance")
    op.drop_index("ix_terms_acceptance_user_version", table_name="terms_acceptance")
    op.drop_table("terms_acceptance")
