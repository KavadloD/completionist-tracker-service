"""community: add thumbnail_url + community items

Revision ID: 745f8c5ac33d
Revises: 3d358b0510ed
Create Date: 2025-08-21 16:49:37.761131

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '745f8c5ac33d'
down_revision = '3d358b0510ed'
branch_labels = None
depends_on = None


def upgrade():
    # --- Community template items ---
    op.create_table(
        'community_checklist_item',
        sa.Column('community_item_id', sa.Integer(), nullable=False),
        sa.Column('community_checklist_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['community_checklist_id'],
            ['community_checklist.community_checklist_id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('community_item_id'),
        sa.UniqueConstraint('community_checklist_id', 'order', name='uq_comm_item_order')
    )

    # --- ChecklistItem: backfill + NOT NULL + keep unique + cascade FK ---
    # Backfill any NULLs before enforcing NOT NULL
    op.execute("UPDATE checklist_item SET completed = FALSE WHERE completed IS NULL")

    with op.batch_alter_table('checklist_item', schema=None) as batch_op:
        batch_op.alter_column(
            'completed',
            existing_type=sa.BOOLEAN(),
            nullable=False,
            server_default=sa.text('false')  # ensures DB-level default going forward
        )
        # unique (game_id, order) is fine:
        # (autogen added it already; leave as-is if present)
        # batch_op.create_unique_constraint('uq_checklist_order_per_game', ['game_id', 'order'])

        # Recreate FK with a stable name and ondelete CASCADE
        batch_op.drop_constraint(batch_op.f('checklist_item_game_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(
            'checklist_item_game_id_fkey',  # <-- give it a deterministic name
            'game',
            ['game_id'], ['game_id'],
            ondelete='CASCADE'
        )

    # --- CommunityChecklist: thumbnail_url ---
    with op.batch_alter_table('community_checklist', schema=None) as batch_op:
        batch_op.add_column(sa.Column('thumbnail_url', sa.Text(), nullable=True))

    # --- Game: media + timestamps ---
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cover_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('thumbnail_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))


def downgrade():
    # --- Game ---
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('thumbnail_url')
        batch_op.drop_column('cover_url')

    # --- CommunityChecklist ---
    with op.batch_alter_table('community_checklist', schema=None) as batch_op:
        batch_op.drop_column('thumbnail_url')

    # --- ChecklistItem ---
    with op.batch_alter_table('checklist_item', schema=None) as batch_op:
        # Drop our named FK and restore the original (no cascade)
        batch_op.drop_constraint('checklist_item_game_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            batch_op.f('checklist_item_game_id_fkey'),
            'game', ['game_id'], ['game_id']
        )
        batch_op.drop_constraint('uq_checklist_order_per_game', type_='unique')
        batch_op.alter_column('completed', existing_type=sa.BOOLEAN(), nullable=True, server_default=None)

    # --- Community template items ---
    op.drop_table('community_checklist_item')
