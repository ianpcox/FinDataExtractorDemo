"""add review_version and processing_state columns

Revision ID: 20251218_add_concurrency_fields
Revises: 
Create Date: 2025-12-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251218_add_concurrency_fields'
down_revision = '003_add_bill_to_address'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invoices', sa.Column('review_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('invoices', sa.Column('processing_state', sa.String(length=32), nullable=False, server_default='PENDING'))
    op.add_column('invoices', sa.Column('content_sha256', sa.String(length=128), nullable=True))
    # Note: SQLite doesn't support ALTER COLUMN DROP DEFAULT, so we leave server_default in place
    # The ORM default will be used for new rows; existing rows already have the backfilled value


def downgrade():
    op.drop_column('invoices', 'content_sha256')
    op.drop_column('invoices', 'processing_state')
    op.drop_column('invoices', 'review_version')

