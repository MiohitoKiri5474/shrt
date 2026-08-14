"""add shared_files kind check constraint

ecc385878bf8 (the migration that created shared_files) already shipped to
develop before this constraint was written — editing that revision in place
would be a no-op for any database that already ran it (Alembic tracks
applied revisions by ID and never re-runs a modified one). This is a
separate revision instead.

Uses batch mode: SQLite has no ALTER TABLE ADD CONSTRAINT, so batch mode
rebuilds the table under the hood there; on Postgres it's a plain ALTER.
Portable across both dialects this app supports (see ADR 0001).

Revision ID: ed728aa6f9fc
Revises: ecc385878bf8
Create Date: 2026-08-13 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ed728aa6f9fc'
down_revision: Union[str, Sequence[str], None] = 'ecc385878bf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('shared_files') as batch_op:
        batch_op.create_check_constraint('ck_shared_files_kind', "kind IN ('image', 'file')")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('shared_files') as batch_op:
        batch_op.drop_constraint('ck_shared_files_kind', type_='check')
