"""إضافة مساحات عمل وعضويات وربط المحادثات بمساحة.

Revision ID: 0020_workspaces
Revises: 0019_conversation_shares
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_workspaces"
down_revision: Union[str, None] = "0019_conversation_shares"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_workspaces_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "name",
            name="uq_workspaces_owner_name",
        ),
    )
    op.create_index(
        "ix_workspaces_owner_id",
        "workspaces",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspaces_owner_id_created_at",
        "workspaces",
        ["owner_id", "created_at"],
        unique=False,
    )

    workspace_role = sa.Enum("owner", "admin", "member", name="workspacerole")
    workspace_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            workspace_role,
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_workspace_members_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_workspace_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
    )
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
        unique=False,
    )

    op.add_column(
        "conversations",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversations_workspace_id",
        "conversations",
        ["workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_workspace_id_workspaces",
        "conversations",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    bind = op.get_bind()
    user_rows = bind.execute(
        sa.text("SELECT id FROM users ORDER BY id")
    ).mappings().all()

    for row in user_rows:
        user_id = row["id"]
        workspace_id = bind.execute(
            sa.text(
                "INSERT INTO workspaces (owner_id, name) "
                "VALUES (:user_id, :name) RETURNING id"
            ),
            {"user_id": user_id, "name": "Personal"},
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO workspace_members "
                "(workspace_id, user_id, role) "
                "VALUES (:workspace_id, :user_id, 'owner')"
            ),
            {"workspace_id": workspace_id, "user_id": user_id},
        )
        bind.execute(
            sa.text(
                "UPDATE conversations SET workspace_id = :workspace_id "
                "WHERE user_id = :user_id AND workspace_id IS NULL"
            ),
            {"workspace_id": workspace_id, "user_id": user_id},
        )

    op.alter_column(
        "conversations",
        "workspace_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_workspace_id_workspaces",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index("ix_conversations_workspace_id", table_name="conversations")
    op.drop_column("conversations", "workspace_id")
    op.drop_index(
        "ix_workspace_members_user_id",
        table_name="workspace_members",
    )
    op.drop_table("workspace_members")
    op.drop_index(
        "ix_workspaces_owner_id_created_at",
        table_name="workspaces",
    )
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_table("workspaces")
    sa.Enum(name="workspacerole").drop(op.get_bind(), checkfirst=True)
