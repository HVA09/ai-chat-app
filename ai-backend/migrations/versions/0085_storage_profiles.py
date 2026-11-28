"""Record immutable storage backend identities for new uploads.
Revision ID: 0087_storage_profiles
Revises: 0086_storage_cleanup_lease_token
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "0087_storage_profiles"
down_revision: Union[str, None] = "0086_storage_cleanup_lease_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "storage_profiles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("bucket", sa.String(255), nullable=True),
        sa.Column("endpoint_url", sa.String(512), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("root_path", sa.String(1024), nullable=True),
        sa.Column("credential_ref", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("provider IN ('local', 's3')", name="ck_storage_profiles_provider"),
        sa.CheckConstraint("(provider = 'local' AND root_path IS NOT NULL AND bucket IS NULL) OR (provider = 's3' AND bucket IS NOT NULL AND endpoint_url IS NOT NULL AND region IS NOT NULL AND root_path IS NULL)", name="ck_storage_profiles_backend_identity"),
    )
    op.add_column("file_attachments", sa.Column("storage_profile_id", sa.String(64), nullable=True))
    op.create_foreign_key("fk_file_attachments_storage_profile_id_storage_profiles","file_attachments","storage_profiles",["storage_profile_id"],["id"],ondelete="RESTRICT")
    op.create_index("ix_file_attachments_storage_profile_id","file_attachments",["storage_profile_id"])

def downgrade() -> None:
    op.drop_index("ix_file_attachments_storage_profile_id", table_name="file_attachments")
    op.drop_constraint("fk_file_attachments_storage_profile_id_storage_profiles","file_attachments",type_="foreignkey")
    op.drop_column("file_attachments","storage_profile_id")
    op.drop_table("storage_profiles")
