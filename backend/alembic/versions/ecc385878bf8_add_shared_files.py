"""add shared_files table

Revision ID: ecc385878bf8
Revises: 01a6d9be959e
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecc385878bf8'
down_revision: Union[str, Sequence[str], None] = '01a6d9be959e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('shared_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('short_code', sa.String(length=16), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=255), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.String(length=512), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shared_files_id'), 'shared_files', ['id'], unique=False)
    op.create_index(op.f('ix_shared_files_short_code'), 'shared_files', ['short_code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_shared_files_short_code'), table_name='shared_files')
    op.drop_index(op.f('ix_shared_files_id'), table_name='shared_files')
    op.drop_table('shared_files')
