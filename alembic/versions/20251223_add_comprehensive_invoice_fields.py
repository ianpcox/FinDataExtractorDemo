"""Add comprehensive invoice fields

Revision ID: 20251223_add_fields
Revises: 20251218_add_concurrency_fields
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251223_add_fields'
down_revision = '20251218_add_concurrency_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add comprehensive invoice fields for Canadian invoicing"""
    
    # Header fields
    op.add_column('invoices', sa.Column('invoice_type', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('reference_number', sa.String(100), nullable=True))
    
    # Vendor contact fields
    op.add_column('invoices', sa.Column('vendor_fax', sa.String(), nullable=True))
    op.add_column('invoices', sa.Column('vendor_email', sa.String(), nullable=True))
    op.add_column('invoices', sa.Column('vendor_website', sa.String(), nullable=True))
    
    # Vendor tax registration
    op.add_column('invoices', sa.Column('gst_number', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('qst_number', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('pst_number', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('business_number', sa.String(50), nullable=True))
    
    # Customer contact fields
    op.add_column('invoices', sa.Column('customer_phone', sa.String(), nullable=True))
    op.add_column('invoices', sa.Column('customer_email', sa.String(), nullable=True))
    op.add_column('invoices', sa.Column('customer_fax', sa.String(), nullable=True))
    
    # Date fields
    op.add_column('invoices', sa.Column('shipping_date', sa.Date(), nullable=True))
    op.add_column('invoices', sa.Column('delivery_date', sa.Date(), nullable=True))
    
    # Financial fields
    op.add_column('invoices', sa.Column('discount_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('shipping_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('handling_fee', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('deposit_amount', sa.Numeric(18, 2), nullable=True))
    
    # Canadian tax fields with rates
    op.add_column('invoices', sa.Column('gst_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('gst_rate', sa.Numeric(5, 4), nullable=True))
    op.add_column('invoices', sa.Column('hst_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('hst_rate', sa.Numeric(5, 4), nullable=True))
    op.add_column('invoices', sa.Column('qst_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('qst_rate', sa.Numeric(5, 4), nullable=True))
    op.add_column('invoices', sa.Column('pst_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('invoices', sa.Column('pst_rate', sa.Numeric(5, 4), nullable=True))
    
    # Payment fields
    op.add_column('invoices', sa.Column('payment_method', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('payment_due_upon', sa.String(), nullable=True))


def downgrade():
    """Remove comprehensive invoice fields"""
    
    # Header fields
    op.drop_column('invoices', 'invoice_type')
    op.drop_column('invoices', 'reference_number')
    
    # Vendor contact
    op.drop_column('invoices', 'vendor_fax')
    op.drop_column('invoices', 'vendor_email')
    op.drop_column('invoices', 'vendor_website')
    
    # Vendor tax registration
    op.drop_column('invoices', 'gst_number')
    op.drop_column('invoices', 'qst_number')
    op.drop_column('invoices', 'pst_number')
    op.drop_column('invoices', 'business_number')
    
    # Customer contact
    op.drop_column('invoices', 'customer_phone')
    op.drop_column('invoices', 'customer_email')
    op.drop_column('invoices', 'customer_fax')
    
    # Dates
    op.drop_column('invoices', 'shipping_date')
    op.drop_column('invoices', 'delivery_date')
    
    # Financial
    op.drop_column('invoices', 'discount_amount')
    op.drop_column('invoices', 'shipping_amount')
    op.drop_column('invoices', 'handling_fee')
    op.drop_column('invoices', 'deposit_amount')
    
    # Canadian taxes
    op.drop_column('invoices', 'gst_amount')
    op.drop_column('invoices', 'gst_rate')
    op.drop_column('invoices', 'hst_amount')
    op.drop_column('invoices', 'hst_rate')
    op.drop_column('invoices', 'qst_amount')
    op.drop_column('invoices', 'qst_rate')
    op.drop_column('invoices', 'pst_amount')
    op.drop_column('invoices', 'pst_rate')
    
    # Payment
    op.drop_column('invoices', 'payment_method')
    op.drop_column('invoices', 'payment_due_upon')
