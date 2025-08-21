from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3d358b0510ed"
down_revision = None  # keep whatever was there before if different
branch_labels = None
depends_on = None

def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    res = bind.execute(
        sa.text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            LIMIT 1
        """),
        {"t": table, "c": col},
    ).scalar()
    return res is not None

def upgrade():
    # Add run_type to game (only if missing)
    if not _col_exists("game", "run_type"):
        with op.batch_alter_table("game", schema=None) as batch_op:
            batch_op.add_column(sa.Column("run_type", sa.String(length=100), nullable=True))

    # Add run_type to community_checklist (only if missing)
    if not _col_exists("community_checklist", "run_type"):
        with op.batch_alter_table("community_checklist", schema=None) as batch_op:
            batch_op.add_column(sa.Column("run_type", sa.String(length=100), nullable=True))

def downgrade():
    # Drop columns only if they exist (safe rollback)
    if _col_exists("community_checklist", "run_type"):
        with op.batch_alter_table("community_checklist", schema=None) as batch_op:
            batch_op.drop_column("run_type")

    if _col_exists("game", "run_type"):
        with op.batch_alter_table("game", schema=None) as batch_op:
            batch_op.drop_column("run_type")
