"""Initial migration - simplified invoice schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='processing'),
        
        # Extracted Data - Header
        sa.Column('invoice_number', sa.String(length=100), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('vendor_name', sa.String(), nullable=True),
        sa.Column('vendor_id', sa.String(), nullable=True),
        sa.Column('vendor_address', sa.JSON(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('entity', sa.String(), nullable=True),
        sa.Column('contract_id', sa.String(), nullable=True),
        sa.Column('po_number', sa.String(length=100), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('tax_breakdown', sa.JSON(), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='CAD'),
        sa.Column('payment_terms', sa.String(), nullable=True),
        
        # Line items (stored as JSON)
        sa.Column('line_items', sa.JSON(), nullable=True),
        
        # Subtype and Extensions
        sa.Column('invoice_subtype', sa.String(length=50), nullable=True),
        sa.Column('extensions', sa.JSON(), nullable=True),
        
        # Metadata
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('field_confidence', sa.JSON(), nullable=True),
        sa.Column('extraction_timestamp', sa.DateTime(), nullable=True),
        
        # Review
        sa.Column('review_status', sa.String(length=50), nullable=True),
        sa.Column('reviewer', sa.String(length=100), nullable=True),
        sa.Column('review_timestamp', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        
        # Approval workflow
        sa.Column('bv_approver', sa.String(length=100), nullable=True),
        sa.Column('bv_approval_date', sa.DateTime(), nullable=True),
        sa.Column('bv_approval_notes', sa.Text(), nullable=True),
        sa.Column('fa_approver', sa.String(length=100), nullable=True),
        sa.Column('fa_approval_date', sa.DateTime(), nullable=True),
        sa.Column('fa_approval_notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_invoices_po_number'), 'invoices', ['po_number'], unique=False)
    op.create_index(op.f('ix_invoices_status'), 'invoices', ['status'], unique=False)
    op.create_index(op.f('ix_invoices_upload_date'), 'invoices', ['upload_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoices_upload_date'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_status'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_po_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_table('invoices')

