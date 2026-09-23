"""initial schema: users, change_requests, approvals, audit_events

Revision ID: 0001
Revises:
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("REQUESTER", "REVIEWER", "ADMIN", name="user_role", create_type=False)
risk_level = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="risk_level", create_type=False)
change_stage = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "ENGINEERING_REVIEW",
    "MANUFACTURING_REVIEW",
    "APPROVED",
    "REJECTED",
    name="change_stage",
    create_type=False,
)
decision = postgresql.ENUM(
    "APPROVE", "REJECT", "REQUEST_CHANGES", name="decision", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)
    change_stage.create(bind, checkfirst=True)
    decision.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("vehicle_program", sa.Text(), nullable=False),
        sa.Column("subsystem", sa.Text(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("current_stage", change_stage, nullable=False),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_key"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_change_requests_current_stage"), "change_requests", ["current_stage"], unique=False
    )
    op.create_index(
        op.f("ix_change_requests_requester_id"), "change_requests", ["requester_id"], unique=False
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("stage", change_stage, nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", decision, nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["change_request_id"], ["change_requests.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
    )
    op.create_index(
        op.f("ix_approvals_change_request_id"), "approvals", ["change_request_id"], unique=False
    )
    op.create_index(op.f("ix_approvals_reviewer_id"), "approvals", ["reviewer_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_request_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("from_stage", change_stage, nullable=True),
        sa.Column("to_stage", change_stage, nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["change_request_id"], ["change_requests.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
    )
    op.create_index(
        "ix_audit_events_change_request_id_created_at",
        "audit_events",
        ["change_request_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("approvals")
    op.drop_table("change_requests")
    op.drop_table("users")

    bind = op.get_bind()
    decision.drop(bind, checkfirst=True)
    change_stage.drop(bind, checkfirst=True)
    risk_level.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
