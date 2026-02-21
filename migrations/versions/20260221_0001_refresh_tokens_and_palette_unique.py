"""Add refresh tokens and palette uniqueness constraint

Revision ID: 20260221_0001
Revises:
Create Date: 2026-02-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260221_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "user" in table_names and "refresh_tokens" not in table_names:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("device_id", sa.String(length=120), nullable=False),
            sa.Column("device_name", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
        op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
        op.create_index("ix_refresh_tokens_device_id", "refresh_tokens", ["device_id"], unique=False)
        op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"], unique=False)
        op.create_index("ix_refresh_tokens_revoked_at", "refresh_tokens", ["revoked_at"], unique=False)
        op.create_index(
            "ix_refresh_tokens_user_device",
            "refresh_tokens",
            ["user_id", "device_id"],
            unique=False,
        )

    if "palette" in table_names:
        duplicate_groups = bind.execute(
            sa.text(
                """
                SELECT user_id, name
                FROM palette
                GROUP BY user_id, name
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        for user_id, name in duplicate_groups:
            duplicate_rows = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM palette
                    WHERE user_id = :user_id AND name = :name
                    ORDER BY id
                    """
                ),
                {"user_id": user_id, "name": name},
            ).fetchall()
            for row in duplicate_rows[1:]:
                bind.execute(
                    sa.text("UPDATE palette SET name = :new_name WHERE id = :palette_id"),
                    {"new_name": f"{name} {row.id}", "palette_id": row.id},
                )

        existing_constraints = {constraint.get("name") for constraint in inspector.get_unique_constraints("palette")}
        if "uq_palette_user_name" not in existing_constraints:
            with op.batch_alter_table("palette") as batch_op:
                batch_op.create_unique_constraint("uq_palette_user_name", ["user_id", "name"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "palette" in table_names:
        existing_constraints = {constraint.get("name") for constraint in inspector.get_unique_constraints("palette")}
        if "uq_palette_user_name" in existing_constraints:
            with op.batch_alter_table("palette") as batch_op:
                batch_op.drop_constraint("uq_palette_user_name", type_="unique")

    if "refresh_tokens" in table_names:
        for index_name in (
            "ix_refresh_tokens_user_device",
            "ix_refresh_tokens_revoked_at",
            "ix_refresh_tokens_expires_at",
            "ix_refresh_tokens_device_id",
            "ix_refresh_tokens_token_hash",
            "ix_refresh_tokens_user_id",
        ):
            op.drop_index(index_name, table_name="refresh_tokens")
        op.drop_table("refresh_tokens")
