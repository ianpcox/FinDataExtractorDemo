"""add bill_to_address column"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_bill_to_address"
down_revision = "002_add_contact_remit_tax_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("invoices")]
    if "bill_to_address" not in cols:
        op.add_column("invoices", sa.Column("bill_to_address", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("invoices")]
    if "bill_to_address" in cols:
        op.drop_column("invoices", "bill_to_address")

