from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "745f8c5ac33d"
down_revision = "3d358b0510ed"
branch_labels = None
depends_on = None

def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            LIMIT 1
        """),
        {"t": table, "c": col},
    ).scalar() is not None

def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :t
            LIMIT 1
        """),
        {"t": table},
    ).scalar() is not None

def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n LIMIT 1"),
        {"n": name},
    ).scalar() is not None

def _is_nullable(table: str, col: str) -> bool:
    bind = op.get_bind()
    val = bind.execute(
        sa.text("""
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            LIMIT 1
        """),
        {"t": table, "c": col},
    ).scalar()
    return (val or "").upper() == "YES"

def upgrade():
    # --- CommunityChecklistItem table (create only if missing) ---
    if not _table_exists("community_checklist_item"):
        op.create_table(
            "community_checklist_item",
            sa.Column("community_item_id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("community_checklist_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["community_checklist_id"],
                ["community_checklist.community_checklist_id"],
                ondelete="CASCADE",
            ),
        )
    # unique (community_checklist_id, order)
    if not _constraint_exists("uq_comm_item_order"):
        op.create_unique_constraint(
            "uq_comm_item_order",
            "community_checklist_item",
            ["community_checklist_id", "order"],
        )

    # --- ChecklistItem.completed: backfill + default + NOT NULL (all idempotent) ---
    if _col_exists("checklist_item", "completed"):
        op.execute("UPDATE checklist_item SET completed = FALSE WHERE completed IS NULL")
        # default false (ignore if already set)
        try:
            op.execute("ALTER TABLE checklist_item ALTER COLUMN completed SET DEFAULT FALSE")
        except Exception:
            pass
        # set NOT NULL only if nullable
        if _is_nullable("checklist_item", "completed"):
            with op.batch_alter_table("checklist_item") as batch_op:
                batch_op.alter_column(
                    "completed",
                    existing_type=sa.Boolean(),
                    nullable=False,
                )

    # --- CommunityChecklist.thumbnail_url ---
    if not _col_exists("community_checklist", "thumbnail_url"):
        with op.batch_alter_table("community_checklist") as batch_op:
            batch_op.add_column(sa.Column("thumbnail_url", sa.Text(), nullable=True))

    # --- Game: cover_url, thumbnail_url, created_at, updated_at ---
    if not _col_exists("game", "cover_url"):
        with op.batch_alter_table("game") as batch_op:
            batch_op.add_column(sa.Column("cover_url", sa.Text(), nullable=True))
    if not _col_exists("game", "thumbnail_url"):
        with op.batch_alter_table("game") as batch_op:
            batch_op.add_column(sa.Column("thumbnail_url", sa.Text(), nullable=True))
    if not _col_exists("game", "created_at"):
        with op.batch_alter_table("game") as batch_op:
            batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
    if not _col_exists("game", "updated_at"):
        with op.batch_alter_table("game") as batch_op:
            batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))

def downgrade():
    # Drop unique & table (guarded)
    if _constraint_exists("uq_comm_item_order"):
        op.drop_constraint("uq_comm_item_order", "community_checklist_item", type_="unique")
    if _table_exists("community_checklist_item"):
        op.drop_table("community_checklist_item")

    # Drop community_checklist.thumbnail_url if present
    if _col_exists("community_checklist", "thumbnail_url"):
        with op.batch_alter_table("community_checklist") as batch_op:
            batch_op.drop_column("thumbnail_url")

    # ChecklistItem.completed back to nullable (guarded)
    if _col_exists("checklist_item", "completed") and not _is_nullable("checklist_item", "completed"):
        with op.batch_alter_table("checklist_item") as batch_op:
            batch_op.alter_column("completed", existing_type=sa.Boolean(), nullable=True)

    # Drop game columns if present
    for c in ("updated_at", "created_at", "thumbnail_url", "cover_url"):
        if _col_exists("game", c):
            with op.batch_alter_table("game") as batch_op:
                batch_op.drop_column(c)
