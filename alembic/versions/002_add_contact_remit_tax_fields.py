"""add contact, remit, standing offer, acceptance %, tax reg"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_add_contact_remit_tax_fields"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("vendor_phone", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("remit_to_address", sa.JSON(), nullable=True))
    op.add_column("invoices", sa.Column("remit_to_name", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("standing_offer_number", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("acceptance_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("invoices", sa.Column("tax_registration_number", sa.String(), nullable=True))


def downgrade():
    op.drop_column("invoices", "tax_registration_number")
    op.drop_column("invoices", "acceptance_percentage")
    op.drop_column("invoices", "standing_offer_number")
    op.drop_column("invoices", "remit_to_name")
    op.drop_column("invoices", "remit_to_address")
    op.drop_column("invoices", "vendor_phone")

